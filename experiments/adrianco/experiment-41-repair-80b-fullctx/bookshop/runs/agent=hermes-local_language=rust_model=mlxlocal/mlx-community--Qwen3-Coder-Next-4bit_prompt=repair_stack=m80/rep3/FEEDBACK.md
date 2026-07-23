# Evaluation feedback on your previous attempt

A previous attempt is already in this directory. It did NOT pass an independent evaluation. Fix it.

## Requirements that must ALL be met
- [R1] POST /books creates a new book (title, author, year, isbn)  (verify: A create route accepts the four fields and persists a book.)
- [R2] GET /books lists all books  (verify: A list route returns the collection.)
- [R3] GET /books supports an ?author= filter  (verify: The list route filters by author query param.)
- [R4] GET /books/{id} returns a single book by id  (verify: A get-by-id route returns one book (404 if absent).)
- [R5] PUT /books/{id} updates a book  (verify: An update route modifies an existing book.)
- [R6] DELETE /books/{id} deletes a book  (verify: A delete route removes a book.)
- [R7] Data stored in SQLite (or an embedded DB equivalent)  (verify: Persistence uses SQLite/embedded DB, not just in-memory state.)
- [R8] Returns JSON responses with appropriate HTTP status codes  (verify: Routes return JSON and correct codes (201/200/404/400 etc.).)
- [R9] Input validation: title and author are required  (verify: Creating without title/author is rejected (400).)
- [R10] GET /health health-check endpoint  (verify: A /health route returns a healthy status.)
- [R11] README.md with setup and run instructions  (verify: README.md documents how to set up and run the service.)
- [R12] At least 3 unit/integration tests  (verify: >= 3 tests exist and run (test_coverage > 0).)

## What went wrong last time
- The build/tests did not fully pass (status: completed, requirement_coverage 0.92).
- GET /books/{id} returns 500 instead of 404 for a missing book

Fix the existing code so every requirement above is met and the tests run and pass.