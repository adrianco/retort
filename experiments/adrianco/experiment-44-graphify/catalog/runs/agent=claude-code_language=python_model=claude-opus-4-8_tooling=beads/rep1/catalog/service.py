"""Catalog facade orchestrating the store and loan services."""
from catalog.loans import LoanService
from catalog.models import Book, Member
from catalog.reservations import ReservationService
from catalog.store import Store


class Catalog:
    def __init__(self) -> None:
        self.store = Store()
        self.loans = LoanService(self.store)
        self.reservations = ReservationService(self.store, self.loans)

    def add_book(self, id: int, title: str, author: str, copies: int = 1) -> Book:
        return self.store.add_book(Book(id=id, title=title, author=author, copies=copies))

    def add_member(self, id: int, name: str) -> Member:
        return self.store.add_member(Member(id=id, name=name))

    def borrow(self, member_id: int, book_id: int):
        return self.loans.borrow(member_id, book_id)

    def return_book(self, member_id: int, book_id: int) -> None:
        self.loans.return_book(member_id, book_id)
        # A returned copy is offered to the earliest reservation, if any, so the
        # copy never becomes generally available while members are waiting.
        next_member_id = self.reservations.pop_earliest(book_id)
        if next_member_id is not None:
            self.loans.borrow(next_member_id, book_id)

    def availability(self, book_id: int) -> int:
        return self.loans.available(book_id)

    def reserve(self, member_id: int, book_id: int):
        return self.reservations.reserve(member_id, book_id)

    def cancel_reservation(self, member_id: int, book_id: int) -> None:
        self.reservations.cancel(member_id, book_id)

    def list_reservations(self, book_id: int) -> list[int]:
        return self.reservations.list_for(book_id)
