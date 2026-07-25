"""Main entry point for the Book Collection REST API service.

The service is implemented using FastAPI and SQLAlchemy with an SQLite backend.
"""

from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from database import SessionLocal, engine, Base
from models import Book
from schemas import BookCreate, BookRead, BookUpdate

app = FastAPI(title="Book Collection API")

# Create database tables on startup
@app.on_event("startup")
async def on_startup():
    Base.metadata.create_all(bind=engine)

# Dependency for DB session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Health check endpoint
@app.get("/health", response_class=JSONResponse)
async def health():
    return {"status": "ok"}

# Create a new book
@app.post("/books", response_model=BookRead, status_code=status.HTTP_201_CREATED)
async def create_book(book: BookCreate, db: Session = Depends(get_db)):
    db_book = Book(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

# List all books, optional author filter
@app.get("/books", response_model=List[BookRead])
async def list_books(author: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Book)
    if author:
        query = query.filter(Book.author == author)
    return query.all()

# Retrieve a single book by id
@app.get("/books/{book_id}", response_model=BookRead)
async def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book

# Update a book
@app.put("/books/{book_id}", response_model=BookRead)
async def update_book(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    for key, value in book_update.dict(exclude_unset=True).items():
        setattr(book, key, value)
    db.commit()
    db.refresh(book)
    return book

# Delete a book
@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    db.delete(book)
    db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={})

# When run directly, start uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
