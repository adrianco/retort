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
                f"book {book_id} has copies available; borrow it instead"
            )
        if any(
            r.book_id == book_id and r.member_id == member_id
            for r in self.reservations
        ):
            raise ReservationError(
                f"member {member_id} already reserves book {book_id}"
            )
        reservation = Reservation(book_id=book_id, member_id=member_id)
        self.reservations.append(reservation)
        return reservation

    def cancel_reservation(self, member_id: int, book_id: int) -> None:
        for reservation in self.reservations:
            if reservation.book_id == book_id and reservation.member_id == member_id:
                self.reservations.remove(reservation)
                return
        raise ReservationError(
            f"member {member_id} has no reservation for book {book_id}"
        )

    def list_reservations(self, book_id: int) -> list[int]:
        """Reserving member ids for a book, in FIFO order."""
        return [r.member_id for r in self._for_book(book_id)]

    def pop_next(self, book_id: int) -> Reservation | None:
        """Remove and return the earliest reservation for a book, if any."""
        for reservation in self.reservations:
            if reservation.book_id == book_id:
                self.reservations.remove(reservation)
                return reservation
        return None
