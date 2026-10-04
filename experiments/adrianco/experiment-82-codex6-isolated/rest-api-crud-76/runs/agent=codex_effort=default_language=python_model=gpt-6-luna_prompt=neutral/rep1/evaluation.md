# Evaluation: rest-api-crud-76 · agent=codex model=gpt-6-luna prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (defect_rate=1.0 from scores.json) — not re-run
- **Lint:** pass — code_quality=0.7889 from scores.json (3 low/info style findings)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

Mechanical scores read from `scores.json` (inline gate output; not re-run):
test_coverage=0.9, defect_rate=1.0, code_quality=0.7889, maintainability=0.9786,
idiomatic=0.7, token_efficiency=0.0213. test_coverage > 0 ⇒ build succeeded and the
suite executed and passed.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:85-90` INSERT + 201; test `test_create_get_update_and_delete` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:92-99`; test `test_list_and_filter_by_author` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:93-98` `parse_qs` → WHERE author=?; test asserts `["Two"]` |
| R4 | GET /books/{id} single, 404 if absent | ✓ implemented | `app.py:101-104` 200/404; test asserts 404 for /books/999 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:106-111` UPDATE + 200/404; test updates to "Dune Messiah" |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:113-116` DELETE + 204/404; test asserts 204 then 404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:11-28` `sqlite3`, CREATE TABLE books |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `app.py:36-40` `response()`; 201/200/204/400/404/405 used |
| R9 | Validation: title and author required | ✓ implemented | `app.py:56-67` `validate()` → 400; test posts `{"title":"Untitled"}` → 400 |
| R10 | GET /health | ✓ implemented | `app.py:76-77` `{"status":"ok"}`; test asserts it |
| R11 | README.md with setup/run | ✓ implemented | `README.md` — Run, Endpoints, Test sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` 3 test methods; test_coverage=0.9 > 0 |

## Build & Test

Not re-run — stored scores used per skill policy (re-running the toolchain is pure
duplication).

```text
# defect_rate=1.0  → build + tests succeeded
# test_coverage=0.9 → suite executed and passed (>0 ⇒ tests ran)
# reproduce: python -m unittest -v   (3 tests, 0 skips)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 194 (app.py 131 + test_app.py 63) |
| Files (excl. artifacts) | 10 |
| Dependencies | 0 (stdlib only) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | not re-run |

## Findings

Full list in `findings.jsonl`. No critical/high/medium items.

1. [low] Dead ternary in the 405 branch — `allowed` computed but both arms return METHOD_NOT_ALLOWED (`app.py:118-119`)
2. [low] 405 response omits the `Allow` header (`app.py:119`)
3. [info] `parse_qs` imported inside the request handler rather than at module top (`app.py:94`)

## Notes

- Clean, idiomatic stdlib-only WSGI implementation; parameterised SQL throughout
  (no injection surface). PUT is a full replace, documented as such in the README.
- No `prompt`-factor requirements beyond TASK.md (prompt=neutral is the plain
  "read TASK.md" framing), so the checklist is R1–R12 only.

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral/rep1"
cat scores.json                 # stored mechanical scores (build/test/lint)
python -m unittest -v           # 3 tests, 0 skips (only if re-verifying)
grep -rE "skip|xfail" test_app.py   # 0 skips
```
