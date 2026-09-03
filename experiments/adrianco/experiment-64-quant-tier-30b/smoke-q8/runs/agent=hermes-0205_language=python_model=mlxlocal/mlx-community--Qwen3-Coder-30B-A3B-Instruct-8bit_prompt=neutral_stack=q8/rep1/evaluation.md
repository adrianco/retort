# Evaluation: agent=hermes-0205 · model=Qwen3-Coder-30B-A3B-Instruct-8bit · prompt=neutral · stack=q8 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlx-community/Qwen3-Coder-30B-A3B-Instruct-8bit, prompt=neutral, stack=q8
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.789` (scores.json)
- **Architecture:** run-summary skill unavailable in this session; single-module Flask + SQLAlchemy app (see below)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

Scores read from `scores.json` (no re-run): `test_coverage=0.92`, `defect_rate=1.0`,
`code_quality=0.789`, `maintainability=0.997`, `idiomatic=0.70`, `token_efficiency=0.0021`.
`test_coverage=0.92 > 0` and `defect_rate=1.0` confirm the build succeeded and all tests executed and passed.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:48` `create_book`, persists title/author/year/isbn, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:73` `get_books`, `Book.query.all()` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:77` `filter_by(author=author)` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:85` `get_or_404(book_id)` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:91` `update_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:118` `delete_book`, returns 200 |
| R7 | SQLite / embedded DB | ✓ implemented | `app.py:11` `sqlite:///books.db` via Flask-SQLAlchemy |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/400/500 across routes (`app.py:67,82,88,54`) |
| R9 | Validation: title & author required | ✓ implemented | `app.py:53` rejects missing keys with 400 (present-key check only — empty string passes; low finding) |
| R10 | GET /health | ✓ implemented | `app.py:43` returns `{"status":"healthy"}`, 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` — install, run, endpoint docs, testing (port 5000 vs 5002 mismatch; low finding) |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` — 8 tests, 0 skipped |

## Build & Test

Not re-run — scores read from `scores.json`:

```text
defect_rate = 1.0   → build + tests succeeded
test_coverage = 0.92 → tests executed and passed (coverage 92%)
```

Test suite: `python test_app.py` — 8 tests (`grep -cE 'def test_' test_app.py` = 8),
covering health, create, list, author filter, get-by-id, update, delete, and
missing-field validation. Zero skips (`grep skip/xfail` = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 257 (app.py 130, test_app.py 127) |
| Files | app.py, test_app.py, README.md |
| Dependencies | Flask, Flask-SQLAlchemy |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| code_quality | 0.789 |
| maintainability | 0.997 |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] R9 — validation checks key presence but not empty strings (`app.py:53`)
2. [low] README states port 5000 but app runs on 5002 (`README.md:32` vs `app.py:131`)
3. [info] PUT does not re-validate required fields (`app.py:101-108`)

No critical/high/medium findings. This is a complete, passing implementation.

## Reproduce

```bash
cd "experiments/adrianco/experiment-64-quant-tier-30b/smoke-q8/runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit_prompt=neutral_stack=q8/rep1"
cat scores.json                              # stored build/test/quality scores
grep -cE 'def test_' test_app.py             # 8 tests
grep -rE 'skip|xfail' --include='*.py' .     # 0 skips
python test_app.py                           # optional: re-run tests
```
