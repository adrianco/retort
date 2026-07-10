# Evaluation: agent=hermes-local language=python prompt=BDD · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown (Flask), prompt=BDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Prompt (BDD):** followed — Given-When-Then Gherkin features, HTTP-only assertions (P1 ✓)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective)
- **Build:** pass — test_coverage=0.97, defect_rate=1.0 from scores.json (no re-run)
- **Lint:** pass — code_quality=0.83 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:14-26`, `models.py:38-49` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:28-32`, `models.py:52-62` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:30-31`, `models.py:55-58`; test `tests/features/test_list_books.py:43` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:34-39` returns 404 when None |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:41-64`, `models.py:75-95` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:66-71`, `models.py:98-108` |
| R7 | Data stored in SQLite | ✓ implemented | `models.py:5,12-35` sqlite3 + CREATE TABLE |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `jsonify` + 201/200/400/404 throughout `app.py` |
| R9 | Validation: title and author required | ✓ implemented | `app.py:19-22` → 400 |
| R10 | GET /health endpoint | ✓ implemented | `app.py:10-12` → `{"status":"ok"}`,200 |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` — Setup/Run/Endpoints sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 16 BDD scenarios, test_coverage=0.97 |

**Prompt factor P1 (BDD):** ✓ implemented — 6 `.feature` files with GWT scenarios; step defs drive the
public REST interface via `app_client` (`tests/features/test_list_books.py:11,18,43`), reading as a
behaviour specification. No internal-method testing.

## Build & Test

Scores read from `scores.json` (no toolchain re-run per skill policy):

```text
test_coverage = 0.97   (build + all 16 tests passed)
defect_rate   = 1.0    (build+test succeeded)
code_quality  = 0.833
maintainability = 0.937
idiomatic     = 0.65
```

```text
pytest -v  →  16 passed  (per _agent_stdout.log; 0 skips confirmed by grep)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: app+models+conftest) | 223 |
| Lines of code (tests) | 327 |
| Files (excl. __pycache__) | 26 |
| Dependencies (requirements.txt) | 5 |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=0.97) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Default SQLite path `books.db` created in CWD, persists across runs — `models.py:9`
2. [info] `year` accepted without type validation on POST/PUT — `app.py:23`
3. [info] Enhancement: 16 BDD scenarios across 6 Gherkin features, far exceeding the 3-test minimum

No critical, high, or medium findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-19-hermes35b-prompts/bookshop/runs/agent=hermes-local_language=python_prompt=BDD/rep3
cat scores.json                                  # stored build/test/quality scores
grep -rc "Scenario:" tests/features/*.feature    # 16 scenarios
grep -rE "pytest\.skip|xfail" tests/ | wc -l      # 0 skips
pip install -r requirements.txt && pytest -v      # optional re-run: 16 passed
```
