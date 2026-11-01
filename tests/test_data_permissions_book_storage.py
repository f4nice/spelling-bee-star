"""Raw BookLearner SQL needs its own ownership predicates, not ORM hooks."""
import os
os.environ['DATABASE_URL']='sqlite+pysqlite:///:memory:'
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'好词好句'))
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from fastapi import HTTPException
from app.data_context import DataContext, data_context
from booklearner import storage


class BookStoragePermissionsTests(unittest.TestCase):
    def context(self,*,readonly=False,modules=None):
        return DataContext(actor_id=1 if readonly else 2,owner_id=2,actor_phone='a',owner_phone='b',
            is_admin=readonly,**({'modules':frozenset(modules)} if modules is not None else {}))

    def test_history_sql_binds_verified_owner_not_a_client_supplied_value(self):
        connection=MagicMock()
        cursor=connection.cursor.return_value
        cursor.fetchall.return_value=[]
        with data_context(self.context()),patch.object(storage,'get_mysql_config',return_value=SimpleNamespace(enabled=True)),patch.object(storage,'_mysql_connector',return_value=object()),patch.object(storage,'_connect',return_value=connection):
            self.assertEqual(storage.list_recent_analyses(),[])
        sql,parameters=cursor.execute.call_args.args
        self.assertIn('WHERE owner_key = %s',sql)
        self.assertEqual(parameters[0],'u:2')

    def test_single_analysis_and_cover_update_always_include_owner(self):
        for action in (lambda:storage.get_analysis(999),lambda:storage.update_analysis_cover(999,'/media/users/u2/book-covers/own.webp')):
            connection=MagicMock()
            cursor=connection.cursor.return_value
            cursor.fetchone.return_value=None
            with self.subTest(action=action),data_context(self.context()),patch.object(storage,'get_mysql_config',return_value=SimpleNamespace(enabled=True)),patch.object(storage,'_mysql_connector',return_value=object()),patch.object(storage,'_connect',return_value=connection):
                self.assertIsNone(action())
            sql,parameters=cursor.execute.call_args.args
            self.assertIn('AND owner_key = %s',sql)
            self.assertEqual(parameters,(999,'u:2'))

    def test_foreign_analysis_cannot_receive_a_clicked_word(self):
        connection=MagicMock()
        cursor=connection.cursor.return_value
        cursor.fetchone.return_value=None
        with data_context(self.context()),patch.object(storage,'get_mysql_config',return_value=SimpleNamespace(enabled=True)),patch.object(storage,'_mysql_connector',return_value=object()),patch.object(storage,'_connect',return_value=connection):
            result=storage.save_clicked_word(999,{'word':'synthetic'})
        self.assertEqual(result['reason'],'not_found')
        self.assertFalse(any('INSERT INTO booklearner_clicked_words' in str(call) for call in cursor.execute.call_args_list))
        connection.commit.assert_not_called()

    def test_readonly_or_ungranted_module_is_rejected_before_opening_database(self):
        with patch.object(storage,'_connect') as connect:
            with data_context(self.context(readonly=True)):
                with self.assertRaises(HTTPException): storage.save_analysis('test',{})
            with data_context(self.context(modules={'words'})):
                with self.assertRaises(HTTPException): storage.list_recent_analyses()
        connect.assert_not_called()


if __name__=='__main__': unittest.main()
