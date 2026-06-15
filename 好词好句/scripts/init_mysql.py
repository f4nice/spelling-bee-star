from __future__ import annotations

import importlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from booklearner.config import ROOT_DIR, get_mysql_admin_config, get_mysql_config


SCHEMA_PATH = ROOT_DIR / "database" / "schema.sql"


def main() -> None:
    connector = _mysql_connector()
    if connector is None:
        raise SystemExit("mysql-connector-python is missing. Run: py -m pip install -r requirements.txt")

    admin_config = get_mysql_admin_config()
    connection = connector.connect(
        host=admin_config.host,
        port=admin_config.port,
        user=admin_config.user,
        password=admin_config.password,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        cursor = connection.cursor()
        for statement in _read_statements(SCHEMA_PATH):
            cursor.execute(statement)
        _ensure_app_user(cursor)
    finally:
        cursor.close()
        connection.close()

    print("MySQL database initialized: booklearner")


def _mysql_connector():
    try:
        return importlib.import_module("mysql.connector")
    except ImportError:
        return None


def _read_statements(path: Path) -> list[str]:
    sql = path.read_text(encoding="utf-8")
    statements = []
    current = []
    for raw_line in sql.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("--"):
            continue
        current.append(raw_line)
        if line.endswith(";"):
            statement = "\n".join(current).strip().rstrip(";").strip()
            if statement:
                statements.append(statement)
            current = []
    if current:
        statements.append("\n".join(current).strip())
    return statements


def _ensure_app_user(cursor) -> None:
    config = get_mysql_config()
    if not config.user or config.user == "root":
        return

    user = _sql_literal(config.user)
    password = _sql_literal(config.password)
    database = _quote_identifier(config.database)
    cursor.execute(f"CREATE USER IF NOT EXISTS {user}@'%' IDENTIFIED BY {password}")
    cursor.execute(f"GRANT ALL PRIVILEGES ON {database}.* TO {user}@'%'")
    cursor.execute("FLUSH PRIVILEGES")


def _sql_literal(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def _quote_identifier(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"


if __name__ == "__main__":
    main()
