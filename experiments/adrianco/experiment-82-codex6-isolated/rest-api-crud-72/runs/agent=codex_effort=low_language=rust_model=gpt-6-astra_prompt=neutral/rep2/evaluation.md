# Evaluation: rest-api-crud · codex/gpt-6-astra/rust/neutral · rep 2

## Summary

- **Factors:** language=rust, agent=codex, model=gpt-6-astra, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective) — from `test_coverage=1.0` in scores.json
- **Build:** pass (test_coverage=1.0 ⇒ build + tests succeeded; not re-run)
- **Lint:** pass — code_quality=0.83 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `lib.rs:164 create_book` — INSERT of 4 fields, returns 201 + Location |
| R2 | GET /books lists all | ✓ implemented | `lib.rs:189 list_books` — SELECT ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `lib.rs:185 BookFilter`, `lib.rs:195` WHERE (?1 IS NULL OR author = ?1); test `list_and_filter_by_exact_author` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `lib.rs:200 get_book` → `find_book` returns `not_found` (404) |
| R5 | PUT /books/{id} updates | ✓ implemented | `lib.rs:207 update_book` — UPDATE, 404 when 0 rows changed |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `lib.rs:226 delete_book` — DELETE, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `rusqlite` bundled (Cargo.toml:15), CREATE TABLE `lib.rs:114`; test `sqlite_data_survives_reopening` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/404/400/204/405/415 across handlers; `ApiError` emits JSON `lib.rs:51` |
| R9 | Validation: title & author required | ✓ implemented | `BookInput::validate` `lib.rs:36` (trim + non-blank → 400) + SQL CHECK; test `validation_rejects_invalid_create_and_update_without_mutation` |
| R10 | GET /health | ✓ implemented | `lib.rs:138 health` — runs `SELECT 1`, returns `{"status":"ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — build/run, env vars, route table, curl examples, test commands |
| R12 | ≥3 unit/integration tests | ✓ implemented | 6 `#[tokio::test]` in `tests.rs`; test_coverage=1.0 |

## Build & Test

Not re-run (per skill: stored scores stand in). From `scores.json`:

```text
test_coverage = 1.0   → cargo build + cargo test succeeded, all tests pass
code_quality  = 0.83  → lint/quality
defect_rate   = 1.0   → build+test succeeded
idiomatic     = 0.76
maintainability = 0.44
```

Test functions (`tests.rs`): `crud_lifecycle`, `list_and_filter_by_exact_author`, `validation_rejects_invalid_create_and_update_without_mutation`, `health_missing_books_and_invalid_ids`, `malformed_json_and_missing_content_type_return_json_errors`, `sqlite_data_survives_reopening`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, lib+main+tests) | 503 |
| Files (excl. target/.git) | 14 |
| Dependencies (Cargo.toml declared) | 5 runtime + 2 dev |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | not re-run |

## Findings

Top findings (full list in `findings.jsonl`) — no defects; both info-level design notes:

1. [info] Single global `Mutex<Connection>` serializes all DB access (correct, race-free; a pool would raise concurrency).
2. [info] `?author=` filter is exact case-sensitive match (documented in README; spec only requires a filter).

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-72/runs/agent=codex_effort=low_language=rust_model=gpt-6-astra_prompt=neutral/rep2"
cat scores.json                                  # stored build/test/lint scores (not re-run)
cat ../../../REQUIREMENTS.json                   # pinned 12-requirement checklist
grep -rE "#\[ignore\]" . --include="*.rs" | wc -l  # skip count = 0
# to independently verify (optional): cargo test --locked
```
