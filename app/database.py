from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

class DataScopedSession(Session):
    """Session.get's identity-map fast path must enforce the same read policy."""
    def get(self, entity, ident, **kwargs):
        from app.data_permissions import bind_session_scope, instance_is_readable
        context = bind_session_scope(self)
        row = super().get(entity,ident,**kwargs)
        return row if row is None or context is None or instance_is_readable(row,context) else None


SessionLocal = sessionmaker(bind=engine, class_=DataScopedSession, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
