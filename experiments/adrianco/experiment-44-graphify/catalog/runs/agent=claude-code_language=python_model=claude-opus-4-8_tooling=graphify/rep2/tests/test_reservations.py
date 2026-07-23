"""Tests for the reservation capability."""
import pytest

from catalog.loans import LoanError
from catalog.service import Catalog


def make_catalog() -> Catalog:
    c = Catalog()
    c.add_book(1, "Dune", "Herbert", copies=1)
    c.add_book(2, "Hyperion", "Simmons", copies=2)
    c.add_member(10, "Ada")
    c.add_member(11, "Linus")
    c.add_member(12, "Grace")
    return c


def test_reserve_requires_zero_availability():
    c = make_catalog()
    # Book 1 has a copy available -> reserving must raise.
    with pytest.raises(LoanError):
        c.reserve(10, 1)


def test_reserve_when_unavailable():
    c = make_catalog()
    c.borrow(10, 1)  # exhaust the single copy
    r = c.reserve(11, 1)
    assert r.member_id == 11 and r.book_id == 1
    assert c.list_reservations(1) == [11]


def test_reserve_unknown_member_or_book():
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(LoanError):
        c.reserve(999, 1)
    with pytest.raises(LoanError):
        c.reserve(11, 999)


def test_reserve_duplicate_raises():
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    with pytest.raises(LoanError):
        c.reserve(11, 1)


def test_reservations_are_fifo():
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    c.reserve(12, 1)
    assert c.list_reservations(1) == [11, 12]


def test_return_fulfills_earliest_reservation():
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    c.reserve(12, 1)
    c.return_book(10, 1)
    # Earliest reserver (11) now holds the loan; availability stays 0.
    assert c.availability(1) == 0
    assert c.list_reservations(1) == [12]
    # 11 really holds it: 11 can return it.
    c.return_book(11, 1)
    # Now 12 gets fulfilled.
    assert c.availability(1) == 0
    assert c.list_reservations(1) == []


def test_return_with_no_reservation_restores_availability():
    c = make_catalog()
    c.borrow(10, 1)
    c.return_book(10, 1)
    assert c.availability(1) == 1


def test_cancel_reservation():
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    c.reserve(12, 1)
    c.cancel_reservation(11, 1)
    assert c.list_reservations(1) == [12]


def test_cancel_missing_reservation_raises():
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(LoanError):
        c.cancel_reservation(11, 1)


def test_cancelled_reservation_not_fulfilled_on_return():
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    c.cancel_reservation(11, 1)
    c.return_book(10, 1)
    # No pending reservation -> the copy is simply free again.
    assert c.availability(1) == 1
