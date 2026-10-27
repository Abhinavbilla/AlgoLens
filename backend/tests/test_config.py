import pytest
from pydantic import ValidationError

from algolens.config import Settings


def test_defaults_are_valid():
    s = Settings(_env_file=None)
    assert s.max_tokens_per_problem == 0  # no cap
    assert s.max_repair_rounds == 2
    assert s.model_brute_a != s.model_brute_b


def test_token_budget_is_configurable(monkeypatch):
    monkeypatch.setenv("ALGOLENS_MAX_TOKENS_PER_PROBLEM", "50000")
    assert Settings(_env_file=None).max_tokens_per_problem == 50_000


def test_token_budget_cannot_be_negative(monkeypatch):
    monkeypatch.setenv("ALGOLENS_MAX_TOKENS_PER_PROBLEM", "-1")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_brute_forces_must_use_different_models(monkeypatch):
    monkeypatch.setenv("ALGOLENS_MODEL_BRUTE_A", "gemini:gemini-3.8-flash")
    monkeypatch.setenv("ALGOLENS_MODEL_BRUTE_B", "gemini:gemini-3.8-flash")
    with pytest.raises(ValidationError, match="must be different models"):
        Settings(_env_file=None)


def test_default_brute_b_is_another_provider():
    s = Settings(_env_file=None)
    assert s.model_brute_a.split(":")[0] != s.model_brute_b.split(":")[0]
