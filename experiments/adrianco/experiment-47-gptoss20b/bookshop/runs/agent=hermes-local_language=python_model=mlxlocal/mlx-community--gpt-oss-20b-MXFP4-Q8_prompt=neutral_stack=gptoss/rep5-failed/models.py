from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel
from typing import Optional

Base = declarative_base()

class BookModel(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    isbn = Column(String, nullable=True)

class Book(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

    class Config:
        orm_mode = True

class BookCreate(BaseModel):
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    isbn: Optional[str] = None
