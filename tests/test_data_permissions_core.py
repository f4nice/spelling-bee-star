"""All tests use synthetic accounts and in-memory SQLite, never NAS or real users."""
import os
os.environ['DATABASE_URL'] = 'sqlite+pysqlite:///:memory:'

from datetime import date
import json
import unittest
from sqlalchemy import create_engine, delete, select, update
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.database import Base, DataScopedSession
from app.data_context import ContextThread, DataContext, ScopedJobStore, data_context, public_data_context, DataMediaDirectory, upload_url
from app.data_media import assert_media_access
from app.data_catalog import seed_public_catalog
from app.data_permissions import resolve_data_context
from app.models import (AdminUserSetting, ChallengeProgress, DataScopeGrant, DiaryEntry,
    Word, WordList, WordListItem, WrongWord, DataPermissionState, WordResourcePool)


class DataPermissionsCoreTests(unittest.TestCase):
    def test_browser_identity_is_stable_across_public_catalog_routes(self):
        from dataclasses import replace
        context=self.context(1)
        catalog=replace(context,catalog_only=True)
        maintenance=replace(catalog,public_write=True)
        self.assertEqual(context.client_key,catalog.client_key)
        self.assertEqual(context.client_key,maintenance.client_key)
        self.assertNotEqual(context.cache_key,catalog.cache_key)
        self.assertNotEqual(context.cache_key,maintenance.cache_key)

    def setUp(self):
        self.engine = create_engine('sqlite+pysqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        with Session(self.engine) as db:
            accounts = [AdminUserSetting(id=i,phone=f'synthetic-{i}',username=f'user-{i}',role=role,
                is_active=True) for i,role in [(1,'admin'),(2,'viewer'),(3,'teacher')]]
            db.add_all(accounts)
            db.add_all([Word(id=1,owner_key='u:1',word='private-a'),Word(id=2,owner_key='u:2',word='private-b'),
                Word(id=3,owner_key='public',word='official')])
            db.add_all([WordList(id=1,owner_key='u:1',name='A'),WordList(id=2,owner_key='u:2',name='B'),
                WordList(id=3,owner_key='public',name='Official')])
            db.flush()
            db.add_all([WordListItem(id=i,owner_key=owner,word_list_id=i,word_id=i)
                for i,owner in [(1,'u:1'),(2,'u:2'),(3,'public')]])
            db.add_all([ChallengeProgress(owner_key='u:1',word_list_id=3,current_index=3,completed_count=2),
                ChallengeProgress(owner_key='u:2',word_list_id=3,current_index=1,completed_count=0)])
            db.add_all([DiaryEntry(phone='synthetic-1',diary_date=date.today(),title='A',body='private A'),
                DiaryEntry(phone='synthetic-2',diary_date=date.today(),title='B',body='private B')])
            db.add(DataPermissionState(key='legacy-owner-id',value='1'))
            db.commit()

    def context(self,actor=1,owner=None,modules=None):
        owner = owner or actor
        return DataContext(actor_id=actor,owner_id=owner,actor_phone=f'synthetic-{actor}',
            owner_phone=f'synthetic-{owner}',is_admin=actor==1,
            **({'modules':frozenset(modules)} if modules is not None else {}))

    def test_select_get_aggregate_and_join_are_scoped(self):
        with data_context(self.context(2)), Session(self.engine) as db:
            self.assertEqual(list(db.scalars(select(Word.id).order_by(Word.id))),[2,3])
            self.assertIsNone(db.get(Word,1))
            self.assertEqual(list(db.execute(select(WordList.name,Word.word)
                .join(WordListItem,WordListItem.word_list_id==WordList.id)
                .join(Word,Word.id==WordListItem.word_id).order_by(Word.id))),[('B','private-b'),('Official','official')])

    def test_shared_official_list_has_independent_progress(self):
        for actor,index in [(1,3),(2,1)]:
            with self.subTest(actor=actor),data_context(self.context(actor)),Session(self.engine) as db:
                progress = db.scalar(select(ChallengeProgress).where(ChallengeProgress.word_list_id==3))
                self.assertEqual(progress.current_index,index)

    def test_phone_owned_records_are_scoped_even_without_handler_predicate(self):
        with data_context(self.context(2)),Session(self.engine) as db:
            self.assertEqual([row.title for row in db.scalars(select(DiaryEntry))],['B'])

    def test_bulk_mutations_cannot_update_or_delete_other_owner_or_public(self):
        with data_context(self.context(2)),Session(self.engine) as db:
            self.assertEqual(db.execute(update(Word).where(Word.id.in_([1,3])).values(note='forbidden')).rowcount,0)
            self.assertEqual(db.execute(delete(WordListItem).where(WordListItem.id.in_([1,3]))).rowcount,0)
            db.commit()
        with Session(self.engine) as db:
            self.assertIsNone(db.get(Word,1).note)
            self.assertIsNone(db.get(Word,3).note)
            self.assertEqual(len(list(db.scalars(select(WordListItem)))),3)

    def test_public_instance_cannot_be_edited_or_deleted(self):
        for action in ('edit','delete'):
            with self.subTest(action=action),data_context(self.context(2)),Session(self.engine) as db:
                word = db.get(Word,3)
                if action=='edit': word.note='forbidden'
                else: db.delete(word)
                with self.assertRaises(HTTPException): db.commit()

    def test_new_rows_get_owner_and_same_spelling_is_independent(self):
        for actor in (1,2):
            with data_context(self.context(actor)),Session(self.engine) as db:
                word = Word(word='same-spelling',note=f'owner-{actor}')
                db.add(word)
                db.commit()
                self.assertEqual(word.owner_key,f'u:{actor}')
        with Session(self.engine) as db:
            self.assertEqual(len(list(db.scalars(select(Word).where(Word.word=='same-spelling')))),2)

    def test_foreign_list_or_word_id_cannot_be_linked_into_own_list(self):
        for list_id,word_id in [(1,2),(2,1),(3,2)]:
            with self.subTest(list_id=list_id,word_id=word_id),data_context(self.context(2)),Session(self.engine) as db:
                db.add(WordListItem(word_list_id=list_id,word_id=word_id))
                with self.assertRaises(HTTPException): db.commit()

    def test_other_owner_view_is_read_only_even_for_admin(self):
        with data_context(self.context(1,2)),Session(self.engine) as db:
            self.assertIsNone(db.get(Word,1))
            word = db.get(Word,2)
            word.note='not allowed'
            with self.assertRaises(HTTPException): db.commit()

    def test_even_admin_cannot_change_grants_inside_other_owner_view(self):
        with data_context(self.context(1,2)),Session(self.engine) as db:
            db.add(DataScopeGrant(owner_id=2,grantee_id=3,granted_by_id=1,modules_json='["words"]'))
            with self.assertRaises(HTTPException): db.commit()

    def test_every_business_model_is_scoped_or_explicitly_shared(self):
        from app.data_permissions import module_for_model
        shared={'admin_user_settings','speakeasy_cache','daily_quotes','cat_world_scenes','cat_world_shop_settings',
            'cat_world_game_settings','cat_world_limited_cat_stocks','cat_world_limited_item_stocks','data_scope_grants','data_permission_state'}
        for mapper in Base.registry.mappers:
            with self.subTest(model=mapper.class_.__name__):
                self.assertTrue(module_for_model(mapper.class_) or mapper.class_.__tablename__ in shared)

    def test_legacy_orphan_pool_provenance_is_retained_but_new_foreign_sources_are_denied(self):
        with Session(self.engine) as db:
            db.add(WordResourcePool(owner_key='u:2',normalized_word='archived',source_word_id=998))
            db.commit()
        with data_context(self.context(2)),Session(self.engine) as db:
            pool=db.scalar(select(WordResourcePool).where(WordResourcePool.normalized_word=='archived'))
            pool.use_count=1
            db.commit()
            self.assertEqual(pool.source_word_id,998)
            db.add(WordResourcePool(normalized_word='not-allowed',source_word_id=1))
            with self.assertRaises(HTTPException): db.commit()

    def test_viewer_cannot_switch_and_teacher_requires_explicit_module_grant(self):
        with Session(self.engine) as db:
            viewer,teacher = db.get(AdminUserSetting,2),db.get(AdminUserSetting,3)
            with self.assertRaises(HTTPException): resolve_data_context(db,viewer,1)
            with self.assertRaises(HTTPException): resolve_data_context(db,teacher,2)
            db.add(DataScopeGrant(owner_id=2,grantee_id=3,granted_by_id=1,modules_json=json.dumps(['words'])))
            db.commit()
            teacher_context = resolve_data_context(db,teacher,2)
        with data_context(teacher_context),Session(self.engine) as db:
            self.assertIsNotNone(db.get(Word,2))
            self.assertEqual(list(db.scalars(select(DiaryEntry))),[])
            self.assertEqual(list(db.scalars(select(ChallengeProgress))),[])

    def test_session_cannot_be_reused_across_owners(self):
        with Session(self.engine) as db:
            with data_context(self.context(1)):
                list(db.scalars(select(Word)))
            with data_context(self.context(2)):
                with self.assertRaises(HTTPException): list(db.scalars(select(Word)))

    def test_core_table_query_and_owner_reassignment_cannot_bypass_policy(self):
        with data_context(self.context(2)),Session(self.engine) as db:
            with self.assertRaises(HTTPException): db.execute(select(Word.__table__))
            with self.assertRaises(HTTPException): db.execute(update(Word).where(Word.id==2).values(owner_key='u:1'))
            with self.assertRaises(HTTPException): db.execute(update(Word).where(Word.id==2).values(image_url='/media/images/private.webp'))

    def test_identity_map_fast_path_does_not_leak_a_preloaded_foreign_row(self):
        with DataScopedSession(self.engine) as db:
            foreign_word = db.get(Word,1)
            self.assertEqual(foreign_word.id,1)
            with data_context(self.context(2)):
                self.assertIsNone(db.get(Word,1))
                own = db.get(Word,2)
                self.assertEqual(own.id,2)
            with data_context(self.context(1)):
                with self.assertRaises(HTTPException): db.get(Word,2)

    def test_job_ids_are_scoped_and_worker_retains_creator_context(self):
        jobs = ScopedJobStore()
        with data_context(self.context(1)):
            jobs['same-id']={'owner':1}
            worker = ContextThread(target=lambda: jobs.__setitem__('worker',{'owner':1}))
        with data_context(self.context(2)):
            self.assertIsNone(jobs.get('same-id'))
            jobs['same-id']={'owner':2}
            worker.start()
            worker.join(timeout=2)
            self.assertFalse(worker.is_alive())
            self.assertIsNone(jobs.get('worker'))
        with data_context(self.context(1)):
            self.assertEqual(jobs['same-id'],{'owner':1})
            self.assertEqual(jobs['worker'],{'owner':1})

    def test_media_namespaces_and_legacy_files_are_authorized_not_just_hidden(self):
        for actor in (1,2):
            with self.subTest(actor=actor),data_context(self.context(actor)),Session(self.engine) as db:
                assert_media_access(f'/media/users/u{actor}/images/synthetic.webp',db)
                with self.assertRaises(HTTPException): assert_media_access(f'/media/users/u{3-actor}/images/synthetic.webp',db)
                with self.assertRaises(HTTPException): assert_media_access(f'/media/users/u{actor}/previews/private.json',db)
                with self.assertRaises(HTTPException): assert_media_access('/media/images/../audio/private.mp3',db)
                if actor==1: assert_media_access('/media/images/old-private.webp',db)
                else:
                    with self.assertRaises(HTTPException): assert_media_access('/media/images/old-private.webp',db)
        with data_context(self.context(2)),Session(self.engine) as db:
            own=db.get(Word,2)
            own.image_url='/media/users/u1/images/stolen.webp'
            with self.assertRaises(HTTPException): db.commit()

    def test_upload_paths_follow_current_owner_without_moving_legacy_files(self):
        from pathlib import Path
        directory=DataMediaDirectory(Path('uploads')/'images')
        self.assertEqual(directory/'old.webp',Path('uploads/images/old.webp'))
        with data_context(self.context(2)):
            target=directory/'new.webp'
            self.assertEqual(target,Path('uploads/users/u2/images/new.webp'))
            self.assertEqual(upload_url(target,'images'),'/media/users/u2/images/new.webp')
        with data_context(self.context(1)),public_data_context(),Session(self.engine) as db:
            target=directory/'new.webp'
            self.assertEqual(target,Path('uploads/public/images/new.webp'))
            self.assertEqual(upload_url(target,'images'),'/media/public/images/new.webp')
            with self.assertRaises(HTTPException): assert_media_access('/media/users/u1/images/private.webp',db)
            with self.assertRaises(HTTPException): assert_media_access('/media/images/legacy-private.webp',db)

    def test_public_catalog_uses_only_official_rows_and_append_only_batches(self):
        sources=[{'name':'Official source','verified_official':True,'rows':[
            {'word':'canonical-a','english_definition':'Official definition','note':'must not copy','image_url':'/media/images/private.webp'},
            {'word':'canonical-b'}]}]
        with data_context(self.context(1)),public_data_context(),Session(self.engine) as db:
            first=seed_public_catalog(db,sources)
            self.assertEqual(first[0]['added'],2)
            lists=list(db.scalars(select(WordList).where(WordList.name.like('Official source-%'))))
            self.assertEqual(len(lists),1)
            original_id=lists[0].id
            word=db.scalar(select(Word).where(Word.word=='canonical-a'))
            self.assertIsNone(word.image_url)
            self.assertNotIn('must not copy',word.note)
            self.assertEqual(seed_public_catalog(db,sources)[0]['added'],0)
            sources[0]['rows'].append({'word':'canonical-c'})
            self.assertEqual(seed_public_catalog(db,sources)[0]['added'],1)
            self.assertIsNotNone(db.get(WordList,original_id))
        with Session(self.engine) as db:
            self.assertEqual(db.get(Word,1).word,'private-a')

    def test_shared_completion_worker_restores_each_accounts_queued_context(self):
        from app.services.list_completion_jobs import ListCompletionJobs
        from sqlalchemy.orm import sessionmaker
        class Deferred:
            def __init__(self,**kwargs): pass
            def start(self): pass
        factory=sessionmaker(self.engine,class_=DataScopedSession,autoflush=False)
        async def complete(db,word,**kwargs):
            from app.data_context import current_data_context
            word.note=f"completed-by-{current_data_context().actor_id}"
            db.commit()
        jobs=ListCompletionJobs(factory,complete,thread_factory=Deferred)
        with data_context(self.context(1)):
            first=jobs.start(1,[1])
        with data_context(self.context(2)):
            second=jobs.start(2,[2])
            self.assertIsNone(jobs.stop(1,first['id']))
        jobs._work()
        for actor in (1,2):
            with data_context(self.context(actor)),factory() as db:
                self.assertEqual(db.get(Word,actor).note,f'completed-by-{actor}')
                self.assertEqual(jobs.current(actor)['done'],1)


if __name__=='__main__':
    unittest.main()
