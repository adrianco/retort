# Evaluation: effort=default language=python model=claude-fable-5-1 prompt=none · rep 3

## Summary

- **Factors:** language=python, model=claude-fable-5-1, prompt=none, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 19 passed / 0 failed / 0 skipped (19 effective) — 13 test functions, one parametrized ×7
- **Build:** pass — `defect_rate=1.0` from `scores.json` (build + tests succeeded)
- **Lint:** pass — `code_quality=0.79` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Scores read from `scores.json` (inline gate output — not re-run):
`test_coverage=0.92`, `defect_rate=1.0`, `code_quality=0.789`, `maintainability=1.0`, `idiomatic=0.87`, `token_efficiency=0.057`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:198 do_POST` → `BookStore.create` (app.py:78) |
| R2 | GET /books lists all | ✓ implemented | `app.py:186` → `BookStore.list` (app.py:86) |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:187-188` query param → `list(author=...)` `WHERE author = ? COLLATE NOCASE` (app.py:90) |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:189-194`; 404 when `get` returns None |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:214 do_PUT` → `BookStore.update` (app.py:104) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:233 do_DELETE` → `BookStore.delete` (app.py:114) |
| R7 | Data stored in SQLite | ✓ implemented | `sqlite3.connect` + CREATE TABLE (app.py:59-72) |
| R8 | JSON + appropriate status codes | ✓ implemented | `_send_json` (app.py:134); 201/200/204/400/404/405/411/413 |
| R9 | Validation: title & author required | ✓ implemented | `validate_book` (app.py:21-51); test at test_app.py:66 |
| R10 | GET /health | ✓ implemented | `app.py:184-185` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run, Tests, Endpoints, examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` — 13 functions (19 effective cases) |

## Build & Test

Not re-run — mechanical scores taken from `scores.json` (per skill step 2):

```text
defect_rate   = 1.0    # build + tests passed
test_coverage = 0.92   # 92% line coverage; tests executed
code_quality  = 0.789  # lint/quality
```

Test suite: 13 functions in `test_app.py`, one parametrized over 7 validation
cases (19 effective assertions/cases), 0 skipped/xfail. Tests start the real
server on an ephemeral port against an in-memory SQLite DB.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 266 (app.py) + 161 (test_app.py) = 427 |
| Files | 4 tracked (app.py, test_app.py, README.md, requirements-dev.txt) |
| Dependencies | 1 dev (pytest); 0 runtime (stdlib only) |
| Tests total | 19 effective cases |
| Tests effective | 19 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — no defects; all info-level enhancements beyond spec:

1. [info] Robustness beyond spec: 411/413 body guards and 1 MB cap
2. [info] Explicit bool-vs-int rejection for `year`
3. [info] Thread-safe SQLite access and HTTP/1.0 to avoid keep-alive desync
4. [info] Case-insensitive exact `?author=` filter (documented)

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=default_language=python_model=claude-fable-5-1_prompt=none/rep3"
cat scores.json                 # mechanical scores (not re-run)
python3 -m venv venv && venv/bin/pip install -r requirements-dev.txt
venv/bin/python -m pytest        # 19 cases, 0 skipped
```
