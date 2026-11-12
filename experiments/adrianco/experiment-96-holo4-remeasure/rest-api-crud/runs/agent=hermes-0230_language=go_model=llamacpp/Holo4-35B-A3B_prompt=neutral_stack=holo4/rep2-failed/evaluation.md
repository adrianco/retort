# Evaluation: rest-api-crud · agent=hermes-0230 language=go model=llamacpp/Holo4-35B-A3B stack=holo4 prompt=neutral · rep 2

> **Second opinion.** This re-checks a prior evaluation that scored
> `requirement_coverage=0.9167` and flagged R1 (POST /books unreachable). The R1
> claim is **confirmed** — see below. Re-scored coverage is unchanged at
> **11/12 = 0.9167**.

## Summary

- **Factors:** language=go, agent=hermes-0230, model=llamacpp/Holo4-35B-A3B, stack=holo4, prompt=neutral
- **Status:** ok (build+tests pass; one integration routing defect)
- **Requirements:** 11/12 implemented, 1 partial (R1), 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective) — `defect_rate=1.0` (build+test succeeded)
- **Build:** pass (from `scores.json`/`defect_rate=1.0`)
- **Lint:** pass — `code_quality=1.0`
- **Coverage:** line `test_coverage=0.644`
- **Findings:** 2 items in `findings.jsonl` (1 high, 1 low)

## Second-opinion verdict on R1

**The first evaluator was correct.** `createBookHandler` is present and fully
implemented (`handlers.go:15`) and persists via `createBook` (`db.go:91`) — so
the *handler* is not missing. But it is **unreachable in the running server**:

- `main.go:11` registers `listBooksHandler` on the **exact** pattern `/books`.
- Go's `ServeMux` routes `POST /books` to that exact handler, which returns
  **405** for non-GET (`handlers.go:50`).
- The `createBookHandler` call sits inside the `/books/` subtree handler behind
  `if r.URL.Path == "/books"` (`main.go:13`) — a branch that can **never fire**,
  because the exact `/books` registration suppresses `ServeMux`'s trailing-slash
  redirect, so `/books` never reaches the subtree handler.

Reproduced standalone with go1.26.6:
`POST /books -> status=405`, `mux.Handler(POST /books)` matched pattern `"/books"`.

Tests pass only because `TestCreateBook`/`TestGetBook`/… call `createBookHandler`
**directly** (bypassing routing), and `TestFullServer` builds a **separate,
corrected** mux (`main_test.go:265-274`) that dispatches POST on the exact
`/books`. The delivered `main.go` wiring is the broken one; the README's own
`curl -X POST .../books` example returns 405 against it.

Classified **partial** (not missing): the create logic is complete and correct,
but the production route is dead-wired, so the requirement is not satisfied as
delivered.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ~ partial | handler `createBookHandler` correct (`handlers.go:15`, persist `db.go:91`) but **unwired**: `main.go:11` sends POST /books to `listBooksHandler` → 405; dead branch `main.go:13`. Reproduced: 405. |
| R2 | GET /books lists all | ✓ implemented | `main.go:11` → `listBooksHandler` (`handlers.go:49`) → `getAllBooks` (`db.go:39`) |
| R3 | GET /books ?author= filter | ✓ implemented | `handlers.go:55` reads `author`; `db.go:44` `WHERE author = ?` |
| R4 | GET /books/{id} | ✓ implemented | `/books/` subtree GET → `getBookHandler` (`main.go:23`, `handlers.go:67`), 404 on miss |
| R5 | PUT /books/{id} | ✓ implemented | `main.go:25` → `updateBookHandler` (`handlers.go:90`, `db.go:106`) |
| R6 | DELETE /books/{id} | ✓ implemented | `main.go:27` → `deleteBookHandler` (`handlers.go:130`, `db.go:134`) |
| R7 | SQLite / embedded DB | ✓ implemented | `db.go:8,15` `go-sqlite3`, `./books.db` |
| R8 | JSON + status codes | ✓ implemented | 201/200/400/404 set across `handlers.go`; JSON encoders throughout |
| R9 | Validation: title+author required | ✓ implemented | `handlers.go:29-36` reject empty title/author with 400 |
| R10 | GET /health | ✓ implemented | `main.go:10` → `healthHandler` (`handlers.go:10`) |
| R11 | README with setup/run | ✓ implemented | `README.md` setup/run/examples (minor: `go run main.go` should be `go run .`) |
| R12 | ≥3 tests | ✓ implemented | 12 `Test*` funcs in `main_test.go`, 0 skips, `test_coverage=0.644>0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
code_quality=1.0  test_coverage=0.644  defect_rate=1.0  maintainability=0.874  idiomatic=0.6
```

`defect_rate=1.0` ⇒ build + tests succeeded. 12 test functions, 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (go, incl. tests) | 694 |
| Go source files | 5 |
| Dependencies (go.sum lines) | 2 |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |

## Findings

Full list in `findings.jsonl`:

1. [high] R1 — POST /books unreachable in delivered server (routing bug); handler correct but unwired.
2. [low] README `go run main.go` omits the other source files; should be `go run .`.

## Reproduce

```bash
# Routing confirmation (standalone, go1.26.6) — a mux mirroring main.go:
#   mux.HandleFunc("/books", listBooksHandler)         # exact
#   mux.HandleFunc("/books/", subtreeHandler)          # subtree with dead /books branch
# POST /books -> status=405; mux.Handler(POST /books) matched pattern "/books"
cd <run_dir>
grep -n 'HandleFunc' main.go          # see /books vs /books/ registration
grep -n 'r.URL.Path == "/books"' main.go   # the dead branch (main.go:13)
```

Architecture summary (`summary/index.md`): not generated in this second-opinion pass.
