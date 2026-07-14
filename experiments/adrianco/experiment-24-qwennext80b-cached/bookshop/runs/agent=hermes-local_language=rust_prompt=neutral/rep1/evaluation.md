# Evaluation: agent=hermes-local language=rust prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, agent=hermes-local, framework=unknown (actix-web), prompt=neutral
- **Status:** ok — builds and all tests pass; one requirement is buggy (R5 partial PUT)
- **Requirements:** 11/12 implemented, 1 partial (R5), 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — but all three are tautological
- **Build:** pass — `test_coverage=1.0` from `scores.json` (build + tests ran cleanly)
- **Lint:** pass — `code_quality=0.83` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 1 high, 1 medium, 3 low)

Prompt factor `neutral` prescribes no methodology (`prompts/neutral.md`), so there are no `P*` requirements — the pinned `REQUIREMENTS.json` is the whole spec.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/lib.rs:153` create_book — INSERT + 201 |
| R2 | GET /books lists all | ✓ implemented | `src/lib.rs:106-117` SELECT * FROM books |
| R3 | GET /books ?author= filter | ✓ implemented | `src/lib.rs:88-104` WHERE author = ?1 |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `src/lib.rs:124-150` — Ok(None) → BookError::NotFound |
| R5 | PUT /books/{id} updates | ~ partial | `src/lib.rs:228-263` — fixed placeholders vs positional binding; partial (non-prefix) updates 500 at runtime |
| R6 | DELETE /books/{id} | ✓ implemented | `src/lib.rs:284-302` — 204, 404 when count==0 |
| R7 | SQLite / embedded DB | ✓ implemented | `src/lib.rs:67-81` rusqlite (bundled) |
| R8 | JSON + HTTP status codes | ✓ implemented | 201/200/404/400/204 across handlers; `src/lib.rs:45-53` ResponseError |
| R9 | Validate title & author required | ✓ implemented | `src/lib.rs:158-163` is_empty() checks → 400 (also serde-required, non-Option) |
| R10 | GET /health | ✓ implemented | `src/lib.rs:62-64` returns {"status":"healthy"} |
| R11 | README with setup/run | ✓ implemented | `README.md` — build/run/endpoints/curl examples |
| R12 | ≥3 tests that run | ✓ implemented | `src/lib.rs:332-373` 3 `#[test]` fns, test_coverage=1.0 (but tautological — see findings) |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill step 2):

```text
test_coverage = 1.0    # build succeeded + all tests passed
defect_rate   = 1.0    # build+test success
code_quality  = 0.83   # lint/quality
```

Tests (inline in `src/lib.rs`, module `tests`): 3 passed, 0 failed, 0 skipped. No `#[ignore]` attributes found. All three assert on locally-constructed values and exercise no handler, route, or DB (see finding `test-quality-1`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | ~370 (src/lib.rs 374, src/main.rs 25, migration 7) |
| Files (excl. target/summary) | 15 |
| Dependencies (Cargo.toml) | 7 runtime + 1 dev (actix-test) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build | pass (test_coverage=1.0) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] R5 — partial PUT /books/{id} updates fail at runtime for non-prefix field subsets (`src/lib.rs:228-263`)
2. [medium] The 3 tests are tautological and exercise no handler/route/DB (`src/lib.rs:332-373`)
3. [low] Duplicate dead `main()` in lib.rs + unused migration file (`src/lib.rs:304-325`, `migrations/0001_init.sql`)
4. [low] `DbPool` is a single `Mutex<Connection>`, not a pool; serializes all requests (`src/lib.rs:7`)
5. [low] `init_pool()` called twice at startup (`src/main.rs:7,10`)

## Reproduce

```bash
cd experiment-24-qwennext80b-cached/bookshop/runs/agent=hermes-local_language=rust_prompt=neutral/rep1
cat scores.json                                              # mechanical scores (build/test/lint)
grep -rnE "#\[test\]|#\[ignore\]" src --include="*.rs"       # test / skip census
cat src/lib.rs src/main.rs README.md                         # requirement conformance
# Optional full rebuild (slow; scores already stored): cargo test
```
