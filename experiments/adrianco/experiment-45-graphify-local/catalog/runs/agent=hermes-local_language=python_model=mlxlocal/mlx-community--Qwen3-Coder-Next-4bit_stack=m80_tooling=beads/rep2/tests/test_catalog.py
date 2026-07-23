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


# Reservation tests


def test_reserve_when_no_copies_available():
    c = make_catalog()
    c.borrow(10, 1)  # Use the only copy
    assert c.availability(1) == 0
    c.reserve(11, 1)  # Linus reserves


def test_reserve_when_copies_available_raises():
    c = make_catalog()
    # Book 1 has 1 copy, book 2 has 2 copies
    with pytest.raises(LoanError):
        c.reserve(10, 2)  # Should raise because copies are available


def test_reserve_unknown_member_raises():
    c = make_catalog()
    with pytest.raises(LoanError):
        c.reserve(999, 1)


def test_reserve_unknown_book_raises():
    c = make_catalog()
    with pytest.raises(LoanError):
        c.reserve(10, 999)


def test_reserve_duplicate_raises():
    c = make_catalog()
    c.borrow(10, 1)  # Use the only copy
    c.reserve(11, 1)  # Linus reserves
    with pytest.raises(LoanError):
        c.reserve(11, 1)  # Linus tries to reserve again


def test_list_reservations_fifo():
    c = make_catalog()
    c.borrow(10, 1)  # Use the only copy
    c.reserve(10, 1)  # Ada reserves first
    c.reserve(11, 1)  # Linus reserves second
    assert c.list_reservations(1) == [10, 11]


def test_cancel_reservation():
    c = make_catalog()
    c.borrow(10, 1)  # Use the only copy
    c.reserve(11, 1)  # Linus reserves
    c.cancel_reservation(11, 1)  # Linus cancels
    assert c.list_reservations(1) == []


def test_cancel_nonexistent_reservation_raises():
    c = make_catalog()
    with pytest.raises(LoanError):
        c.cancel_reservation(10, 1)


def test_return_book_fulfills_reservation():
    c = make_catalog()
    c.borrow(10, 1)  # Ada borrows the only copy
    assert c.availability(1) == 0
    c.reserve(11, 1)  # Linus reserves (no copies available)
    c.return_book(10, 1)  # Ada returns
    # Linus should now have the loan, Ada has nothing
    assert c.availability(1) == 0
    # Linus should have a loan of book 1
    loans = c.loans.loans
    assert any(l.book_id == 1 and l.member_id == 11 for l in loans)


def test_return_book_fulfills_earliest_reservation_first():
    c = make_catalog()
    c.borrow(10, 1)  # Ada borrows the only copy
    c.reserve(11, 1)  # Linus reserves first
    c.reserve(10, 1)  # Ada reserves second (after her loan is returned)
    c.return_book(10, 1)  # Ada returns
    # Linus should get the book (earliest reservation)
    assert c.list_reservations(1) == [10]  # Only Ada's reservation remains
    # Linus should have the loan
    loans = c.loans.loans
    assert any(l.book_id == 1 and l.member_id == 11 for l in loans)


def test_multiple_returns_with_reservations():
    c = Catalog()
    c.add_book(1, "Test Book", "Author", copies=1)
    c.add_member(10, "Ada")
    c.add_member(11, "Linus")
    c.add_member(12, "Charlie")
    
    c.borrow(10, 1)  # Ada borrows
    c.reserve(11, 1)  # Linus reserves
    c.reserve(12, 1)  # Charlie reserves
    c.return_book(10, 1)  # Ada returns
    # Linus gets the book
    assert c.availability(1) == 0
    loans = c.loans.loans
    assert any(l.book_id == 1 and l.member_id == 11 for l in loans)
    # Linus's reservation is gone, Charlie's remains
    assert c.list_reservations(1) == [12]
