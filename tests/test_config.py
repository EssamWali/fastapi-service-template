"""Settings parsing, which is only exercised for real when the process boots.

The rest of the suite constructs Settings directly, so it never goes through the
environment source - which is exactly where the comma-separated key list broke.
"""

import pytest

from app.config import Settings


def test_api_keys_parse_from_a_comma_separated_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_API_KEYS", "key-one,key-two , key-three")
    settings = Settings(_env_file=None)
    assert settings.api_keys == ["key-one", "key-two", "key-three"]


def test_single_api_key_still_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_API_KEYS", "only-key")
    assert Settings(_env_file=None).api_keys == ["only-key"]


def test_settings_read_the_app_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("APP_CACHE_TTL_SECONDS", "900")
    settings = Settings(_env_file=None)
    assert settings.env == "staging"
    assert settings.cache_ttl_seconds == 900
    assert settings.is_prod is False
