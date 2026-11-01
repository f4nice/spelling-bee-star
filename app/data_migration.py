"""Explicit, idempotent ownership migration. Never run automatically at startup.

The caller must stop application writers and take a restorable database backup.
Existing IDs and business columns are copied byte-for-byte; only owner_key is
backfilled. Already phone-owned records are deliberately NOT reassigned.
"""
import hashlib
import json
import re

from sqlalchemy import DateTime, MetaData, Table, UniqueConstraint, inspect, select, text
from sqlalchemy.schema import CreateTable, CreateIndex

from app.database import Base
from app.models import AdminUserSetting, DataOwnerMixin, DataPermissionState, DataScopeGrant
from app.data_scope_http import MIGRATION_KEY

LEGACY_KEY = "legacy-owner-id"


def owned_tables():
    return sorted([mapper.class_.__table__ for mapper in Base.registry.mappers
        if issubclass(mapper.class_,DataOwnerMixin)],key=lambda table:table.name)


def quote_identifier(connection,name):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",name):
        raise ValueError("Unsupported migration identifier")
    return connection.dialect.identifier_preparer.quote(name)


def legacy_owner(connection):
    table = AdminUserSetting.__table__
    rows = list(connection.execute(select(table.c.id).where(
        table.c.username=="jerry",table.c.is_active.is_(True),table.c.role=="admin")))
    if len(rows)!=1:
        raise ValueError("Expected exactly one active administrator named jerry; no rows were reassigned")
    return int(rows[0][0])


def table_receipt(connection, name, columns=None, max_id=None):
    table = Table(name,MetaData(),autoload_with=connection)
    columns = columns or [column.name for column in table.columns if column.name!="owner_key"]
    statement = select(*(table.c[name] for name in columns))
    if max_id is not None:
        statement = statement.where(table.c.id<=max_id)
    if "id" in table.c:
        statement = statement.order_by(table.c.id)
    else:
        statement = statement.order_by(*table.primary_key.columns)
    digest,count = hashlib.sha256(),0
    for row in connection.execution_options(stream_results=True).execute(statement):
        digest.update(json.dumps(list(row),ensure_ascii=False,default=str,separators=(",",":")).encode())
        digest.update(b"\n")
        count+=1
    return {"count":count,"sha256":digest.hexdigest(),"columns":columns}


def migration_plan(connection):
    owner_id = legacy_owner(connection)
    existing = set(inspect(connection).get_table_names())
    tables = {}
    for table in owned_tables():
        if table.name not in existing:
            raise ValueError("Legacy database is missing an application table: "+table.name)
        columns = {column["name"] for column in inspect(connection).get_columns(table.name)}
        receipt = table_receipt(connection,table.name)
        receipt["add_owner_column"] = "owner_key" not in columns
        tables[table.name] = receipt
    # Also fingerprint phone-owned rows without changing them.
    phone_owned = {}
    for table in Base.metadata.sorted_tables:
        if table.name in existing and "phone" in table.c and table.name!="admin_user_settings":
            phone_owned[table.name] = table_receipt(connection,table.name)
    books={name:table_receipt(connection,name) for name in ("analyses","analysis_quotes","analysis_vocabulary","booklearner_clicked_words") if name in existing}
    return {"schema":"ownership-v1","legacy_owner_id":owner_id,"dialect":connection.dialect.name,
        "tables":tables,"phone_owned":phone_owned,"book_owned":books}


def sqlite_rebuild(connection, table):
    # SQLite cannot drop an implicit UNIQUE index. Rebuild with current schema,
    # preserving all columns/IDs and foreign keys (checked before committing).
    old_columns = [column["name"] for column in inspect(connection).get_columns(table.name)]
    if set(old_columns)-set(table.c.keys()):
        raise ValueError("Unexpected legacy columns; refusing to discard them in "+table.name)
    temporary = "__ownership_"+table.name
    if inspect(connection).has_table(temporary):
        raise ValueError("A previous migration staging table exists: "+temporary)
    ddl = str(CreateTable(table).compile(dialect=connection.dialect))
    original = quote_identifier(connection,table.name)
    staged = quote_identifier(connection,temporary)
    # SQLAlchemy omits quotes for simple identifiers. Replace only CREATE TABLE.
    ddl = re.sub(r"(CREATE TABLE\s+)(?:\""+re.escape(table.name)+r"\"|"+re.escape(table.name)+r")(?=\s|\()",
        lambda match:match.group(1)+staged,ddl,count=1)
    connection.exec_driver_sql(ddl)
    column_sql = ",".join(quote_identifier(connection,column) for column in old_columns)
    connection.exec_driver_sql(f"INSERT INTO {staged} ({column_sql}) SELECT {column_sql} FROM {original}")
    connection.exec_driver_sql(f"DROP TABLE {original}")
    connection.exec_driver_sql(f"ALTER TABLE {staged} RENAME TO {original}")
    for index in table.indexes:
        connection.execute(CreateIndex(index))


def migrate_owned_table(connection,table,owner_key):
    column_details=inspect(connection).get_columns(table.name)
    columns = {column["name"] for column in column_details}
    name = quote_identifier(connection,table.name)
    if "owner_key" not in columns:
        connection.exec_driver_sql(f"ALTER TABLE {name} ADD COLUMN owner_key VARCHAR(64) NOT NULL DEFAULT 'legacy'")
    preserve_timestamps="".join(f",{quote_identifier(connection,column['name'])}={quote_identifier(connection,column['name'])}" for column in column_details if isinstance(column['type'],DateTime))
    connection.execute(text(f"UPDATE {name} SET owner_key=:owner{preserve_timestamps} WHERE owner_key='legacy' OR owner_key='' OR owner_key IS NULL"),{"owner":owner_key})
    inspector = inspect(connection)
    uniques = inspector.get_unique_constraints(table.name)
    indexes = inspector.get_indexes(table.name)
    old_unique = [item for item in uniques+indexes if item.get("unique",True) and "owner_key" not in item["column_names"]
        and set(item["column_names"])!={"word_list_id","word_id"}]
    required = [constraint for constraint in table.constraints if isinstance(constraint,UniqueConstraint) and "owner_key" in constraint.columns]
    if connection.dialect.name=="sqlite":
        if old_unique:
            sqlite_rebuild(connection,table)
        else:
            known={tuple(item["column_names"]) for item in uniques+indexes if item.get("unique",True)}
            for constraint in required:
                names=tuple(column.name for column in constraint.columns)
                if names not in known:
                    fields=",".join(quote_identifier(connection,column) for column in names)
                    connection.exec_driver_sql(f"CREATE UNIQUE INDEX {quote_identifier(connection,constraint.name)} ON {name} ({fields})")
        return
    if connection.dialect.name!="mysql":
        raise ValueError("Only SQLite/MySQL ownership migrations are supported")
    known={tuple(item["column_names"]) for item in uniques+indexes if item.get("unique",True)}
    for constraint in required:
        names=tuple(column.name for column in constraint.columns)
        if names not in known:
            fields=",".join(quote_identifier(connection,column) for column in names)
            connection.exec_driver_sql(f"ALTER TABLE {name} ADD UNIQUE INDEX {quote_identifier(connection,constraint.name)} ({fields})")
    for index_name in {item["name"] for item in old_unique}:
        connection.exec_driver_sql(f"ALTER TABLE {name} DROP INDEX {quote_identifier(connection,index_name)}")
    if not any(item["column_names"]==["owner_key"] for item in inspect(connection).get_indexes(table.name)):
        connection.exec_driver_sql(f"CREATE INDEX {quote_identifier(connection,'ix_'+table.name+'_owner_key')} ON {name} (owner_key)")


def apply_migration(connection, plan, *, writers_stopped=False, backup_verified=False):
    if not writers_stopped or not backup_verified:
        raise ValueError("Stop application writers and verify a restorable backup before applying")
    if connection.dialect.name=="sqlite" and connection.exec_driver_sql('PRAGMA foreign_keys').scalar():
        raise ValueError("SQLite rebuild requires foreign_keys=OFF before starting the migration transaction")
    if migration_plan(connection)!=plan:
        raise ValueError("Database changed after the dry run; take a fresh backup and plan")
    owner_key = f"u:{plan['legacy_owner_id']}"
    DataPermissionState.__table__.create(connection,checkfirst=True)
    DataScopeGrant.__table__.create(connection,checkfirst=True)
    state = DataPermissionState.__table__
    previous = connection.execute(select(state.c.value).where(state.c.key==LEGACY_KEY)).scalar_one_or_none()
    if previous and previous!=str(plan["legacy_owner_id"]):
        raise ValueError("The recorded historical owner differs from jerry; refusing reassignment")
    connection.execute(state.delete().where(state.c.key==MIGRATION_KEY))
    for table in owned_tables():
        migrate_owned_table(connection,table,owner_key)
    existing = set(inspect(connection).get_table_names())
    # BookLearner is sometimes a second database. The release preflight must
    # separately verify its target; only tables in THIS database are touched.
    for table_name in ("analyses","booklearner_clicked_words"):
        if table_name in existing:
            table = quote_identifier(connection,table_name)
            if "owner_key" not in {column["name"] for column in inspect(connection).get_columns(table_name)}:
                connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN owner_key VARCHAR(64) NOT NULL DEFAULT 'legacy'")
            preserve_timestamps="".join(f",{quote_identifier(connection,column['name'])}={quote_identifier(connection,column['name'])}" for column in inspect(connection).get_columns(table_name) if isinstance(column['type'],DateTime))
            connection.execute(text(f"UPDATE {table} SET owner_key=:owner{preserve_timestamps} WHERE owner_key='legacy'"),{"owner":owner_key})
            if not any(index['column_names']==['owner_key'] for index in inspect(connection).get_indexes(table_name)):
                connection.exec_driver_sql(f"CREATE INDEX {quote_identifier(connection,'ix_'+table_name+'_owner_key')} ON {table} (owner_key)")
    for name,receipt in {**plan["tables"],**plan["phone_owned"],**plan["book_owned"]}.items():
        actual=table_receipt(connection,name,receipt["columns"])
        if actual["count"]!=receipt["count"] or actual["sha256"]!=receipt["sha256"]:
            raise ValueError("Business data verification failed: "+name)
    if connection.dialect.name=="sqlite" and list(connection.exec_driver_sql("PRAGMA foreign_key_check")):
        raise ValueError("Ownership migration failed foreign key validation")
    if not previous:
        connection.execute(state.insert().values(key=LEGACY_KEY,value=str(plan["legacy_owner_id"])))
    # Catalog/media/release checks are separate. A successful schema migration
    # alone MUST NOT make the HTTP boundary serve a half-migrated application.
    return {"schema_migrated":True,"ready":False,"legacy_owner_id":plan["legacy_owner_id"],
        "verified_tables":len(plan["tables"])+len(plan["phone_owned"])+len(plan["book_owned"])}
