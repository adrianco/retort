"""Tests for the reservations capability."""
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
    # A copy is still available, so reserving is not allowed.
    with pytest.raises(LoanError):
        c.reserve(10, 1)


def test_reserve_when_unavailable():
    c = make_catalog()
    c.borrow(10, 1)  # exhausts the single copy
    res = c.reserve(11, 1)
    assert res.book_id == 1
    assert res.member_id == 11
    assert c.list_reservations(1) == [11]


def test_reserve_unknown_member_or_book():
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(LoanError):
        c.reserve(999, 1)
    with pytest.raises(LoanError):
        c.reserve(10, 999)


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
    # Earliest reservation (11) is fulfilled: availability stays 0,
    # the reservation is removed, and 12 remains queued.
    assert c.availability(1) == 0
    assert c.list_reservations(1) == [12]
    # 11 now holds the loan and can return it, fulfilling 12.
    c.return_book(11, 1)
    assert c.availability(1) == 0
    assert c.list_reservations(1) == []
    # 12 holds the loan; returning it now frees the copy.
    c.return_book(12, 1)
    assert c.availability(1) == 1


def test_return_without_reservation_frees_copy():
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
    assert c.availability(1) == 1
    assert c.list_reservations(1) == []


def test_list_reservations_isolated_per_book():
    c = make_catalog()
    c.borrow(10, 1)
    c.borrow(11, 2)
    c.borrow(12, 2)  # book 2 now exhausted too
    c.reserve(11, 1)
    c.reserve(10, 2)
    assert c.list_reservations(1) == [11]
    assert c.list_reservations(2) == [10]
