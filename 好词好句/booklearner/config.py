from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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


@dataclass(frozen=True)
class MySQLConfig:
    enabled: bool
    host: str
    port: int
    database: str
    user: str
    password: str
    charset: str = "utf8mb4"


def get_mysql_config() -> MySQLConfig:
    load_env_file()
    return MySQLConfig(
        enabled=_truthy(os.getenv("BOOKLEARNER_MYSQL_ENABLED")),
        host=os.getenv("BOOKLEARNER_MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("BOOKLEARNER_MYSQL_PORT", "3306")),
        database=os.getenv("BOOKLEARNER_MYSQL_DATABASE", "booklearner"),
        user=os.getenv("BOOKLEARNER_MYSQL_USER", ""),
        password=os.getenv("BOOKLEARNER_MYSQL_PASSWORD", ""),
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
