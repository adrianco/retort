# Evaluation: hermes-0205 · rust · Qwen3.6-35B-A3B · m35-verify-on · rep 1

## Summary

- **Factors:** language=rust, agent=hermes-0205, model=mlxlocal/Qwen3.6-35B-A3B, prompt=neutral, stack=m35-verify-on
- **Status:** ok (builds + tests pass) — one live-runtime defect (R7)
- **Requirements:** 11/12 implemented, 0 partial, 1 missing (R7)
- **Tests:** 21 passed / 0 failed / 0 skipped (21 effective) — test_coverage=1.0 from scores.json
- **Build:** pass — test_coverage=1.0 (build + all tests ran)
- **Lint:** code_quality=0.8333 from scores.json
- **Findings:** 2 items in `findings.jsonl` (1 high, 1 info)

## Second-opinion verdict

This re-check was asked to re-verify one disputed claim from a prior evaluation
(requirement_coverage=0.9167, R7 not met). **The first evaluator was correct.**

- **R7 (SQLite persistence / live server never creates the books table): CONFIRMED not met.**
  `src/main.rs:79` binds the server's connection `db` to a fresh
  `rusqlite::Connection::open_in_memory()` on which `CREATE TABLE` is **never** run.
  `src/main.rs:80` runs `TABLE_DEF` on a *different* connection —
  `models::create_connection("in-memory")` — whose result is immediately discarded
  with `.ok()`. Because SQLite's `open()` treats `"in-memory"` as a **file path**
  (not the `:memory:` sentinel), this wrote a real on-disk file named `in-memory`.
  That 12288-byte artifact was verified to contain a populated `books` table —
  it is the discarded connection's output. `src/main.rs:82` then wraps the
  schema-less `db` into app state, so every live `/books` request would fail at
  runtime with `no such table: books`. The 21 tests pass only because each builds
  its own initialized connection (`create_db()` at main.rs:107-111,
  `get_test_conn()` at database.rs:144-148), masking the defect.

I looked for a schema-init on the server's own connection and it is genuinely
absent. Confirmed, not invented.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/main.rs:89` route → `database::create_book` (database.rs:5) |
| R2 | GET /books lists all | ✓ implemented | `src/main.rs:88` route → `database::list_books` (database.rs:37) |
| R3 | GET /books ?author= filter | ✓ implemented | `src/main.rs:31` reads `author` param; `database.rs:38-44` `LIKE` filter |
| R4 | GET /books/{id} single book | ✓ implemented | `src/main.rs:90` route → `get_book_by_id`; 404 at database.rs:78 |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/main.rs:91` route → `database::update_book` (database.rs:82) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/main.rs:92` route → `database::delete_book` (database.rs:117) |
| R7 | Data stored in SQLite, not just in-memory state | ✗ missing | server connection never gets the schema; see verdict above (`src/main.rs:79-82`) |
| R8 | JSON responses + status codes | ✓ implemented | Created/Ok/NotFound/BadRequest/NoContent across `src/main.rs:21-72` |
| R9 | Validation: title & author required | ✓ implemented | `src/database.rs:7-8`; tests main.rs:179-243 assert 400 |
| R10 | GET /health | ✓ implemented | `src/main.rs:11-13,87` returns `{"status":"healthy"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — features, prerequisites, setup/run sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 21 tests (10 in main.rs, 11 in database.rs), test_coverage=1.0 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill step 2):

```text
test_coverage = 1.0     → build + all 21 tests passed
code_quality  = 0.8333
defect_rate   = 1.0
```

Skipped/disabled tests: `#[ignore]` count = 0.

## Metrics

| Metric | Value |
|--------|-------|
| Source files (rust) | 3 (main.rs, database.rs, models.rs) |
| Tests total | 21 |
| Tests effective | 21 |
| Skip ratio | 0% |
| test_coverage | 1.0 |
| code_quality | 0.8333 |
| requirement_coverage | 0.9167 (11/12) |

## Findings

1. [high] R7 — Live server never initializes the books table; schema created on a discarded connection (`src/main.rs:79-82`). Every live `/books` request fails at runtime with `no such table: books`.
2. [info] Passing tests mask the runtime bug — each test builds its own initialized connection, so main()'s wiring is never exercised.

## Reproduce

```bash
cd "experiments/adrianco/experiment-62-verify-on-stop/grid/runs/agent=hermes-0205_language=rust_model=mlxlocal/Qwen3.6-35B-A3B_prompt=neutral_stack=m35-verify-on/rep1"
cat scores.json
sqlite3 in-memory ".schema books"   # the discarded connection's output — proves the schema went to the wrong DB
sed -n '79,82p' src/main.rs
```
