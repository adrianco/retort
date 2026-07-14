# Evaluation: agent=hermes-local language=python prompt=ATDD · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local (model qwen3-coder-30b), prompt=ATDD, framework=Flask
- **Status:** ok — all 12 task requirements implemented; ATDD prompt instruction only partially followed
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (TASK.md R1–R12) · prompt P1 partial
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass (`defect_rate=1.0` from scores.json — build+test succeeded)
- **Lint:** pass — code_quality=0.83, idiomatic=0.58 (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 1 high, 1 medium, 3 low, 1 info)

Scores are read from `scores.json` (inline gate output); no toolchain was re-run.
`test_coverage=0.92` (coverage fraction, not a pass rate) with `defect_rate=1.0`
confirms the build compiled and every test passed.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:42 create_book`; `test_app.py:26 test_create_book` |
| R2 | GET /books lists all | ✓ implemented | `app.py:67 get_books`; `test_app.py:62 test_get_all_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:69-74 filter_by(author=...)`; `test_app.py:76 test_get_books_by_author` |
| R4 | GET /books/{id} single | ✓ implemented | `app.py:79 get_book` + 404; `test_app.py:94,108` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:85 update_book`; `test_app.py:113 test_update_book` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:108 delete_book`; `test_app.py:158,170` |
| R7 | SQLite / embedded DB | ✓ implemented | `app.py:6 sqlite:///books.db`; `instance/books.db` present |
| R8 | JSON responses + status codes | ✓ implemented* | success paths JSON (`app.py:61,76,82,102,115`); *404 via `get_or_404` returns HTML — see finding R8 |
| R9 | Validation: title & author required | ✓ implemented | `app.py:47-48,91-92`; `test_app.py:47,138` |
| R10 | GET /health | ✓ implemented | `app.py:37 health_check`; `test_app.py:19 test_health_check` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, endpoints, curl examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 11 tests in `test_app.py`; test_coverage=0.92 |

### Prompt factor (ATDD)

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Test only via public HTTP interface, no back-door DB access | ~ partial | 6/11 tests seed via `db.session.add(Book(...))` (`test_app.py:65,79,97,116,141,161`) instead of POSTing |
| P2 | Assert WHAT not HOW, in domain language | ✓ followed | Tests assert on status codes + JSON contract, not internals |
| P3 | Atomic & independent, each starts empty | ✓ followed | `setUp` create_all / `tearDown` drop_all per test (`test_app.py:6-17`) |

## Build & Test

No commands were re-run — scores come from the inline gate (`scores.json`):

```text
scores.json: {"code_quality": 0.833, "test_coverage": 0.92, "defect_rate": 1.0,
              "maintainability": 0.890, "idiomatic": 0.58, "token_efficiency": 0.013}
=> build+test succeeded (defect_rate=1.0); 11/11 tests pass; 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 307 (app.py 121, test_app.py 176, run.py 10) |
| Files (source) | 5 (app.py, run.py, test_app.py, README.md, + instance db) |
| Dependencies | 2 (flask, flask-sqlalchemy) — unpinned, README only |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [high] P1 — ATDD prompt violated: acceptance tests use back-door DB access (`test_app.py:65,79,97,116,141,161`)
2. [medium] R8 — 404 responses are HTML, not JSON (`app.py:81,87,109 get_or_404`)
3. [low] dep-1 — No pinned dependency manifest (no requirements.txt/pyproject.toml)
4. [low] lint-1 — Deprecated `datetime.utcnow` used (`app.py:18-19`)
5. [low] sec-1 — Dev server runs with `debug=True` (`app.py:121`, `run.py:10`)

## Reproduce

```bash
cd "experiment-17-hermes/bookshop/runs/agent=hermes-local_language=python_prompt=ATDD/rep2"
cat scores.json                    # stored mechanical scores (no re-run)
grep -cE "def test_" test_app.py   # 11 tests
grep -nE "db\.session\.add|get_or_404" test_app.py app.py   # back-door seeding + HTML 404s
```
