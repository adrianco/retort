# Evaluation: effort=low language=rust model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=rust, model=claude-haiku-5-5, effort=low, prompt=neutral (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — from `scores.json` test_coverage=1.0
- **Build:** pass (test_coverage=1.0 ⇒ build + tests ran) — not re-run
- **Lint:** pass — code_quality=0.83 from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Scores read from `scores.json` (inline gate output): test_coverage=1.0, defect_rate=1.0, code_quality=0.833, maintainability=0.788, idiomatic=0.72, token_efficiency=0.085. Build/test/lint were **not** re-run per the evaluate-run skill.

## Requirements

Using the pinned `REQUIREMENTS.json` checklist (12 requirements, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/lib.rs:85 create_book` → `book.rs:121 insert`; returns 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `src/lib.rs:102 list_books` → `book.rs:141 list` |
| R3 | GET /books ?author= filter | ✓ implemented | `book.rs:144 WHERE (?1 IS NULL OR author = ?1 COLLATE NOCASE)`; test `list_filters_by_author` api.rs:91 |
| R4 | GET /books/{id} single book (404) | ✓ implemented | `src/lib.rs:110 get_book` → `ApiError::NotFound`; test `missing_book_returns_404` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/lib.rs:116 update_book` → `book.rs:152 update`; test `update_replaces_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/lib.rs:127 delete_book` → `book.rs:164 delete`; test `delete_removes_book` |
| R7 | Data stored in SQLite | ✓ implemented | `Cargo.toml` rusqlite bundled; `book.rs:99 init_schema` real table |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `src/lib.rs:43 IntoResponse for ApiError`; 201/200/204/400/404/422/500 |
| R9 | Validation: title & author required | ✓ implemented | `book.rs:40-41,75 required()`; test `create_rejects_missing_required_fields` (returns 422, see finding) |
| R10 | GET /health | ✓ implemented | `src/lib.rs:81 health` → `{"status":"ok"}`; test `health_reports_ok` |
| R11 | README with setup/run | ✓ implemented | `README.md` setup, run, endpoints, env vars, examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 15 test functions (6 unit `book.rs`, 9 integration `api.rs`); test_coverage=1.0 |

## Build & Test

Not re-run — scores read from `scores.json`:

```text
test_coverage = 1.0   # cargo build + cargo test succeeded, all tests passed
defect_rate   = 1.0   # build+test success
code_quality  = 0.833 # lint/quality
```

Skip/ignore scan (read-only grep): 0 `#[ignore]`, 0 `#[cfg(ignore)]`. No disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 537 |
| Files (src + tests) | 4 |
| Dependencies (Cargo.toml) | 5 runtime + 2 dev |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | not re-run (gate) |

## Findings

Full list in `findings.jsonl`. No critical/high/medium/low findings.

1. [info] R9 — validation errors return 422 (Unprocessable Entity) rather than the 400 cited as an example; defensible and documented in README.
2. [info] Input validation exceeds spec — adds year-range (0–9999) and ISBN-10/13 format checks beyond the required title/author presence.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=rust_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                                             # stored mechanical scores (no re-run)
grep -rE "#\[ignore\]|#\[cfg\(ignore\)\]" . --include="*.rs" | wc -l   # skip scan -> 0
# Pinned requirements:
cat ../../REQUIREMENTS.json
```
