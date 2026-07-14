# Evaluation: language=rust_model=sonnet-4.6_prompt=tdd · rep 1

## Summary

- **Factors:** language=rust, model=sonnet-4.6, prompt=tdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective) — from `test_coverage=1.0`
- **Build:** pass (test_coverage=1.0 ⇒ build + all tests passed, per scores.json)
- **Lint:** pass — code_quality=0.833, idiomatic=0.70 (no re-run; from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

Pinned checklist from `experiment-15-sonnet5/rest-api/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `handlers.rs:19 create_book` → `db.rs:17 create_book` INSERTs all 4 fields; `main.rs:126 test_create_book_success` |
| R2 | GET /books lists all | ✓ implemented | `handlers.rs:46 list_books` → `db.rs:34`; `main.rs:157 test_list_books_empty`, `:198` len==2 |
| R3 | GET /books ?author= filter | ✓ implemented | `db.rs:35-44` WHERE author=?; `BookFilter` models.rs:28; `main.rs:203` filter asserts len==1 |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `handlers.rs:60 get_book` Ok(None)→404; `main.rs:211` found, `:218 test_get_book_not_found` |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.rs:75` → `db.rs:82 update_book` preserves unset fields; `main.rs:249` update, `:269 test_update_not_found` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handlers.rs:91 delete_book`; `db.rs:99`; `main.rs:260` delete, `:280 test_delete_not_found` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | rusqlite bundled, `db.rs:5 init_db` CREATE TABLE books; opened in-memory (`main.rs:26`) — see finding R7 |
| R8 | JSON responses + appropriate status codes | ✓ implemented | JSON everywhere; 201/200/404/422; `handlers.rs` StatusCode uses throughout |
| R9 | Validation: title & author required | ✓ implemented | `handlers.rs:23-34` rejects empty/absent title & author (returns 422; spec suggests 400 — finding R9) |
| R10 | GET /health health-check | ✓ implemented | `handlers.rs:15 health` → `{"status":"ok"}`; `main.rs:119 test_health_check` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — cargo run, endpoints table, curl examples, validation, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | 10 `#[tokio::test]` in `main.rs`; test_coverage=1.0 |

**Prompt factor (prompt=tdd), process instructions — cannot-verify from final artifacts:**
The `prompts/tdd.md` red/green/refactor discipline is a process constraint not directly verifiable from the final snapshot. Consistent with TDD: 10 comprehensive tests exist and `_agent_stdout.log` narrates 6 sequential TDD cycles (health → create+validation → list+filter → get+404 → update+404 → delete+404). No test-first history is recoverable, so not counted as a pass/fail requirement.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
test_coverage   = 1.0    # build + all 10 tests passed
defect_rate     = 1.0    # build+test succeeded
code_quality    = 0.833
maintainability = 0.899
idiomatic       = 0.70
token_efficiency= 0.064
```

Skip scan (`grep -rE "#\[ignore\]|#\[cfg\(ignore\)\]" src`): 0 skipped/ignored tests → 10 effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, incl. inline tests) | 521 (main 284, handlers 104, db 102, models 31) |
| Non-test source (approx.) | ~356 (main.rs test module ≈ 165 lines) |
| Files (excl. target/.git) | 15 |
| Dependencies (Cargo.toml) | 7 runtime (axum, tokio, rusqlite, serde, serde_json, uuid, tower) + 2 dev |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=1.0) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] R9 — Validation returns 422 (Unprocessable Entity) instead of the spec-suggested 400. Defensible design; still rejects invalid input. `handlers.rs:24-33`
2. [low] R7 — SQLite opened in-memory (`main.rs:26`), so data is not durable across restarts. Requirement satisfied (genuine embedded DB used); README documents the in-memory choice.
3. [info] Enhancement — 10 integration tests, well beyond the 3-test minimum (R12).

No critical, high, or medium findings. This is a clean, fully-conformant run.

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=rust_model=sonnet-4.6_prompt=tdd/rep1
cat scores.json                 # build/test/lint scores (not re-run)
grep -rE "#\[ignore\]" src      # skip scan → 0
grep -rcE "#\[tokio::test\]" src/main.rs   # 10 tests
cargo test                      # (optional) re-verify: 10 passed
```
