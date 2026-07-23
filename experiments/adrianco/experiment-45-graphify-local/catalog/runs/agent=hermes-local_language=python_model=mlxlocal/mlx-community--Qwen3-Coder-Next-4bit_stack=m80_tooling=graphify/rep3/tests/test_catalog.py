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


# New reservation tests


def test_reserve_unavailable_book():
    """Reserve a book with no available copies."""
    c = make_catalog()
    c.borrow(10, 1)  # Uses the only copy
    assert c.availability(1) == 0
    c.reserve(11, 1)  # Linus reserves
    assert c.list_reservations(1) == [11]


def test_reserve_available_book_raises():
    """Cannot reserve a book that has copies available."""
    c = make_catalog()
    assert c.availability(1) == 1
    with pytest.raises(LoanError):
        c.reserve(10, 1)


def test_reserve_unknown_member_raises():
    """Cannot reserve with unknown member."""
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(LoanError):
        c.reserve(999, 1)


def test_reserve_unknown_book_raises():
    """Cannot reserve unknown book."""
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(LoanError):
        c.reserve(10, 999)


def test_duplicate_reservation_raises():
    """Member cannot hold two reservations for same book."""
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    with pytest.raises(LoanError):
        c.reserve(11, 1)


def test_list_reservations_fifo():
    """Reservations are returned in FIFO order."""
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)  # Linus first
    c.reserve(10, 1)  # Ada second
    assert c.list_reservations(1) == [11, 10]


def test_return_fulfills_reservation():
    """When book returned with reservations, earliest reservation is fulfilled."""
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)  # Linus reserves
    c.return_book(10, 1)  # Ada returns
    # Linus should now have the loan
    assert c.availability(1) == 0
    assert c.list_reservations(1) == []  # Reservation fulfilled


def test_cancel_reservation():
    """Cancel a pending reservation."""
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    assert c.list_reservations(1) == [11]
    c.cancel_reservation(11, 1)
    assert c.list_reservations(1) == []


def test_cancel_nonexistent_reservation_raises():
    """Cannot cancel a reservation that doesn't exist."""
    c = make_catalog()
    with pytest.raises(LoanError):
        c.cancel_reservation(11, 1)


def test_multiple_reservations_fulfilled_on_return():
    """Multiple reservations: only earliest is fulfilled on first return."""
    c = Catalog()
    c.add_book(1, "1984", "Orwell", copies=1)
    c.add_member(10, "Ada")
    c.add_member(11, "Linus")
    c.add_member(12, "Charlie")
    
    c.borrow(10, 1)
    c.reserve(11, 1)  # Linus first in line
    c.reserve(12, 1)  # Charlie second in line
    
    c.return_book(10, 1)
    # Linus gets the book, Charlie's reservation remains
    assert c.availability(1) == 0
    assert c.list_reservations(1) == [12]
