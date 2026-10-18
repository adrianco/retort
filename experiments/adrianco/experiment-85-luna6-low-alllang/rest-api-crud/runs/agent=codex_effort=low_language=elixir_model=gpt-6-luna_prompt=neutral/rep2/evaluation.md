# Evaluation: agent=codex_effort=low_language=elixir_model=gpt-6-luna_prompt=neutral · rep 2

## Summary

- **Factors:** language=elixir, agent=codex, model=gpt-6-luna, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`); prompt `neutral.md` adds no checkable instructions beyond "include tests"
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective). `test_coverage=1.0` from `scores.json`, not re-run
- **Build:** pass (`defect_rate=1.0` from `scores.json`)
- **Lint:** pass (`code_quality=1.0`)
- **Architecture:** see `summary/index.md`
- **Findings:** 8 items in `findings.jsonl` (0 critical, 1 high, 2 medium, 3 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `router.ex:4`, `store.ex:27`; test "creates, fetches…" |
| R2 | GET /books lists all | ✓ implemented | `router.ex:13`, `store.ex:38` |
| R3 | ?author= filter | ✓ implemented | `store.ex:39`; test asserts filtered list |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `router.ex:16`; test "missing book returns 404" |
| R5 | PUT /books/{id} | ✓ implemented | `router.ex:24`, `store.ex:46`; test asserts "Revised" |
| R6 | DELETE /books/{id} | ✓ implemented | `router.ex:37` → 204; test confirms 404 afterwards |
| R7 | SQLite storage | ✓ implemented | `store.ex:62` shells out to the `sqlite3` CLI against `data/books.sqlite3` |
| R8 | JSON + proper status codes | ✓ implemented | `server.ex:105-125`; 200/201/204/400/404/422 |
| R9 | title/author required | ✓ implemented | `router.ex:51-58` → 422 (not 400; see info finding) |
| R10 | GET /health | ✓ implemented | `router.ex:2`; test "health check" |
| R11 | README with setup/run | ✓ implemented | `README.md`: `mix run --no-halt`, env vars, `mix test` |
| R12 | ≥3 tests | ✓ implemented | 4 tests in `test/book_api_test.exs`, `test_coverage=1.0` |

## Build & Test

```text
Not re-run (per skill). scores.json:
test_coverage=1.0 defect_rate=1.0 code_quality=1.0 maintainability=0.675 idiomatic=0.45 token_efficiency=0.0
```

The only command run was a one-line `elixir -e` check showing that `to_string/1` on an integer list returns raw text without escaping it. That confirms the injection finding.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (lib + test) | 468 |
| Files (source) | 7 (5 lib, 2 test) |
| Dependencies | 0 (Hex); runtime needs the `sqlite3` CLI |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] SQL injection via a JSON array for `year`/`isbn`. `q/1` escapes only binaries, and `to_string/1` on a charlist emits raw SQL into an INSERT that is run as multiple statements (`store.ex:80`).
2. [medium] A non-scalar `year`/`isbn` such as `{}` crashes the Store GenServer, so the client gets no response (`store.ex:80`).
3. [medium] Read errors such as `{:error, :too_large}` match the `{status, body}` clause and crash `send_response`, so the 400 fallback can never run (`server.ex:28-32`).
4. [low] `sql/2` ignores the sqlite3 exit status (`store.ex:61`).
5. [low] Tests call the router directly and write into the default dev database (`test/book_api_test.exs`).

The earlier judge pass (`_judge/attempt-001`) called the interpolated SQL "safe on current paths". That is wrong for list-typed `year`/`isbn`, so this report raises it to high.

## Reproduce

```bash
cd "{run_dir}"
cat scores.json
elixir -e 'IO.puts(to_string(String.to_charlist("1); DROP TABLE books; --")))'
```
