"""Tests for the reservations capability."""
import pytest

from catalog.reservations import ReservationError
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
    # Book 1 still has a copy available -> cannot reserve.
    with pytest.raises(ReservationError):
        c.reserve(10, 1)


def test_reserve_when_unavailable():
    c = make_catalog()
    c.borrow(10, 1)
    assert c.availability(1) == 0
    c.reserve(11, 1)
    assert c.list_reservations(1) == [11]


def test_reserve_unknown_member_or_book():
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(ReservationError):
        c.reserve(999, 1)
    with pytest.raises(ReservationError):
        c.reserve(11, 999)


def test_no_duplicate_reservation():
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    with pytest.raises(ReservationError):
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

    # Copy handed to the earliest reserver -> availability stays 0.
    assert c.availability(1) == 0
    # Earliest reservation consumed; the next one remains.
    assert c.list_reservations(1) == [12]
    # Linus (11) now holds the loan and can return it.
    c.return_book(11, 1)
    assert c.availability(1) == 0
    assert c.list_reservations(1) == []


def test_return_without_reservations_restores_availability():
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
    with pytest.raises(ReservationError):
        c.cancel_reservation(11, 1)


def test_cancelled_member_not_fulfilled_on_return():
    c = make_catalog()
    c.borrow(10, 1)
    c.reserve(11, 1)
    c.reserve(12, 1)
    c.cancel_reservation(11, 1)

    c.return_book(10, 1)
    # 12 is now the earliest and gets the copy.
    assert c.list_reservations(1) == []
    c.return_book(12, 1)
    assert c.availability(1) == 1
