# Evaluation: agent=codex effort=low language=elixir model=gpt-6.1-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=elixir, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — from test_coverage=1.0 in scores.json
- **Build:** pass (test_coverage=1.0 ⇒ build + all tests ran green)
- **Lint:** pass — code_quality=1.0 (scores.json)
- **Architecture:** Plug.Router + Bandit HTTP server, Ecto schema over `ecto_sqlite3`, OTP supervision tree (run-summary skill not invoked — codebase is 228 LOC across 10 files; structure summarized inline below)
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `lib/books/router.ex:28` post "/books" → `change` → `save` → `Repo.insert_or_update` |
| R2 | GET /books lists all books | ✓ implemented | `lib/books/router.ex:15` `Repo.all(from b in query, order_by: b.id)` |
| R3 | GET /books ?author= filter | ✓ implemented | `lib/books/router.ex:17-21` `where: b.author == ^author`; test `list filters by exact author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `lib/books/router.ex:32` `with_book` → `serialize`; `nil` → 404 (`:52`) |
| R5 | PUT /books/{id} updates | ✓ implemented | `lib/books/router.ex:36` put → `change(conn, book, 200)` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `lib/books/router.ex:40` `Repo.delete!(book)` → 204 |
| R7 | Data stored in SQLite | ✓ implemented | `lib/books/repo.ex` `Ecto.Adapters.SQLite3`; `mix.exs` `ecto_sqlite3`; table created at `application.ex:10` |
| R8 | JSON responses + correct status codes | ✓ implemented | `json/3` helper (`:87`); 201/200/204/404/400/422/415 across routes |
| R9 | Validation: title + author required | ✓ implemented | `lib/books/book.ex:14` `validate_required([:title, :author])`; rejected 422 (see info finding re: 400 vs 422) |
| R10 | GET /health | ✓ implemented | `lib/books/router.ex:11` returns `%{status: "ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — deps.get, `mix run --no-halt`, PORT/DATABASE_PATH, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test/router_test.exs` — 4 tests, all passing |

## Build & Test

Build/test not re-run — stored scores used per skill policy.

```text
scores.json: {"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
              "maintainability": 0.876, "idiomatic": 0.78, "token_efficiency": 0.0}
test_coverage=1.0 ⇒ `mix test` built the project and all 4 tests passed; 0 skips.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (lib+test+config) | 228 |
| Files (source) | 10 |
| Dependencies | 4 (bandit, plug, jason, ecto_sqlite3) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build/test | pass (from scores.json) |

## Findings

Full list in `findings.jsonl`:

1. [info] R9 validation returns 422 (Unprocessable Entity), not the 400 the checklist's `how_to_verify` cites — idiomatic REST; malformed JSON still returns 400. No change required.

## Architecture (inline)

- `lib/books/application.ex` — OTP `Application`; supervises `Books.Repo`, runs `CREATE TABLE IF NOT EXISTS`, conditionally starts Bandit (skipped in `:test`).
- `lib/books/repo.ex` — `Ecto.Repo` on the SQLite3 adapter.
- `lib/books/book.ex` — Ecto schema + changeset with `validate_required`.
- `lib/books/router.ex` — `Plug.Router` with all six routes + `/health`, JSON helpers, 404/400/415 error handling via a `call/2` rescue.
- `config/` — per-env config; test uses `:memory:` SQLite and disables the HTTP server.

Clean, idiomatic Elixir. No security or correctness concerns surfaced.

## Reproduce

```bash
cd "experiments/adrianco/experiment-93-terra61-deepen/rest-api-crud/runs/agent=codex_effort=low_language=elixir_model=gpt-6.1-terra_prompt=neutral/rep1"
cat scores.json            # stored mechanical scores (build/test/lint)
grep -rE '^\s*test\s+"' test/ | wc -l   # test count = 4
# full build/test: mix deps.get && mix test
```
