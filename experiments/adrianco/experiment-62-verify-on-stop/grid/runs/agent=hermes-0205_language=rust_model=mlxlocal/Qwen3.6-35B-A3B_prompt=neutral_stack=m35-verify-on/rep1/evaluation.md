# Evaluation: agent=hermes-0205 · rust · mlxlocal/Qwen3.6-35B-A3B · m35-verify-on · rep 1

> **Second-opinion re-check.** A first evaluation scored requirement_coverage=0.9167
> and marked R7 as not met. This re-check **CONFIRMS** that finding: the live server
> genuinely never initializes the `books` table on its served connection. See R7 below.

## Summary

- **Factors:** language=rust, agent=hermes-0205, model=mlxlocal/Qwen3.6-35B-A3B, prompt=neutral, stack=m35-verify-on (REPAIR task)
- **Status:** ok (build+tests pass) but with a **critical live-server defect** — every DB route fails at runtime
- **Requirements:** 11/12 implemented, 1 partial (R7), 0 missing
- **Tests:** 21 passed / 0 failed / 0 skipped (21 effective) — from test_coverage=1.0
- **Build:** pass — test_coverage=1.0 from scores.json (build + all tests ran and passed)
- **Lint:** pass — code_quality=0.833 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 1 high, 0 medium, 1 low, 1 info)

## Re-check of the disputed claim (R7)

**First evaluator's claim:** "Live server never initializes the books table (schema
created on a discarded connection)." **Verdict: CONFIRMED — the first evaluator was right.**

Evidence gathered by reading the actual code and workspace:

- `src/main.rs:79` — the served connection is `rusqlite::Connection::open_in_memory()`,
  a fresh `:memory:` database. **No DDL is ever applied to it.**
- `src/main.rs:80` — `models::create_connection("in-memory").ok()` opens a connection to
  a file literally named `in-memory` (rusqlite `open()` treats the string as a path, not
  `:memory:`), runs `TABLE_DEF` on it (`models.rs:40-44`), then **discards it** via `.ok()`.
- `src/main.rs:82` — `web::Data::new(Mutex::new(db))` wraps the schema-less connection
  from line 79. Every route handler locks this connection.
- **Physical proof:** the workspace contains a stray on-disk SQLite file `in-memory`
  (3 pages). `sqlite3 in-memory .tables` → `books`; `.schema` matches `models::TABLE_DEF`.
  That file is the table created on the discarded connection.
- **Why tests still pass (test_coverage=1.0):** every test builds its OWN connection with
  the schema applied — `create_db()` at `main.rs:107-111` and `get_test_conn()` at
  `database.rs:144-148` both call `conn.execute_batch(models::TABLE_DEF)`. The tests never
  exercise `main()`, so the live-server bug is invisible to the test gate.

Consequence: on a real `cargo run`, the first `POST /books` (or any DB route) fails with
`no such table: books`. This is the exact regression FEEDBACK.md told the repair to fix,
and it was **not** fixed. R7 ("persistence uses SQLite/embedded DB, not just in-memory
state") is therefore not functionally met. Re-scored requirement_coverage = **11/12 = 0.9167**,
matching the first evaluation.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.rs:15-24`, `database.rs:5-35` |
| R2 | GET /books lists all books | ✓ implemented | `main.rs:26-36`, `database.rs:37-65` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.rs:31`, `database.rs:38-49` (LIKE) |
| R4 | GET /books/{id} single book | ✓ implemented | `main.rs:38-45`, `database.rs:67-80` (404 if absent) |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.rs:47-64`, `database.rs:82-115` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.rs:66-73`, `database.rs:117-126` |
| R7 | Data stored in SQLite | ~ partial | live server serves schema-less `:memory:` conn — `main.rs:79-82`; table created on a discarded conn |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/400/204 across `main.rs:20-72` |
| R9 | title & author required | ✓ implemented | `database.rs:6-15` (400 on missing/empty) |
| R10 | GET /health | ✓ implemented | `main.rs:11-13,87` returns `{"status":"healthy"}` |
| R11 | README with setup/run | ✓ implemented | `README.md:28-48` (build/run/test instructions) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 21 tests (main.rs + database.rs), test_coverage=1.0 |

## Build & Test

Scores read from `scores.json` (not re-run, per evaluate-run skill):

```text
test_coverage = 1.0   → build succeeded, all 21 tests ran and passed
code_quality  = 0.833
defect_rate   = 1.0
token_efficiency = 1.0   maintainability = 0.341   idiomatic = 0.58
```

Skipped-test scan: `grep -rE "#\[ignore\]|#\[cfg\(ignore\)\]"` → 0. No skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Source files (rust) | 3 (`main.rs`, `models.rs`, `database.rs`) |
| Tests total | 21 |
| Tests effective | 21 |
| Skip ratio | 0% |
| Dependencies | 8 (Cargo.toml) |
| test_coverage | 1.0 |
| code_quality | 0.833 |

## Findings

Full list in `findings.jsonl`:

1. **[high]** R7 — Live server never initializes the books table; schema created on a
   discarded connection (`main.rs:79-82`). Every DB route fails at runtime with
   "no such table: books"; tests mask it by building their own schema-initialized conn.
2. **[low]** README claims working in-memory SQLite storage that does not function on the
   live server (`README.md:20`).
3. **[info]** The repair attempt did not address the FEEDBACK-flagged defect; verify-on-stop
   did not catch the persisting live-server bug.

## Reproduce

```bash
cd "experiments/adrianco/experiment-62-verify-on-stop/grid/runs/agent=hermes-0205_language=rust_model=mlxlocal/Qwen3.6-35B-A3B_prompt=neutral_stack=m35-verify-on/rep1"
sed -n '75,98p' src/main.rs          # served conn = open_in_memory(), no DDL; table made on discarded "in-memory" conn
file in-memory && sqlite3 in-memory ".tables"   # -> books  (the discarded connection's table, left on disk)
cat scores.json                       # test_coverage=1.0 — tests build their own schema, so the bug is invisible to them
grep -rEn "#\[ignore\]" src/          # 0 skipped tests
```
