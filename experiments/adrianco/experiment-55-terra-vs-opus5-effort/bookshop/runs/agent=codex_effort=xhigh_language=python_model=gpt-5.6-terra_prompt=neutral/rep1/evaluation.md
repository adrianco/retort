# Evaluation: agent=codex effort=xhigh language=python model=gpt-5.6-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-terra, effort=xhigh, prompt=neutral, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — `defect_rate=1.0` from scores.json (build + tests succeeded)
- **Lint:** pass — `code_quality=0.789` from scores.json
- **Architecture:** run-summary skill unavailable in this environment; summary omitted
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores read from `scores.json` (no re-run): `test_coverage=0.93`, `defect_rate=1.0`,
`code_quality=0.789`, `maintainability=0.941`, `idiomatic=0.78`,
`token_efficiency=0.026`. `test_coverage=0.93` is a coverage fraction; `defect_rate=1.0`
confirms the build compiled and all tests passed.

## Requirements

Checklist is the pinned `bookshop/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:49` `create_book`, INSERT of title/author/year/isbn, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:63` `list_books` selects all rows ordered by id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:70-75` `WHERE author = ? COLLATE NOCASE`; test `test_app.py:49` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:78` `get_book`, 404 when absent (`app.py:82`) |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:85` `update_book`, UPDATE, 404 when absent; test `test_app.py:63` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:102` `delete_book`, returns 204, 404 when rowcount 0 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:117-135` sqlite3 connect + schema; on-disk `instance/books.sqlite3` |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify` throughout; 201/200/204/400/404 returned explicitly |
| R9 | Validation: title & author required | ✓ implemented | `app.py:161-190` `parse_book_payload`; test `test_app.py:80` |
| R10 | GET /health | ✓ implemented | `app.py:45` `health` returns `{"status":"ok"}`; test `test_app.py:87` |
| R11 | README with setup/run | ✓ implemented | `README.md` setup, run, endpoints, curl example, test command |
| R12 | ≥3 unit/integration tests | ✓ implemented | 5 `test_*` in `test_app.py`; `test_coverage=0.93` |

No enhancements beyond spec beyond minor robustness (case-insensitive author filter);
see `findings.jsonl`.

## Build & Test

Not re-run — stored scores used per the evaluate-run skill.

```text
scores.json: defect_rate=1.0  →  build + tests passed
scores.json: test_coverage=0.93 (coverage fraction)
test_app.py: 5 test functions, 0 skips/xfail
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, non-blank) | 158 (`app.py`) |
| Lines of code (tests, non-blank) | 65 (`test_app.py`) |
| Files (excl. .git/instance/pycache) | 12 |
| Dependencies | 1 (`Flask>=2.3,<4.0`) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All findings are informational (0 critical/high/medium/low):

1. [info] R3 — Author filter is case-insensitive (COLLATE NOCASE); robustness beyond spec
2. [info] R5 — PUT performs a full replace of optional fields (correct PUT semantics)
3. [info] R12 — 5 tests provided, exceeding the minimum of 3

## Reproduce

```bash
cd "runs/agent=codex_effort=xhigh_language=python_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json                       # stored mechanical scores (no re-run)
grep -cE "^def test_" test_app.py     # test count = 5
grep -rE "pytest\.skip|xfail" . --include="*.py" | wc -l   # skips = 0
# Optional full re-run:
python3 -m pytest -q
```
