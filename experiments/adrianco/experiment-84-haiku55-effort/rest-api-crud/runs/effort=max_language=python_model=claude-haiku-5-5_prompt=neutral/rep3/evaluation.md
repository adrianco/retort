# Evaluation: effort=max language=python model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, effort=max, prompt=neutral (agent/framework=unknown in stack.json; Flask + stdlib sqlite3 in code)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 37 passed / 0 failed / 0 skipped (37 effective) — per `test_coverage=1.0`
- **Build:** pass — not re-run (stored `test_coverage=1.0` ⇒ build + import + tests all succeeded)
- **Lint:** n/a — stored `code_quality=0.6667` from `scores.json`; no linter re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info — all enhancements beyond spec)

## Requirements

Pinned list from `rest-api-crud/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `bookapi/books.py:13` `create_book` → `repository.py:9` `insert_book`; returns 201 + Location |
| R2 | GET /books lists all | ✓ implemented | `bookapi/books.py:21` `list_books` → `repository.py:18` ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `bookapi/books.py:23` + `repository.py:21` `WHERE author = ? COLLATE NOCASE`; test `test_list_books_filters_by_author` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `bookapi/books.py:28-33`; `_not_found` → 404; test `test_get_missing_book_returns_404` |
| R5 | PUT /books/{id} updates | ✓ implemented | `bookapi/books.py:36-41` → `repository.py:30` `update_book`; 404 when rowcount 0 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `bookapi/books.py:44-48` → `repository.py:41` `delete_book`; returns 204 |
| R7 | Data stored in SQLite | ✓ implemented | `bookapi/db.py` stdlib `sqlite3`, `SCHEMA` books table; `test_books_persist_across_app_instances` |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify` throughout; 201/200/204/400/404/405/503; `errors.py` JSON error handlers |
| R9 | Validation: title & author required | ✓ implemented | `bookapi/validation.py:45-59` `_text`; `test_create_book_requires_title_and_author` → 400 |
| R10 | GET /health | ✓ implemented | `bookapi/__init__.py:21,25-30`; probes DB, 503 on error; `test_health_reports_ok` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup, Run, Test, API sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 37 test functions across `tests/`; `test_coverage=1.0` |

No partial, missing, or cannot-verify requirements.

## Build & Test

Build/test were **not re-run** — stored mechanical scores from `scores.json` stand in (per the evaluate-run skill):

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.6667
             maintainability=0.9644  idiomatic=0.88  token_efficiency=0.0038
```

`test_coverage=1.0` ⇒ the package imported, the app built, and all tests passed.
`defect_rate=1.0` confirms build + test success. The run is in the archive as an
inline-gate run, so it is not yet a row in `retort.db`; `scores.json` is authoritative.

Test inventory (static): 37 `test_*` functions — 28 HTTP integration tests
(`tests/test_books_api.py`) + 9 validation unit tests (`tests/test_validation.py`,
several parametrized). Skip scan found **0** skips/xfails.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 304 (`bookapi/*.py`) |
| Lines of code (tests) | 380 (`tests/*.py`) |
| Files (source + tests) | 9 |
| Dependencies | 1 runtime (Flask), 1 test (pytest) |
| Tests total | 37 |
| Tests effective | 37 |
| Skip ratio | 0% |
| Build duration | not re-run (gate score reused) |

## Findings

All 4 findings are `info`-level enhancements beyond the spec — no defects, no missing
requirements, no skipped tests. Full list in `findings.jsonl`:

1. [info] ISBN-10/13 checksum validation (`validation.py:87-98`) — beyond "input validation"
2. [info] JSON error responses for 404/405 and malformed bodies (`errors.py:25-30`, `books.py:51-57`)
3. [info] Health check probes the DB and returns 503 when unavailable (`__init__.py:25-30`)
4. [info] Case-insensitive, full-name author filter with blank rejection (`repository.py:22`, `validation.py:28-34`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=max_language=python_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                                   # stored mechanical scores (build+test reused)
cat ../../REQUIREMENTS.json                        # pinned 12-item checklist
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l   # 0
grep -rcE "^def test_" tests/*.py                  # 37 total
# Optional full re-run (not required; gate already scored it):
#   pip install -e ".[test]" && pytest
```
