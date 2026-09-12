from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import (
    declarative_base,
    relationship
)


Base = declarative_base()


# =========================================================
# USER MODEL
# =========================================================

class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    name = Column(
        String(120),
        nullable=False
    )

    email = Column(
        String(180),
        unique=True,
        nullable=False,
        index=True
    )

    # 255 is safer for Werkzeug password hashes
    password = Column(
        String(255),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    reports = relationship(
        "AnalysisReport",
        back_populates="user",
        cascade="all, delete-orphan"
    )


# =========================================================
# ANALYSIS REPORT MODEL
# =========================================================

class AnalysisReport(Base):

    __tablename__ = "analysis_reports"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    target_role = Column(
        String(180),
        nullable=False
    )

    filename = Column(
        String(255),
        default="",
        nullable=True
    )

    resume_text = Column(
        Text,
        default="",
        nullable=True
    )

    # Stores complete AI analysis JSON
    result = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="reports"
    )