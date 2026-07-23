# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| catalog/models.py | Domain dataclasses | `Book`, `Member`, `Loan`, `Reservation` |
| catalog/store.py | In-memory persistence for books and members | `Store.add_book`, `get_book`, `list_books`, `add_member`, `get_member` |
| catalog/loans.py | Borrow/return logic layered on the Store | `LoanError`, `LoanService.available/borrow/return_book` |
| catalog/reservations.py | FIFO reservation logic layered on Store + LoanService | `ReservationError`, `ReservationService.reserve/cancel/list_for_book/fulfill_next` |
| catalog/service.py | Catalog facade orchestrating store/loan/reservation services | `Catalog` |
| catalog/__init__.py | Package marker | (none) |
| tests/test_catalog.py | Pre-existing catalog suite (unchanged) | 6 test functions |
| tests/test_reservations.py | New reservation-behavior tests | 9 test functions |
| conftest.py | Adds run dir to `sys.path` for imports | (none) |

`reservations.py` is the only new source module; `models.py` (added `Reservation`)
and `service.py` (added facade methods + fulfill-on-return) were extended. The
existing `store.py` and `loans.py` are untouched, preserving the layering.
