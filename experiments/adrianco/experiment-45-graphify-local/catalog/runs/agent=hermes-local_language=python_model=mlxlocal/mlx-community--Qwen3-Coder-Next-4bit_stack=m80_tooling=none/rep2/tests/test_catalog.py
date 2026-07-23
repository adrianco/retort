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


def test_reserve_unavailable_book():
    c = Catalog()
    c.add_book(1, "Test Book", "Author", copies=1)
    c.add_member(10, "Ada")
    c.borrow(10, 1)  # Use the only copy
    assert c.availability(1) == 0
    reservation = c.reserve(10, 1)
    assert reservation.book_id == 1
    assert reservation.member_id == 10
    assert c.list_reservations(1) == [10]


def test_reserve_when_copies_available_raises():
    c = Catalog()
    c.add_book(1, "Test Book", "Author", copies=2)
    c.add_member(10, "Ada")
    with pytest.raises(ReservationError):
        c.reserve(10, 1)


def test_reserve_unknown_member():
    c = Catalog()
    c.add_book(1, "Test Book", "Author", copies=0)
    with pytest.raises(ReservationError):
        c.reserve(999, 1)


def test_reserve_unknown_book():
    c = Catalog()
    c.add_member(10, "Ada")
    with pytest.raises(ReservationError):
        c.reserve(10, 999)


def test_reserve_duplicate_raises():
    c = Catalog()
    c.add_book(1, "Test Book", "Author", copies=0)
    c.add_member(10, "Ada")
    c.reserve(10, 1)
    with pytest.raises(ReservationError):
        c.reserve(10, 1)


def test_list_reservations_fifo():
    c = Catalog()
    c.add_book(1, "Test Book", "Author", copies=0)
    c.add_member(10, "Ada")
    c.add_member(11, "Bob")
    c.add_member(12, "Carol")
    c.reserve(10, 1)
    c.reserve(11, 1)
    c.reserve(12, 1)
    assert c.list_reservations(1) == [10, 11, 12]


def test_cancel_reservation():
    c = Catalog()
    c.add_book(1, "Test Book", "Author", copies=0)
    c.add_member(10, "Ada")
    c.reserve(10, 1)
    c.cancel_reservation(10, 1)
    assert c.list_reservations(1) == []


def test_cancel_reservation_not_found_raises():
    c = Catalog()
    c.add_book(1, "Test Book", "Author", copies=0)
    c.add_member(10, "Ada")
    with pytest.raises(ReservationError):
        c.cancel_reservation(10, 1)


def test_return_book_fulfills_reservation():
    c = Catalog()
    c.add_book(1, "Test Book", "Author", copies=1)
    c.add_member(10, "Ada")
    c.add_member(11, "Bob")
    c.borrow(10, 1)
    c.reserve(11, 1)  # Bob reserves while Ada has the book
    assert c.availability(1) == 0
    c.return_book(10, 1)  # Bob gets the book
    assert c.availability(1) == 0  # Still 0 because Bob has it
    assert c.list_reservations(1) == []


def test_return_book_fulfills_earliest_reservation():
    c = Catalog()
    c.add_book(1, "Test Book", "Author", copies=1)
    c.add_member(10, "Ada")
    c.add_member(11, "Bob")
    c.add_member(12, "Carol")
    c.borrow(10, 1)
    c.reserve(11, 1)  # Bob reserves
    c.reserve(12, 1)  # Carol reserves
    c.return_book(10, 1)  # Bob (earliest) gets the book
    assert c.availability(1) == 0
    assert c.list_reservations(1) == [12]


def test_multiple_reservations_multiple_returns():
    c = Catalog()
    c.add_book(1, "Test Book", "Author", copies=1)
    c.add_member(10, "Ada")
    c.add_member(11, "Bob")
    c.add_member(12, "Carol")
    c.borrow(10, 1)
    c.reserve(11, 1)
    c.reserve(12, 1)
    c.return_book(10, 1)  # Bob gets it (via reservation)
    assert c.availability(1) == 0
    assert c.list_reservations(1) == [12]
    c.return_book(11, 1)  # Bob returns it, Carol gets it (via reservation)
    assert c.availability(1) == 0
    assert c.list_reservations(1) == []


def test_existing_tests_still_pass():
    # These are the original tests that must still pass
    def make_catalog():
        c = Catalog()
        c.add_book(1, "Dune", "Herbert", copies=1)
        c.add_book(2, "Hyperion", "Simmons", copies=2)
        c.add_member(10, "Ada")
        c.add_member(11, "Linus")
        return c

    # test_add_and_list_books
    c = make_catalog()
    titles = {b.title for b in c.store.list_books()}
    assert titles == {"Dune", "Hyperion"}

    # test_borrow_reduces_availability
    c = make_catalog()
    assert c.availability(1) == 1
    c.borrow(10, 1)
    assert c.availability(1) == 0

    # test_return_restores_availability
    c = make_catalog()
    c.borrow(10, 1)
    c.return_book(10, 1)
    assert c.availability(1) == 1

    # test_borrow_unavailable_raises
    c = make_catalog()
    c.borrow(10, 1)
    with pytest.raises(LoanError):
        c.borrow(11, 1)

    # test_multiple_copies
    c = make_catalog()
    c.borrow(10, 2)
    assert c.availability(2) == 1
    c.borrow(11, 2)
    assert c.availability(2) == 0

    # test_unknown_member_or_book
    c = make_catalog()
    with pytest.raises(LoanError):
        c.borrow(999, 1)
    with pytest.raises(LoanError):
        c.availability(999)
