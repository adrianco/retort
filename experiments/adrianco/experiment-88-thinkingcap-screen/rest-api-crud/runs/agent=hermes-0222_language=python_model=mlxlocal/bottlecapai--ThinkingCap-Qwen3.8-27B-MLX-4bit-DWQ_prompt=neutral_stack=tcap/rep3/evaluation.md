# Evaluation: rest-api-crud · python · hermes-0222 · ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ · neutral · tcap · rep 3

## Summary

- **Factors:** language=python, agent=hermes-0222, model=mlxlocal/bottlecapai--ThinkingCap-Qwen3.8-27B-MLX-4bit-DWQ, prompt=neutral, stack=tcap
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 27 passed / 0 failed / 0 skipped (27 effective)
- **Build:** pass (import/collection succeeded — `test_coverage=0.97`, `defect_rate=1.0` from scores.json)
- **Lint:** pass — `code_quality=0.9556` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Scores read from `scores.json` (inline gate output); not re-run per the skill. `test_coverage=0.97`, `defect_rate=1.0`, `maintainability=1.0`, `idiomatic=0.85`, `code_quality=0.9556`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:100-133` `create_book`, INSERT with all 4 fields; test_app.py:33 |
| R2 | GET /books lists all | ✓ implemented | `app.py:135-145` `list_books`; test_app.py:90 |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:137-142` filters by `author` arg; test_app.py:99 |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:147-154` `get_book`, 404 branch; test_app.py:118,125 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:156-200` `update_book` (partial + full); test_app.py:138,151 |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:202-209` `delete_book`, 204/404; test_app.py:194 |
| R7 | SQLite persistence | ✓ implemented | `app.py:11,28-53` `sqlite3` connect + CREATE TABLE; test_app.py:220 persistence test |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/404/400/204/405 across handlers; `error()` helper app.py:65 |
| R9 | Validation: title & author required | ✓ implemented | `app.py:107-112` required + non-blank check; test_app.py:52,58,64 |
| R10 | GET /health | ✓ implemented | `app.py:96-98` returns `{"status":"ok"}`; test_app.py:25 |
| R11 | README with setup/run | ✓ implemented | `README.md` setup, run, env vars, endpoint table, field rules |
| R12 | >= 3 tests | ✓ implemented | `test_app.py` 27 tests, 0 skips; `test_coverage=0.97` |

## Build & Test

Not re-run (skill §2 — stored scores exist). From `scores.json`:

```text
test_coverage = 0.97   # build + tests executed and passed (test gate)
defect_rate   = 1.0    # build + test succeeded
maintainability = 1.0
code_quality  = 0.9556 # lint/quality
idiomatic     = 0.85
```

Test inventory (static): 27 `test_*` functions in `test_app.py`, 0 skip/xfail markers.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, app.py) | 192 non-blank / 232 total |
| Lines of code (tests) | 156 non-blank / 223 total |
| Files (source) | app.py, test_app.py, requirements.txt, README.md |
| Dependencies | 1 (`flask>=3.0`) |
| Tests total | 27 |
| Tests effective | 27 |
| Skip ratio | 0% |
| API calls (agent) | 29 (+1 aux) |
| Tokens (total) | 778,876 |

## Findings

Top findings (full list in `findings.jsonl`) — no defects; both are beyond-spec notes:

1. [info] Validation and error handling exceed the spec (int year, unknown-field rejection, global JSON 404/405).
2. [info] 27 tests cover all CRUD paths plus edge cases (spec asked for ≥3).

## Reproduce

```bash
cd "<run_dir>"
cat scores.json                                  # stored mechanical scores (no re-run)
grep -cE "^def test_" test_app.py                # 27
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l   # 0
# optional fresh run:
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && pytest -q
```
