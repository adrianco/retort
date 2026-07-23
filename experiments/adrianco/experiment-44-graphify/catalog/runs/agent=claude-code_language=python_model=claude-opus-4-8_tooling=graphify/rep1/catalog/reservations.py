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
        # book_id -> FIFO list of reservations (earliest first)
        self.reservations: dict[int, list[Reservation]] = {}

    def _queue(self, book_id: int) -> list[Reservation]:
        return self.reservations.setdefault(book_id, [])

    def reserve(self, member_id: int, book_id: int) -> Reservation:
        if self.store.get_member(member_id) is None:
            raise ReservationError(f"unknown member {member_id}")
        if self.store.get_book(book_id) is None:
            raise ReservationError(f"unknown book {book_id}")
        if self.loans.available(book_id) > 0:
            raise ReservationError(
                f"book {book_id} has copies available; borrow it instead"
            )
        queue = self._queue(book_id)
        if any(r.member_id == member_id for r in queue):
            raise ReservationError(
                f"member {member_id} already reserved book {book_id}"
            )
        reservation = Reservation(book_id=book_id, member_id=member_id)
        queue.append(reservation)
        return reservation

    def cancel(self, member_id: int, book_id: int) -> None:
        queue = self.reservations.get(book_id, [])
        for reservation in queue:
            if reservation.member_id == member_id:
                queue.remove(reservation)
                return
        raise ReservationError(
            f"member {member_id} has no reservation for book {book_id}"
        )

    def list(self, book_id: int) -> list[int]:
        return [r.member_id for r in self.reservations.get(book_id, [])]

    def fulfill(self, book_id: int) -> Reservation | None:
        """Grant a returned copy to the earliest reservation, if any."""
        queue = self.reservations.get(book_id, [])
        if not queue:
            return None
        reservation = queue.pop(0)
        self.loans.borrow(reservation.member_id, book_id)
        return reservation
