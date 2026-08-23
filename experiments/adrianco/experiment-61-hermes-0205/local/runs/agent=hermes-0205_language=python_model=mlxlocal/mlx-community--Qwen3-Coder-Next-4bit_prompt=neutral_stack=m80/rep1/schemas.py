from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class BookBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    year: int = Field(ge=1440, le=2100)
    isbn: str = Field(min_length=10, max_length=13)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    title: Optional[str] = Field(None, min_length=1)
    author: Optional[str] = Field(None, min_length=1)
    year: Optional[int] = Field(None, ge=1440, le=2100)
    isbn: Optional[str] = Field(None, min_length=10, max_length=13)


class Book(BookBase):
    id: Optional[int] = None
