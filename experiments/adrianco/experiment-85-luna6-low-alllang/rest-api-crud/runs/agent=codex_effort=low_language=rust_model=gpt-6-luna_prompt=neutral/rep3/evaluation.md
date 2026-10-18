# Evaluation: rest-api-crud · agent=codex language=rust model=gpt-6-luna prompt=neutral · rep 3

## Summary

- **Factors:** language=rust, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok (repair task — prior attempt's axum-version route bug is fixed)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (REQUIREMENTS.json pinned list)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass — not re-run; `test_coverage=1.0` ⇒ build + all tests passed (scores.json)
- **Lint:** pass — `code_quality=0.611` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/main.rs:70` create_book; test `creates_and_reads_book:161` |
| R2 | GET /books lists all | ✓ implemented | `src/main.rs:80` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `src/main.rs:81-87`; test `...filters_by_author:171` asserts len==1 |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `src/main.rs:91` get_book, route `:id` `src/main.rs:120`; test asserts 404 `:189` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/main.rs:97` update_book; test asserts 200 `:187` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/main.rs:106` delete_book; test asserts 204 `:188` |
| R7 | Data in SQLite | ✓ implemented | sqlx sqlite pool + `CREATE TABLE books` `src/main.rs:123-128` |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/204/404/400 via handlers + `ApiError` IntoResponse `src/main.rs:46-57` |
| R9 | Validation: title/author required | ✓ implemented | `validate()` `src/main.rs:64-68`; test asserts 400 `:173`. See low finding re: absent-field 422 |
| R10 | GET /health | ✓ implemented | `health` `src/main.rs:112`, route `:117` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run/Endpoints/Tests sections |
| R12 | >= 3 tests | ✓ implemented | 3 `#[tokio::test]` in `src/main.rs:160-190`; `test_coverage=1.0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill step 2):

```text
test_coverage   = 1.0    # build + all tests passed
defect_rate     = 1.0    # build+test succeeded
code_quality    = 0.611
maintainability = 0.667
idiomatic       = 0.42
token_efficiency= 0.025
```

The repair fixed the reported defect: id-routes now use axum 0.7's `:id` syntax
(`src/main.rs:120`) matching the pinned `axum = "0.7"` in Cargo.toml, so
GET/PUT/DELETE `/books/{id}` match and the two previously-failing tests pass.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 191 (src/main.rs, incl. tests) |
| Files (source) | 3 (main.rs, Cargo.toml, README.md) |
| Dependencies | 4 direct + 2 dev (Cargo.toml) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] R9 — an entirely omitted `title`/`author` field returns serde's 422 rather than the handler's 400 (empty-string case is correctly 400).

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=rust_model=gpt-6-luna_prompt=neutral/rep3"
cat scores.json                       # stored mechanical scores (build/test/lint)
grep -rE "#\[ignore\]" src            # skip detection -> 0
grep -cE "#\[tokio::test\]" src/main.rs  # 3 tests
# build/tests NOT re-run: test_coverage=1.0 in scores.json already proves pass
```
