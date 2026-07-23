"""Domain data types."""
from dataclasses import dataclass


@dataclass
class Book:
    id: int
    title: str
    author: str
    copies: int = 1


@dataclass
class Member:
    id: int
    name: str


@dataclass
class Loan:
    book_id: int
    member_id: int


@dataclass
class Reservation:
    book_id: int
    member_id: int
