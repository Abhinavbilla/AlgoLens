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
# Largest output to ask for. Groq's free tier counts prompt + max_tokens against 8000 tokens a
# minute, and solutions here are far shorter than this.
MAX_OUTPUT = {"groq": 4096}
MAX_WAIT_S = 120  # a provider asking us to wait longer than this has run out of quota
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
class TextReply:
    text: str
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

    def complete_text(
        self, role: str, system: str, messages: list[dict], budget: Budget, max_tokens: int = 1200
    ) -> TextReply:
        """A plain-prose reply to a conversation ([{"role": "user"|"assistant", "content"}]),
        for the tutor. Same pacing, retries and budget as complete_json."""
        provider, model = parse_role(self.roles[role])
        size = len(system) + sum(len(m["content"]) for m in messages)
        with budget.reserve(size // 3 + max_tokens, stage=role) as charge:
            if provider == "fake":
                if self.fake is None:
                    raise AIUnavailable("no fake responses configured")
                transcript = "\n\n".join(f"{m['role']}: {m['content']}" for m in messages)
                text = str(self.fake(role, system, transcript).get("text", ""))
                reply = TextReply(text, size // 4, len(text) // 4, model)
            else:
                reply = self._call_text(provider, model, system, messages, max_tokens)
            charge(reply.input_tokens + reply.output_tokens)
            return reply

    # --- providers ---------------------------------------------------------------------------

    def _send(self, provider, model, system, messages, max_tokens, json_mode, attempt):
        """One paced request: (text, usage), or a _Retryable to wait out and try again."""
        _pacer(provider).wait()
        try:
            if provider == "anthropic":
                return self._anthropic(model, system, messages, max_tokens, json_mode)
            return self._openai_compatible(provider, model, system, messages, max_tokens, json_mode)
        except _Retryable as exc:
            if exc.wait > MAX_WAIT_S:
                minutes = round(exc.wait / 60)
                raise AIError(
                    f"{provider} rate limit for {model}: try again in about {minutes} min "
                    f"({_quota_message(str(exc))})"
                ) from exc
            time.sleep(exc.wait if exc.wait else min(60, 2 ** (attempt + 1)))
            return exc

    def _call_text(self, provider, model, system, messages, max_tokens) -> TextReply:
        last_error = "no attempt"
        for attempt in range(RETRIES):
            sent = self._send(provider, model, system, messages, max_tokens, False, attempt)
            if isinstance(sent, _Retryable):
                last_error = str(sent)
                continue
            text, usage = sent
            # Reasoning models (Qwen, DeepSeek) may think out loud first: keep only the answer.
            text = re.sub(r"<think>.*?(</think>|$)", "", text, flags=re.DOTALL).strip()
            if text:
                return TextReply(text, usage[0], usage[1], model)
            last_error = "empty reply"
        raise AIError(f"{provider} failed after {RETRIES} attempts: {last_error}")

    def _call(self, provider: str, model: str, system: str, prompt: str, max_tokens: int) -> Reply:
        last_error = "no attempt"
        for attempt in range(RETRIES):
            messages = [{"role": "user", "content": prompt}]
            sent = self._send(provider, model, system, messages, max_tokens, True, attempt)
            if isinstance(sent, _Retryable):
                last_error = str(sent)
                continue
            text, usage = sent
            data = extract_json(text)
            if data is not None:
                return Reply(data, usage[0], usage[1], model)
            last_error = f"reply wasn't a JSON object: {text[:200]!r}"
            prompt += "\n\nYour previous reply was not one valid JSON object. Reply with JSON only."
        raise AIError(f"{provider} failed after {RETRIES} attempts: {last_error}")

    def _openai_compatible(self, provider, model, system, messages, max_tokens, json_mode=True):
        base, key_name = ENDPOINTS[provider]
        key = os.environ.get(key_name)
        if not key:
            raise AIUnavailable(f"{key_name} is not set")
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system}, *messages],
            "max_tokens": min(max_tokens, MAX_OUTPUT.get(provider, max_tokens)),
            "temperature": 0.2 if json_mode else 0.4,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {key}"}
        last = ""
        for _ in range(3):
            try:
                resp = self._post(f"{base}/chat/completions", body, headers)
                break
            except (_Retryable, AIError) as exc:
                last = str(exc)
                smaller = _fitting_max_tokens(str(exc), body["max_tokens"])
                if smaller is not None:
                    body["max_tokens"] = smaller
                elif "json_validate_failed" in str(exc) and "response_format" in body:
                    # The provider's strict JSON mode rejected the model's own reply (Groq).
                    # Ask again without it: extract_json() still checks the reply.
                    body.pop("response_format")
                else:
                    raise
        else:
            raise AIError(f"{provider} kept rejecting the request size for {model}: {last[:300]}")
        choice = resp["choices"][0]["message"].get("content") or ""
        usage = resp.get("usage") or {}
        return choice, (usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))

    def _anthropic(self, model, system, messages, max_tokens, json_mode=True):
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise AIUnavailable("ANTHROPIC_API_KEY is not set")
        if json_mode:
            system += "\nReply with a single JSON object and nothing else."
        body = {
            "model": model,
            "system": system,
            "messages": messages,
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
            raise _Retryable(f"HTTP {r.status_code}: {r.text[:400]}", seconds)
        if r.status_code in (401, 403):
            raise AIUnavailable(f"the AI service refused the key (HTTP {r.status_code})")
        if r.status_code >= 400:
            raise AIError(f"HTTP {r.status_code}: {r.text[:500]}")
        return r.json()

    def close(self) -> None:
        self._http.close()


MIN_OUTPUT_TOKENS = 1500


def _fitting_max_tokens(error: str, max_tokens: int) -> int | None:
    """A smaller max_tokens when the provider says the request can never fit its per-minute
    limit (Groq: "Request too large ... (TPM): Limit 8000, Requested 8166", or the output-only
    OTPM limit); None if that isn't the problem or nothing useful would fit."""
    if "Request too large" not in error:
        return None
    m = re.search(r"\((O?TPM)\): Limit (\d+), Requested (\d+)", error)
    if not m:
        return None
    kind, limit, requested = m.group(1), int(m.group(2)), int(m.group(3))
    new = limit - 16 if kind == "OTPM" else max_tokens - (requested - limit) - 64
    return new if MIN_OUTPUT_TOKENS <= new < max_tokens else None


def _quota_message(error: str) -> str:
    """The provider's own explanation, e.g. "tokens per day (TPD): Limit 200000"."""
    m = re.search(r'"message":\s*"([^"]{0,200})', error)
    return m.group(1) if m else error[:200]


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
    roles["explain"] = s.model_explain or s.model_narration
    roles["tutor"] = s.model_tutor or s.model_narration
    return AIClient(roles, fake=fake)


def roles_fingerprint(roles: dict[str, str]) -> str:
    return ",".join(f"{k}={v}" for k, v in sorted(roles.items()))


__all__ = [
    "AIClient",
    "AIError",
    "AIUnavailable",
    "Reply",
    "TextReply",
    "client_from_settings",
    "extract_json",
]
