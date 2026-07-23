"""Reservation logic, layered on the Store and LoanService.

A member may reserve a book only when it has no available copies. Reservations
are FIFO and are fulfilled automatically when a copy is returned.
"""
from catalog.loans import LoanError, LoanService
from catalog.models import Reservation
from catalog.store import Store


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
            raise LoanError(f"unknown member {member_id}")
        # available() validates the book exists (raises for unknown book).
        if self.loans.available(book_id) > 0:
            raise LoanError(f"book {book_id} still has copies available")
        if self._find(member_id, book_id) is not None:
            raise LoanError(f"member {member_id} already reserved book {book_id}")
        reservation = Reservation(book_id=book_id, member_id=member_id)
        self.reservations.append(reservation)
        return reservation

    def cancel(self, member_id: int, book_id: int) -> None:
        reservation = self._find(member_id, book_id)
        if reservation is None:
            raise LoanError(f"member {member_id} has no reservation for book {book_id}")
        self.reservations.remove(reservation)

    def list_reservations(self, book_id: int) -> list[int]:
        return [r.member_id for r in self.reservations if r.book_id == book_id]

    def fulfill_next(self, book_id: int) -> Reservation | None:
        """Grant the loan to the earliest reserver of book_id, if any.

        Assumes a copy has just become available (e.g. after a return).
        """
        for reservation in self.reservations:
            if reservation.book_id == book_id:
                self.reservations.remove(reservation)
                self.loans.borrow(reservation.member_id, book_id)
                return reservation
        return None
