# Evaluation: rest-api-crud · agent=codex effort=low language=rust model=gpt-6-luna prompt=neutral · rep 2

## Summary

- **Factors:** language=rust, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — from `test_coverage=1.0`
- **Build:** pass (test_coverage=1.0 ⇒ build + all tests passed; from `scores.json`)
- **Lint:** pass — code_quality=0.611 (from `scores.json`); 0 `#[ignore]` tests
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Clean pass. A compact, idiomatic Axum + rusqlite(SQLite) REST API that satisfies every pinned requirement, with build and all tests green per the stored scores.

## Requirements

Checklist from the task's pinned `REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/main.rs:74` `create_book`, persists 4 fields |
| R2 | GET /books lists all books | ✓ implemented | `src/main.rs:84` `list_books` returns `Vec<Book>` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/main.rs:86-95` branches on `author` query param; test `main.rs:162` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `src/main.rs:100` `get_book`, `.optional()...ok_or_else(not_found)` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/main.rs:107` `update_book`, `UPDATE ... WHERE id` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/main.rs:117` `delete_book`, returns 204 / 404 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `src/main.rs:54-65` rusqlite `books.db`, `CREATE TABLE books` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/204/400/404/500 across handlers; `HttpError` JSON body `main.rs:35-40` |
| R9 | Input validation: title and author required | ✓ implemented | `src/main.rs:46-51` `validate()` → 400; test `main.rs:169` |
| R10 | GET /health endpoint | ✓ implemented | `src/main.rs:68` returns `{"status":"ok"}`; test `main.rs:188` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Run/Endpoints/Tests sections |
| R12 | At least 3 tests (test_coverage > 0) | ✓ implemented | 4 `#[tokio::test]` fns `main.rs:153-192`; test_coverage=1.0 |

## Build & Test

Build/test not re-run — stored mechanical scores used per skill policy.

```text
scores.json: {"test_coverage": 1.0, "defect_rate": 1.0, "code_quality": 0.611,
              "maintainability": 0.667, "idiomatic": 0.45, "token_efficiency": 0.0182}
test_coverage=1.0 ⇒ cargo build succeeded and all tests passed.
```

```text
Tests (from src/main.rs #[cfg(test)] mod tests):
  creates_lists_and_filters_books ....... (POST, GET list, ?author= filter)
  validates_required_fields_and_returns_not_found ... (400 + 404)
  updates_and_deletes_books ............. (PUT, DELETE, 404 after delete)
  health_endpoint_is_json ............... (GET /health)
4 tests, 0 failed, 0 skipped (#[ignore] count = 0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 193 (`src/main.rs`) |
| Files | 1 source module (+ Cargo.toml, Cargo.lock, README.md) |
| Dependencies | 5 runtime + 1 dev (Cargo.toml) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; test_coverage=1.0) |

## Findings

Top findings (full list in `findings.jsonl`) — none at medium or above:

1. [low] Mutex lock uses `.unwrap()` in every handler — a panic poisons the mutex, 500ing all later requests (`src/main.rs:76,85,101,109,118`).
2. [info] Synchronous rusqlite calls inside async handlers on one shared connection (`src/main.rs:74-122`).
3. [info] PUT is full-replace (requires title/author), no partial-update path (`src/main.rs:107`). No deduction.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=rust_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json            # stored mechanical scores (build+test already run)
cat ../../../REQUIREMENTS.json   # pinned 12-item checklist
grep -rnE "#\[ignore\]" src --include="*.rs" | wc -l   # skip count = 0
# optional full re-run (slow; not required): cargo test
```
