"""Borrow/return logic, layered on the Store."""
from catalog.models import Loan, Reservation
from catalog.store import Store


class LoanError(Exception):
    pass


class ReservationError(Exception):
    pass


class LoanService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.loans: list[Loan] = []

    def _on_loan_count(self, book_id: int) -> int:
        return sum(1 for loan in self.loans if loan.book_id == book_id)

    def available(self, book_id: int) -> int:
        book = self.store.get_book(book_id)
        if book is None:
            raise LoanError(f"unknown book {book_id}")
        return book.copies - self._on_loan_count(book_id)

    def borrow(self, member_id: int, book_id: int) -> Loan:
        if self.store.get_member(member_id) is None:
            raise LoanError(f"unknown member {member_id}")
        if self.available(book_id) <= 0:
            raise LoanError(f"no copies of book {book_id} available")
        loan = Loan(book_id=book_id, member_id=member_id)
        self.loans.append(loan)
        return loan

    def return_book(self, member_id: int, book_id: int) -> None:
        for loan in self.loans:
            if loan.book_id == book_id and loan.member_id == member_id:
                self.loans.remove(loan)
                # Check if there are reservations for this book
                reservations = self.store.get_reservations(book_id)
                if reservations:
                    # Fulfill the earliest reservation
                    earliest_reservation = reservations[0]
                    # Remove the reservation
                    self.store.remove_reservation(earliest_reservation)
                    # Create a loan for the member
                    self.loans.append(Loan(book_id=book_id, member_id=earliest_reservation.member_id))
                return
        raise LoanError(f"member {member_id} has no loan of book {book_id}")

    def reserve(self, member_id: int, book_id: int) -> Reservation:
        if self.store.get_member(member_id) is None:
            raise ReservationError(f"unknown member {member_id}")
        if self.store.get_book(book_id) is None:
            raise ReservationError(f"unknown book {book_id}")
        if self.available(book_id) > 0:
            raise ReservationError(f"book {book_id} has copies available, borrow instead of reserve")
        # Check if member already has a reservation for this book
        reservations = self.store.get_reservations(book_id)
        if any(r.member_id == member_id for r in reservations):
            raise ReservationError(f"member {member_id} already has a reservation for book {book_id}")
        reservation = Reservation(book_id=book_id, member_id=member_id)
        self.store.add_reservation(reservation)
        return reservation

    def cancel_reservation(self, member_id: int, book_id: int) -> None:
        if self.store.get_member(member_id) is None:
            raise ReservationError(f"unknown member {member_id}")
        if self.store.get_book(book_id) is None:
            raise ReservationError(f"unknown book {book_id}")
        reservations = self.store.get_reservations(book_id)
        reservation = next((r for r in reservations if r.member_id == member_id), None)
        if reservation is None:
            raise ReservationError(f"member {member_id} has no reservation for book {book_id}")
        self.store.remove_reservation(reservation)

    def list_reservations(self, book_id: int) -> list[int]:
        if self.store.get_book(book_id) is None:
            raise ReservationError(f"unknown book {book_id}")
        reservations = self.store.get_reservations(book_id)
        return [r.member_id for r in reservations]
