from __future__ import annotations

import importlib.util
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def build_database_config(*, env, base_dir: Path) -> dict[str, dict]:
    """Build the sole database configuration from environment variables."""

    database_url = env("DATABASE_URL", default="").strip()
    default_engine = "postgresql" if database_url else "sqlite"
    selected_engine = env("DATABASE_ENGINE", default=default_engine).strip().lower()

    if selected_engine in {"sqlite", "sqlite3"}:
        configured_path = env("SQLITE_PATH", default="db.sqlite3").strip()
        if not configured_path:
            raise ImproperlyConfigured("SQLITE_PATH cannot be empty when SQLite is selected")
        if configured_path == ":memory:":
            database_name: str | Path = configured_path
        else:
            database_path = Path(configured_path).expanduser()
            database_name = (
                database_path if database_path.is_absolute() else base_dir / database_path
            )
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": database_name,
                "CONN_MAX_AGE": 0,
                "OPTIONS": {"timeout": env.int("SQLITE_TIMEOUT_SECONDS", default=20)},
            }
        }

    if selected_engine in {"postgres", "postgresql", "postgresql_psycopg"}:
        if importlib.util.find_spec("psycopg") is None:
            raise ImproperlyConfigured(
                'PostgreSQL is selected but its driver is not installed. Install ".[postgres]".'
            )
        if database_url:
            database = env.db_url("DATABASE_URL")
            if database["ENGINE"] != "django.db.backends.postgresql":
                raise ImproperlyConfigured(
                    "DATABASE_URL must be a PostgreSQL URL when DATABASE_ENGINE=postgresql"
                )
        else:
            name = env("DB_NAME", default="").strip()
            user = env("DB_USER", default="").strip()
            if not name or not user:
                raise ImproperlyConfigured(
                    "DB_NAME and DB_USER are required when PostgreSQL is selected without "
                    "DATABASE_URL"
                )
            database = {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": name,
                "USER": user,
                "PASSWORD": env("DB_PASSWORD", default=""),
                "HOST": env("DB_HOST", default="localhost"),
                "PORT": env("DB_PORT", default="5432"),
            }
        database["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)
        database["CONN_HEALTH_CHECKS"] = env.bool("DATABASE_CONN_HEALTH_CHECKS", default=True)
        return {"default": database}

    raise ImproperlyConfigured(
        f"Unsupported DATABASE_ENGINE {selected_engine!r}; choose 'sqlite' or 'postgresql'"
    )
