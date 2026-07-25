# Evaluation: language=elixir_model=claude-fable-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=elixir, model=claude-fable-5, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective) — from test_coverage=1.0
- **Build:** pass (test_coverage=1.0 ⇒ build+tests ran, from scores.json)
- **Lint:** pass — code_quality=1.0 (from scores.json)
- **Architecture:** run-summary skill unavailable in this environment; summary below
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

A clean, idiomatic Elixir implementation using Plug + Bandit for HTTP and Ecto
with SQLite for persistence. All twelve pinned requirements are satisfied with
supporting tests; both mechanical scores (test_coverage, code_quality) are 1.0.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `lib/books_api/router.ex:34`, `books.ex:20 create_book`, `book.ex:15 changeset` casts all 4 fields |
| R2 | GET /books lists all books | ✓ implemented | `router.ex:22`, `books.ex:8 list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `router.ex:25-29`, `books.ex:15-16 filter_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `router.ex:41`, `with_book` returns 404 (`router.ex:75`) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `router.ex:45`, `books.ex:26 update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `router.ex:54`, `books.ex:32 delete_book`; returns 204 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `repo.ex:3 Ecto.Adapters.SQLite3`, migration `priv/repo/migrations/20260725000001_create_books.exs` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `send_json` (`router.ex:90`); 201/200/204/404/422 across routes |
| R9 | Input validation: title + author required | ✓ implemented | `book.ex:18 validate_required([:title, :author])`; see info finding on 422 vs 400 |
| R10 | GET /health endpoint | ✓ implemented | `router.ex:18` returns `%{status: "ok"}` |
| R11 | README.md with setup + run instructions | ✓ implemented | `README.md` — Setup, Run, API, curl examples, layout |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 13 tests: `router_test.exs` (7), `books_test.exs` (6); test_coverage=1.0 |

## Build & Test

Mechanical scores read from `scores.json` (not re-run per skill guidance):

```text
test_coverage = 1.0   ⇒ build succeeded, all tests passed
code_quality  = 1.0   ⇒ lint/format clean
defect_rate   = 1.0   ⇒ build+test succeeded
maintainability = 0.965
idiomatic     = 0.73
token_efficiency = 0.0
```

Test command (`mix.exs` alias): `ecto.create --quiet` → `ecto.migrate --quiet` → `test`.
13 tests present, 0 skipped → 13 effective. DataCase wipes the books table before
each test (`test/support/data_case.ex`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .ex/.exs) | 424 |
| Files (lib/test/config/priv) | 15 |
| Dependencies (mix.exs) | 5 (plug, bandit, jason, ecto_sql, ecto_sqlite3) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] R9 validation failures return 422 rather than the spec's suggested 400 — `router.ex:87`. 422 Unprocessable Entity is an appropriate rejection code and R8 permits any appropriate 4xx; no change needed, noted for cross-run comparison.

## Architecture

`run-summary` skill unavailable in this environment. Structure by hand:

- `lib/books_api/application.ex` — OTP application; starts `Repo` and (unless
  `:server` disabled for tests) a Bandit HTTP server on port 4000.
- `lib/books_api/router.ex` — Plug.Router; all six routes + `/health`, JSON
  encoding, `Plug.ErrorHandler`, id-parse/404 helper.
- `lib/books_api/books.ex` — CRUD context wrapping the repo.
- `lib/books_api/book.ex` — Ecto schema + changeset (required title/author,
  length + year-range validation, Jason encoder deriving public fields).
- `lib/books_api/repo.ex` — Ecto repo on the SQLite3 adapter.
- `priv/repo/migrations/` — books table with author index.
- `test/` — `data_case.ex` support, context tests, router integration tests.

Clean separation of router / context / schema / repo — idiomatic Phoenix-less
Elixir. No stubs, no skipped tests, no dead code observed.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-48-fable5-gaps/bookshop/runs/language=elixir_model=claude-fable-5_prompt=neutral/rep1
cat scores.json                       # mechanical scores (test_coverage=1.0, code_quality=1.0)
find lib test config priv -type f     # source inventory
grep -rniE ':skip|xtest' test/        # skip detection → 0
# to actually run: mix deps.get && mix test   (builds + migrates + tests)
```
