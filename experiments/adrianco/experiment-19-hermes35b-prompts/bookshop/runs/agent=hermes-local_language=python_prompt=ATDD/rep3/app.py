"""Book Collection REST API service."""

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from models import (
    BookCreate,
    BookResponse,
    BookUpdate,
    BookModel,
    init_db,
    engine,
)

app = FastAPI(title="Book Collection API")


@app.on_event("startup")
def on_startup():
    init_db()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /books — Create a new book
# ---------------------------------------------------------------------------
@app.post("/books", status_code=201)
def create_book(book: BookCreate):
    """Create a new book in the collection."""
    with Session(engine) as session:
        now = _now_iso()
        db_book = BookModel(
            title=book.title,
            author=book.author,
            year=book.year,
            isbn=book.isbn,
            created_at=now,
            updated_at=now,
        )
        session.add(db_book)
        session.commit()
        session.refresh(db_book)
    return _book_to_response(db_book)


# ---------------------------------------------------------------------------
# GET /books — List all books (with optional ?author= filter)
# ---------------------------------------------------------------------------
@app.get("/books")
def list_books(author: str | None = None):
    """List all books; optionally filter by author."""
    with Session(engine) as session:
        if author is not None:
            books = session.query(BookModel).filter(BookModel.author == author).all()
        else:
            books = session.query(BookModel).all()
    return [_book_to_response(b) for b in books]


# ---------------------------------------------------------------------------
# GET /books/{id} — Get a single book
# ---------------------------------------------------------------------------
@app.get("/books/{book_id}")
def get_book(book_id: int):
    """Get a single book by its ID."""
    with Session(engine) as session:
        book = session.query(BookModel).get(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return _book_to_response(book)


# ---------------------------------------------------------------------------
# PUT /books/{id} — Update a book
# ---------------------------------------------------------------------------
@app.put("/books/{book_id}")
def update_book(book_id: int, book_update: BookUpdate):
    """Update an existing book."""
    with Session(engine) as session:
        book = session.query(BookModel).get(book_id)
        if book is None:
            raise HTTPException(status_code=404, detail="Book not found")

        # Apply only provided fields
        update_data = book_update.model_dump(exclude_unset=True)
        if not update_data:
            return _book_to_response(book)

        for key, value in update_data.items():
            setattr(book, key, value)
        book.updated_at = _now_iso()
        session.commit()
        session.refresh(book)
    return _book_to_response(book)


# ---------------------------------------------------------------------------
# DELETE /books/{id} — Delete a book
# ---------------------------------------------------------------------------
@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    """Delete a book by its ID."""
    with Session(engine) as session:
        book = session.query(BookModel).get(book_id)
        if book is None:
            raise HTTPException(status_code=404, detail="Book not found")
        session.delete(book)
        session.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_iso():
    from datetime import datetime
    return datetime.utcnow().isoformat()


def _book_to_response(book: BookModel):
    return BookResponse(
        id=book.id,
        title=book.title,
        author=book.author,
        year=book.year,
        isbn=book.isbn,
        created_at=book.created_at,
        updated_at=book.updated_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
