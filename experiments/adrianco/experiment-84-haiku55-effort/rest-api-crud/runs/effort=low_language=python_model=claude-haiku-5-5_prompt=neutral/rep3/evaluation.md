# Evaluation: effort=low_language=python_model=claude-haiku-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (R5 noted as full-replace PUT, still satisfies the spec)
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass (test_coverage=0.92 from scores.json ⇒ build + tests ran; defect_rate=1.0)
- **Lint:** pass — code_quality=0.62, maintainability=0.93, idiomatic=0.82 (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Checklist pinned by `rest-api-crud/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create (title, author, year, isbn) | ✓ implemented | `books_api.py:255 _post` → `store.create` (`:82`) |
| R2 | GET /books list all | ✓ implemented | `books_api.py:244` → `store.list` (`:94`) |
| R3 | GET /books ?author= filter | ✓ implemented | `books_api.py:245` + `LOWER(author)=LOWER(?)` (`:98`); `test_list_and_author_filter` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `books_api.py:247-252`; `test_crud_lifecycle` |
| R5 | PUT /books/{id} update | ✓ implemented | `books_api.py:267 _put` → `store.update` (`:105`); full-replace semantics (see findings) |
| R6 | DELETE /books/{id} | ✓ implemented | `books_api.py:278 _delete`; 204/404; `test_delete_missing_book_returns_404` |
| R7 | SQLite / embedded DB | ✓ implemented | `sqlite3.connect` (`:51`), `SCHEMA` (`:21`) |
| R8 | JSON responses + HTTP status codes | ✓ implemented | `_send_json` (`:167`); 201/200/204/400/404/409/500 across routes |
| R9 | Validation: title + author required | ✓ implemented | `validate_book` (`:131`); `test_create_rejects_missing_required_fields` |
| R10 | GET /health | ✓ implemented | `books_api.py:242` → `{"status":"ok"}`; `test_health` |
| R11 | README.md setup + run | ✓ implemented | `README.md` setup/run/endpoints sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 12 `test_*` functions in `test_books_api.py`; test_coverage=0.92 |

## Build & Test

Scores read from `scores.json` (inline eval gate — not re-run per skill policy):

```text
test_coverage   = 0.92   # build + tests executed, 92% coverage
defect_rate     = 1.00   # build + test succeeded
code_quality    = 0.6222
maintainability = 0.9308
idiomatic       = 0.82
token_efficiency= 0.0384
```

12 test functions, 0 skips (`grep -Ec "pytest.skip|@pytest.mark.skip|xfail" test_books_api.py` → 0).
Tests spin up the real `ThreadingHTTPServer` on an ephemeral port and exercise every route
including validation, duplicate-ISBN 409, and 404 paths.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 319 (books_api.py) + 141 (tests) |
| Files | 3 (source, tests, README) |
| Dependencies | 0 runtime (stdlib only); pytest for tests |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (scores from inline gate) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] R5 — PUT /books/{id} is full-replace; omitted year/isbn are cleared (spec-compliant, documented in README).
2. [info] Hardening beyond spec — ISBN uniqueness → 409, body-size cap, `Location` header on create.
3. [info] code_quality=0.62 despite high maintainability/idiomatic — recorded for cross-run comparison.

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=low_language=python_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                                   # stored mechanical scores
grep -Ec "pytest.skip|@pytest.mark.skip|xfail" test_books_api.py   # 0 skips
grep -cE "^def test_" test_books_api.py            # 12 tests
# (optional) python -m pytest -q                   # rebuilds + runs tests
```
