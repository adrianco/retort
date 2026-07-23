# Interfaces

## HTTP routes

(none — this is a library, not a service)

## CLI commands

(none)

## Library API — `catalog.service.Catalog`

| Method | Signature | Returns | Notes |
|--------|-----------|---------|-------|
| add_book | `add_book(id, title, author, copies=1)` | `Book` | |
| add_member | `add_member(id, name)` | `Member` | |
| borrow | `borrow(member_id, book_id)` | `Loan` | raises `LoanError` if none available / unknown member |
| return_book | `return_book(member_id, book_id)` | `None` | auto-fulfills earliest reservation after returning |
| availability | `availability(book_id)` | `int` | copies − on-loan count |
| reserve | `reserve(member_id, book_id)` | `Reservation` | **new** — only when availability == 0 |
| cancel_reservation | `cancel_reservation(member_id, book_id)` | `None` | **new** — raises if no such reservation |
| list_reservations | `list_reservations(book_id)` | `list[int]` | **new** — FIFO member ids |

Errors: `LoanError` (loans.py), `ReservationError` (reservations.py).

## Data schema

In-memory only. `Store` holds `dict[int, Book]` and `dict[int, Member]`.
`LoanService.loans` is a `list[Loan]`; `ReservationService.reservations` is a
`list[Reservation]` whose insertion order encodes per-book FIFO.
