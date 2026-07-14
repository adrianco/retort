from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status

from app import crud, database
from app.schemas import Book, BookCreate, BookUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(title="Book Collection API", lifespan=lifespan)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_book(book: BookCreate):
    book_id = crud.create_book(book)
    return Book(id=book_id, **book.model_dump())


@app.get("/books", response_model=List[Book])
def list_books(author: Optional[str] = None):
    return crud.list_books(author=author)


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int):
    book = crud.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, book: BookUpdate):
    updated = crud.update_book(book_id, book)
    if not updated:
        raise HTTPException(status_code=404, detail="Book not found")
    return Book(id=book_id, **book.model_dump())


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int):
    deleted = crud.delete_book(book_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Book not found")
    return None
