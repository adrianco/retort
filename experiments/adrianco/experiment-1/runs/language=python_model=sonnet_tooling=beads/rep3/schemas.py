from pydantic import BaseModel
from typing import Optional


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


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int] = None
    isbn: Optional[str] = None

    model_config = {"from_attributes": True}
