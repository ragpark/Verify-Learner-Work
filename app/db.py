from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings
from .models import Base

def get_engine():
    url = settings.DATABASE_URL or "sqlite:///./app.db"
    engine = create_engine(url, pool_pre_ping=True)
    return engine

engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    Base.metadata.create_all(bind=engine)
