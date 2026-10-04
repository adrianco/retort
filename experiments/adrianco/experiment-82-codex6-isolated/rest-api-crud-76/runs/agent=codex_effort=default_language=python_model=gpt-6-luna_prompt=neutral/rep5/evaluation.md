# Evaluation: rest-api-crud-76 · agent=codex model=gpt-6-luna prompt=neutral · rep 5

## Summary

- **Factors:** language=python, agent=codex, model=gpt-6-luna, framework=unknown, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — `defect_rate=1.0` (scores.json); `python -m py_compile` clean per agent log
- **Lint:** pass — `code_quality=0.7889` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low)

Scores read from `scores.json` (inline gate output) — not re-run: `test_coverage=0.48`, `defect_rate=1.0`, `code_quality=0.7889`, `maintainability=0.8444`, `idiomatic=0.62`, `token_efficiency=0.0247`.

## Requirements

Denominator fixed by the pinned `rest-api-crud-76/REQUIREMENTS.json` (12 items). The `prompt=neutral` factor (`prompts/neutral.md`) prescribes no methodology and only asks for demonstrating tests — no additional checkable constraints beyond R12.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:85` do_POST → INSERT `app.py:95`, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:65-72` SELECT * ORDER BY id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:66-71` LIKE '%author%' COLLATE NOCASE |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:74-82`; 404 at `app.py:79` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:99-115` UPDATE, 404 on rowcount 0 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:117-127` DELETE, 404 on rowcount 0 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:12-22` sqlite3 + books table DDL |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `send_json` `app.py:27`; 201/200/404/400/204 used (but untested — see findings) |
| R9 | Validation: title and author required | ✓ implemented | `normalize` `app.py:45-58`; tested `test_app.py:17` |
| R10 | GET /health health check | ✓ implemented | `app.py:62-63` → 200 {"status":"ok"} |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` run + endpoint + test sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` 3 methods; `test_coverage=0.48` > 0, all pass |

## Build & Test

```text
# python -m unittest -v   (from agent log; not re-run)
test_book_id_route_parsing ... ok
test_required_fields_and_optional_field_validation ... ok
test_sqlite_create_filter_update_and_delete ... ok
----------------------------------------------------------------------
Ran 3 tests in 0.002s
OK
# python -m py_compile app.py test_app.py  -> clean
```

```text
# Stored scores (scores.json) — authoritative, not re-run
test_coverage = 0.48   (tests executed; ~half the code — the HTTP dispatch layer — is uncovered)
defect_rate   = 1.0    (build + tests succeeded)
code_quality  = 0.7889
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 199 (app.py 154 + test_app.py 45) |
| Files | 3 source (app.py, test_app.py, README.md) |
| Dependencies | 0 (Python standard library only) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; defect_rate=1.0) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [medium] HTTP handlers (do_GET/do_POST/do_PUT/do_DELETE) are never exercised by tests — tests cover only `normalize`, `book_id`, and raw SQLite CRUD; status codes, JSON serialization, and `?author=` parsing go untested (`test_coverage=0.48`). The agent dropped its original in-process HTTP tests because the sandbox blocked socket binding.
2. [low] DELETE returns 204 with a `null` JSON body (`app.py:127` → `send_json`) — 204 should carry no body.
3. [low] `CREATE TABLE IF NOT EXISTS` and a fresh connection run on every request (`app.py:12-22`).

No requirements are missing or partial; the run fully conforms to the spec.

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral/rep5"
cat scores.json                       # stored mechanical scores (not re-run)
cat ../../REQUIREMENTS.json           # pinned 12-item checklist
grep -rEc "def test_" test_app.py     # 3 tests
grep -rEn "skip|xfail" test_app.py    # 0 skips
python -m unittest -v                 # optional: reproduces 3 passing tests
```
