"""Real NEWABBY handlers behind the scope middleware, with synthetic SQLite only."""
import os
os.environ['DATABASE_URL']='sqlite+pysqlite:///:memory:'
from contextlib import ExitStack
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, DataScopedSession
from app.data_scope_http import DataScopeMiddleware, SCOPE_COOKIE, signed_scope
from app.models import AdminUserSetting, DataPermissionState, DataScopeGrant, Word, WordList, WordListItem, DiaryEntry
from app.models import CatWorldState, ChallengeProgress
from app.services.fun_math import MathDailySession
from datetime import date


class DataPermissionsHttpTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack()
        self.addCleanup(self.stack.close)
        self.engine=create_engine('sqlite+pysqlite:///:memory:',poolclass=StaticPool,connect_args={'check_same_thread':False})
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.factory=sessionmaker(self.engine,class_=DataScopedSession,autoflush=False)
        with self.factory() as db:
            db.add_all([AdminUserSetting(id=i,phone=f'1380000000{i}',username=name,role=role,is_active=True)
                for i,name,role in [(1,'jerry','admin'),(2,'reader','viewer'),(3,'teacher','teacher')]])
            db.add(DataPermissionState(key='ownership-v1',value='ready'))
            db.add(DataPermissionState(key='legacy-owner-id',value='1'))
            db.add_all([Word(id=i,owner_key=owner,word=spelling,english_definition='synthetic definition',
                chinese_definition='合成释义',english_example='This is a synthetic example.',phonetic='test',part_of_speech='n.')
                for i,owner,spelling in [(1,'u:1','private-jerry'),(2,'u:2','private-reader'),(3,'public','official')]])
            db.add_all([WordList(id=i,owner_key=owner,name=name) for i,owner,name in [(1,'u:1','A'),(2,'u:2','B'),(3,'public','Official')]])
            db.flush()
            db.add_all([WordListItem(word_list_id=i,word_id=i,owner_key=owner) for i,owner in [(1,'u:1'),(2,'u:2'),(3,'public')]])
            db.add(DiaryEntry(phone='13800000002',diary_date=date(2026,1,1),title='Reader only',body='private synthetic diary'))
            db.commit()
        application=FastAPI()
        self.maintenance_file=""
        application.router.routes.extend(main.app.router.routes)
        def get_test_db():
            with self.factory() as db: yield db
        self.stack.enter_context(patch.dict(main.app.dependency_overrides,{main.get_db:get_test_db}))
        original_auth=main.authenticated_phone_from_request
        auth=lambda request:request.headers.get('x-synthetic-user','') or original_auth(request)
        self.stack.enter_context(patch.object(main,'authenticated_phone_from_request',auth))
        self.stack.enter_context(patch.object(main,'list_featured_good_words_quotes',return_value=[]))
        application.add_middleware(DataScopeMiddleware,enabled=lambda:True,session_factory=self.factory,
            authenticated_phone=auth,signer=main.sign_login_payload,session_stamp=auth,
            maintenance_file=lambda:self.maintenance_file)
        self.client=self.stack.enter_context(TestClient(application))

    def headers(self,actor=2):
        return {'x-synthetic-user':f'1380000000{actor}'}

    def test_release_gate_never_bypasses_authentication_or_ownership(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as folder:
            path=Path(folder)/'maintenance.token'
            path.write_text('synthetic-release-token',encoding='utf8')
            self.maintenance_file=str(path)
            blocked=self.client.get('/api/vue/lists',headers=self.headers(1))
            self.assertEqual(blocked.status_code,503)
            self.assertEqual(blocked.headers['cache-control'],'private, no-store')
            release={'X-Newabby-Release-Check':'synthetic-release-token'}
            self.assertEqual(self.client.get('/api/vue/lists',headers=release).status_code,401)
            self.assertEqual(self.client.get('/api/vue/words/1',headers={**release,**self.headers(2)}).status_code,404)
            self.assertEqual(self.client.get('/api/vue/lists',headers={**release,**self.headers(2)}).status_code,200)
            path.unlink()
            self.assertEqual(self.client.get('/api/vue/lists',headers=self.headers(2)).status_code,200)

    def test_release_gate_rejects_malformed_or_empty_tokens(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as folder:
            path=Path(folder)/'maintenance.token'
            self.maintenance_file=str(path)
            for expected,supplied in [('synthetic-release-token','synthetic-release-token-extra'),
                ('synthetic-release-token',' synthetic-release-token'),
                ('synthetic-release-token','synthetic-release-token '),(' \n',''),(' \n',' ')]:
                with self.subTest(expected_empty=not expected.strip(),supplied=supplied):
                    path.write_text(expected,encoding='utf8')
                    response=self.client.get('/api/vue/lists',headers={**self.headers(2),'X-Newabby-Release-Check':supplied})
                    self.assertEqual(response.status_code,503)
                    self.assertEqual(response.headers['cache-control'],'private, no-store')
                    self.assertEqual(response.headers['retry-after'],'60')
                    self.assertNotIn('cards',response.json())

    def test_guessed_word_and_list_ids_do_not_expose_foreign_data(self):
        own=self.client.get('/api/vue/words/2?edit=1&list_id=2',headers=self.headers())
        self.assertEqual(own.status_code,200,own.text)
        self.assertEqual(own.json()['word']['word'],'private-reader')
        for url in ('/api/vue/words/1?edit=1','/api/vue/lists/1'):
            response=self.client.get(url,headers=self.headers())
            self.assertEqual(response.status_code,404,response.text)
        public=self.client.get('/api/vue/words/3?edit=1&list_id=3',headers=self.headers())
        self.assertEqual(public.status_code,200,public.text)
        self.assertFalse(public.json()['can_edit'])

    def test_cache_is_private_and_same_url_returns_only_each_accounts_data(self):
        first=self.client.get('/api/vue/lists',headers=self.headers(1))
        second=self.client.get('/api/vue/lists',headers=self.headers(2))
        self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(second.status_code,200,second.text)
        self.assertEqual([card['list']['id'] for card in first.json()['cards']],[1])
        self.assertEqual([card['list']['id'] for card in second.json()['cards']],[2])
        self.assertEqual(second.headers['cache-control'],'private, no-store')
        self.assertNotEqual(first.headers['x-newabby-scope'],second.headers['x-newabby-scope'])
        self.assertNotIn('newabby_data_cache',second.headers.get('set-cookie',''))

    def test_switch_is_verified_and_admin_other_owner_writes_are_denied(self):
        denied=self.client.post('/api/vue/data-scope',headers=self.headers(2),json={'ownerId':1})
        self.assertEqual(denied.status_code,403,denied.text)
        allowed=self.client.post('/api/vue/data-scope',headers=self.headers(1),json={'ownerId':2})
        self.assertEqual(allowed.status_code,200,allowed.text)
        read=self.client.get('/api/vue/words/2?edit=1&list_id=2',headers=self.headers(1))
        self.assertEqual(read.status_code,200,read.text)
        self.assertFalse(read.json()['can_edit'])
        write=self.client.post('/api/vue/lists/groups',headers=self.headers(1),json={'name':'not allowed'})
        self.assertEqual(write.status_code,403,write.text)
        restore=self.client.post('/api/vue/data-scope',headers=self.headers(1),json={'ownerId':1})
        self.assertEqual(restore.status_code,200,restore.text)

    def test_teacher_module_grants_and_revocation_take_effect_on_next_request(self):
        with self.factory() as db:
            db.add(DataScopeGrant(owner_id=2,grantee_id=3,granted_by_id=1,modules_json='["words"]'))
            db.commit()
        selected=self.client.post('/api/vue/data-scope',headers=self.headers(3),json={'ownerId':2})
        self.assertEqual(selected.status_code,200,selected.text)
        self.assertEqual(self.client.get('/api/vue/lists/2',headers=self.headers(3)).status_code,200)
        self.assertEqual(self.client.get('/api/vue/diary',headers=self.headers(3)).status_code,403)
        with self.factory() as db:
            db.delete(db.scalar(select(DataScopeGrant)))
            db.commit()
        self.assertEqual(self.client.get('/api/vue/lists/2',headers=self.headers(3)).status_code,403)
        self.assertEqual(self.client.post('/api/vue/data-scope',headers=self.headers(3),json={'ownerId':3}).status_code,200)

    def test_learning_grant_cannot_silently_expand_to_words(self):
        response=self.client.post('/api/vue/admin/data-grants',headers=self.headers(1),
            json={'ownerId':2,'teacherId':3,'modules':['learning']})
        self.assertEqual(response.status_code,400,response.text)
        with self.factory() as db:
            self.assertEqual(list(db.scalars(select(DataScopeGrant))),[])

    def test_forged_scope_cookie_and_missing_migration_are_fail_closed(self):
        self.client.cookies.set(SCOPE_COOKIE,'scope-v1:2:1:forged')
        self.assertEqual(self.client.get('/api/vue/lists',headers=self.headers()).status_code,403)
        self.client.cookies.clear()
        with self.factory() as db:
            db.delete(db.get(DataPermissionState,'ownership-v1'))
            db.commit()
        response=self.client.get('/api/vue/lists',headers=self.headers())
        self.assertEqual(response.status_code,503,response.text)

    def test_public_copy_preserves_private_rows_and_shared_catalog(self):
        response=self.client.post('/api/vue/lists/3/personal-copy',headers=self.headers())
        self.assertEqual(response.status_code,200,response.text)
        target_id=response.json()['word_list_id']
        with self.factory() as db:
            private=db.scalar(select(Word).where(Word.owner_key=='u:2',Word.word=='official'))
            self.assertIsNotNone(private)
            self.assertEqual(db.get(Word,3).owner_key,'public')
            self.assertEqual(db.get(Word,2).word,'private-reader')
            self.assertEqual(db.get(WordList,target_id).owner_key,'u:2')
        self.assertEqual(self.client.post('/api/vue/lists/1/personal-copy',headers=self.headers()).status_code,403)

    def test_other_owner_gets_do_not_create_learning_cat_or_math_records(self):
        self.client.post('/api/vue/data-scope',headers=self.headers(1),json={'ownerId':2})
        for url in ('/api/vue/lists/2','/api/vue/cat-world','/api/vue/fun-math','/api/vue/diary'):
            with self.subTest(url=url):
                response=self.client.get(url,headers=self.headers(1))
                self.assertEqual(response.status_code,200,response.text)
        diary=self.client.get('/api/vue/diary',headers=self.headers(1)).json()
        self.assertEqual(diary['entries'][0]['title'],'Reader only')
        with self.factory() as db:
            self.assertEqual(list(db.scalars(select(ChallengeProgress))),[])
            self.assertEqual(list(db.scalars(select(CatWorldState))),[])
            self.assertEqual(list(db.scalars(select(MathDailySession))),[])

    def test_anonymous_html_still_redirects_to_login_and_api_returns_401(self):
        html=self.client.get('/',follow_redirects=False)
        self.assertEqual(html.status_code,303,html.text)
        self.assertTrue(html.headers['location'].startswith('/login?next='))
        self.assertEqual(self.client.get('/api/vue/lists').status_code,401)

    def test_real_signed_login_cookie_resolves_its_account_without_test_header(self):
        with patch.object(main.settings,'login_enabled',True),patch.object(main.settings,'login_phone_allowlist',''):
            self.client.cookies.set(main.settings.login_cookie_name,main.build_login_cookie('13800000002'))
            response=self.client.get('/api/vue/lists')
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual([card['list']['id'] for card in response.json()['cards']],[2])

    def test_public_word_mutation_is_blocked_before_calling_providers(self):
        with patch.object(main,'generate_word_image') as provider:
            response=self.client.post('/api/vue/words/3/ai-image',headers=self.headers(),data={'edit_token':'1'})
        self.assertEqual(response.status_code,403,response.text)
        provider.assert_not_called()

    def test_self_readonly_audit_mode_cannot_write_or_expand_data_access(self):
        headers={**self.headers(2),'X-Newabby-Read-Only':'1'}
        own=self.client.get('/api/vue/words/2?edit=1&list_id=2',headers=headers)
        self.assertEqual(own.status_code,200,own.text)
        self.assertFalse(own.json()['can_edit'])
        self.assertEqual(self.client.get('/api/vue/words/1?edit=1',headers=headers).status_code,404)
        self.assertEqual(self.client.post('/api/vue/lists/groups',headers=headers,json={'name':'cannot create'}).status_code,403)
        self.assertEqual(self.client.get('/api/vue/cat-world',headers=headers).status_code,200)
        self.assertEqual(self.client.get('/api/vue/fun-math',headers=headers).status_code,200)
        with self.factory() as db:
            self.assertEqual(list(db.scalars(select(CatWorldState))),[])
            self.assertEqual(list(db.scalars(select(MathDailySession))),[])
            self.assertEqual(list(db.scalars(select(ChallengeProgress))),[])

    def test_isolated_startup_does_not_run_unscoped_private_backfills(self):
        directory_names=('PREVIEW_DIR','IMAGE_DIR','AUDIO_DIR','BOOK_COVER_DIR','ESSAY_COVER_DIR','SCIENCE_DISCOVERY_CACHE_DIR')
        public_seeds=('seed_cat_world_scenes','seed_cat_world_limited_cat_stock','seed_cat_world_limited_item_stock','seed_daily_quotes')
        with ExitStack() as stack:
            stack.enter_context(patch.object(main.settings,'data_permissions_enabled',True))
            stack.enter_context(patch.object(main.Base.metadata,'create_all'))
            stack.enter_context(patch.object(main,'ensure_schema_columns'))
            stack.enter_context(patch.object(main,'ensure_version_matrix_file'))
            stack.enter_context(patch.object(main,'SessionLocal',self.factory))
            for name in directory_names: stack.enter_context(patch.object(main,name))
            for name in public_seeds: stack.enter_context(patch.object(main,name))
            essay=stack.enter_context(patch.object(main,'backfill_essay_best_writing_results'))
            words=stack.enter_context(patch.object(main,'ensure_default_word_list'))
            pool=stack.enter_context(patch.object(main,'seed_word_resource_pool'))
            main.startup()
            essay.assert_not_called();words.assert_not_called();pool.assert_not_called()


if __name__=='__main__': unittest.main()
