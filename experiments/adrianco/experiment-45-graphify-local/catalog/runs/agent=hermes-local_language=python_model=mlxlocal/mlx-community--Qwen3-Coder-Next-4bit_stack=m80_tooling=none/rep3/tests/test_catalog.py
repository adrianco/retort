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


def test_reserve_unavailable_book():
    c = make_catalog()
    c.borrow(10, 1)  # Exhaust all copies
    assert c.availability(1) == 0
    c.reserve(11, 1)  # Linus can reserve
    assert c.list_reservations(1) == [11]


def test_reserve_available_book_raises():
    c = make_catalog()
    assert c.availability(2) == 2  # 2 copies available
    with pytest.raises(ReservationError):
        c.reserve(10, 2)  # Should raise because copies are available


def test_reserve_unknown_member_raises():
    c = make_catalog()
    c.borrow(10, 1)  # Exhaust copies
    with pytest.raises(ReservationError):
        c.reserve(999, 1)  # Unknown member


def test_reserve_unknown_book_raises():
    c = make_catalog()
    c.add_member(999, "Unknown")
    with pytest.raises(ReservationError):
        c.reserve(999, 999)  # Unknown book


def test_reserve_duplicate_raises():
    c = make_catalog()
    c.borrow(10, 1)  # Exhaust copies
    c.reserve(11, 1)
    with pytest.raises(ReservationError):
        c.reserve(11, 1)  # Same member, same book


def test_cancel_reservation():
    c = make_catalog()
    c.borrow(10, 1)  # Exhaust copies
    c.reserve(11, 1)
    assert c.list_reservations(1) == [11]
    c.cancel_reservation(11, 1)
    assert c.list_reservations(1) == []


def test_cancel_reservation_none_raises():
    c = make_catalog()
    with pytest.raises(ReservationError):
        c.cancel_reservation(11, 1)  # No reservation exists


def test_fulfill_reservation_on_return():
    c = make_catalog()
    c.borrow(10, 1)  # Ada borrows, availability = 0
    assert c.availability(1) == 0
    c.reserve(11, 1)  # Linus reserves
    assert c.list_reservations(1) == [11]
    c.return_book(10, 1)  # Ada returns
    # Linus gets the loan, reservation is fulfilled
    assert c.availability(1) == 0
    assert c.list_reservations(1) == []


def test_multiple_reservations_fulfill_earliest():
    c = make_catalog()
    c.borrow(10, 1)  # Exhaust copies
    c.reserve(11, 1)  # Linus reserves (first)
    c.reserve(10, 1)  # Ada reserves (second)
    assert c.list_reservations(1) == [11, 10]
    c.return_book(10, 1)  # Ada returns
    # Linus (earliest) gets the loan
    assert c.availability(1) == 0
    assert c.list_reservations(1) == [10]  # Linus's reservation gone, Ada still there
