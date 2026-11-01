"""Migration fixtures are synthetic; no user database is opened."""
import os
os.environ['DATABASE_URL']='sqlite+pysqlite:///:memory:'
import re
import unittest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.schema import CreateTable
from sqlalchemy.orm import Session

from app.database import Base
from app.data_migration import apply_migration, migration_plan
from app.models import AdminUserSetting, Word, DiaryEntry, DataPermissionState


class DataMigrationTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite+pysqlite:///:memory:')
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.exec_driver_sql('DROP TABLE words')
            ddl=str(CreateTable(Word.__table__).compile(dialect=connection.dialect))
            ddl=re.sub(r"\s*owner_key VARCHAR\(64\) DEFAULT 'legacy' NOT NULL,",'',ddl)
            ddl=ddl.replace('UNIQUE (owner_key, word)','UNIQUE (word)')
            connection.exec_driver_sql(ddl)
            connection.execute(AdminUserSetting.__table__.insert(),[
                {'id':1,'phone':'fixture-jerry','username':'jerry','role':'admin','is_active':True},
                {'id':2,'phone':'fixture-reader','username':'reader','role':'viewer','is_active':True}])
            connection.exec_driver_sql("INSERT INTO words (id,word,note,enrichment_status) VALUES (7,'synthetic','keep private','done')")
            connection.execute(DiaryEntry.__table__.insert().values(phone='fixture-reader',diary_date=__import__('datetime').date(2026,1,1),body='reader keeps this',title='private'))

    def test_dry_run_does_not_modify_schema_or_business_rows(self):
        with self.engine.connect() as connection:
            plan=migration_plan(connection)
            self.assertTrue(plan['tables']['words']['add_owner_column'])
            self.assertEqual(plan['legacy_owner_id'],1)
            self.assertNotIn('owner_key',{c['name'] for c in inspect(connection).get_columns('words')})

    def test_requires_stopped_writers_and_verified_backup(self):
        with self.engine.begin() as connection:
            plan=migration_plan(connection)
            with self.assertRaises(ValueError): apply_migration(connection,plan)

    def test_backfill_keeps_ids_data_and_phone_owners_and_is_idempotent(self):
        with self.engine.begin() as connection:
            plan=migration_plan(connection)
            receipt=apply_migration(connection,plan,writers_stopped=True,backup_verified=True)
            self.assertFalse(receipt['ready'])
            self.assertEqual(connection.execute(text('SELECT id,word,note,owner_key FROM words')).one(),(7,'synthetic','keep private','u:1'))
            self.assertEqual(connection.execute(select(DiaryEntry.phone,DiaryEntry.body)).one(),('fixture-reader','reader keeps this'))
            second=apply_migration(connection,migration_plan(connection),writers_stopped=True,backup_verified=True)
            self.assertEqual(receipt,second)
            # Old global spelling uniqueness must be replaced, not retained.
            connection.execute(Word.__table__.insert().values(word='synthetic',owner_key='u:2'))
            self.assertIsNone(connection.execute(select(DataPermissionState.value).where(DataPermissionState.key=='ownership-v1')).scalar_one_or_none())

    def test_refuses_changed_database_since_dry_run(self):
        with self.engine.begin() as connection:
            plan=migration_plan(connection)
            connection.exec_driver_sql("UPDATE words SET note='concurrent write' WHERE id=7")
            with self.assertRaises(ValueError): apply_migration(connection,plan,writers_stopped=True,backup_verified=True)


if __name__=='__main__': unittest.main()
