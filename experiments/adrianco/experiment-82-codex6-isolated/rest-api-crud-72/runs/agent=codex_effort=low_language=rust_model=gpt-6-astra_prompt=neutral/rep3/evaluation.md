# Evaluation: agent=codex_effort=low_language=rust_model=gpt-6-astra_prompt=neutral · rep 3

## Summary

- **Factors:** language=rust, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral, framework=unknown (axum)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — via `test_coverage=1.0` from `scores.json`
- **Build:** pass — `test_coverage=1.0` ⇒ build + all tests passed (not re-run)
- **Lint:** pass (score-derived) — `code_quality=0.833` from `scores.json` (not re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Checklist from the pinned `REQUIREMENTS.json` (12 items, constant across all runs).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title,author,year,isbn) | ✓ implemented | `lib.rs:166 create` INSERTs all four fields; tested `tests.rs:50 crud_lifecycle` |
| R2 | GET /books lists all books | ✓ implemented | `lib.rs:190 list`; tested `tests.rs:91` (expects 3) |
| R3 | GET /books supports ?author= filter | ✓ implemented | `lib.rs:186-199` Filter + `WHERE (?1 IS NULL OR author=?1)`; tested `tests.rs:111` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `lib.rs:203 fetch` → `get_book` → `ApiError::missing` (404); tested `tests.rs:167` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `lib.rs:210 update` (full replace); tested `tests.rs:68` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `lib.rs:229 remove`, 404 when 0 rows; tested `tests.rs:79` |
| R7 | Data stored in SQLite | ✓ implemented | `rusqlite` bundled (`Cargo.toml:15`), `Connection::open` (`lib.rs:19`); persistence tested `tests.rs:197` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201+Location (`lib.rs:180`), 200, 204 (`lib.rs:238`), 404, 400, 405; JSON error body `lib.rs:98-102` |
| R9 | Validation: title and author required | ✓ implemented | `BookInput::validate` (`lib.rs:67-77`) + DB CHECK (`lib.rs:25-26`); tested `tests.rs:132` |
| R10 | GET /health health check | ✓ implemented | `lib.rs:116 health` runs `SELECT 1`; tested `tests.rs:167` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — setup, run, env vars, API table, curl examples, verification |
| R12 | At least 3 unit/integration tests | ✓ implemented | 5 `#[tokio::test]` in `tests.rs`; `test_coverage=1.0` |

No requirements missing or partial. Beyond spec: 405 method-not-allowed handling, Location header on create, graceful shutdown, injection-like input covered by a test.

## Build & Test

Not re-run — stored mechanical scores used per skill guidance (`scores.json`):

```text
test_coverage = 1.0   → cargo build + all tests passed
defect_rate   = 1.0   → build+test succeeded
code_quality  = 0.833 → lint/quality (fmt + clippy referenced in README)
```

Test files (5 integration tests, driven through the router via `tower::oneshot`):

```text
tests.rs: crud_lifecycle, lists_and_filters_authors_exactly,
          rejects_invalid_input_without_mutation,
          missing_books_invalid_ids_and_health,
          data_survives_database_reopening
skips (#[ignore]): 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 488 (lib 244 / main 16 / tests 228) |
| Files (excl. target/.git) | 14 |
| Direct dependencies | 5 runtime + 1 dev (axum, rusqlite, serde, serde_json, tokio; tower dev) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| code_quality | 0.833 |
| maintainability | 0.450 |
| idiomatic | 0.83 |
| token_efficiency | 0.059 |

## Findings

All findings are info-level design notes; none affect conformance (full list in `findings.jsonl`):

1. [info] PUT /books/{id} is a full replace, not a partial update (`lib.rs:217-225`) — acceptable per spec.
2. [info] Single shared SQLite connection serialized by a Mutex (`lib.rs:16,40-43`) — fine at this scale.

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-72/runs/agent=codex_effort=low_language=rust_model=gpt-6-astra_prompt=neutral/rep3"
cat scores.json                                   # stored build/test/lint scores (not re-run)
cat ../../REQUIREMENTS.json                        # pinned 12-item checklist
grep -rE "#\[ignore\]" . --include="*.rs" | wc -l  # skip count → 0
grep -rE "#\[tokio::test\]|#\[test\]" . --include="*.rs" | wc -l  # 5
# Optional full verification (slow; scores already stored):
# cargo test --locked && cargo clippy --locked --all-targets -- -D warnings
```
