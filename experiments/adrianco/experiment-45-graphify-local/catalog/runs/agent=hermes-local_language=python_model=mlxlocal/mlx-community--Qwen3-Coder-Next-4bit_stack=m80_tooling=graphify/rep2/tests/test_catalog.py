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


def test_reserve_when_unavailable():
    c = make_catalog()
    c.borrow(10, 1)  # Borrow the only copy
    assert c.availability(1) == 0
    c.reserve(11, 1)  # Linus reserves
    assert c.list_reservations(1) == [11]


def test_reserve_when_available_raises():
    c = make_catalog()
    assert c.availability(1) == 1
    with pytest.raises(ReservationError):
        c.reserve(10, 1)


def test_reserve_unknown_member_raises():
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(ReservationError):
        c.reserve(999, 1)


def test_reserve_unknown_book_raises():
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(ReservationError):
        c.reserve(10, 999)


def test_reserve_duplicate_raises():
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    with pytest.raises(ReservationError):
        c.reserve(11, 1)


def test_list_reservations_fifo():
    c = make_catalog()
    c.borrow(10, 1)  # Only copy borrowed
    c.reserve(11, 1)  # Linus first
    c.reserve(10, 1)  # Ada second
    assert c.list_reservations(1) == [11, 10]


def test_reservation_fulfilled_on_return():
    c = make_catalog()
    c.borrow(10, 1)  # Ada borrows
    c.reserve(11, 1)  # Linus reserves
    assert c.availability(1) == 0
    c.return_book(10, 1)  # Ada returns
    # Linus should now have the loan, Ada has no loan
    assert c.availability(1) == 0
    assert c.list_reservations(1) == []


def test_cancel_reservation():
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    c.reserve(10, 1)
    c.cancel_reservation(11, 1)
    assert c.list_reservations(1) == [10]


def test_cancel_reservation_no_such_reservation():
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(ReservationError):
        c.cancel_reservation(11, 1)
