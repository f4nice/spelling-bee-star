from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT_DIR = Path(__file__).resolve().parent.parent
HOST_ROOT_DIR = ROOT_DIR.parent


def load_env_file(path: Path | None = None) -> None:
    env_paths = [path] if path else [HOST_ROOT_DIR / ".env", ROOT_DIR / ".env"]

    for env_path in env_paths:
        if not env_path or not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class MySQLConfig:
    enabled: bool
    host: str
    port: int
    database: str
    user: str
    password: str
    charset: str = "utf8mb4"


def _config_from_database_url(database_url: str | None, *, enabled: bool) -> MySQLConfig | None:
    if not database_url:
        return None

    parsed = urlparse(database_url)
    if not parsed.scheme.startswith("mysql") or not parsed.hostname:
        return None

    database = (parsed.path or "").lstrip("/")
    if not database:
        return None

    charset = parse_qs(parsed.query).get("charset", ["utf8mb4"])[0] or "utf8mb4"
    return MySQLConfig(
        enabled=enabled,
        host=parsed.hostname,
        port=parsed.port or 3306,
        database=database,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        charset=charset,
    )


def get_mysql_config() -> MySQLConfig:
    load_env_file()
    enabled = _truthy(os.getenv("BOOKLEARNER_MYSQL_ENABLED"))
    if _truthy(os.getenv("BOOKLEARNER_MYSQL_USE_DATABASE_URL")):
        database_url_config = _config_from_database_url(os.getenv("DATABASE_URL"), enabled=enabled)
        if database_url_config is not None:
            return database_url_config

    return MySQLConfig(
        enabled=enabled,
        host=os.getenv("BOOKLEARNER_MYSQL_HOST", "127.0.0.1"),
        port=_env_int("BOOKLEARNER_MYSQL_PORT", 3306),
        database=os.getenv("BOOKLEARNER_MYSQL_DATABASE", "booklearner"),
        user=os.getenv("BOOKLEARNER_MYSQL_USER", ""),
        password=os.getenv("BOOKLEARNER_MYSQL_PASSWORD", ""),
        charset=os.getenv("BOOKLEARNER_MYSQL_CHARSET", "utf8mb4"),
    )


@dataclass(frozen=True)
class MySQLAdminConfig:
    host: str
    port: int
    user: str
    password: str


def get_mysql_admin_config() -> MySQLAdminConfig:
    load_env_file()
    app_config = get_mysql_config()
    return MySQLAdminConfig(
        host=app_config.host,
        port=app_config.port,
        user=os.getenv("BOOKLEARNER_MYSQL_ADMIN_USER", "root"),
        password=os.getenv("BOOKLEARNER_MYSQL_ADMIN_PASSWORD", ""),
    )
