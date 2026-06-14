import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL comes from environment variable (set via ConfigMap/Secret in k8s,
# or docker-compose env, or local .env file)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://chatuser:chatpass@localhost:5432/chatdb"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
