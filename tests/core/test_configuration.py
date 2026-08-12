from pathlib import Path

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings.database import build_database_config

DATABASE_VARIABLES = [
    "DATABASE_ENGINE",
    "DATABASE_URL",
    "SQLITE_PATH",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "DB_PORT",
]


def clean_database_environment(monkeypatch) -> None:
    for variable in DATABASE_VARIABLES:
        monkeypatch.delenv(variable, raising=False)


def test_database_configuration_defaults_to_sqlite(monkeypatch, tmp_path):
    clean_database_environment(monkeypatch)

    configured = build_database_config(env=environ.Env(), base_dir=tmp_path)["default"]

    assert configured["ENGINE"] == "django.db.backends.sqlite3"
    assert configured["NAME"] == tmp_path / "db.sqlite3"
    assert configured["CONN_MAX_AGE"] == 0


def test_database_configuration_supports_explicit_postgresql(monkeypatch, tmp_path):
    clean_database_environment(monkeypatch)
    monkeypatch.setattr(
        "config.settings.database.importlib.util.find_spec", lambda package: object()
    )
    monkeypatch.setenv("DATABASE_ENGINE", "postgresql")
    monkeypatch.setenv("DB_NAME", "foundation")
    monkeypatch.setenv("DB_USER", "foundation_user")
    monkeypatch.setenv("DB_PASSWORD", "not-a-real-secret")
    monkeypatch.setenv("DB_HOST", "database.internal")
    monkeypatch.setenv("DB_PORT", "5433")

    configured = build_database_config(env=environ.Env(), base_dir=tmp_path)["default"]

    assert configured == {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "foundation",
        "USER": "foundation_user",
        "PASSWORD": "not-a-real-secret",
        "HOST": "database.internal",
        "PORT": "5433",
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }


def test_database_configuration_rejects_unknown_engine(monkeypatch, tmp_path):
    clean_database_environment(monkeypatch)
    monkeypatch.setenv("DATABASE_ENGINE", "unknown")

    with pytest.raises(ImproperlyConfigured, match="Unsupported DATABASE_ENGINE"):
        build_database_config(env=environ.Env(), base_dir=tmp_path)


def test_postgresql_selection_explains_missing_optional_driver(monkeypatch, tmp_path):
    clean_database_environment(monkeypatch)
    monkeypatch.setenv("DATABASE_ENGINE", "postgresql")
    monkeypatch.setattr("config.settings.database.importlib.util.find_spec", lambda package: None)

    with pytest.raises(ImproperlyConfigured, match=r"Install.*postgres"):
        build_database_config(env=environ.Env(), base_dir=tmp_path)


def test_sqlite_absolute_path_is_preserved(monkeypatch, tmp_path):
    clean_database_environment(monkeypatch)
    database_path = (tmp_path / "custom.sqlite3").resolve()
    monkeypatch.setenv("DATABASE_ENGINE", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", str(database_path))

    configured = build_database_config(env=environ.Env(), base_dir=Path("unused"))["default"]

    assert configured["NAME"] == database_path
