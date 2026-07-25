"""FastAPI application for managing a book collection.

The application exposes REST endpoints for CRUD operations on books and a health check.
Database is SQLite. The schema is a simple `books` table with columns: id, title, author, year, isbn.

The app is intentionally minimal and self‑contained so it can be started with:

    uvicorn app:app --reload

"""

from __future__ import annotations

import os
from typing import List, Optional, Generator

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, Integer, MetaData, String, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///file::memory:?cache=shared")
engine: Engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Book(Base):
    """SQLAlchemy model for a book."""

    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    isbn = Column(String, nullable=True)


# Create tables if they don't exist
Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookUpdate(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int]
    isbn: Optional[str]

    class Config:
        orm_mode = True


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Book Collection API")


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session for request-scoped usage."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Health check endpoint
@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(content={"status": "ok"})


# Create a new book
@app.post("/books", response_model=BookOut, status_code=status.HTTP_201_CREATED)
async def create_book(book: BookCreate, db: Session = Depends(get_db)):
    db_book = Book(**book.dict())
    db.add(db_book)
    try:
        db.commit()
        db.refresh(db_book)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return db_book


# List books, optional author filter
@app.get("/books", response_model=List[BookOut])
async def list_books(
    author: Optional[str] = Query(None, description="Filter by author name"),
    db: Session = Depends(get_db),
):
    stmt = select(Book)
    if author:
        stmt = stmt.where(Book.author == author)
    books = db.execute(stmt).scalars().all()
    return books


# Get a single book by ID
@app.get("/books/{book_id}", response_model=BookOut)
async def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


# Update a book
@app.put("/books/{book_id}", response_model=BookOut)
async def update_book(book_id: int, book: BookUpdate, db: Session = Depends(get_db)):
    db_book = db.get(Book, book_id)
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    for key, value in book.dict().items():
        setattr(db_book, key, value)
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


# Delete a book
@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int, db: Session = Depends(get_db)):
    db_book = db.get(Book, book_id)
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(db_book)
    db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={})


# ---------------------------------------------------------------------------
# For manual testing: run with `uvicorn app:app --reload`
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

"""
The module exposes the FastAPI `app` object.
"""
