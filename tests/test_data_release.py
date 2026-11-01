"""Release runner guardrails, using only synthetic in-memory SQLite data."""
import hashlib
import json
import unittest
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import create_engine

from app.data_release import encoded, validate_target, verify_original


class DataReleaseTests(unittest.TestCase):
    def test_isolated_startup_cannot_reintroduce_global_wrong_word_uniqueness(self):
        import os
        os.environ['DATABASE_URL']='sqlite+pysqlite:///:memory:'
        from contextlib import contextmanager
        from types import SimpleNamespace
        from unittest.mock import patch
        from app import main
        from app.database import Base
        statements=[]
        class Inspector:
            def get_columns(self,name): return [{'name':column.name} for column in Base.metadata.tables[name].columns]
            def get_table_names(self): return list(Base.metadata.tables)
            def get_indexes(self,name): return []
        @contextmanager
        def transaction():
            yield SimpleNamespace(execute=lambda statement:statements.append(str(statement)))
        with patch.object(main,'engine',SimpleNamespace(dialect=SimpleNamespace(name='mysql'),begin=transaction)),\
            patch.object(main,'inspect',return_value=Inspector()),patch.object(main.settings,'data_permissions_enabled',True):
            main.ensure_schema_columns()
        self.assertFalse(any('UNIQUE INDEX' in statement for statement in statements))

    def test_only_new_nas_release_schemas_are_allowed(self):
        base='mysql+pymysql://fixture:fixture@192.168.1.247:3307/'
        for name in ('newabby_permissions_verify_20261101','newabby_permissions_live_20261101'):
            self.assertEqual(validate_target(base+name,name).database,name)
        for url, expected in [(base+'spelling_bee','spelling_bee'),
            (base+'mysql','mysql'), (base+'newabby_permissions_live_20261101','newabby_permissions_verify_20261101'),
            ('mysql+pymysql://fixture@127.0.0.1:3307/newabby_permissions_live_20261101','newabby_permissions_live_20261101')]:
            with self.assertRaises(ValueError): validate_target(url,expected)

    def test_raw_value_fingerprint_matches_backup_type_encoding(self):
        self.assertEqual(encoded(datetime(2026,1,1,2,3)),{'__dt__':'2026-01-01T02:03:00'})
        self.assertEqual(encoded(date(2026,1,1)),{'__date__':'2026-01-01'})
        self.assertEqual(encoded(Decimal('1.20')),{'__decimal__':'1.20'})
        self.assertEqual(encoded(b'ab'),{'__bytes__':'YWI='})

    def test_original_rows_are_verified_even_after_additive_public_seed(self):
        engine=create_engine('sqlite+pysqlite:///:memory:')
        self.addCleanup(engine.dispose)
        values=[1,'synthetic private text']
        digest=hashlib.sha256((json.dumps(values,ensure_ascii=False,separators=(',',':'))+'\n').encode()).hexdigest()
        receipt={'tables':{'fixture':{'columns':['id','body'],'primary':['id'],'rows':1,'sha256':digest}}}
        with engine.begin() as connection:
            connection.exec_driver_sql('CREATE TABLE fixture (id INTEGER PRIMARY KEY,body TEXT)')
            connection.exec_driver_sql('INSERT INTO fixture VALUES (?,?)',tuple(values))
            cutoffs=verify_original(connection,receipt)
            self.assertEqual(cutoffs,{'fixture':1})
            connection.exec_driver_sql("INSERT INTO fixture VALUES (2,'synthetic public text')")
            verify_original(connection,receipt,cutoffs)
            connection.exec_driver_sql("UPDATE fixture SET body='changed' WHERE id=1")
            with self.assertRaisesRegex(ValueError,'Original business fields changed'):
                verify_original(connection,receipt,cutoffs)


if __name__=='__main__': unittest.main()
