"""Request data ownership, independent of authentication and database imports."""
from collections.abc import MutableMapping
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Thread


PUBLIC_OWNER = "public"
DATA_MODULES = frozenset({"words", "learning", "writing", "cats", "books"})


@dataclass(frozen=True)
class DataContext:
    actor_id: int
    owner_id: int
    actor_phone: str
    owner_phone: str
    is_admin: bool = False
    modules: frozenset[str] = DATA_MODULES
    public_write: bool = False
    include_public: bool = True
    catalog_only: bool = False
    read_only: bool = False

    @property
    def owner_key(self):
        return PUBLIC_OWNER if self.public_write else f"u:{self.owner_id}"

    @property
    def can_write(self):
        return not self.read_only and (self.actor_id == self.owner_id or self.public_write)

    @property
    def cache_key(self):
        return (self.actor_id, self.owner_key, tuple(sorted(self.modules)), self.include_public, self.catalog_only, self.read_only)

    @property
    def client_key(self):
        # A route may temporarily select the shared catalog for DB queries.
        # That must NOT look like an account switch to a running SPA.
        return (self.actor_id, self.owner_id, tuple(sorted(self.modules)), self.is_admin, self.read_only)

    @property
    def job_key(self):
        return (self.actor_id, self.owner_id)


_context = ContextVar("newabby_data_context", default=None)


def current_data_context() -> DataContext | None:
    return _context.get()


@contextmanager
def data_context(context):
    token = _context.set(context)
    try:
        yield context
    finally:
        _context.reset(token)


@contextmanager
def public_data_context():
    current = current_data_context()
    if current is None or not current.is_admin or not current.can_write:
        raise PermissionError("Only an administrator in their own workspace can maintain the public catalog")
    with data_context(replace(current, public_write=True, include_public=True, catalog_only=True)) as context:
        yield context


class ContextThread(Thread):
    """Every new worker retains its creator's verified scope, not global state."""
    def __init__(self, *args, **kwargs):
        self._data_context = copy_context()
        super().__init__(*args, **kwargs)

    def run(self):
        self._data_context.run(super().run)


class ScopedJobStore(MutableMapping):
    """Opaque job IDs cannot be used to read or stop a different owner's task."""
    def __init__(self, *, public_catalog=False):
        self._items = {}
        self.public_catalog=public_catalog

    def _namespace(self):
        context=current_data_context()
        if context and self.public_catalog and context.is_admin and context.catalog_only:
            return ("public-catalog",)
        return context.job_key if context else None

    def _key(self, key):
        return (self._namespace(), key)

    def __getitem__(self, key):
        return self._items[self._key(key)]

    def __setitem__(self, key, value):
        self._items[self._key(key)] = value

    def __delitem__(self, key):
        del self._items[self._key(key)]

    def __iter__(self):
        namespace = self._namespace()
        return iter([key for (owner, key) in list(self._items) if owner == namespace])

    def __len__(self):
        return sum(1 for _ in self)


def owner_media_directory(base: Path) -> Path:
    context = current_data_context()
    if context is None:
        return Path(base)
    if context.public_write:
        base=Path(base)
        return base.parent / "public" / base.name
    if not context.can_write:
        from fastapi import HTTPException
        raise HTTPException(403,"只读数据空间不能创建或管理上传文件。")
    base = Path(base)
    return base.parent / "users" / f"u{context.owner_id}" / base.name


def media_url_for_file(path: Path, media_root: Path) -> str:
    relative = Path(path).resolve().relative_to(Path(media_root).resolve())
    return "/media/" + relative.as_posix()


class DataMediaDirectory:
    """Resolve a legacy upload directory at use time, including worker threads."""
    def __init__(self, base):
        self.base = Path(base)

    def path(self):
        return owner_media_directory(self.base)

    def __fspath__(self):
        return str(self.path())

    def __truediv__(self, child):
        return self.path() / child

    def __getattr__(self, name):
        return getattr(self.path(), name)


def upload_url(target: Path, kind: str) -> str:
    """Keep old unscoped paths usable while all NEW writes get an owner path."""
    target = Path(target)
    parts = target.parts
    if len(parts)>=4 and parts[-4]=="users" and parts[-2]==kind:
        return "/media/"+Path(*parts[-4:]).as_posix()
    if len(parts)>=3 and parts[-3]=="public" and parts[-2]==kind:
        return "/media/"+Path(*parts[-3:]).as_posix()
    return f"/media/{kind}/{target.name}"


def data_owner_phone(fallback):
    context = current_data_context()
    return context.owner_phone if context else fallback
