from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, Session

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books.db')
SQLALCHEMY_URL = f'sqlite:///{DB_PATH}'

engine = create_engine(SQLALCHEMY_URL, connect_args={'check_same_thread': False})
Base = declarative_base()


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model
# ---------------------------------------------------------------------------
class BookModel(Base):
    __tablename__ = 'books'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    isbn = Column(String, nullable=True)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


def init_db():
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def delete_db():
    """Remove the database file so tests start from a clean slate."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


# ---------------------------------------------------------------------------
# Pydantic schemas (API contract)
# ---------------------------------------------------------------------------
class BookCreate(BaseModel):
    """Request body for creating a book."""

    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookUpdate(BaseModel):
    """Request body for updating a book (all fields optional)."""

    title: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookResponse(BaseModel):
    """Response body returned to the client."""

    id: int
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None
    created_at: str
    updated_at: str
