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


def test_reserve_unavailable_book():
    c = Catalog()
    c.add_book(1, "Dune", "Herbert", copies=1)
    c.add_member(10, "Ada")
    c.borrow(10, 1)  # No copies available now
    reservation = c.reserve(10, 1)
    assert reservation.book_id == 1
    assert reservation.member_id == 10


def test_reserve_available_book_raises():
    c = Catalog()
    c.add_book(1, "Dune", "Herbert", copies=2)
    c.add_member(10, "Ada")
    with pytest.raises(ReservationError):
        c.reserve(10, 1)


def test_reserve_unknown_member_raises():
    c = Catalog()
    c.add_book(1, "Dune", "Herbert", copies=1)
    with pytest.raises(ReservationError):
        c.reserve(999, 1)


def test_reserve_unknown_book_raises():
    c = Catalog()
    c.add_member(10, "Ada")
    with pytest.raises(ReservationError):
        c.reserve(10, 999)


def test_reserve_duplicate_raises():
    c = Catalog()
    c.add_book(1, "Dune", "Herbert", copies=1)
    c.add_member(10, "Ada")
    c.borrow(10, 1)  # No copies available
    c.reserve(10, 1)  # First reservation
    with pytest.raises(ReservationError):
        c.reserve(10, 1)  # Duplicate reservation


def test_list_reservations():
    c = Catalog()
    c.add_book(1, "Dune", "Herbert", copies=1)
    c.add_member(10, "Ada")
    c.add_member(11, "Linus")
    c.add_member(12, "Charlie")
    c.borrow(10, 1)  # No copies available
    c.reserve(10, 1)
    c.reserve(11, 1)
    c.reserve(12, 1)
    reservations = c.list_reservations(1)
    assert reservations == [10, 11, 12]


def test_list_reservations_unknown_book_raises():
    c = Catalog()
    with pytest.raises(ReservationError):
        c.list_reservations(999)


def test_cancel_reservation():
    c = Catalog()
    c.add_book(1, "Dune", "Herbert", copies=1)
    c.add_member(10, "Ada")
    c.borrow(10, 1)  # No copies available
    c.reserve(10, 1)
    c.cancel_reservation(10, 1)
    reservations = c.list_reservations(1)
    assert reservations == []


def test_cancel_reservation_unknown_member_raises():
    c = Catalog()
    c.add_book(1, "Dune", "Herbert", copies=1)
    with pytest.raises(ReservationError):
        c.cancel_reservation(999, 1)


def test_cancel_reservation_unknown_book_raises():
    c = Catalog()
    c.add_member(10, "Ada")
    with pytest.raises(ReservationError):
        c.cancel_reservation(10, 999)


def test_cancel_reservation_not_found_raises():
    c = Catalog()
    c.add_book(1, "Dune", "Herbert", copies=1)
    c.add_member(10, "Ada")
    c.borrow(10, 1)  # No copies available
    with pytest.raises(ReservationError):
        c.cancel_reservation(10, 1)


def test_reservation_fulfilled_on_return():
    c = Catalog()
    c.add_book(1, "Dune", "Herbert", copies=1)
    c.add_member(10, "Ada")
    c.add_member(11, "Linus")
    c.borrow(10, 1)  # No copies available
    c.reserve(11, 1)  # Linus reserves
    assert c.availability(1) == 0
    c.return_book(10, 1)  # Ada returns, Linus's reservation is fulfilled
    assert c.availability(1) == 0  # Still 0 because Linus now has it
    reservations = c.list_reservations(1)
    assert reservations == []  # No reservations left
    # Verify Linus now has the book
    loans = c.loans.loans
    assert len(loans) == 1
    assert loans[0].book_id == 1
    assert loans[0].member_id == 11


def test_reservation_fifo_order():
    c = Catalog()
    c.add_book(1, "Dune", "Herbert", copies=1)
    c.add_member(10, "Ada")
    c.add_member(11, "Linus")
    c.add_member(12, "Charlie")
    c.borrow(10, 1)  # No copies available
    c.reserve(10, 1)
    c.reserve(11, 1)
    c.reserve(12, 1)
    c.return_book(10, 1)  # First in line (Ada) gets it
    reservations = c.list_reservations(1)
    assert reservations == [11, 12]  # Linus and Charlie remain
    loans = c.loans.loans
    assert loans[0].member_id == 10  # Ada has the book


def test_multiple_copies_with_reservations():
    c = Catalog()
    c.add_book(1, "Dune", "Herbert", copies=2)
    c.add_member(10, "Ada")
    c.add_member(11, "Linus")
    c.borrow(10, 1)
    c.borrow(11, 1)  # Both copies borrowed
    c.reserve(10, 1)  # Ada reserves (0 copies available)
    c.reserve(11, 1)  # Linus reserves
    c.return_book(10, 1)  # Ada gets it back (first in line)
    assert c.availability(1) == 0
    reservations = c.list_reservations(1)
    assert reservations == [11]  # Linus remains
    loans = c.loans.loans
    assert 10 in [l.member_id for l in loans]  # Ada has the book
