# Evaluation: effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=medium (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective) — `test_coverage=0.96`, `defect_rate=1.0` from `scores.json`
- **Build:** pass (implied — `defect_rate=1.0`, tests executed; pure stdlib, no build step)
- **Lint:** pass — `code_quality=0.7889` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:67-74` INSERT + 201; `test_app.py:39` test_create_and_get |
| R2 | GET /books lists all books | ✓ implemented | `app.py:79-81`; `test_app.py:53` test_list_and_author_filter |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:76-78` WHERE author=?; `test_app.py:57` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:93-94` (200) / `86-92` (404); `test_app.py:41,73` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:95-100` UPDATE; `test_app.py:61` test_update |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:101-103` (204); `test_app.py:70` test_delete_and_not_found |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:16-24` connect() + CREATE TABLE, `sqlite3` |
| R8 | JSON responses + status codes | ✓ implemented | `app.py:106-130` json.dumps + STATUS map (200/201/204/400/404/405) |
| R9 | Validation: title & author required | ✓ implemented | `app.py:31-53` validate(); `test_app.py:45` test_validation |
| R10 | GET /health endpoint | ✓ implemented | `app.py:64-65`; `test_app.py:35` test_health |
| R11 | README with setup/run | ✓ implemented | `README.md:7-9` run cmd + env vars + endpoints |
| R12 | ≥3 unit/integration tests | ✓ implemented | 6 tests in `test_app.py`; `test_coverage=0.96` |

Prompt factor `neutral` (`prompts/neutral.md`) prescribes no methodology and only asks for tests demonstrating the requirements — already covered by R12; no additional `P*` requirements.

## Build & Test

Scores read from `scores.json` (inline gate) — not re-run per skill guidance.

```text
scores.json
test_coverage = 0.96   (tests executed, 96% coverage)
defect_rate   = 1.0    (build + tests succeeded)
code_quality  = 0.7889
maintainability = 0.9414
idiomatic     = 0.68
token_efficiency = 0.0234
```

```text
6 tests collected, 0 skipped (grep: 0 skip/xfail markers)
test_health, test_create_and_get, test_validation,
test_list_and_author_filter, test_update, test_delete_and_not_found
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 213 (app.py 138 + test_app.py 75) |
| Files | 10 (incl. archive artifacts); 3 authored: app.py, test_app.py, README.md |
| Dependencies | 0 (stdlib only — no requirements.txt/pyproject) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | n/a (interpreted, no build step) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Single sqlite3 connection shared across all requests — `app.py:57-58` (safe under single-threaded wsgiref; would break under a threaded server)
2. [info] 405 Method Not Allowed handled beyond spec — `app.py:65,82,88`
3. [info] Type validation for optional year/isbn beyond required fields — `app.py:43-50`

## Reproduce

```bash
cd "experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral/rep3"
cat scores.json                                   # stored mechanical scores (no re-run)
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py"   # 0 skips
grep -rEn "^def test_" test_app.py                # 6 tests
wc -l app.py test_app.py                          # source LOC
# Fallback build+test (not needed; scores present):
#   python -m pytest
```
