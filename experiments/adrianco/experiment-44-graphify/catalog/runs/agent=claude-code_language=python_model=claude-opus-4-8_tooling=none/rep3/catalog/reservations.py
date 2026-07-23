"""Reservation logic, layered on the Store and LoanService."""
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

    def _for_book(self, book_id: int) -> list[Reservation]:
        return [r for r in self.reservations if r.book_id == book_id]

    def reserve(self, member_id: int, book_id: int) -> Reservation:
        if self.store.get_member(member_id) is None:
            raise ReservationError(f"unknown member {member_id}")
        if self.store.get_book(book_id) is None:
            raise ReservationError(f"unknown book {book_id}")
        if self.loans.available(book_id) > 0:
            raise ReservationError(
                f"book {book_id} still has copies available; borrow it instead"
            )
        for r in self.reservations:
            if r.book_id == book_id and r.member_id == member_id:
                raise ReservationError(
                    f"member {member_id} already reserved book {book_id}"
                )
        reservation = Reservation(book_id=book_id, member_id=member_id)
        self.reservations.append(reservation)
        return reservation

    def cancel(self, member_id: int, book_id: int) -> None:
        for r in self.reservations:
            if r.book_id == book_id and r.member_id == member_id:
                self.reservations.remove(r)
                return
        raise ReservationError(
            f"member {member_id} has no reservation for book {book_id}"
        )

    def list_for_book(self, book_id: int) -> list[int]:
        return [r.member_id for r in self._for_book(book_id)]

    def fulfill_next(self, book_id: int) -> Reservation | None:
        """Give the earliest (FIFO) reservation for a book its loan.

        Returns the fulfilled reservation, or None if there were none.
        """
        pending = self._for_book(book_id)
        if not pending:
            return None
        reservation = pending[0]
        self.loans.borrow(reservation.member_id, book_id)
        self.reservations.remove(reservation)
        return reservation
