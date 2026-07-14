from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Optional

DATABASE_URL = "sqlite:///./books.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class BookRecord(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    isbn = Column(String, nullable=True)


class BookIn(BaseModel):
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

    @field_validator("title", "author")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int]
    isbn: Optional[str]

    model_config = {"from_attributes": True}


app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/books", response_model=BookOut, status_code=201)
def create_book(book: BookIn):
    db = SessionLocal()
    try:
        record = BookRecord(**book.model_dump())
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()


@app.get("/books", response_model=list[BookOut])
def list_books(author: Optional[str] = None):
    db = SessionLocal()
    try:
        q = db.query(BookRecord)
        if author:
            q = q.filter(BookRecord.author == author)
        return q.all()
    finally:
        db.close()


@app.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int):
    db = SessionLocal()
    try:
        record = db.get(BookRecord, book_id)
        if not record:
            raise HTTPException(status_code=404, detail="Book not found")
        return record
    finally:
        db.close()


@app.put("/books/{book_id}", response_model=BookOut)
def update_book(book_id: int, book: BookIn):
    db = SessionLocal()
    try:
        record = db.get(BookRecord, book_id)
        if not record:
            raise HTTPException(status_code=404, detail="Book not found")
        for field, value in book.model_dump().items():
            setattr(record, field, value)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()


@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    db = SessionLocal()
    try:
        record = db.get(BookRecord, book_id)
        if not record:
            raise HTTPException(status_code=404, detail="Book not found")
        db.delete(record)
        db.commit()
    finally:
        db.close()
