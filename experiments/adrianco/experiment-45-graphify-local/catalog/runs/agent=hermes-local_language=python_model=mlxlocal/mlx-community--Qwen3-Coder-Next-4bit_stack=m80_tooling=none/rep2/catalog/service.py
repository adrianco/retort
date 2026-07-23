"""Catalog facade orchestrating the store and loan services."""
from catalog.loans import LoanError, ReservationError, LoanService
from catalog.models import Book, Member, Reservation
from catalog.store import Store


class Catalog:
    def __init__(self) -> None:
        self.store = Store()
        self.loans = LoanService(self.store)

    def add_book(self, id: int, title: str, author: str, copies: int = 1) -> Book:
        return self.store.add_book(Book(id=id, title=title, author=author, copies=copies))

    def add_member(self, id: int, name: str) -> Member:
        return self.store.add_member(Member(id=id, name=name))

    def borrow(self, member_id: int, book_id: int):
        return self.loans.borrow(member_id, book_id)

    def return_book(self, member_id: int, book_id: int) -> None:
        self.loans.return_book(member_id, book_id)

    def availability(self, book_id: int) -> int:
        return self.loans.available(book_id)

    def reserve(self, member_id: int, book_id: int) -> Reservation:
        return self.loans.reserve(member_id, book_id)

    def cancel_reservation(self, member_id: int, book_id: int) -> None:
        self.loans.cancel_reservation(member_id, book_id)

    def list_reservations(self, book_id: int) -> list[int]:
        return self.loans.list_reservations(book_id)
