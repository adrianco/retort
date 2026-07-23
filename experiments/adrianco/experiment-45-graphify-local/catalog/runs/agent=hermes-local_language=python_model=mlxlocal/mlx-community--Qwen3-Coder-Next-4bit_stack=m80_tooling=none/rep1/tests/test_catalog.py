"""The catalog's EXISTING suite — must keep passing after any change."""
import pytest

from catalog.loans import LoanError
from catalog.service import Catalog
from catalog.loans import ReservationError


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


def test_reserve_when_unavailable():
    """Reserve a book when no copies are available."""
    c = make_catalog()
    c.borrow(10, 1)  # Use the only copy
    assert c.availability(1) == 0
    reservation = c.reserve(11, 1)  # Linus reserves
    assert reservation.book_id == 1
    assert reservation.member_id == 11


def test_reserve_when_available_raises():
    """Cannot reserve a book that has copies available."""
    c = make_catalog()
    # Book 1 has 1 copy, book 2 has 2 copies
    assert c.availability(1) == 1
    with pytest.raises(ReservationError):
        c.reserve(10, 1)


def test_reserve_unknown_member():
    """Cannot reserve with unknown member."""
    c = make_catalog()
    c.borrow(10, 1)
    assert c.availability(1) == 0
    with pytest.raises(LoanError):
        c.reserve(999, 1)


def test_reserve_unknown_book():
    """Cannot reserve unknown book."""
    c = make_catalog()
    c.borrow(10, 1)
    assert c.availability(1) == 0
    with pytest.raises(LoanError):
        c.reserve(10, 999)


def test_reserve_duplicate_raises():
    """Member cannot have two reservations for same book."""
    c = make_catalog()
    c.borrow(10, 1)
    assert c.availability(1) == 0
    c.reserve(11, 1)
    with pytest.raises(ReservationError):
        c.reserve(11, 1)


def test_list_reservations_fifo():
    """Reservations should be returned in FIFO order."""
    c = make_catalog()
    c.borrow(10, 1)
    assert c.availability(1) == 0
    c.reserve(10, 1)  # Ada first
    c.reserve(11, 1)  # Linus second
    reservations = c.list_reservations(1)
    assert reservations == [10, 11]


def test_return_book_fulfills_reservation():
    """Returning a book with reservations fulfills the earliest one."""
    c = make_catalog()
    c.borrow(10, 1)
    assert c.availability(1) == 0
    c.reserve(11, 1)  # Linus reserves
    c.return_book(10, 1)  # Ada returns
    # Linus now has the book, Ada has no reservation
    assert c.availability(1) == 0  # Still 0 because loan was fulfilled
    reservations = c.list_reservations(1)
    assert reservations == []  # Reservation fulfilled and removed


def test_return_book_no_reservation():
    """Returning a book with no reservations just restores availability."""
    c = make_catalog()
    c.borrow(10, 1)
    assert c.availability(1) == 0
    c.return_book(10, 1)
    assert c.availability(1) == 1


def test_cancel_reservation():
    """Cancel a pending reservation."""
    c = make_catalog()
    c.borrow(10, 1)
    assert c.availability(1) == 0
    c.reserve(11, 1)
    reservations = c.list_reservations(1)
    assert reservations == [11]
    c.cancel_reservation(11, 1)
    reservations = c.list_reservations(1)
    assert reservations == []


def test_cancel_nonexistent_reservation():
    """Cannot cancel a reservation that doesn't exist."""
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(ReservationError):
        c.cancel_reservation(11, 1)


def test_multiple_reservations_fulfilled_on_return():
    """Multiple reservations are fulfilled one at a time."""
    c = Catalog()
    c.add_book(1, "Test", "Author", copies=1)
    c.add_member(10, "Ada")
    c.add_member(11, "Linus")
    c.add_member(12, "Carol")

    # Ada borrows and returns it twice
    c.borrow(10, 1)  # Ada has the book
    c.reserve(11, 1)  # Linus reserves
    c.reserve(12, 1)  # Carol reserves

    c.return_book(10, 1)  # Linus gets the book
    assert c.list_reservations(1) == [12]  # Carol still waiting

    c.return_book(11, 1)  # Carol gets the book
    assert c.list_reservations(1) == []  # No more reservations
