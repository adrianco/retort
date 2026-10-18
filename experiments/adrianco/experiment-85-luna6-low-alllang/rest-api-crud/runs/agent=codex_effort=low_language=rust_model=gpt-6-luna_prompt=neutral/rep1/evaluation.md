# Evaluation: agent=codex effort=low language=rust model=gpt-6-luna prompt=neutral · rep 1

## Summary

- **Factors:** language=rust, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral, framework=axum/sqlx
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — from `scores.json` `defect_rate=1.0` (build + tests succeeded)
- **Lint:** pass — `code_quality=0.611` from `scores.json` (no re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

Scores read from `scores.json` (inline gate, not yet in `retort.db`): `test_coverage=0.75`, `defect_rate=1.0`, `code_quality=0.611`, `maintainability=0.660`, `idiomatic=0.72`, `token_efficiency=0.0305`. `defect_rate=1.0` confirms the build compiled and the test suite ran and passed; `test_coverage=0.75` is a coverage ratio, not a pass/fail gate.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create (title, author, year, isbn) | ✓ implemented | `src/main.rs:62` `create_book`, INSERT at `:67`, returns 201 at `:76` |
| R2 | GET /books list all | ✓ implemented | `src/main.rs:79` `list_books`, SELECT all at `:91` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/main.rs:83` branches on `query.author`, `WHERE author = ?` at `:85` |
| R4 | GET /books/{id} single, 404 if absent | ✓ implemented | `src/main.rs:99` `get_book` → `get_book_row` `:106`, 404 at `:112` |
| R5 | PUT /books/{id} update | ✓ implemented | `src/main.rs:115` `update_book`, UPDATE at `:122`, 404 at `:132` |
| R6 | DELETE /books/{id} delete | ✓ implemented | `src/main.rs:137` `delete_book`, 204 at `:149`, 404 at `:147` |
| R7 | Data in SQLite / embedded DB | ✓ implemented | sqlx `SqlitePool` `:9`, table DDL `:172`, not in-memory state |
| R8 | JSON responses + correct status codes | ✓ implemented | `Json(..)` returns; 201/200/204/400/404/500 across handlers; `ApiError` JSON body `:46` |
| R9 | Validation: title & author required | ✓ implemented | `validate()` `:52` trims and rejects empty → 400; exercised by test `:269` |
| R10 | GET /health | ✓ implemented | `src/main.rs:152` `health` returns `"ok"`, route `:158` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Run (`cargo run`), env vars, endpoints, Test sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 4 `#[tokio::test]` fns `:242,:249,:269,:284`; `defect_rate=1.0` ⇒ they ran & passed |

No prompt-factor requirements (`prompt=neutral`; no additional checkable instructions).

## Build & Test

Not re-run — stored scores used per skill policy.

```text
scores.json: defect_rate=1.0  ⇒ cargo build + cargo test succeeded
             test_coverage=0.75 (coverage ratio), code_quality=0.611
```

```text
4 integration tests (tower oneshot against in-memory SQLite):
  health_returns_ok, create_and_retrieve_book,
  rejects_missing_required_fields_and_unknown_ids,
  filters_lists_and_supports_update_and_delete
0 skipped (#[ignore] count = 0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src/main.rs, incl. tests) | 319 |
| Source files | 1 (`src/main.rs`) |
| Dependencies | 7 (4 runtime + 3 dev) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] PUT /books/{id} uses full-replace semantics (omitted year/isbn cleared) — intended REST behavior, documented in README; no change needed.

No correctness, build, test, lint, or security defects found. Clean, idiomatic implementation that satisfies the full spec.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=rust_model=gpt-6-luna_prompt=neutral/rep1"
cat scores.json                                   # stored build/test/lint scores
grep -rnE "#\[ignore\]" src --include="*.rs"      # skipped-test check (0)
grep -cE "#\[tokio::test\]" src/main.rs           # test count (4)
# optional, NOT required (scores already stored):
# cargo test
```
