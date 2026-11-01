"""Synthetic-only security and route tests. Never connect to a configured database."""
import os
os.environ['DATABASE_URL'] = 'sqlite+pysqlite:///:memory:'
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, DataScopedSession
from app.data_scope_http import DataScopeMiddleware, SCOPE_COOKIE, signed_scope
from app.models import AdminUserSetting, DataPermissionState, WordList, WordListGroup
from app.services.site_security import DeletePasswordStore


OLD = 'synthetic-old-confirmation'
NEW = 'synthetic-new-confirmation'
ADMIN = 'synthetic-admin-login'


class StoreTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'site-security.json'
        self.store = self.fresh()

    def fresh(self):
        return DeletePasswordStore(str(self.path), OLD, hash_password=main.hash_login_password, verify_password=main.verify_login_password)

    def test_existing_password_unchanged_until_explicit_save(self):
        self.assertTrue(self.store.verify(OLD))
        self.assertFalse(self.store.verify(NEW))
        self.assertTrue(self.store.status()['usesServerPassword'])
        self.assertFalse(self.path.exists())

    def test_long_legacy_password_is_preserved_without_new_policy_restriction(self):
        old = 'synthetic-legacy-' * 12
        store = DeletePasswordStore('', old, hash_password=main.hash_login_password, verify_password=main.verify_login_password)
        self.assertTrue(store.verify(old));self.assertFalse(store.verify(old+'wrong'))

    def test_empty_save_leaves_existing_file_byte_identical(self):
        self.store.save(NEW, NEW, actor_id=1)
        before = self.path.read_bytes()
        self.assertFalse(self.store.save('', '', actor_id=1))
        self.assertEqual(self.path.read_bytes(), before)

    def test_blank_default_save_does_not_create_file(self):
        self.assertFalse(self.store.save('', '', actor_id=1))
        self.assertFalse(self.path.exists())

    def test_hash_only_persistent_across_instances_and_unicode(self):
        new = '合成确认密码-2026'
        self.store.save(new, new, actor_id=1)
        serialized = self.path.read_text()
        for value in (new, OLD, ADMIN):self.assertNotIn(value, serialized)
        self.assertTrue(self.fresh().verify(new))
        self.assertFalse(self.fresh().verify(OLD))
        self.assertFalse(self.fresh().status()['usesServerPassword'])
        if os.name == 'posix':self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_status_does_not_disclose_hash_or_password(self):
        self.store.save(NEW, NEW, actor_id=1)
        status = json.dumps(self.store.status())
        self.assertNotIn(NEW, status);self.assertNotIn('pbkdf2', status);self.assertNotIn('passwordHash', status)

    def test_bad_inputs_never_replace_existing_password(self):
        for password, confirmation in [('short', 'short'), (NEW, 'different'), ('x' * 129, 'x' * 129), (' '+NEW, ' '+NEW), ('bad\npassword', 'bad\npassword'), (123456, 123456), ([], [])]:
            with self.subTest(kind=type(password).__name__), self.assertRaises(HTTPException):
                self.store.save(password, confirmation, actor_id=1)
        self.assertFalse(self.path.exists());self.assertTrue(self.store.verify(OLD))

    def test_corrupt_store_fails_closed_not_server_fallback(self):
        self.path.write_text('{invalid');self.path.chmod(0o600)
        with self.assertRaises(HTTPException) as error:self.store.verify(OLD)
        self.assertEqual(error.exception.status_code, 503)
        self.assertNotIn('{invalid', error.exception.detail)

    def test_atomic_write_failure_keeps_old_file_and_cleans_temp(self):
        self.store.save(NEW, NEW, actor_id=1)
        before = self.path.read_bytes()
        with patch('app.services.site_security.os.replace', side_effect=OSError('synthetic failure')):
            with self.assertRaises(HTTPException):self.store.save(NEW+'2', NEW+'2', actor_id=1)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob('.site-security-*.tmp')), [])

    def test_missing_persistence_never_silently_accepts_change(self):
        store = DeletePasswordStore('', OLD, hash_password=main.hash_login_password, verify_password=main.verify_login_password)
        self.assertFalse(store.status()['canChange'])
        with self.assertRaises(HTTPException):store.save(NEW, NEW, actor_id=1)
        self.assertTrue(store.verify(OLD))

    def test_nonregular_or_public_files_rejected(self):
        self.path.mkdir()
        with self.assertRaises(HTTPException):self.store.verify(OLD)
        self.path.rmdir()
        if os.name == 'posix':
            self.store.save(NEW, NEW, actor_id=1);self.path.chmod(0o644)
            with self.assertRaises(HTTPException):self.store.verify(NEW)


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite+pysqlite:///:memory:', poolclass=StaticPool, connect_args={'check_same_thread':False})
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine, class_=DataScopedSession, autoflush=False, expire_on_commit=False)
        self.folder = tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'site-security.json'
        for key, value in [('site_security_settings_file', str(self.path)), ('list_delete_password', OLD)]:
            p = patch.object(main.settings, key, value);p.start();self.addCleanup(p.stop)
        with self.factory() as db:
            db.add_all([AdminUserSetting(id=i, phone=f'1380000000{i}', username='synthetic', role=role, is_active=True,
                permissions='{"admin":true}', login_password_hash=main.hash_login_password(ADMIN)) for i,role in [(1,'admin'), (2,'teacher'), (3,'viewer')]])
            db.add(DataPermissionState(key='ownership-v1', value='ready'));db.commit()
        application = FastAPI();application.router.routes.extend(main.app.router.routes)
        def get_db():
            with self.factory() as db:yield db
        p = patch.dict(main.app.dependency_overrides, {main.get_db:get_db})
        p.start();self.addCleanup(p.stop)
        p = patch.object(main, 'authenticated_phone_from_request', lambda request:request.headers.get('x-synthetic-user',''))
        p.start();self.addCleanup(p.stop)
        application.add_middleware(DataScopeMiddleware, enabled=lambda:True, session_factory=self.factory,
            authenticated_phone=lambda request:request.headers.get('x-synthetic-user',''), signer=main.sign_login_payload)
        self.client = TestClient(application)
        self.addCleanup(self.client.close)

    def post(self, actor=1, payload=None, extra=None):
        headers = {'x-synthetic-user':f'1380000000{actor}', **(extra or {})} if actor else {}
        return self.client.post('/api/vue/admin/site/delete-password', json=payload if payload is not None else {
            'newPassword':NEW, 'confirmPassword':NEW, 'adminPassword':ADMIN}, headers=headers)

    def test_admin_can_save_and_response_contains_no_credentials(self):
        response = self.post();self.assertEqual(response.status_code,200)
        self.assertTrue(response.json()['changed']);self.assertTrue(main.site_delete_password_store().verify(NEW))
        for value in (OLD,NEW,ADMIN,'pbkdf2','passwordHash'):self.assertNotIn(value,response.text)

    def test_teacher_viewer_and_anonymous_denied_even_with_admin_permission_bit(self):
        for actor, expected in [(2,403),(3,403),(0,401)]:
            with self.subTest(actor=actor):self.assertEqual(self.post(actor).status_code,expected)
        self.assertFalse(self.path.exists())

    def test_disabled_admin_denied(self):
        with self.factory() as db:u=db.get(AdminUserSetting,1);u.is_active=False;db.commit()
        self.assertEqual(self.post().status_code,403);self.assertFalse(self.path.exists())

    def test_admin_viewing_another_account_and_forced_readonly_denied(self):
        self.client.cookies.set(SCOPE_COOKIE,signed_scope(1,3,main.sign_login_payload))
        self.assertEqual(self.post().status_code,403)
        self.client.cookies.clear()
        self.assertEqual(self.post(extra={'X-Newabby-Read-Only':'1'}).status_code,403)
        self.assertFalse(self.path.exists())

    def test_login_password_required_and_wrong_password_keeps_old(self):
        for value in ('','synthetic-wrong',123):
            response=self.post(payload={'newPassword':NEW,'confirmPassword':NEW,'adminPassword':value})
            self.assertEqual(response.status_code,403)
        self.assertFalse(self.path.exists());self.assertTrue(main.site_delete_password_store().verify(OLD))

    def test_empty_submission_keeps_old_without_reauthentication(self):
        response=self.post(payload={'newPassword':'','confirmPassword':''})
        self.assertEqual(response.status_code,200);self.assertFalse(response.json()['changed'])
        self.assertTrue(response.json()['deletePassword']['usesServerPassword']);self.assertFalse(self.path.exists())

    def test_invalid_payload_returns_safe_error_and_does_not_write(self):
        for payload in ([], {'newPassword':NEW,'confirmPassword':'wrong'}, {'newPassword':False,'confirmPassword':False}):
            response=self.post(payload=payload);self.assertEqual(response.status_code,400)
            self.assertNotIn(NEW,response.text);self.assertNotIn(ADMIN,response.text)
        self.assertFalse(self.path.exists())

    def test_list_and_group_delete_use_updated_password(self):
        with self.factory() as db:
            db.add(WordList(id=1,owner_key='u:1',name='synthetic list'))
            db.add(WordListGroup(id=1,owner_key='u:1',name='synthetic group'));db.commit()
        self.assertEqual(self.post().status_code,200)
        headers={'x-synthetic-user':'13800000001'}
        for url,body_type in [('/api/vue/lists/1/delete','data'),('/api/vue/lists/groups/1/delete','json')]:
            self.assertEqual(self.client.post(url,**{body_type:{'password':OLD}},headers=headers).status_code,403)
            self.assertEqual(self.client.post(url,**{body_type:{'password':NEW}},headers=headers).status_code,200)
        with self.factory() as db:
            self.assertIsNone(db.get(WordList,1));self.assertIsNone(db.get(WordListGroup,1))

    def test_original_login_signing_seed_unchanged_after_delete_password_update(self):
        before=main.build_login_cookie('13800000001',issued_at=123)
        self.assertEqual(self.post().status_code,200)
        self.assertEqual(main.build_login_cookie('13800000001',issued_at=123),before)


if __name__=='__main__':unittest.main()
