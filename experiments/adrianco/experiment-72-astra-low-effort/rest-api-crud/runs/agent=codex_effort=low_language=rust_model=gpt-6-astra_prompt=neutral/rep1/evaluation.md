# Evaluation: agent=codex effort=low language=rust model=gpt-6-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — from `test_coverage=1.0`
- **Build:** pass (from `scores.json` `test_coverage=1.0`; not re-run)
- **Lint:** not re-run — `code_quality=0.8333` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

## Requirements

Pinned checklist from `REQUIREMENTS.json` (12 items). The prompt factor `neutral` prescribes no methodology and adds no checkable instructions, so the `P*` list is empty.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `lib.rs:147 create` — parameterized INSERT of all four fields; test `crud_lifecycle` |
| R2 | GET /books lists all books | ✓ implemented | `lib.rs:179 list` — `SELECT ... ORDER BY id`; test `crud_lifecycle` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `lib.rs:175 Filter` + `lib.rs:187` `WHERE (?1 IS NULL OR author = ?1)`; test `author_filter_is_exact_and_parameterized` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `lib.rs:192 read` + `ApiError::missing`; tests `crud_lifecycle`, `health_missing_ids_and_routes` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `lib.rs:206 update` — UPDATE, 404 when 0 rows changed; test `crud_lifecycle` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `lib.rs:230 delete` — DELETE, 404 when 0 rows; test `crud_lifecycle` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `lib.rs:16 Database::open` rusqlite (bundled); persistence test `books_persist_after_database_reopen` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `IntoResponse` for `ApiError` `lib.rs:92`; 201/200/404/400/405/413/415/500 mapping; content-type asserted in tests |
| R9 | Input validation: title and author required | ✓ implemented | `lib.rs:67 BookInput::validate` (trim + non-blank) plus DB CHECK; test `invalid_input_does_not_change_data` |
| R10 | GET /health health-check | ✓ implemented | `lib.rs:135` returns `{"status":"ok"}`; test `health_missing_ids_and_routes` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — setup, `cargo build/run`, env vars, API table, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/api.rs` — 5 `#[tokio::test]` functions |

## Build & Test

Not re-run per skill guidance — mechanical scores read from `scores.json`:

```text
test_coverage = 1.0   -> build succeeded and all tests passed
defect_rate   = 1.0   -> build+test succeeded
code_quality  = 0.8333
maintainability = 0.7435
idiomatic     = 0.77
token_efficiency = 0.0337
```

Skipped/disabled tests: 0 (`grep #[ignore]` → 0 matches). Effective tests = 5.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 450 (lib.rs 242, main.rs 16, tests/api.rs 192) |
| Files (excl. target/.git) | 14 |
| Dependencies (Cargo.toml decl.) | 5 runtime + 3 dev |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. All 12 requirements implemented and verified by passing tests; no skipped tests, no build/test/lint failures surfaced. `findings.jsonl` is empty.

## Reproduce

```bash
cd "experiments/adrianco/experiment-72-astra-low-effort/rest-api-crud/runs/agent=codex_effort=low_language=rust_model=gpt-6-astra_prompt=neutral/rep1"
cat scores.json                                   # mechanical scores (build/test/lint)
cat ../../../REQUIREMENTS.json                     # pinned 12-item checklist
grep -rE "#\[ignore\]" . --include="*.rs" | wc -l  # skipped tests: 0
grep -rcE "#\[tokio::test\]|#\[test\]" tests/      # test count: 5
# Optional full re-run: cargo test --locked
```
