# Evaluation: agent=codex effort=low language=rust model=gpt-6.2-sol prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, model=gpt-6.2-sol, agent=codex, effort=low, prompt=neutral, framework=unknown (axum used)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `test_coverage=1.0` from `scores.json`
- **Build:** pass — compiled during scoring (`test_coverage=1.0` ⇒ build + tests passed; `defect_rate=1.0`)
- **Lint:** pass — `code_quality=0.789` from `scores.json`
- **Architecture:** single-binary axum service (`main.rs`) + test module (`tests.rs`); `summary/` skill unavailable in this environment
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.rs:87 create_book` — INSERT … RETURNING, 201 + Location |
| R2 | GET /books lists all | ✓ implemented | `main.rs:110 list_books` — SELECT … ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `main.rs:115-123` — WHERE author = ?; test `tests.rs:113` |
| R4 | GET /books/{id} single | ✓ implemented | `main.rs:133 get_book`; 404 via `From<sqlx::Error>` `main.rs:70` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.rs:145 update_book` — UPDATE … RETURNING |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.rs:166 delete_book` — 204; 404 when rows_affected=0 |
| R7 | SQLite / embedded DB | ✓ implemented | `main.rs:191 open_database` — sqlx SqlitePool, file `books.db` |
| R8 | JSON responses + status codes | ✓ implemented | `ApiError` `main.rs:61`; 201/200/204/404/422/415/400 across handlers |
| R9 | Validate title & author required | ✓ implemented | `main.rs:35-45 BookInput::validate` — 422 on blank; test `tests.rs:163` |
| R10 | GET /health | ✓ implemented | `main.rs:180 health` — SELECT 1, 503 on failure; test `tests.rs:194` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build/test/run, env vars, API table, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 4 `#[tokio::test]` in `tests.rs`; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (run evaluated inline as a gate — not yet in `retort.db`); build/test not re-run per skill guidance.

```text
test_coverage = 1.0   # cargo build --locked + cargo test --locked passed, all tests green
defect_rate   = 1.0   # build + test succeeded
code_quality  = 0.789 # lint/quality
```

```text
4 tests (tests.rs): book_lifecycle, list_filters_by_author,
  validates_required_fields_and_ids, health_checks_database
0 skipped / 0 #[ignore] / 0 todo!/unimplemented!
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 455 (main.rs 242, tests.rs 213) |
| Files (excl. target) | 12 |
| Dependencies (Cargo.toml) | 5 (axum, serde, serde_json, sqlx, tokio; +tower dev) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scored inline) |

## Findings

All findings are info-level; no correctness, build, test, or requirement defects.

1. [info] R9 — validation returns 422 where the requirement example cites 400 (semantically correct; documented).
2. [info] Author filter is exact, case-sensitive match (spec leaves matching semantics unspecified).

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=rust_model=gpt-6.2-sol_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores
grep -cE "#\[tokio::test\]|#\[test\]" tests.rs     # 4
grep -rE "#\[ignore\]|\.skip\(|todo!\(" --include="*.rs" .  # 0 skips
# Optional re-verify (slow): cargo test --locked
```
