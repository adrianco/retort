# Codebase Summary — catalog (reservations capability)

A small in-memory library-catalog library, modified to add a **reservations**
capability on top of the seeded book/member/loan model.

## Modules

| Module | Role | Change |
|--------|------|--------|
| `catalog/models.py` | Domain dataclasses: `Book`, `Member`, `Loan`, `Reservation` | Added `Reservation(book_id, member_id)` |
| `catalog/store.py` | In-memory persistence for books/members | Unchanged (seed) |
| `catalog/loans.py` | `LoanService`: borrow / return / availability | Unchanged (seed) |
| `catalog/reservations.py` | **New** `ReservationService` + `ReservationError` | New file |
| `catalog/service.py` | `Catalog` facade orchestrating store/loans/reservations | Wired reservations in |
| `tests/test_catalog.py` | Seed suite (6 tests) | Unchanged — must keep passing |
| `tests/test_reservations.py` | **New** reservation tests (10 tests) | New file |

## Interfaces

- `ReservationService(store, loans)` holds an ordered `list[Reservation]` (FIFO by
  append order). Methods: `reserve`, `cancel`, `list_for_book`, `pop_earliest`,
  and a private `_find`.
- `Catalog` exposes `reserve`, `cancel_reservation`, `list_reservations`, and
  fulfills the earliest reservation inside `return_book`.

## Reservation flow

1. `reserve` validates member/book existence, requires `available == 0`, and
   rejects a duplicate (member, book) pair, then appends a `Reservation`.
2. `return_book` first returns the loan via `LoanService`, then `pop_earliest`
   removes the head-of-line reservation for that book and immediately re-borrows
   the freed copy for that member — so availability stays 0 while a reservation
   is outstanding.
3. `cancel_reservation` removes a pending reservation or raises if absent.

Layering (models → store → loans → service, with reservations parallel to loans)
is preserved as the task required.
