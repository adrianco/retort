from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import Book as BookModel
from schemas import BookCreate, BookUpdate


def get_book(db: Session, book_id: int):
    return db.query(BookModel).filter(BookModel.id == book_id).first()


def get_books(db: Session, author: Optional[str] = None):
    if author:
        return db.query(BookModel).filter(BookModel.author == author).all()
    return db.query(BookModel).all()


def create_book(db: Session, book: BookCreate):
    db_book = BookModel(
        title=book.title,
        author=book.author,
        year=book.year,
        isbn=book.isbn
    )
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


def update_book(db: Session, book_id: int, book: BookUpdate):
    db_book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if db_book is None:
        return None
    
    update_data = book.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_book, key, value)
    
    db.commit()
    db.refresh(db_book)
    return db_book


def delete_book(db: Session, book_id: int):
    db_book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if db_book is None:
        return False
    
    db.delete(db_book)
    db.commit()
    return True
