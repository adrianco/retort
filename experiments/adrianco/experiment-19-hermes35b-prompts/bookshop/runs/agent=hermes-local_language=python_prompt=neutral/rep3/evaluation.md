# Evaluation: agent=hermes-local language=python prompt=neutral · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local (Qwen3.6-35B-A3B, oMLX), framework=Flask, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 18 passed / 0 failed / 0 skipped (18 effective) — from `test_coverage=0.98`, `defect_rate=1.0` in scores.json
- **Build:** pass (import + tests executed; `test_coverage=0.98`)
- **Lint:** pass — `code_quality=0.79` (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:53 create_book`, INSERT at :73 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:91 list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:97-100` LIKE filter; `test_app.py:153 test_list_books_filter_by_author` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `app.py:117 get_book`, 404 at :124; `test_app.py:192 test_get_book_not_found` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:140 update_book`; `test_app.py:200 test_update_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:184 delete_book`; `test_app.py:224 test_delete_book` verifies removal |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:29 init_db`, `sqlite3` connection, `books.db` |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify(...)` with 201/200/400/404 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:66-70`; `test_app.py:72/81/102/109` cover missing & empty |
| R10 | GET /health | ✓ implemented | `app.py:47 health_check`; `test_app.py:46 test_health_check` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — setup, run, endpoints, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | 18 tests in `test_app.py`; `test_coverage=0.98` |

**Prompt factor (neutral):** `prompts/neutral.md` prescribes no methodology and asks for tests demonstrating the requirements. Satisfied — 18 passing tests cover every endpoint plus validation and not-found paths. No additional `P*` requirements.

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.98   -> build + tests executed and passed
defect_rate   = 1.0    -> build+test succeeded
code_quality  = 0.789
maintainability = 0.986
idiomatic     = 0.70
```

```text
grep -cE "^def test_" test_app.py  -> 18
grep skip/xfail                    -> 0 skipped
Agent log: "All 17 tests pass" (actual count 18 test functions)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py, non-blank) | 159 |
| Lines of code (test_app.py, non-blank) | 198 |
| Files (source, excl. artifacts) | app.py, test_app.py, requirements.txt, README.md |
| Dependencies | 2 (flask, pytest) |
| Tests total | 18 |
| Tests effective | 18 |
| Skip ratio | 0% |
| Agent tokens | 520,613 total (22 API calls); token_efficiency=0.014 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] init_db() runs at import time and writes books.db into the workspace — `app.py:200`
2. [info] Author filter uses LIKE substring match rather than exact equality — `app.py:99`
3. [info] PUT partial-update null-vs-omitted semantics undocumented — `app.py:153-156`

No critical, high, or medium findings. This is a clean, fully-conformant run.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-19-hermes35b-prompts/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep3
cat scores.json                                    # stored mechanical scores
grep -cE "^def test_" test_app.py                  # 18
grep -rE "pytest\.skip|xfail" . --include="*.py"   # 0
# tests (only if re-verifying): pip install -r requirements.txt && pytest test_app.py -v
```
