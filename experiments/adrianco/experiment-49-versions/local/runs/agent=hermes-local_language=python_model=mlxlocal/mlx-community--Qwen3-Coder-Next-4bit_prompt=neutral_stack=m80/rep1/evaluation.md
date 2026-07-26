# Evaluation: mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok — build + tests passed
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 14 defined / 0 skipped (14 effective) — `test_coverage=0.94` (scores.json)
- **Build:** pass (from `defect_rate=1.0`, `test_coverage=0.94`; not re-run)
- **Lint:** pass — `code_quality=0.7888` (scores.json); idiomatic=0.68
- **Architecture:** run-summary skill unavailable in this session; single-module Flask app (`app.py`) + pytest suite (`test_app.py`). See inline notes below.
- **Findings:** 3 items in `findings.jsonl` (0 critical, 1 high, 1 medium, 1 info)

## Requirements

Assessed against the pinned `local/REQUIREMENTS.json` (constant 12-item denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:81 create_book` INSERTs all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:109 list_books` returns collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:116-117` `WHERE author LIKE` (substring, see enh-1) |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:127 get_book` returns 404 at :137 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:142 update_book` dynamic partial update |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:193 delete_book`, 404 at :203 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:15,30-42` sqlite3 + CREATE TABLE books |
| R8 | JSON responses + appropriate status codes | ✓ implemented | jsonify + 201/200/400/404 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:46 validate_book_data` → 400; test_app.py:75,94 |
| R10 | GET /health | ✓ implemented | `app.py:75 health_check` returns 200 healthy |
| R11 | README with setup/run instructions | ✓ implemented | `README.md:21-32` setup+run (but see deps-1) |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 14 `test_*` in test_app.py; test_coverage=0.94 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.94   # build + tests executed and passed
defect_rate   = 1.0    # build+test succeeded
code_quality  = 0.7888
maintainability = 0.9908
idiomatic     = 0.68
```

14 tests defined, 0 skipped/xfail (`grep -c "^def test_" test_app.py` = 14; skip grep = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 470 (app.py 214, test_app.py 256) |
| Files | 14 (incl. run artifacts); 3 deliverables (app.py, test_app.py, requirements.txt) + README |
| Dependencies declared | 1 (pytest) — **Flask missing**, see deps-1 |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. **[high] deps-1** — `requirements.txt` omits Flask; documented `pip install -r requirements.txt && python app.py` fails with ModuleNotFoundError in a clean env (scored run passed only because flask was preinstalled).
2. **[medium] test-iso-1** — Tests set `app.config['DATABASE']` but app reads a module-level `DATABASE='books.db'` constant, so the suite runs against the real `books.db`, not the temp fixture DB.
3. **[info] enh-1** — `?author=` is a substring (`LIKE %..%`) match rather than exact; harmless enhancement, test relies on it.

## Reproduce

```bash
cd "runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep1"
cat scores.json                                   # stored build/test/quality scores
grep -c "^def test_" test_app.py                  # 14 tests
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py  # 0 skips
grep -i flask requirements.txt || echo "Flask NOT declared"
```
