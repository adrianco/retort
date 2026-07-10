# Evaluation: agent=qwen3-coder-local language=rust prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, agent=qwen3-coder-local, framework=axum, prompt=neutral
- **Status:** ok (builds + tests pass) — but with functional defects (see findings)
- **Requirements:** 8/12 implemented, 3 partial, 1 missing
- **Tests:** 1 passed / 0 failed / 0 skipped (1 effective)
- **Build:** pass — `cargo build` clean (verified in scratchpad copy; test_coverage=1.0 in scores.json)
- **Lint:** pass — code_quality=0.8333 (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 3 high, 1 medium, 1 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/lib.rs:86` create_book → INSERT, 201 |
| R2 | GET /books lists all | ✓ implemented | `src/lib.rs:131` get_books returns all when no filter |
| R3 | GET /books ?author= filter | ~ partial | `src/lib.rs:131` uses `Option<String>` (body extractor); query param never read → filter is non-functional |
| R4 | GET /books/{id} single book | ✓ implemented | `src/lib.rs:174` get_book, 404 on RowNotFound |
| R5 | PUT /books/{id} update | ~ partial | `src/lib.rs:232` `unwrap_or_default()` clobbers unspecified fields → partial update corrupts data |
| R6 | DELETE /books/{id} | ✓ implemented | `src/lib.rs:281` delete_book, 404 when rows_affected=0, 204 |
| R7 | Data stored in SQLite | ~ partial | `src/lib.rs:66` `sqlite::memory:` — embedded but not persistent |
| R8 | JSON + correct HTTP codes | ✓ implemented | 201/200/404/400/204/500 across handlers |
| R9 | Validation: title/author required | ✓ implemented | `src/lib.rs:91-95` empty-check → 400; missing field → 422 via serde |
| R10 | GET /health | ✓ implemented | `src/lib.rs:309` health_check → `{"status":"healthy"}` |
| R11 | README with setup/run | ✓ implemented | `README.md:19-35` setup + run instructions |
| R12 | >= 3 unit/integration tests | ✗ missing | Only `src/lib.rs:328` test_book_struct (1 test, no endpoint exercised); `tests/` empty |

**Prompt factor (neutral):** "include tests that demonstrate the implementation meets the requirements" — not satisfied; the single struct test demonstrates no requirement. Folded into R12.

## Build & Test

```text
cargo build
Finished `dev` profile — clean, no warnings (verified on a scratchpad copy; run_dir not modified)
```

```text
cargo test
running 1 test
test tests::test_book_struct ... ok
test result: ok. 1 passed; 0 failed; 0 ignored
```

Matches stored `test_coverage=1.0` (build + all tests passed).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 366 (lib.rs 342 + main.rs 24) |
| Files (excl. target/ + agent logs) | 12 |
| Dependencies | 6 (axum, tokio, serde, serde_json, sqlx, tower/uuid) |
| Tests total | 1 |
| Tests effective | 1 |
| Skip ratio | 0% |
| Build | pass (clean) |
| code_quality | 0.8333 |
| maintainability | 0.2583 |
| token_efficiency | 0.0306 (very low; `_agent_stdout.log` is 545 MB) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] R3 — `?author=` filter non-functional: `Option<String>` is a body extractor, query param never read.
2. [high] R12 — Only 1 test (need ≥3); it exercises no endpoint; `tests/` empty.
3. [high] R5 — PUT clobbers unspecified fields with defaults → partial update corrupts data.
4. [medium] R7 — SQLite is `sqlite::memory:` only; no persistence across restarts.
5. [low] maint-1 — Entire app in one 342-line `lib.rs`.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-16-qwen3coder/bookshop-256k/runs/agent=qwen3-coder-local_language=rust_prompt=neutral/rep1
cat scores.json                 # stored mechanical scores (test_coverage=1.0)
# Build/test verified on a copy to avoid mutating run_dir:
#   cp -R src Cargo.toml Cargo.lock <tmp>/ && cd <tmp> && cargo test
```
