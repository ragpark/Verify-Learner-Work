from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings
from .models import Base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings
import sys

def get_engine():
    url = settings.DATABASE_URL or "sqlite:///./app.db"
    try:
        engine = create_engine(url, pool_pre_ping=True)
    except Exception as e:
        print(f"[WARN] Invalid DATABASE_URL='{url}': {e}", file=sys.stderr)
        print("[WARN] Falling back to sqlite:///./app.db", file=sys.stderr)
        engine = create_engine("sqlite:///./app.db", pool_pre_ping=True)
    return engine

engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    from .models import Base
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[WARN] init_db failed: {e}", file=sys.stderr)

def get_engine():
    url = settings.DATABASE_URL or "sqlite:///./app.db"
    engine = create_engine(url, pool_pre_ping=True)
    return engine

engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    Base.metadata.create_all(bind=engine)
