"""Fail-closed, explicit NAS ownership release runner (not normal startup).

Only a newly restored NEWABBY permissions schema is accepted. Full backup rows
stay on the NAS; this runner only needs the non-content backup receipt. The
maintenance token never bypasses authentication or ownership checks.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


RELEASE_KEY = "release-20261101"


def encoded(value):
    if isinstance(value, datetime):
        return {"__dt__": value.isoformat()}
    if isinstance(value, date):
        return {"__date__": value.isoformat()}
    if isinstance(value, Decimal):
        return {"__decimal__": str(value)}
    if isinstance(value, bytes):
        return {"__bytes__": base64.b64encode(value).decode("ascii")}
    return value


def ident(name):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError("Unsupported release identifier")
    return "`" + name + "`"


def validate_target(url, expected):
    target = make_url(url)
    if target.drivername != "mysql+pymysql" or target.host != "192.168.1.247" or target.port != 3307:
        raise ValueError("Only the configured NAS MySQL endpoint is allowed")
    if target.database != expected or not re.fullmatch(r"newabby_permissions_(?:verify|live)_20261101", expected):
        raise ValueError("Never migrate the original database or an unrelated schema")
    return target


def verify_original(connection, receipt, cutoffs=None):
    """Compare raw DBAPI values; JSON text must not be ORM-deserialized."""
    limits = dict(cutoffs or {})
    for name, table in receipt["tables"].items():
        fields = ",".join(ident(column) for column in table["columns"])
        suffix = ""
        if cutoffs is not None and "id" in table["columns"]:
            maximum = limits[name]
            suffix = " WHERE 1=0" if maximum is None else " WHERE id<=" + str(int(maximum))
        elif "id" in table["columns"]:
            limits[name] = connection.exec_driver_sql("SELECT MAX(id) FROM " + ident(name)).scalar()
        order = ",".join(ident(column) for column in table["primary"])
        rows = connection.execution_options(stream_results=True).exec_driver_sql(
            "SELECT " + fields + " FROM " + ident(name) + suffix + " ORDER BY " + order)
        digest, count = hashlib.sha256(), 0
        for row in rows:
            line = json.dumps([encoded(value) for value in row], ensure_ascii=False, separators=(",", ":"))
            digest.update(line.encode("utf8") + b"\n")
            count += 1
        if count != table["rows"] or digest.hexdigest() != table["sha256"]:
            raise ValueError("Original business fields changed: " + name)
    return limits


def verify_account_queries(engine, legacy_id):
    from app.database import DataScopedSession
    from app.data_context import data_context
    from app.data_permissions import resolve_data_context, scoped_models
    from app.models import AdminUserSetting, DataOwnerMixin, Word
    factory = sessionmaker(engine, class_=DataScopedSession, autoflush=False)
    with factory() as db:
        accounts = db.scalars(select(AdminUserSetting).order_by(AdminUserSetting.id)).all()
        contexts = [replace(resolve_data_context(db, actor), read_only=True) for actor in accounts if actor.is_active]
        foreign_id = db.scalar(select(Word.id).where(Word.owner_key == f"u:{legacy_id}").limit(1))
    results = []
    for context in contexts:
        counts = {}
        with data_context(context), factory() as db, engine.connect() as trusted:
            for model in scoped_models():
                table = model.__table__
                if issubclass(model, DataOwnerMixin):
                    keys = [context.owner_key]
                    if model.__public_read__:
                        keys.append("public")
                    predicate = table.c.owner_key.in_(keys)
                else:
                    predicate = table.c.phone == context.owner_phone
                expected = trusted.execute(select(func.count()).select_from(table).where(predicate)).scalar_one()
                actual = db.scalar(select(func.count()).select_from(model))
                if actual != expected:
                    raise ValueError("Account query isolation mismatch: " + model.__tablename__)
                counts[model.__tablename__] = actual
            if context.owner_id != legacy_id and foreign_id is not None and db.get(Word, foreign_id) is not None:
                raise ValueError("A guessed private word ID was readable")
        results.append({"account_id": context.actor_id, "role_admin": context.is_admin, "counts": counts,
            "foreign_private_id_denied": context.owner_id != legacy_id})
    if not results:
        raise ValueError("No active accounts were verified")
    return results


def prepare_database(url, control, *, rehearse=False):
    target = validate_target(url, control["target_schema"])
    receipt = control["backup_receipt"]
    restored = control["restore_receipt"]
    if (receipt.get("source") != "spelling_bee" or not restored.get("verified")
            or restored.get("restored_schema") != target.database
            or restored.get("backup_sha256") != receipt["file_sha256"]):
        raise ValueError("A verified NAS-local restoration is required")
    sources_path = Path(control["sources_file"])
    if hashlib.sha256(sources_path.read_bytes()).hexdigest() != control["sources_sha256"]:
        raise ValueError("Official source manifest changed")
    # These imports register policy events and every phone-owned module, but do
    # not import main/startup or run application seed/backfill routines.
    from app.services import fun_math  # noqa: F401
    from app.database import DataScopedSession
    from app.data_context import DataContext, data_context, public_data_context
    from app.data_migration import apply_migration, migration_plan, owned_tables
    from app.data_catalog import seed_public_catalog
    from app.models import AdminUserSetting, DataPermissionState
    from app.data_scope_http import MIGRATION_KEY
    engine = create_engine(target, hide_parameters=True, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            cutoffs = verify_original(connection, receipt)
            plan = migration_plan(connection)
            migration = apply_migration(connection, plan, writers_stopped=True, backup_verified=True)
        if rehearse:
            with engine.begin() as connection:
                apply_migration(connection, migration_plan(connection), writers_stopped=True, backup_verified=True)
        with engine.connect() as connection:
            verify_original(connection, receipt)
            owner_key = f"u:{plan['legacy_owner_id']}"
            for table in owned_tables():
                if connection.execute(select(func.count()).select_from(table).where(table.c.owner_key != owner_key)).scalar_one():
                    raise ValueError("Historical ownership backfill is incomplete")
        factory = sessionmaker(engine, class_=DataScopedSession, autoflush=False)
        with factory() as db:
            actor = db.get(AdminUserSetting, plan["legacy_owner_id"])
            context = DataContext(actor_id=actor.id, owner_id=actor.id, actor_phone=actor.phone,
                owner_phone=actor.phone, is_admin=True)
        with data_context(context), public_data_context(), factory() as db:
            sources = json.loads(sources_path.read_text(encoding="utf8"))
            catalog = seed_public_catalog(db, sources)
            if rehearse and any(row["added"] for row in seed_public_catalog(db, sources)):
                raise ValueError("Public catalog seed was not idempotent")
        with engine.connect() as connection:
            verify_original(connection, receipt, cutoffs)
        accounts = verify_account_queries(engine, plan["legacy_owner_id"])
        with engine.begin() as connection:
            table = DataPermissionState.__table__
            connection.execute(table.delete().where(table.c.key.in_([MIGRATION_KEY, RELEASE_KEY])))
            connection.execute(table.insert(), [{"key": MIGRATION_KEY, "value": "ready"},
                {"key": RELEASE_KEY, "value": control["release_manifest_sha256"]}])
        return {"passed": True, "schema": target.database, "migration": migration,
            "original_tables_verified": len(receipt["tables"]), "cutoffs": cutoffs,
            "backup_sha256": receipt["file_sha256"], "catalog": catalog, "accounts": accounts,
            "release_manifest_sha256": control["release_manifest_sha256"]}
    finally:
        engine.dispose()


def launch():
    from app.config import get_settings
    settings = get_settings()
    input_path = Path(os.environ.get("NEWABBY_RELEASE_INPUT", "/app/release-input/input.json"))
    state_path = Path(os.environ.get("NEWABBY_RELEASE_STATE", "/app/release-state"))
    control = json.loads(input_path.read_text(encoding="utf8"))
    target = validate_target(settings.database_url, control["target_schema"])
    if not settings.data_permissions_enabled or not settings.login_session_secret:
        raise ValueError("Isolation and a pinned session secret are required")
    engine = create_engine(target, hide_parameters=True)
    try:
        from sqlalchemy import inspect
        from app.models import DataPermissionState
        ready = None
        with engine.connect() as connection:
            if inspect(connection).has_table(DataPermissionState.__tablename__):
                ready = connection.execute(select(DataPermissionState.__table__.c.value).where(
                    DataPermissionState.__table__.c.key == RELEASE_KEY)).scalar_one_or_none()
    finally:
        engine.dispose()
    if ready != control["release_manifest_sha256"]:
        state_path.mkdir(parents=True, exist_ok=True)
        attempted = state_path / "migration-attempted.json"
        if attempted.exists():
            raise ValueError("A previous migration attempt needs manual review; refusing automatic retry")
        if not settings.data_permissions_maintenance_file or not Path(settings.data_permissions_maintenance_file).is_file():
            raise ValueError("The maintenance gate must exist before first migration")
        attempted.write_text(json.dumps({"release": control["release_manifest_sha256"]}), encoding="utf8")
        result = prepare_database(settings.database_url, control)
        (state_path / "migration-verified.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8")
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8011, log_level="info")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rehearse", action="store_true")
    args = parser.parse_args()
    try:
        if args.rehearse:
            control = json.load(sys.stdin)
            result = prepare_database(control.pop("database_url"), control, rehearse=True)
            print(json.dumps(result, ensure_ascii=False), flush=True)
        else:
            launch()
    except Exception as exc:
        # Never emit SQL parameters, credentials, phones, or user row contents.
        print(json.dumps({"release_failed": True, "error_class": type(exc).__name__,
            "reason": str(exc) if isinstance(exc, ValueError) else "See private release evidence"}), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
