"""HTTP boundary for verified data scopes. No browser-supplied owner is trusted."""
from dataclasses import replace
import hashlib
import hmac
import json
import re
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from urllib.parse import quote
from starlette.concurrency import run_in_threadpool

from app.data_context import DATA_MODULES, current_data_context, data_context
from app.data_permissions import resolve_data_context
from app.models import AdminUserSetting, DataPermissionState, DataScopeGrant, Word, WordList

SCOPE_COOKIE = "newabby_data_scope"
CACHE_COOKIE = "newabby_data_cache"
MIGRATION_KEY = "ownership-v1"
MODULE_LABELS = {"words":"单词表", "learning":"学习记录", "writing":"作文、日记与辩论", "cats":"猫咪世界", "books":"书摘"}


def module_for_path(path):
    if path.startswith(("/api/vue/admin", "/admin")):
        return "admin"
    if path.startswith(("/booklearner", "/api/vue/booklearner")):
        return "books"
    if path.startswith(("/api/vue/essays", "/essays", "/api/vue/diary", "/diary", "/api/vue/debate", "/debate")):
        return "writing"
    if path.startswith(("/api/vue/cat-world", "/cat-world")):
        return "cats"
    if path.startswith(("/api/challenge", "/challenge", "/api/vue/challenge", "/api/vue/wrong-words", "/wrong-words", "/api/vue/fun-math", "/fun-math")):
        return "learning"
    if path.startswith(("/api/vue/words", "/words", "/api/vue/lists", "/lists", "/api/vue/spb", "/spb", "/upload", "/api/vue/upload")):
        return "words"
    return None


def signed_scope(actor_id, owner_id, sign):
    payload = f"scope-v1:{actor_id}:{owner_id}"
    return f"{payload}:{sign(payload)}"


def read_scope(value, actor_id, sign):
    if not value:
        return actor_id
    parts = str(value).split(":")
    if len(parts) != 4 or parts[0] != "scope-v1" or not parts[1].isdigit() or not parts[2].isdigit():
        raise HTTPException(403,"无效的数据空间选择。请切回自己的数据。")
    payload = ":".join(parts[:3])
    if int(parts[1]) != actor_id or not hmac.compare_digest(parts[3],sign(payload)):
        raise HTTPException(403,"数据空间签名无效。请切回自己的数据。")
    return int(parts[2])


def scope_payload(db):
    context = current_data_context()
    if not context:
        return None
    if context.is_admin:
        owners = db.scalars(select(AdminUserSetting).order_by(AdminUserSetting.id)).all()
    else:
        granted_ids = select(DataScopeGrant.owner_id).where(DataScopeGrant.grantee_id==context.actor_id)
        owners = db.scalars(select(AdminUserSetting).where(
            (AdminUserSetting.id==context.actor_id) | (AdminUserSetting.id.in_(granted_ids) & AdminUserSetting.is_active.is_(True))
        ).order_by(AdminUserSetting.id)).all()
    # Resolve every option again: a stale grant must not make a viewer a teacher.
    actor = db.get(AdminUserSetting,context.actor_id)
    choices = []
    for owner in owners:
        try:
            verified = resolve_data_context(db,actor,owner.id)
        except HTTPException:
            continue
        choices.append({"id":owner.id,"name":owner.username or f"用户{owner.id}",
            "isSelf":owner.id==context.actor_id,"modules":sorted(verified.modules)})
    selected = next((item for item in choices if item["id"]==context.owner_id),None)
    return {"actorId":context.actor_id,"ownerId":context.owner_id,"ownerName":selected["name"] if selected else "我的数据",
        "readOnly":not context.can_write,"modules":sorted(context.modules),"options":choices}


class DataScopeMiddleware:
    def __init__(self, app, *, enabled, session_factory, authenticated_phone, signer, media_check=None, session_stamp=lambda request: "", maintenance_file=lambda: ""):
        self.app, self.enabled = app, enabled
        self.session_factory, self.authenticated_phone, self.signer = session_factory, authenticated_phone, signer
        self.media_check = media_check
        self.session_stamp = session_stamp
        self.maintenance_file = maintenance_file

    def resolve(self,request):
        phone = self.authenticated_phone(request)
        if not phone:
            raise HTTPException(401,"请先用手机号登录。")
        with self.session_factory() as db:
            try:
                ready = db.get(DataPermissionState,MIGRATION_KEY)
            except Exception:
                raise HTTPException(503,"账号数据隔离尚未完成迁移，暂不开放访问。") from None
            if not ready or ready.value != "ready":
                raise HTTPException(503,"账号数据隔离尚未完成迁移，暂不开放访问。")
            actor = db.scalar(select(AdminUserSetting).where(AdminUserSetting.phone==phone))
            if not actor or not actor.is_active:
                raise HTTPException(403,"账号不可用。")
            # Selection endpoints always operate as the actor, so a revoked or
            # invalid old cookie cannot prevent returning to one's own space.
            owner_id = actor.id if request.url.path=="/api/vue/data-scope" else read_scope(request.cookies.get(SCOPE_COOKIE),actor.id,self.signer)
            context = resolve_data_context(db,actor,owner_id)
            # A caller may reduce its own rights for a side-effect-free audit.
            # This is never an authorization bypass or a way to expand scope.
            if request.headers.get('X-Newabby-Read-Only')=='1':
                context=replace(context,read_only=True)
            if request.url.path.startswith(("/spb","/api/vue/spb")):
                context = replace(context,catalog_only=True)
                if request.method not in {"GET","HEAD","OPTIONS"}:
                    if not context.is_admin or not context.can_write:
                        raise HTTPException(403,"官方词库由管理员维护；个人修改请先复制到自己的词表。")
                    context=replace(context,public_write=True)
            return context

    async def __call__(self,scope,receive,send):
        if not self.enabled() or scope["type"]!="http":
            return await self.app(scope,receive,send)
        request = Request(scope)
        path = request.url.path
        # A one-time release gate keeps real writers out until the restored
        # database and real-account read-only HTTP checks have passed. Possessing
        # this token only bypasses maintenance, never normal authentication.
        maintenance = str(self.maintenance_file() or "")
        if maintenance:
            try:
                token_path = Path(maintenance)
                if token_path.exists():
                    expected = token_path.read_text(encoding="utf8").strip()
                    supplied = request.headers.get("X-Newabby-Release-Check", "")
                    if not expected or not hmac.compare_digest(expected, supplied):
                        return await JSONResponse({"detail":"正在升级账号数据隔离，请稍后刷新。"},status_code=503,
                            headers={"Cache-Control":"private, no-store","Retry-After":"60"})(scope,receive,send)
            except OSError:
                return await JSONResponse({"detail":"升级校验尚未完成，暂不开放访问。"},status_code=503,
                    headers={"Cache-Control":"private, no-store"})(scope,receive,send)
        if path in {"/login","/logout","/favicon.ico"} or path.startswith("/static/") or request.method=="OPTIONS":
            return await self.app(scope,receive,send)
        try:
            context = await run_in_threadpool(self.resolve,request)
            module = module_for_path(path)
            if module == "admin" and (not context.is_admin or not context.can_write):
                raise HTTPException(403,"只有管理员在自己的数据空间可管理网站。")
            if module and module != "admin" and module not in context.modules:
                raise HTTPException(403,"没有此模块的数据查看授权。")
            if not context.can_write and request.method not in {"GET","HEAD"} and path!="/api/vue/data-scope":
                raise HTTPException(403,"正在只读查看其他账号，不能修改数据。")
            if not context.can_write and path=="/booklearner/api/analyze":
                raise HTTPException(403,"只读查看时不能创建新的书籍分析。")
            with data_context(context):
                if request.method not in {"GET","HEAD","OPTIONS"}:
                    await run_in_threadpool(self.check_target_write,path,context)
                if path.startswith("/media/") and self.media_check:
                    await run_in_threadpool(self.media_check,request)
                marker = ("w-" if context.can_write else "r-")+self.signer("data-cache-v1:"+self.session_stamp(request)+":"+repr(context.client_key))[:32]
                async def protected_send(message):
                    if message["type"]=="http.response.start":
                        headers = [(k,v) for k,v in message.get("headers",[]) if k.lower() not in {b"cache-control",b"pragma",b"expires"}]
                        headers.extend([(b"cache-control",b"private, no-store"),(b"pragma",b"no-cache"),
                            (b"x-newabby-scope",marker.encode()),(b"vary",b"Cookie")])
                        secure = "; Secure" if request.url.scheme=="https" else ""
                        if not path.startswith(("/api/","/booklearner/api/","/media/")):
                            headers.append((b"set-cookie",f"{CACHE_COOKIE}={marker}; Path=/; SameSite=Lax{secure}".encode()))
                        message["headers"] = headers
                    await send(message)
                await self.app(scope,receive,protected_send)
        except HTTPException as exc:
            api_path=path.startswith(("/api/","/booklearner/api/","/media/"))
            if exc.status_code==401 and not api_path:
                target=path+("?"+request.url.query if request.url.query else "")
                return await RedirectResponse('/login?next='+quote(target,safe=''),status_code=303)(scope,receive,send)
            await JSONResponse({"detail":exc.detail},status_code=exc.status_code)(scope,receive,send)

    def check_target_write(self,path,context):
        word_match=re.match(r"^/(?:api/vue/)?words/(\d+)(?:/|$)",path)
        list_match=re.match(r"^/(?:api/vue/)?lists/(\d+)(?:/|$)",path)
        if not word_match and (not list_match or path.endswith('/personal-copy')):
            return
        model=Word if word_match else WordList
        identity=int((word_match or list_match).group(1))
        with self.session_factory() as db:
            target=db.get(model,identity)
            if not target: raise HTTPException(404,"记录不存在。")
            if target.owner_key!=context.owner_key:
                raise HTTPException(403,"官方词库为公共只读，请先复制到自己的词表。")
