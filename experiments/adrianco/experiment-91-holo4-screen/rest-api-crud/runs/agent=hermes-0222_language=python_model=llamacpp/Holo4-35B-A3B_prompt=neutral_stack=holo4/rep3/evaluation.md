# Evaluation: rest-api-crud · agent=hermes-0222 model=llamacpp/Holo4-35B-A3B prompt=neutral stack=holo4 · rep 3

## Summary

- **Factors:** language=python, model=llamacpp/Holo4-35B-A3B, agent=hermes-0222, framework=Flask (inferred), prompt=neutral, stack=holo4
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass — from `defect_rate=1.0` in `scores.json` (build + tests succeeded)
- **Lint:** pass — `code_quality=0.956` in `scores.json`, no skipped tests
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

Scores read from `scores.json` (run evaluated inline as a gate; no row yet in
`retort.db`): `test_coverage=0.95`, `code_quality=0.956`, `defect_rate=1.0`,
`maintainability=1.0`, `idiomatic=0.45`, `token_efficiency=0.0087`. The agent's
own stdout log confirms "All 10 unit/integration tests passing".

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:62 create_book` inserts all 4 fields; test `test_create_book` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:97 list_books`; test `test_list_books` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:103` branches on `author` query param; test `test_list_books_filter_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:116 get_book`, 404 at `app.py:126`; tests `test_get_book`, `test_get_book_not_found` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:131 update_book`; test `test_update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:172 delete_book`; test `test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,42` `sqlite3` + `books.db` file; schema `app.py:20` |
| R8 | JSON responses + correct status codes | ✓ implemented | `jsonify(...)` with 201/200/404/400 throughout `app.py` |
| R9 | Input validation: title & author required | ✓ implemented | `app.py:72-75` (POST), `app.py:152-155` (PUT); tests `test_create_book_missing_title`/`_author` |
| R10 | GET /health health check | ✓ implemented | `app.py:56 health` → `{"status":"ok"}`; test `test_health_check` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — install, run, endpoints, test commands |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` has 10 `test_*` methods (`test_coverage=0.95 > 0`) |

## Build & Test

Not re-run — stored scores used per the evaluate-run skill (`scores.json` present; no `retort.db` row for this inline-gated rep).

```text
scores.json
defect_rate     = 1.0    # build + tests succeeded
test_coverage   = 0.95   # coverage ratio; tests executed and passed
code_quality    = 0.956
```

```text
_agent_stdout.log
✅ App server started and running on port 5000
✅ All 10 unit/integration tests passing
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 389 (app.py 190 + test_app.py 199) |
| Files (source/deliverable) | 4 (app.py, test_app.py, README.md, requirements.txt) |
| Dependencies | 1 (Flask==2.3.3) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl`:

1. [low] Books-table schema duplicated across `_ensure_table` (`app.py:20`) and `init_db` (`app.py:43`).
2. [info] `year`/`isbn` accepted without type validation (`app.py:77-78`) — beyond the spec, which mandates only title/author.

No correctness, requirement, or test-integrity issues found.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-91-holo4-screen/rest-api-crud/runs/agent=hermes-0222_language=python_model=llamacpp/Holo4-35B-A3B_prompt=neutral_stack=holo4/rep3
cat scores.json                                   # stored build/test/lint scores
cat ../../../../REQUIREMENTS.json 2>/dev/null || cat REQUIREMENTS.json   # pinned checklist (walk up to task dir)
grep -cE "def test_" test_app.py                  # 10 tests
grep -rE "pytest\.skip|unittest\.skip|xfail" . --include="*.py" | wc -l  # 0 skips
```
