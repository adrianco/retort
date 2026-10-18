# Evaluation: effort=low_language=rust_model=claude-haiku-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=rust, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective) — from `test_coverage=1.0`
- **Build:** pass (not re-run — `test_coverage=1.0` in `scores.json` ⇒ build + tests passed)
- **Lint:** pass — `code_quality=0.83` (`scores.json`); 0 skips/ignores found
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

Clean pass. Haiku 5.5 at low effort produced a complete, idiomatic axum + rusqlite
service with full endpoint coverage, a real SQLite backend, layered error handling, and
13 passing tests. No defects found.

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 items, fixed denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/lib.rs:179` `create_book`, route `:113`; test `tests/api.rs:57` |
| R2 | GET /books lists all | ✓ implemented | `src/lib.rs:195` `list_books`, route `:113`; test `tests/api.rs:109` |
| R3 | GET /books ?author= filter | ✓ implemented | `src/lib.rs:200-208` `COLLATE NOCASE`; test `tests/api.rs:113` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `src/lib.rs:219` `get_book`; tests `tests/api.rs:66,177` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/lib.rs:229` `update_book`; tests `tests/api.rs:125,147` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/lib.rs:248` `delete_book` (204); test `tests/api.rs:161` |
| R7 | Data stored in SQLite | ✓ implemented | `rusqlite` bundled, `src/lib.rs:93` `init_schema`, parameterised SQL throughout |
| R8 | JSON responses + correct status codes | ✓ implemented | 201 `:191`, 200, 404 `:66`, 400/422 `:63-67`, 204 `:257`; `ApiError:IntoResponse` |
| R9 | Validation: title & author required | ✓ implemented | `src/lib.rs:123` `validate` / `:149` `required`; tests `tests/api.rs:72`. (Returns 422, not the 400 hinted — see findings, info only) |
| R10 | GET /health | ✓ implemented | `src/lib.rs:175` `health` returns `{"status":"ok"}`; test `tests/api.rs:49` |
| R11 | README with setup & run | ✓ implemented | `README.md` — prerequisites, build/test/run, env vars, endpoints, curl examples |
| R12 | ≥3 tests | ✓ implemented | 4 unit (`src/lib.rs:260`) + 9 integration (`tests/api.rs`) = 13; `test_coverage=1.0` |

No requirements missing or partial. One enhancement beyond spec: malformed JSON (400)
is distinguished from field-validation failure (422), both rendered as `{"error": ...}`.

## Build & Test

Not re-run per the skill — stored mechanical scores stand in for the toolchain.

```text
source: scores.json
test_coverage = 1.0   ⇒ cargo build + cargo test succeeded, all tests passed
defect_rate   = 1.0   ⇒ build + test success
code_quality  = 0.833
idiomatic     = 0.80
maintainability = 0.685
```

```text
test inventory (grep):
  src/lib.rs   #[test]          : 4
  tests/api.rs #[tokio::test]   : 9
  total effective tests         : 13  (0 skipped, 0 #[ignore])
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 513 (`lib.rs` 313, `tests/api.rs` 182, `main.rs` 18) |
| Files (excl. build artifacts) | 14 |
| Dependencies | 5 runtime (axum, rusqlite, serde, serde_json, tokio) + 2 dev (tower, http-body-util) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | not re-run (scored inline) |

## Findings

Top items (full list in `findings.jsonl`):

1. [info] R9 validation returns 422 rather than the 400 hinted in the requirement's `how_to_verify`. Semantically correct (well-formed JSON failing field validation); malformed JSON still returns 400. No change needed — recorded for cross-run comparison.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=rust_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                   # stored mechanical scores (build+test signal)
cat ../../REQUIREMENTS.json                        # pinned 12-item checklist
grep -cE '#\[test\]' src/lib.rs                    # 4 unit tests
grep -cE '#\[tokio::test\]' tests/api.rs           # 9 integration tests
grep -rnE '#\[ignore\]' . --include='*.rs'         # 0 skips
# Optional full re-run (not required): cargo test
```
