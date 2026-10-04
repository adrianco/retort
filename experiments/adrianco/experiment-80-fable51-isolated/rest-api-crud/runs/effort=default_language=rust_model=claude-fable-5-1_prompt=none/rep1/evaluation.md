# Evaluation: effort=default language=rust model=claude-fable-5-1 prompt=none · rep 1

## Summary

- **Factors:** language=rust, model=claude-fable-5-1, prompt=none, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — from `test_coverage=1.0` in scores.json (not re-run)
- **Lint:** pass — `code_quality=0.833` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `lib.rs:176 create_book` — INSERT then echo persisted row |
| R2 | GET /books lists all | ✓ implemented | `lib.rs:190 list_books` — SELECT ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `lib.rs:195-199` — WHERE author = ?1; test `list_books_with_author_filter` |
| R4 | GET /books/{id} single | ✓ implemented | `lib.rs:208 get_book` + `find_book` 404 via `.optional()` |
| R5 | PUT /books/{id} update | ✓ implemented | `lib.rs:215 update_book` — UPDATE, 404 when 0 rows |
| R6 | DELETE /books/{id} | ✓ implemented | `lib.rs:232 delete_book` — DELETE, 204/404 |
| R7 | SQLite / embedded DB | ✓ implemented | `rusqlite` bundled; `lib.rs:143 open_db` real table |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/204; `ApiError` maps 400/422/500 (`lib.rs:65`) |
| R9 | Validation: title+author required | ✓ implemented | `lib.rs:92 validate` — trims, non-empty; test `create_requires_title_and_author` (returns 422 — see finding) |
| R10 | GET /health | ✓ implemented | `lib.rs:172 health` → `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — requirements, run, test, env vars, API table, curl examples |
| R12 | ≥3 tests | ✓ implemented | 7 `#[tokio::test]` in `tests/api.rs`; `test_coverage=1.0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
test_coverage = 1.0    # build + all tests passed
defect_rate   = 1.0    # build+test succeeded
code_quality  = 0.833
idiomatic     = 0.87
maintainability = 0.757
```

Test inventory (grep): 7 `#[tokio::test]` functions covering health, create+get,
validation, malformed JSON, author filter, update (incl. 404 + revalidation),
delete (incl. 404). No `#[ignore]` / disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 427 (lib 243, main 19, tests 165) |
| Files | 14 (incl. Cargo.lock, README) |
| Dependencies | 4 direct (axum, tokio, rusqlite, serde) + serde_json |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Validation failures return 422 where R9's `how_to_verify` cites 400 — `src/lib.rs:71`. Defensible REST semantics (422 Unprocessable Entity for a well-formed but invalid body; 400 is still used for malformed JSON). Requirement R9 — reject missing title/author — is satisfied.

## Reproduce

```bash
cd experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=default_language=rust_model=claude-fable-5-1_prompt=none/rep1
cat scores.json                     # mechanical scores (build/test/lint), not re-run
grep -rE "#\[tokio::test\]|#\[test\]" tests src --include="*.rs" | wc -l   # 7
grep -rE "#\[ignore\]" . --include="*.rs" | wc -l                          # 0
# Optional full re-run: cargo test
```
