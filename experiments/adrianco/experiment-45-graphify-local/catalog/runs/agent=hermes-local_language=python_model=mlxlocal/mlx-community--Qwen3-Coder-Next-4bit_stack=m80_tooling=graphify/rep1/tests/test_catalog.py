"""The catalog's EXISTING suite — must keep passing after any change."""
import pytest

from catalog.loans import LoanError
from catalog.service import Catalog


def make_catalog() -> Catalog:
    c = Catalog()
    c.add_book(1, "Dune", "Herbert", copies=1)
    c.add_book(2, "Hyperion", "Simmons", copies=2)
    c.add_member(10, "Ada")
    c.add_member(11, "Linus")
    return c


def test_add_and_list_books():
    c = make_catalog()
    titles = {b.title for b in c.store.list_books()}
    assert titles == {"Dune", "Hyperion"}


def test_borrow_reduces_availability():
    c = make_catalog()
    assert c.availability(1) == 1
    c.borrow(10, 1)
    assert c.availability(1) == 0


def test_return_restores_availability():
    c = make_catalog()
    c.borrow(10, 1)
    c.return_book(10, 1)
    assert c.availability(1) == 1


def test_borrow_unavailable_raises():
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(LoanError):
        c.borrow(11, 1)


def test_multiple_copies():
    c = make_catalog()
    c.borrow(10, 2)
    assert c.availability(2) == 1
    c.borrow(11, 2)
    assert c.availability(2) == 0


def test_unknown_member_or_book():
    c = make_catalog()
    with pytest.raises(LoanError):
        c.borrow(999, 1)
    with pytest.raises(LoanError):
        c.availability(999)


# Reservation tests
from catalog.loans import ReservationError


def test_reserve_unavailable_book():
    """Reserve a book with no available copies."""
    c = make_catalog()
    c.borrow(10, 1)  # Use the only copy
    assert c.availability(1) == 0
    c.reserve(11, 1)  # Linus reserves
    assert c.list_reservations(1) == [11]


def test_reserve_available_book_raises():
    """Reserving a book with available copies should raise."""
    c = make_catalog()
    assert c.availability(1) == 1
    with pytest.raises(ReservationError):
        c.reserve(10, 1)


def test_reserve_unknown_member_raises():
    """Reserving with unknown member should raise."""
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(ReservationError):
        c.reserve(999, 1)


def test_reserve_unknown_book_raises():
    """Reserving unknown book should raise."""
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(ReservationError):
        c.reserve(10, 999)


def test_duplicate_reservation_raises():
    """Member cannot reserve same book twice."""
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    with pytest.raises(ReservationError):
        c.reserve(11, 1)


def test_list_reservations_fifo():
    """Reservations should be returned in FIFO order."""
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)  # Linus first
    c.reserve(10, 1)  # Ada second
    assert c.list_reservations(1) == [11, 10]


def test_return_fulfills_reservation():
    """Returning a book fulfills the earliest reservation."""
    c = make_catalog()
    c.borrow(10, 1)  # Ada borrows
    c.reserve(11, 1)  # Linus reserves (Ada has the only copy)
    assert c.availability(1) == 0
    c.return_book(10, 1)  # Ada returns
    # Linus should now have the book, Ada has no reservation
    assert c.availability(1) == 0
    assert c.list_reservations(1) == []


def test_return_fulfills_and_restores():
    """After reservation is fulfilled, book is still unavailable."""
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    c.return_book(10, 1)
    # Linus now has the loan, so availability is 0
    assert c.availability(1) == 0


def test_cancel_reservation():
    """Cancel a pending reservation."""
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    assert c.list_reservations(1) == [11]
    c.cancel_reservation(11, 1)
    assert c.list_reservations(1) == []


def test_cancel_no_reservation_raises():
    """Canceling a non-existent reservation should raise."""
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(ReservationError):
        c.cancel_reservation(11, 1)


def test_multiple_copies_reservation():
    """Reservations work correctly with multiple copies."""
    c = make_catalog()
    # Hyperion has 2 copies
    c.borrow(10, 2)
    c.borrow(11, 2)
    assert c.availability(2) == 0
    c.reserve(10, 2)  # Ada reserves
    c.return_book(10, 2)  # Ada returns one
    # Ada's reservation should be fulfilled, she gets the book back
    assert c.availability(2) == 0
    assert c.list_reservations(2) == []


def test_multiple_reservations_fulfilled():
    """Multiple reservations are fulfilled in FIFO order."""
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)  # Linus first
    c.reserve(10, 1)  # Ada second
    c.return_book(10, 1)  # Ada returns
    # Linus should be fulfilled (first in line)
    assert c.availability(1) == 0
    assert c.list_reservations(1) == [10]  # Ada still has reservation
