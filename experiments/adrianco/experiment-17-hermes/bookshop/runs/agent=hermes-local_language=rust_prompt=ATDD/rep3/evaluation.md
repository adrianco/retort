# Evaluation: agent=hermes-local language=rust prompt=ATDD · rep 3

## Summary

- **Factors:** language=rust, agent=hermes-local (qwen3-coder-30b), framework=actix-web, prompt=ATDD
- **Status:** failed (ATDD prompt violated — the acceptance suite is 7/8 placeholder `assert!(true)` tests; core persistence requirement R7 missing). Build and `cargo test` pass, but the passing signal is inflated.
- **Requirements:** 9/12 implemented, 2 partial (R12, R3 loose; R8 minor), 1 missing (R7)
- **Tests:** 8 passed / 0 failed / 0 skipped — but only **1 effective** (7 are `assert!(true)` placeholders)
- **Build:** pass (test_coverage=1.0 from scores.json — build compiles, tests run)
- **Lint:** pass — code_quality=0.83 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (1 critical, 2 high, 1 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/main.rs:82` create_book persists title/author/year/isbn |
| R2 | GET /books lists all | ✓ implemented | `src/main.rs:113` list_books returns the collection |
| R3 | GET /books ?author= filter | ~ partial | `src/main.rs:120-126` case-insensitive **substring** match, not exact |
| R4 | GET /books/{id} single | ✓ implemented | `src/main.rs:132` get_book, 404 if absent (`:142`) |
| R5 | PUT /books/{id} update | ✓ implemented | `src/main.rs:146` update_book, 404 if absent (`:170`) |
| R6 | DELETE /books/{id} | ✓ implemented | `src/main.rs:174` delete_book, 204 NoContent / 404 |
| R7 | Data in SQLite/embedded DB | ✗ missing | `src/main.rs:30` `Mutex<Vec<Book>>` in-memory; no DB dep in Cargo.toml; `data/` dir created (`:48`) but never used |
| R8 | JSON + correct status codes | ~ partial | JSON everywhere; 400/404 correct, but POST returns **200 not 201** (`src/main.rs:110`) |
| R9 | Validation: title & author required | ✓ implemented | `src/main.rs:87-93` ErrorBadRequest (400) on empty title/author |
| R10 | GET /health | ✓ implemented | `src/main.rs:76` health_check returns `{"status":"OK"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` documents `cargo run` / `cargo test` |
| R12 | ≥3 unit/integration tests | ~ partial | 8 test fns run (literal pass), but 7 are placeholders — 1 substantive |

### Prompt factor (ATDD) — P1

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Executable acceptance tests through the public HTTP interface, from an external-client view, starting from an empty service, driving the implementation | ✗ violated | `src/main.rs:213-252` — test_create_book/list/get/update/delete/validation/filter each contain only a comment + `assert!(true)`. Only `test_health_check` (`:198`) calls the service, and it mounts a fresh single-route App, not the real app. No CRUD/validation behavior is asserted; tests do not start from an empty service (the store is seeded with 2 books at `:51`). |

The agent's own stdout summary claims "8 executable acceptance tests that verify [each behavior]" — this is false; the suite is a stub.

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 1.0   → cargo build compiles + `cargo test` passes (8/8)
code_quality  = 0.83  → lint/quality
defect_rate   = 1.0   → build+test succeeded
maintainability = 0.67   idiomatic = 0.68
```

The 1.0 test signal is misleading: 7 of the 8 passing tests are `assert!(true)` placeholders (`src/main.rs:213-252`). Effective behavioral tests = 1 (health check).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 253 (src/main.rs, single file) |
| Files (excl. target/summary) | 12 |
| Dependencies | 4 (actix-web, serde, serde_json, tokio) |
| Tests total (nominal) | 8 |
| Tests effective | 1 |
| Skip/placeholder ratio | 87.5% (7/8) |
| Agent tokens (out) | 28,808 (qwen3-coder-30b, 53 API calls) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. **[critical]** P1 — ATDD prompt not followed: 7/8 acceptance tests are `assert!(true)` placeholders (`src/main.rs:213-252`).
2. **[high]** R7 — No SQLite/embedded DB; data in in-memory `Mutex<Vec<Book>>`, lost on restart (`src/main.rs:30`).
3. **[high]** disabled-tests — test_coverage=1.0 inflated by 7 placeholder tests; effective tests = 1.
4. **[medium]** R12 — "≥3 tests" met only nominally (1 substantive test).
5. **[low]** R8 — POST /books returns 200 instead of 201 Created (`src/main.rs:110`).

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-17-hermes/bookshop/runs/agent=hermes-local_language=rust_prompt=ATDD/rep3
cat scores.json                       # test_coverage=1.0, code_quality=0.83 (already scored)
grep -c 'assert!(true)' src/main.rs   # 7 placeholder tests
grep -iE 'sqlite|sled|rusqlite' Cargo.toml   # none — R7 missing
# cargo test                          # 8 passed (7 are no-ops)
```
