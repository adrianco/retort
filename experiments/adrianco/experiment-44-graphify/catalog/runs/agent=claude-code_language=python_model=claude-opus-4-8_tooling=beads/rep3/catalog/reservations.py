"""Reservation logic, layered on the Store and LoanService.

A member may reserve a book that currently has no available copies. Reservations
are kept in FIFO order per book and fulfilled automatically when a copy frees up.
"""
from catalog.loans import LoanService
from catalog.models import Reservation
from catalog.store import Store


class ReservationError(Exception):
    pass


class ReservationService:
    def __init__(self, store: Store, loans: LoanService) -> None:
        self.store = store
        self.loans = loans
        self.reservations: list[Reservation] = []

    def _find(self, member_id: int, book_id: int) -> Reservation | None:
        for reservation in self.reservations:
            if reservation.book_id == book_id and reservation.member_id == member_id:
                return reservation
        return None

    def reserve(self, member_id: int, book_id: int) -> Reservation:
        if self.store.get_member(member_id) is None:
            raise ReservationError(f"unknown member {member_id}")
        if self.store.get_book(book_id) is None:
            raise ReservationError(f"unknown book {book_id}")
        if self.loans.available(book_id) > 0:
            raise ReservationError(
                f"book {book_id} still has copies available; borrow it instead"
            )
        if self._find(member_id, book_id) is not None:
            raise ReservationError(
                f"member {member_id} already reserved book {book_id}"
            )
        reservation = Reservation(book_id=book_id, member_id=member_id)
        self.reservations.append(reservation)
        return reservation

    def cancel_reservation(self, member_id: int, book_id: int) -> None:
        reservation = self._find(member_id, book_id)
        if reservation is None:
            raise ReservationError(
                f"member {member_id} has no reservation for book {book_id}"
            )
        self.reservations.remove(reservation)

    def list_reservations(self, book_id: int) -> list[int]:
        """Reserving member ids for a book, in the order they were made (FIFO)."""
        return [r.member_id for r in self.reservations if r.book_id == book_id]

    def fulfill_next(self, book_id: int) -> Reservation | None:
        """Give a freed copy to the earliest reserver, if any, and drop it.

        Returns the fulfilled reservation, or None if there were none pending.
        """
        for reservation in self.reservations:
            if reservation.book_id == book_id:
                self.reservations.remove(reservation)
                self.loans.borrow(reservation.member_id, book_id)
                return reservation
        return None
