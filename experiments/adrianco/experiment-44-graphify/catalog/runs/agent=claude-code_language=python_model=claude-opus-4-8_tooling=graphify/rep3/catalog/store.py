"""In-memory persistence for books and members."""
from catalog.models import Book, Member


class Store:
    def __init__(self) -> None:
        self._books: dict[int, Book] = {}
        self._members: dict[int, Member] = {}

    def add_book(self, book: Book) -> Book:
        self._books[book.id] = book
        return book

    def get_book(self, book_id: int) -> Book | None:
        return self._books.get(book_id)

    def list_books(self) -> list[Book]:
        return list(self._books.values())

    def add_member(self, member: Member) -> Member:
        self._members[member.id] = member
        return member

    def get_member(self, member_id: int) -> Member | None:
        return self._members.get(member_id)
