from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from ..core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)
    if "sqlite" in DATABASE_URL:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(tasks)"))
            columns = [row[1] for row in result.fetchall()]
            if columns and "completed_at" not in columns:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN completed_at DATETIME"))
                conn.commit()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
