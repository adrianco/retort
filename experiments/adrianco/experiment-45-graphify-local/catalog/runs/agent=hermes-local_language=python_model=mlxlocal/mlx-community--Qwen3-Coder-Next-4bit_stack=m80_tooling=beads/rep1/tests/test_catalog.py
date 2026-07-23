"""The catalog's EXISTING suite — must keep passing after any change."""
import pytest

from catalog.loans import LoanError
from catalog.service import Catalog, ReservationError


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


def test_reserve_when_no_copies_available():
    c = make_catalog()
    c.borrow(10, 1)  # Borrow the only copy
    assert c.availability(1) == 0
    c.reserve(11, 1)  # Linus reserves
    assert c.list_reservations(1) == [11]


def test_reserve_when_copies_available_raises():
    c = make_catalog()
    assert c.availability(1) == 1
    with pytest.raises(ReservationError):
        c.reserve(10, 1)


def test_reserve_unknown_member():
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(LoanError):
        c.reserve(999, 1)


def test_reserve_unknown_book():
    c = make_catalog()
    with pytest.raises(LoanError):
        c.reserve(10, 999)


def test_cannot_reserve_same_book_twice():
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(10, 1)
    with pytest.raises(ReservationError):
        c.reserve(10, 1)


def test_list_reservations_fifo():
    c = make_catalog()
    c.borrow(10, 1)  # Only copy borrowed
    c.reserve(10, 1)  # Ada reserves first
    c.reserve(11, 1)  # Linus reserves second
    assert c.list_reservations(1) == [10, 11]


def test_cancel_reservation():
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    c.cancel_reservation(11, 1)
    assert c.list_reservations(1) == []


def test_cancel_nonexistent_reservation():
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(ReservationError):
        c.cancel_reservation(11, 1)


def test_cancel_unknown_member():
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(10, 1)
    with pytest.raises(LoanError):
        c.cancel_reservation(999, 1)


def test_cancel_unknown_book():
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(10, 1)
    with pytest.raises(LoanError):
        c.cancel_reservation(10, 999)


def test_return_fulfills_reservation():
    """When a book is returned and has reservations, the earliest is fulfilled."""
    c = make_catalog()
    c.borrow(10, 1)  # Ada borrows the only copy
    c.reserve(11, 1)  # Linus reserves (no copies available)
    assert c.availability(1) == 0
    c.return_book(10, 1)  # Ada returns the book
    # Linus's reservation is fulfilled, he gets the loan
    assert c.availability(1) == 0  # Still 0 because Linus now has it
    assert c.list_reservations(1) == []  # No more reservations


def test_return_fulfills_earliest_reservation():
    """When multiple reservations exist, only the earliest is fulfilled."""
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(10, 1)  # Ada reserves first
    c.reserve(11, 1)  # Linus reserves second
    c.return_book(10, 1)  # Ada returns
    # Ada's reservation is fulfilled (she gets the loan back)
    assert c.availability(1) == 0
    assert c.list_reservations(1) == [11]  # Linus still has a reservation


def test_multiple_returns_multiple_fulfillments():
    """Multiple returns fulfill multiple reservations one at a time."""
    c = Catalog()
    c.add_book(1, "Test", "Author", copies=1)
    c.add_member(10, "Ada")
    c.add_member(11, "Linus")
    c.add_member(12, "Carol")

    c.borrow(10, 1)  # Ada borrows the only copy
    c.reserve(11, 1)  # Linus reserves
    c.reserve(12, 1)  # Carol reserves

    c.return_book(10, 1)  # Ada returns
    assert c.availability(1) == 0  # Linus gets it
    assert c.list_reservations(1) == [12]

    c.return_book(11, 1)  # Linus returns
    assert c.availability(1) == 0  # Carol gets it
    assert c.list_reservations(1) == []


def test_reservation_with_multiple_copies_book():
    """Reserving a book with copies available should raise."""
    c = make_catalog()
    assert c.availability(2) == 2  # Hyperion has 2 copies
    with pytest.raises(ReservationError):
        c.reserve(10, 2)
