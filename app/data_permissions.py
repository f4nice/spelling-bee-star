"""Central row-level safeguards for the application's ORM sessions.

Authentication is resolved separately. Only a server-created DataContext may
select a workspace. No request execution-option/header can disable this policy.
"""
import json

from fastapi import HTTPException
from sqlalchemy import event, false, inspect, select
from sqlalchemy.orm import Session, with_loader_criteria

from app.database import Base
from app.data_context import DATA_MODULES, PUBLIC_OWNER, current_data_context, DataContext
from app.models import (
    AdminUserSetting, DataOwnerMixin, DataScopeGrant, DataPermissionState,
    Word, WordList, WordListGroup, WordListItem,
)


PHONE_MODULES = {
    "essay_entries": "writing", "diary_entries": "writing", "debate_sessions": "writing",
    "fun_math_daily_sessions": "learning",
    "cat_world_states": "cats", "cat_world_cat_profiles": "cats", "cat_world_festival_earnings": "cats",
    "cat_world_energy_grants": "cats", "cat_world_play_time_grants": "cats", "cat_world_user_scenes": "cats",
    "cat_world_blind_box_draws": "cats", "cat_world_daily_logs": "cats",
}


def module_for_model(model):
    if issubclass(model, DataOwnerMixin):
        return model.__data_module__
    return PHONE_MODULES.get(model.__tablename__)


def parse_grant_modules(raw):
    try:
        values = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return frozenset()
    if not isinstance(values, list):
        return frozenset()
    return frozenset(value for value in values if isinstance(value,str) and value in DATA_MODULES)


def resolve_data_context(db, actor, selected_owner_id=None):
    if not actor or not actor.is_active:
        raise HTTPException(403, "账号不可用。")
    owner_id = selected_owner_id if selected_owner_id is not None else actor.id
    if not isinstance(owner_id,int) or owner_id <= 0:
        raise HTTPException(403, "无效的数据空间。")
    owner = db.get(AdminUserSetting,owner_id)
    if not owner:
        raise HTTPException(404, "数据空间不存在。")
    if not owner.is_active and actor.role != "admin":
        raise HTTPException(403, "数据空间不可用。")
    modules = DATA_MODULES
    is_admin = actor.role == "admin"
    if actor.id != owner.id and not is_admin:
        if actor.role != "teacher":
            raise HTTPException(403, "只能查看自己的数据。")
        grant = db.scalar(select(DataScopeGrant).where(DataScopeGrant.owner_id==owner.id,
            DataScopeGrant.grantee_id==actor.id))
        modules = parse_grant_modules(grant.modules_json if grant else None)
        if not modules:
            raise HTTPException(403, "未获得该账号的数据查看授权。")
    return DataContext(actor_id=actor.id,owner_id=owner.id,actor_phone=actor.phone,
        owner_phone=owner.phone,is_admin=is_admin,modules=modules)


def scoped_models():
    return [mapper.class_ for mapper in Base.registry.mappers if module_for_model(mapper.class_)]


def bind_session_scope(session):
    context = current_data_context()
    if context is None:
        if session.info.get("data_scope_bound"):
            raise HTTPException(403, "数据空间上下文已结束。")
        return None
    key = context.cache_key
    if session.info.get("data_scope_bound") and session.info["data_scope_bound"] != key:
        raise HTTPException(403, "不能在同一数据库会话中切换数据空间。")
    if not session.info.get("data_scope_actor_checked"):
        table=AdminUserSetting.__table__
        actor=session.connection().execute(select(table.c.is_active,table.c.role,table.c.phone).where(table.c.id==context.actor_id)).first()
        if not actor or not actor.is_active or actor.phone!=context.actor_phone or (context.is_admin and actor.role!="admin"):
            raise HTTPException(403,"账号权限已变化，请重新登录。")
        session.info["data_scope_actor_checked"]=True
    session.info["data_scope_bound"] = key
    return context


def read_predicate(model,context):
    module = module_for_model(model)
    if module not in context.modules:
        return false()
    if issubclass(model,DataOwnerMixin):
        if context.catalog_only and model.__public_read__:
            return model.owner_key == PUBLIC_OWNER
        keys = [context.owner_key]
        if context.include_public and model.__public_read__:
            keys.append(PUBLIC_OWNER)
        return model.owner_key.in_(keys)
    return model.phone == context.owner_phone


def write_predicate(model,context):
    if module_for_model(model) not in context.modules:
        raise HTTPException(403, "未获得此模块的数据权限。")
    if not context.can_write:
        raise HTTPException(403, "正在只读查看其他账号，不能修改数据。")
    if issubclass(model,DataOwnerMixin):
        return model.owner_key == context.owner_key
    return model.phone == context.owner_phone


def instance_is_readable(row,context):
    model = type(row)
    module = module_for_model(model)
    if not module:
        return True
    if module not in context.modules:
        return False
    if isinstance(row,DataOwnerMixin):
        if context.catalog_only and row.__public_read__:
            return row.owner_key == PUBLIC_OWNER
        return row.owner_key == context.owner_key or (
            context.include_public and row.__public_read__ and row.owner_key == PUBLIC_OWNER)
    return row.phone == context.owner_phone


@event.listens_for(Session,"do_orm_execute")
def apply_data_scope(execute_state):
    context = bind_session_scope(execute_state.session)
    if context is None:
        return
    if not execute_state.is_orm_statement:
        if str(execute_state.statement).strip().upper()!="BEGIN IMMEDIATE":
            raise HTTPException(403,"账号数据请求不能绕过受保护的 ORM 查询。")
        return
    if execute_state.is_select:
        statement = execute_state.statement
        for model in scoped_models():
            statement = statement.options(with_loader_criteria(model,read_predicate(model,context),include_aliases=True))
        execute_state.statement = statement
    elif execute_state.is_update or execute_state.is_delete:
        mapper = execute_state.bind_mapper
        if mapper and module_for_model(mapper.class_):
            model = mapper.class_
            if execute_state.is_update:
                if execute_state.is_executemany:
                    raise HTTPException(403,"批量写入必须使用逐条校验的 ORM 流程。")
                keys={getattr(key,"key",str(key)) for key in (getattr(execute_state.statement,"_values",None) or {})}
                if keys & {"id","owner_key","phone","word_id","word_list_id","group_id","source_word_id",
                    "image_url","cover_url","american_audio_url","british_audio_url","english_definition_audio_url","english_example_audio_url"}:
                    raise HTTPException(403,"不能批量更改数据归属或关联。")
            if execute_state.is_delete and context.public_write:
                raise HTTPException(403,"公共词库维护只允许补缺和更新，不允许删除。")
            execute_state.statement = execute_state.statement.where(write_predicate(model,context))
        elif mapper and mapper.class_ in (DataScopeGrant,DataPermissionState,AdminUserSetting) and not context.is_admin:
            raise HTTPException(403, "只有管理员可修改账号和数据授权。")
    elif execute_state.is_insert:
        # ORM executemany/insert bypasses before_flush. Use checked ORM adds for owned rows.
        mapper = execute_state.bind_mapper
        if mapper and (module_for_model(mapper.class_) or mapper.class_ in (AdminUserSetting,DataScopeGrant,DataPermissionState)):
            raise HTTPException(403, "私有记录必须通过受保护的写入流程。")


def check_foreign_keys(db, row, context):
    if getattr(row,"source_word_id",None) and (row in db.new or inspect(row).attrs.source_word_id.history.has_changes()):
        source=db.get(Word,row.source_word_id)
        if not source or source.owner_key!=row.owner_key:
            raise HTTPException(403,"资源来源必须属于同一数据空间。")
    if isinstance(row,WordList) and row.group_id:
        parent = db.get(WordListGroup,row.group_id)
        if not parent or parent.owner_key != row.owner_key:
            raise HTTPException(403, "不能使用其他空间的词表分组。")
    if hasattr(row,"word_list_id") and row.word_list_id:
        parent = db.get(WordList,row.word_list_id)
        if not parent:
            raise HTTPException(403, "不能访问该词表。")
        if isinstance(row,WordListItem):
            if parent.owner_key != row.owner_key:
                raise HTTPException(403, "不能修改公共或他人的词表关联。")
        elif parent.owner_key not in {context.owner_key,PUBLIC_OWNER}:
            raise HTTPException(403, "不能向他人的词表写入学习记录。")
    if hasattr(row,"word_id") and row.word_id:
        parent = db.get(Word,row.word_id)
        if not parent:
            raise HTTPException(403, "不能访问该单词。")
        if isinstance(row,WordListItem) and parent.owner_key not in {row.owner_key,PUBLIC_OWNER}:
            raise HTTPException(403, "不能加入其他账号的私有单词。")


@event.listens_for(Session,"before_flush")
def protect_data_writes(db,*_):
    context = bind_session_scope(db)
    if context is None:
        return
    for row in list(db.new)+list(db.dirty)+list(db.deleted):
        model = type(row)
        module = module_for_model(model)
        if not module:
            if isinstance(row,(DataScopeGrant,DataPermissionState,AdminUserSetting)) and not context.can_write:
                raise HTTPException(403,"只读数据空间不能更改账号或授权。")
            if isinstance(row,(DataScopeGrant,DataPermissionState)) and not context.is_admin:
                raise HTTPException(403,"只有管理员可修改数据授权。")
            if isinstance(row,AdminUserSetting) and not context.is_admin:
                sensitive = {"role","permissions","phone","is_active","login_password_hash"}
                state = inspect(row)
                if row.id != context.actor_id or row in db.new or row in db.deleted or any(state.attrs[key].history.has_changes() for key in sensitive):
                    raise HTTPException(403,"没有账号管理权限。")
            continue
        if row not in db.new and row not in db.deleted and not db.is_modified(row,include_collections=False):
            continue
        if module not in context.modules or not context.can_write:
            raise HTTPException(403,"此数据空间仅供查看，不能修改。")
        if isinstance(row,DataOwnerMixin):
            state = inspect(row)
            if row in db.new and row.owner_key in (None,"legacy"):
                row.owner_key = context.owner_key
            elif row not in db.new and state.attrs.owner_key.history.has_changes():
                raise HTTPException(403,"不能更改记录归属。")
            if row.owner_key != context.owner_key:
                raise HTTPException(403,"不能修改公共或其他账号的数据。")
            if context.public_write and row in db.deleted:
                raise HTTPException(403,"不能删除公共词库的数据。")
            if row not in db.deleted:
                check_foreign_keys(db,row,context)
        elif row.phone != context.owner_phone:
            raise HTTPException(403,"不能修改其他账号的个人记录。")
        if row not in db.deleted:
            from app.data_media import assert_media_access, WORD_URL_FIELDS
            fields = WORD_URL_FIELDS if isinstance(row,(Word,)) else ("cover_url",)
            state = inspect(row)
            for field in fields:
                value = getattr(row,field,None)
                if str(value or "").startswith("/media/") and (row in db.new or state.attrs[field].history.has_changes()):
                    assert_media_access(value,db)
