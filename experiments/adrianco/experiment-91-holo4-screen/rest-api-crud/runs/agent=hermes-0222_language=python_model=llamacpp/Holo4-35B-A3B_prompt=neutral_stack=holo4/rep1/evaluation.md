# Evaluation: rest-api-crud · agent=hermes-0222 language=python model=llamacpp/Holo4-35B-A3B prompt=neutral stack=holo4 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-0222, model=llamacpp/Holo4-35B-A3B, prompt=neutral, stack=holo4
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective) — `test_coverage=0.91` from `scores.json`
- **Build:** pass (not re-run — `defect_rate=1.0`, `test_coverage=0.91` from `scores.json`)
- **Lint:** pass — `code_quality=0.9556` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

The neutral prompt factor (`prompts/neutral.md`) prescribes no methodology and adds no checkable instructions, so there are no `P*` requirements — TASK.md (pinned as `REQUIREMENTS.json`) is the whole spec.

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:45` `create_book` INSERTs all four fields; `test_app.py:33` `test_create_book` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:79` `list_books`; `test_app.py:55` `test_list_books` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:82-84` filters by `author` arg; `test_app.py:66` `test_list_books_author_filter` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:90` `get_book` + 404 at `:95`; `test_get_book` / `test_get_book_not_found` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:99` `update_book`; `test_app.py:98` `test_update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:135` `delete_book` returns 204; `test_app.py:114` `test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:11` `sqlite3.connect(DATABASE)`; `books` table created `app.py:28` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `jsonify` throughout; 201/200/404/400/204 returned (`app.py:42,49,76,95,143`) |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:53-56` rejects empty title/author with 400; `test_create_book_missing_title` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:40-42` returns `{"status":"ok"}` 200; `test_app.py:26` `test_health` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — install, run, test, example curl requests |
| R12 | At least 3 unit/integration tests | ✓ implemented | 9 test methods in `tests/test_app.py`; `test_coverage=0.91` > 0 |

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill):

```text
test_coverage   = 0.91   # build + tests ran; 91% coverage
defect_rate     = 1.0    # build + test succeeded
code_quality    = 0.9556
maintainability = 1.0
idiomatic       = 0.6
token_efficiency= 0.0188
```

Test inventory (9 methods, 0 skipped — grep for skip/xfail markers returned 0):

```text
test_health, test_create_book, test_create_book_missing_title,
test_list_books, test_list_books_author_filter,
test_get_book, test_get_book_not_found,
test_update_book, test_delete_book
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 287 (app.py 159 + test_app.py 128) |
| Files (source, excl. build/db/logs) | 3 (app.py, tests/test_app.py, README.md) |
| Dependencies | 1 (flask; no manifest — see finding info-2) |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build duration | not re-run (scored inline) |

## Findings

Full list in `findings.jsonl` (no finding above `low`):

1. [low] No dependency manifest (requirements.txt / pyproject.toml) — README instructs manual `pip install flask`.
2. [info] `init_db()` runs as an import-time side effect (`app.py:156`).
3. [info] `?author=` filter uses exact-match equality (acceptable per spec).

## Reproduce

```bash
cd "/Users/adriancockcroft/code/retort/experiments/adrianco/experiment-91-holo4-screen/rest-api-crud/runs/agent=hermes-0222_language=python_model=llamacpp/Holo4-35B-A3B_prompt=neutral_stack=holo4/rep1"
cat scores.json                                 # stored mechanical scores (build/test/lint)
cat ../../../../REQUIREMENTS.json               # pinned 12-item checklist (walk up to task dir)
grep -cE "def test_" tests/test_app.py          # 9 tests
grep -rE "skip|xfail" tests/ --include="*.py"   # 0 skips
# Optional re-run of the suite (builds too):
python -m unittest discover tests -v
```
