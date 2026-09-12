from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from dotenv import load_dotenv


load_dotenv()


# =========================================================
# DATABASE URL
# =========================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///career_copilot.db"
)


# =========================================================
# SQLITE SPECIAL CONFIG
# =========================================================

connect_args = {}

if DATABASE_URL.startswith("sqlite"):

    connect_args = {
        "check_same_thread": False
    }


# =========================================================
# ENGINE
# =========================================================

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)


# =========================================================
# SESSION FACTORY
# =========================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# =========================================================
# OPTIONAL DB SESSION HELPER
# =========================================================

def get_db_session():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()