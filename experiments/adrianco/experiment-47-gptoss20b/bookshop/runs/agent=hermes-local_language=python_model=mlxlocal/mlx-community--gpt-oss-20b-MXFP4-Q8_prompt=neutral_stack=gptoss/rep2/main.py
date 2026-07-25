"""
FastAPI application for managing a book collection.
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from typing import List, Optional
import sqlalchemy
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import os

# Database setup
DATABASE_URL = "sqlite:///./books.db"
engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Book ORM model
class BookORM(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    isbn = Column(String, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic schemas
class BookBase(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: Optional[int] = None
    isbn: Optional[str] = None

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    isbn: Optional[str] = None

class Book(BookBase):
    id: int

    class Config:
        orm_mode = True

app = FastAPI(title="Book Collection API")

# Dependency for DB session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Create a new book
@app.post("/books", status_code=201, response_model=Book)
async def create_book(book: BookCreate, db: Session = Depends(get_db)):
    db_book = BookORM(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

# List books, optional author filter
@app.get("/books", response_model=List[Book])
async def list_books(
    author: Optional[str] = Query(None, description="Filter by author name"),
    db: Session = Depends(get_db),
):
    query = db.query(BookORM)
    if author:
        query = query.filter(BookORM.author == author)
    books = query.all()
    return books

# Get single book by ID
@app.get("/books/{book_id}", response_model=Book)
async def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(BookORM).filter(BookORM.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

# Update a book
@app.put("/books/{book_id}", response_model=Book)
async def update_book(book_id: int, book_in: BookUpdate, db: Session = Depends(get_db)):
    book = db.query(BookORM).filter(BookORM.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    update_data = book_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(book, key, value)
    db.commit()
    db.refresh(book)
    return book

# Delete a book
@app.delete("/books/{book_id}")
async def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(BookORM).filter(BookORM.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    return JSONResponse(status_code=204, content=None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
