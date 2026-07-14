# Evaluation: agent=hermes-local language=python prompt=BDD · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3.6-35B-A3B), framework=Flask (unspecified in stack), prompt=BDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (+ BDD prompt instruction P1 satisfied)
- **Tests:** 19 passed / 0 failed / 0 skipped (19 effective)
- **Build:** pass — from `defect_rate=1.0` in scores.json (build+test succeeded)
- **Lint:** pass — `code_quality=0.79`, `idiomatic=0.78` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:63 create_book`, INSERT at `app.py:89-92`; test `test_create_book_succeeds_with_valid_data` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:112 list_books`; test `test_list_books_returns_all_books` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:118-121` LIKE partial match; tests `test_list_books_filtered_by_exact_author`, `..._partial_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:130 get_book`, 404 at `app.py:136-137`; tests `test_get_book_returns_200...`, `...404...` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:143 update_book`; test `test_update_book_changes_fields` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:178 delete_book`; tests `test_delete_book_removes_it`, `..._prevents_it_from_appearing_in_list` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:19 sqlite3.connect`, schema `app.py:36-44` |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `jsonify(...)` with 201/200/400/404 throughout `app.py`; asserted across tests |
| R9 | Input validation: title & author required | ✓ implemented | `app.py:79-83` (create), `app.py:157-160` (update); tests `..._fails_when_title_is_missing`, `..._author_is_missing` |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:56 health_check`; test `test_health_endpoint_returns_200_with_healthy_status` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Setup, Run, API reference sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 19 tests in `test_app.py` (`test_coverage=0.97`) |
| P1 | BDD prompt: GWT scenarios, one per behaviour, via public HTTP interface | ✓ implemented | `test_app.py` — 6 `Feature` classes, 19 Given-When-Then scenario docstrings, all through the Flask test client / JSON contracts |

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.97   # tests executed, ~97% line coverage
defect_rate   = 1.0    # build + tests succeeded
code_quality  = 0.789
maintainability = 1.0
idiomatic     = 0.78
token_efficiency = 0.0084
```

```text
python -m pytest test_app.py -v
19 tests defined, 0 skip/xfail markers → 19 effective, all passing (defect_rate=1.0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 195 (app.py) + 385 (test_app.py) = 580 |
| Files | 12 (incl. .coverage, logs, meta) |
| Dependencies | 1 (flask; no manifest file) |
| Tests total | 19 |
| Tests effective | 19 |
| Skip ratio | 0% |
| Build duration | n/a (read from cache) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] init_db() runs on every request via before_request (`app.py:49-52`)
2. [low] App runs with debug=True and binds 0.0.0.0 (`app.py:195`)
3. [info] No dependency manifest (requirements.txt / pyproject.toml)
4. [info] Dead config assignment in test fixture (`test_app.py:30`)
5. [info] Enhancement — BDD prompt fully realized with 19 GWT scenarios

No critical, high, or medium findings. This run implements the full spec and follows the BDD prompt factor.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-19-hermes35b-prompts/bookshop/runs/agent=hermes-local_language=python_prompt=BDD/rep1
cat scores.json            # cached mechanical scores (build/test/lint)
grep -cE "def test_" test_app.py
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py
python -m pytest test_app.py -v   # optional: re-run to confirm 19 pass
```
