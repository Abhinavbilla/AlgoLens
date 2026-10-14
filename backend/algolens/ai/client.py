"""Provider-neutral AI client (plan §2, decided after M4: free Gemini + Groq to start).

Each pipeline role (parse, brute_a, brute_b, approaches, checker, repair, narration) is
configured as "provider:model", e.g. "gemini:gemini-2.5-flash" or "groq:openai/gpt-oss-120b".
Every call asks for a JSON object and returns it parsed, plus the tokens used. Providers:

    gemini     Google's OpenAI-compatible endpoint     GEMINI_API_KEY
    groq       Groq's OpenAI-compatible endpoint       GROQ_API_KEY
    openai     any other OpenAI-compatible endpoint    OPENAI_API_KEY (+ OPENAI_BASE_URL)
    anthropic  the Messages API                        ANTHROPIC_API_KEY
    fake       scripted responses, for tests

Free tiers are rate-limited, so calls are spaced per provider and 429s / 5xx are retried
with backoff (honouring Retry-After). Every call is charged to the problem's token budget.
"""

import json
import os
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

from algolens.ai.budget import Budget

ENDPOINTS = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "openai": (os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"), "OPENAI_API_KEY"),
}
# Minimum seconds between calls to one provider (free tiers: Gemini ~15/min, Groq ~30/min).
MIN_INTERVAL = {"gemini": 4.2, "groq": 2.1, "openai": 0.0, "anthropic": 0.0, "fake": 0.0}
RETRIES = 5
TIMEOUT_S = 180


class AIError(RuntimeError):
    """The AI service failed (unreachable, refused, or kept returning unusable output)."""


class AIUnavailable(AIError):
    """No usable configuration or the service is down: new problems can't be processed."""


@dataclass
class Reply:
    data: dict
    input_tokens: int
    output_tokens: int
    model: str


@dataclass
class _Pacer:
    interval: float
    lock: threading.Lock = field(default_factory=threading.Lock)
    last: float = 0.0

    def wait(self) -> None:
        with self.lock:
            delay = self.last + self.interval - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self.last = time.monotonic()


_pacers: dict[str, _Pacer] = {}


def _pacer(provider: str) -> _Pacer:
    if provider not in _pacers:
        _pacers[provider] = _Pacer(MIN_INTERVAL.get(provider, 0.0))
    return _pacers[provider]


def parse_role(spec: str) -> tuple[str, str]:
    provider, sep, model = spec.partition(":")
    if not sep or not model or provider not in (*ENDPOINTS, "anthropic", "fake"):
        raise AIUnavailable(f"bad model setting {spec!r}; expected provider:model")
    return provider, model


class AIClient:
    """Calls the model configured for a role and returns a JSON object."""

    def __init__(self, roles: dict[str, str], fake: Callable[[str, str, str], dict] | None = None):
        self.roles = roles
        self.fake = fake  # (role, system, prompt) -> dict, for tests
        self._http = httpx.Client(timeout=TIMEOUT_S)

    def complete_json(
        self, role: str, system: str, prompt: str, budget: Budget, max_tokens: int = 8000
    ) -> Reply:
        provider, model = parse_role(self.roles[role])
        estimate = (len(system) + len(prompt)) // 3 + max_tokens
        with budget.reserve(estimate, stage=role) as charge:
            if provider == "fake":
                if self.fake is None:
                    raise AIUnavailable("no fake responses configured")
                data = self.fake(role, system, prompt)
                reply = Reply(
                    data, (len(system) + len(prompt)) // 4, len(json.dumps(data)) // 4, model
                )
            else:
                reply = self._call(provider, model, system, prompt, max_tokens)
            charge(reply.input_tokens + reply.output_tokens)
            return reply

    # --- providers ---------------------------------------------------------------------------

    def _call(self, provider: str, model: str, system: str, prompt: str, max_tokens: int) -> Reply:
        last_error = "no attempt"
        for attempt in range(RETRIES):
            _pacer(provider).wait()
            try:
                if provider == "anthropic":
                    text, usage = self._anthropic(model, system, prompt, max_tokens)
                else:
                    text, usage = self._openai_compatible(
                        provider, model, system, prompt, max_tokens
                    )
            except _Retryable as exc:
                last_error = str(exc)
                time.sleep(exc.wait if exc.wait else min(60, 2 ** (attempt + 1)))
                continue
            data = extract_json(text)
            if data is not None:
                return Reply(data, usage[0], usage[1], model)
            last_error = f"reply wasn't a JSON object: {text[:200]!r}"
            prompt += "\n\nYour previous reply was not one valid JSON object. Reply with JSON only."
        raise AIError(f"{provider} failed after {RETRIES} attempts: {last_error}")

    def _openai_compatible(self, provider, model, system, prompt, max_tokens):
        base, key_name = ENDPOINTS[provider]
        key = os.environ.get(key_name)
        if not key:
            raise AIUnavailable(f"{key_name} is not set")
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        resp = self._post(f"{base}/chat/completions", body, {"Authorization": f"Bearer {key}"})
        choice = resp["choices"][0]["message"].get("content") or ""
        usage = resp.get("usage") or {}
        return choice, (usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))

    def _anthropic(self, model, system, prompt, max_tokens):
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise AIUnavailable("ANTHROPIC_API_KEY is not set")
        body = {
            "model": model,
            "system": system + "\nReply with a single JSON object and nothing else.",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        resp = self._post("https://api.anthropic.com/v1/messages", body, headers)
        text = "".join(
            b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text"
        )
        usage = resp.get("usage") or {}
        return text, (usage.get("input_tokens", 0), usage.get("output_tokens", 0))

    def _post(self, url: str, body: dict, headers: dict) -> dict:
        try:
            r = self._http.post(url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise _Retryable(f"network error: {exc}") from exc
        if r.status_code == 429 or r.status_code >= 500:
            wait = r.headers.get("retry-after") or ""
            seconds = float(wait) if wait.replace(".", "").isdigit() else 0
            raise _Retryable(f"HTTP {r.status_code}: {r.text[:200]}", seconds)
        if r.status_code in (401, 403):
            raise AIUnavailable(f"the AI service refused the key (HTTP {r.status_code})")
        if r.status_code >= 400:
            raise AIError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    def close(self) -> None:
        self._http.close()


class _Retryable(Exception):
    def __init__(self, message: str, wait: float = 0):
        super().__init__(message)
        self.wait = wait


def extract_json(text: str) -> dict | None:
    """The JSON object in a reply, tolerating code fences or a little text around it."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    candidates = [fenced.group(1)] if fenced else []
    candidates.append(text)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for c in candidates:
        try:
            value = json.loads(c)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def client_from_settings(fake: Callable[[str, str, str], dict] | None = None) -> AIClient:
    from algolens.config import get_settings

    s = get_settings()
    names = ("parse", "brute_a", "brute_b", "approaches", "checker", "repair", "narration")
    roles = {r: getattr(s, f"model_{r}") for r in names}
    return AIClient(roles, fake=fake)


def roles_fingerprint(roles: dict[str, str]) -> str:
    return ",".join(f"{k}={v}" for k, v in sorted(roles.items()))


__all__ = ["AIClient", "AIError", "AIUnavailable", "Reply", "client_from_settings", "extract_json"]
