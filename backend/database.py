from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./backend/dashboard.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_sqlite_schema() -> None:
    """Apply additive migrations for existing SQLite files (create_all skips new columns)."""
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(employees)")).fetchall()
        colnames = {r[1] for r in rows}
        if "email" not in colnames:
            conn.execute(text("ALTER TABLE employees ADD COLUMN email VARCHAR DEFAULT ''"))


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
