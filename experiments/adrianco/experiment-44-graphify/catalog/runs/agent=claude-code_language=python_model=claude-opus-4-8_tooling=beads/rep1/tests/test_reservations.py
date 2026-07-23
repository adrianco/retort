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
    # Book 1 has a copy available -> reserving is not allowed.
    with pytest.raises(ReservationError):
        c.reserve(11, 1)
    c.borrow(10, 1)  # now unavailable
    c.reserve(11, 1)
    assert c.list_reservations(1) == [11]


def test_reserve_unknown_member_or_book():
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(ReservationError):
        c.reserve(999, 1)
    # Unknown book id: no copies exist so it is "unavailable", but it must
    # still raise as unknown.
    with pytest.raises(ReservationError):
        c.reserve(11, 999)


def test_reserve_duplicate_raises():
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

    # Earliest reserver (11) now holds the loan; availability stays at 0.
    assert c.availability(1) == 0
    assert c.list_reservations(1) == [12]

    # 11 really has the loan: 11 can return it, fulfilling 12 next.
    c.return_book(11, 1)
    assert c.availability(1) == 0
    assert c.list_reservations(1) == []

    # With no reservations left, a return frees the copy normally.
    c.return_book(12, 1)
    assert c.availability(1) == 1


def test_return_without_reservations_frees_copy():
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

    # Cancelled reservation is not fulfilled on return; 12 is next.
    c.return_book(10, 1)
    assert c.list_reservations(1) == []
    assert c.availability(1) == 0


def test_cancel_without_reservation_raises():
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(ReservationError):
        c.cancel_reservation(11, 1)


def test_multi_copy_reservation_flow():
    c = make_catalog()
    # Exhaust both copies of book 2.
    c.borrow(10, 2)
    c.borrow(11, 2)
    assert c.availability(2) == 0
    c.reserve(12, 2)

    # Returning one copy fulfills the reservation rather than freeing the copy.
    c.return_book(10, 2)
    assert c.availability(2) == 0
    assert c.list_reservations(2) == []
