# Evaluation: rest-api-crud · effort=default language=python model=claude-opus-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-5-5, prompt=neutral, effort=default (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** all passed / 0 failed / 0 skipped (22 test functions, several parametrized; effective = all)
- **Build:** pass (import/collection succeeded) — from `scores.json`/retort.db, not re-run
- **Lint:** pass — code_quality=0.833 (`scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Mechanical scores (from `scores.json`, inline gate; retort.db in parentheses where it differs):
test_coverage=0.95 (0.97), defect_rate=1.0, code_quality=0.833, maintainability=0.892 (0.903), idiomatic=0.80 (0.77), token_efficiency=0.062 (0.036). `defect_rate=1.0` and `test_coverage=0.95` ⇒ build + all tests passed.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:137-144` → `db.py:40-49 BookStore.create`; `test_app.py:73` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:133-136` → `db.py:51-59 list`; `test_app.py:146` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:134-135`, `db.py:54-56` (`WHERE author = ? COLLATE NOCASE`); `test_app.py:155` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:150-154`, `db.py:61-67`; `test_app.py:132`, `test_not_found` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:155-163` → `db.py:69-81 update`; `test_app.py:173` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:164-167` → `db.py:83-87 delete`; `test_app.py:203` |
| R7 | Data stored in SQLite | ✓ implemented | `db.py:3,35-38` `sqlite3.connect`; `test_data_persists_across_app_instances` (`test_app.py:220`) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `app.py:99-117` (JSON body + Content-Type); 201/200/204/400/404/405/409/413 used throughout |
| R9 | Validation: title and author required (400) | ✓ implemented | `validate_book` `app.py:40-49,64-65`; `test_create_validation_errors` (`test_app.py:100`) |
| R10 | GET /health health-check | ✓ implemented | `app.py:127-130` returns `{"status":"ok"}`; `test_health` (`test_app.py:66`) |
| R11 | README.md with setup + run instructions | ✓ implemented | `README.md` — Run / Test / API sections, env vars, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` — 22 test functions (many parametrized); test_coverage=0.95 |

No partial or missing requirements. No skipped/disabled tests (`grep` for skip/xfail = 0). Enhancements beyond spec (ISBN uniqueness→409, 413 body cap, 405 Allow header, zero dependencies) recorded as info findings, not deductions.

## Build & Test

Not re-run — stored scores are authoritative per the skill.

```text
scores.json: defect_rate=1.0, test_coverage=0.95
=> pytest collected and all tests passed; coverage 95%.
retort.db (completed row) agrees: defect_rate=1.0, test_coverage=0.97
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: app.py+db.py) | 288 |
| Lines of code (incl. test_app.py) | 563 |
| Files (source + docs, excl. artifacts) | 5 (app.py, db.py, test_app.py, README.md, requirements-dev.txt) |
| Dependencies (runtime) | 0 (stdlib only) |
| Dependencies (dev) | 1 (pytest) |
| Tests total (functions) | 22 (several parametrized → more cases) |
| Tests effective | 22 (0 skipped) |
| Skip ratio | 0% |
| Build/test | pass (from stored scores) |

## Findings

Top items (full list in `findings.jsonl`) — all info-level enhancements, no defects:

1. [info] ISBN uniqueness enforced with 409 Conflict (beyond spec)
2. [info] Request hardening: 1 MB body cap (413), 405 with Allow header, non-leaking 500
3. [info] Zero-dependency implementation (standard library only)

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=default_language=python_model=claude-opus-5-5_prompt=neutral/rep2"
cat scores.json                                   # stored mechanical scores (authoritative)
sqlite3 -readonly ../../../retort.db "SELECT metric_name,value FROM run_results WHERE run_id=(SELECT id FROM experiment_runs WHERE json_extract(run_config_json,'$.model')='claude-opus-5-5' AND replicate=2 AND status='completed' ORDER BY finished_at DESC LIMIT 1);"
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py | wc -l   # 0 skips
grep -cE "^def test_" test_app.py                 # 22 test functions
# To independently verify (optional): python -m pip install -r requirements-dev.txt && python -m pytest
```
