import pytest
from pydantic import ValidationError

from algolens.config import Settings


def test_defaults_are_valid():
    s = Settings(_env_file=None)
    assert s.max_tokens_per_problem == 200_000
    assert s.max_repair_rounds == 2
    assert s.model_brute_a != s.model_brute_b


def test_token_budget_is_configurable(monkeypatch):
    monkeypatch.setenv("ALGOLENS_MAX_TOKENS_PER_PROBLEM", "50000")
    assert Settings(_env_file=None).max_tokens_per_problem == 50_000


@pytest.mark.parametrize("value", ["0", "-1"])
def test_token_budget_must_be_positive(monkeypatch, value):
    monkeypatch.setenv("ALGOLENS_MAX_TOKENS_PER_PROBLEM", value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_brute_forces_must_use_different_models(monkeypatch):
    monkeypatch.setenv("ALGOLENS_MODEL_BRUTE_A", "claude-opus-5-5")
    monkeypatch.setenv("ALGOLENS_MODEL_BRUTE_B", "claude-opus-5-5")
    with pytest.raises(ValidationError, match="must be different models"):
        Settings(_env_file=None)


def test_api_key_accepts_standard_variable(monkeypatch):
    monkeypatch.delenv("ALGOLENS_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert Settings(_env_file=None).anthropic_api_key == "sk-test"
