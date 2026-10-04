# Evaluation: rest-api-crud (effort=low, python, opus-5-5, neutral) · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** all passed / 0 failed / 0 skipped (12 functions, one parametrized ×8 ≈ 19 cases) — test_coverage=0.92 from scores.json
- **Build:** pass (import + tests executed; defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.79, idiomatic=0.83 (no lint re-run; stored scores)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:198 _create_book` → `app.py:85 BookStore.create` |
| R2 | GET /books lists all | ✓ implemented | `app.py:194 _list_books` → `app.py:93 BookStore.list` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:195` parses `author`; `app.py:96` `WHERE author = ? COLLATE NOCASE` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `app.py:202 _get_book`, 404 at `app.py:205` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:208 _update_book` → `app.py:106 BookStore.update` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:214 _delete_book` → `app.py:114 BookStore.delete` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:63-117 BookStore` uses `sqlite3`; table DDL `app.py:71` |
| R8 | JSON responses + correct codes | ✓ implemented | `app.py:128 _send_json`; 201/200/204/400/404/405/413/500 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `app.py:38-45 validate_book`; tested `test_app.py:70` |
| R10 | GET /health | ✓ implemented | `app.py:191 _health` → `{"status":"ok"}`; tested `test_app.py:40` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup / Run / Test / Endpoints |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` — 12 test functions; test_coverage=0.92 |

No partial or missing requirements. Two info-level enhancements (413/405 handling,
thread-safe per-op connections, bool-excluding year validation) are noted in
`findings.jsonl` as positive signal, not deductions.

## Build & Test

Not re-run — stored mechanical scores are authoritative (per skill Step 2).

```text
scores.json
  test_coverage = 0.92   # build + tests executed and passed (coverage fraction)
  defect_rate   = 1.0    # build + test succeeded
  code_quality  = 0.7889
  maintainability = 1.0
  idiomatic     = 0.83
  token_efficiency = 0.0631
```

Skip scan (`grep pytest.skip|@pytest.mark.skip|xfail`): 0 matches → 0 skipped.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source) | app.py 245 + test_app.py 145 = 390 |
| Files (excl .git/.coverage) | 11 (2 source, 1 test, README, TASK, stack, meta, scores, logs) |
| Dependencies | 0 runtime (stdlib only); pytest for tests |
| Tests total | 12 functions (~19 cases with parametrize) |
| Tests effective | ~19 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [info] Robustness beyond spec: 413/405 handling and thread-safe SQLite
2. [info] Validation excludes bool from integer year and reports per-field details

No critical/high/medium/low findings.

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=python_model=claude-opus-5-5_prompt=neutral/rep2"
cat scores.json                                    # stored mechanical scores
cat ../../../REQUIREMENTS.json                     # pinned 12-item checklist
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l   # 0
# (build/test not re-run — scores.json is authoritative)
```
