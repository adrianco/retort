"""SQLAlchemy model definitions for the Book Collection API."""

from sqlalchemy import Column, Integer, String
from database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    isbn = Column(String, nullable=True)

    def __repr__(self):
        return f"<Book(id={self.id!r}, title={self.title!r})>"
