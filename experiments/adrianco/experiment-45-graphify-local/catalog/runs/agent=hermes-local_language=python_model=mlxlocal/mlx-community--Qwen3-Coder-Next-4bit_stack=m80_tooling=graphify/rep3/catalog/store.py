"""In-memory persistence for books, members, and reservations."""
from catalog.models import Book, Member, Reservation


class Store:
    def __init__(self) -> None:
        self._books: dict[int, Book] = {}
        self._members: dict[int, Member] = {}
        self._reservations: list[Reservation] = []

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

    def add_reservation(self, reservation: Reservation) -> Reservation:
        self._reservations.append(reservation)
        return reservation

    def get_reservations(self, book_id: int) -> list[Reservation]:
        return [r for r in self._reservations if r.book_id == book_id]

    def remove_reservation(self, reservation: Reservation) -> None:
        self._reservations.remove(reservation)

    def get_reservation(self, member_id: int, book_id: int) -> Reservation | None:
        for r in self._reservations:
            if r.member_id == member_id and r.book_id == book_id:
                return r
        return None
