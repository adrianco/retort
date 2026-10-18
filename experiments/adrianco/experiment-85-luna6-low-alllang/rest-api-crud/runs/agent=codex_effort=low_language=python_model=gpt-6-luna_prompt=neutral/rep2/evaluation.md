# Evaluation: agent=codex effort=low language=python model=gpt-6-luna prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** passed (test_coverage=0.83, defect_rate=1.0) / 0 failed / 0 skipped (4 effective test methods)
- **Build:** pass — from stored scores (`defect_rate=1.0`, `test_coverage=0.83`); not re-run
- **Lint:** pass (noted) — `code_quality=0.6222` from `scores.json`
- **Architecture:** `run-summary` skill unavailable in this session — see Architecture note below
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 0 info)

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (constant denominator = 12). Prompt factor `neutral` adds no new checkable requirement (it only states no methodology is prescribed and to include tests — covered by R12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:149 do_POST` → `validate_book` → `store.create` (app.py:43); test_app.py:43 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:136` → `store.list()` (app.py:52); test_app.py:51 |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:137 parse_qs(...).get("author")` → `store.list(author)` (app.py:56, COLLATE NOCASE); test_app.py:53 |
| R4 | GET /books/{id} returns one book | ✓ implemented | `app.py:139 do_GET /books/` → `store.get` (app.py:62), 404 on miss (app.py:145); test_app.py:46,66 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:164 do_PUT` → `store.update` (app.py:67); test_app.py:56 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:182 do_DELETE` → `store.delete` (app.py:78); test_app.py:59 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:18 BookStore` uses `sqlite3`, CREATE TABLE books (app.py:24) |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `app.py:103 _send` JSON-encodes; `HTTPStatus` CREATED/OK/NOT_FOUND/BAD_REQUEST/NO_CONTENT throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:84 validate_book` rejects empty/missing title/author (400); test_app.py:63,73 |
| R10 | GET /health endpoint | ✓ implemented | `app.py:134` returns `{"status":"ok"}`; test_app.py:41 |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — Run, Endpoints, Tests sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 test methods in `test_app.py`; test_coverage=0.83 > 0 |

## Build & Test

Not re-run — stored scores used per skill (test gate already executed during scoring):

```text
scores.json: test_coverage=0.83, defect_rate=1.0  ⇒ build + all tests passed
code_quality=0.6222, maintainability=0.9107, idiomatic=0.72, token_efficiency=0.0214
```

Tests (4 methods, unittest-based, no skips):
```text
test_health_and_create_then_get_book
test_list_filter_update_and_delete
test_validation_and_missing_resources
test_validation_requires_title_author_and_valid_optional_fields
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 293 (app.py 213 + test_app.py 80) |
| Files | 10 (incl. logs/caches; 3 code+README: app.py, test_app.py, README.md) |
| Dependencies | 0 (Python stdlib only — http.server + sqlite3) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl`:

1. [low] `delete()` leaks its SQLite connection — `app.py:79` uses the connection as a context manager without `contextlib.closing()`, unlike every other BookStore method; the connection is not closed until GC.

No critical/high/medium findings. All 12 spec requirements implemented and exercised by passing tests.

## Architecture

The `run-summary` skill is not available in this session, so `summary/index.md` was not generated. Brief manual note: single-module design (`app.py`) — `BookStore` (SQLite persistence), `validate_book` (input validation), `make_handler`/`BookHandler` (stdlib `BaseHTTPRequestHandler` routing GET/POST/PUT/DELETE), `create_server` (ThreadingHTTPServer). Tests in `test_app.py` drive the handler directly via a synthesized request object.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=python_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json                              # stored mechanical scores (build/test gate)
cat ../../../REQUIREMENTS.json               # pinned 12-requirement checklist
grep -rE "pytest\.skip|unittest\.skip|xfail" . --include="*.py" | wc -l   # 0 skips
grep -c "def test_" test_app.py              # 4 test methods
# (optional fallback verification) python -m unittest -v
```
