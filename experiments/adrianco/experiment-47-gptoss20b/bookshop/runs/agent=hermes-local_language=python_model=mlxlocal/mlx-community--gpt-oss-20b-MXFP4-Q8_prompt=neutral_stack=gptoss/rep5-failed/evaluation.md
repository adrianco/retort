# Evaluation: python · hermes-local · gpt-oss-20b · rep 5 (SECOND OPINION)

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok
- **Requirements:** 10/12 implemented, 1 partial (R12), 1 missing (R11)
- **Tests:** 2 test functions, both effective (0 skipped); test_coverage=0.77 from scores.json (tests build + run)
- **Build:** pass — test_coverage=0.77 (>0 ⇒ import + tests executed)
- **Lint:** code_quality=0.8333 from scores.json
- **Architecture:** small Flask + SQLAlchemy app (main.py), duplicate model definitions in models.py (unused by main.py)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 1 high, 1 medium)

## Second-opinion re-check of prior claims

The first evaluation scored requirement_coverage=0.8333 and flagged **R11 (README missing)** as not met.

- **R11 — CONFIRMED MISSING.** Checked `ls README*` (no matches) and `find . -iname 'readme*'` (none). The run_dir contains only main.py, models.py, tests/, TASK.md, and metadata files — no README.md. TASK.md:19 and REQUIREMENTS.json R11 both require it. The first evaluator was correct.

Additionally re-scored the full checklist: **R12 (≥3 tests) is also not met** — `tests/test_api.py` defines only 2 test functions (`test_health`, `test_crud_book`). This is consistent with the first evaluator's 10/12 = 0.8333 (10 implemented, R11 + R12 not fully met). Re-score stands at **0.8333**.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.py:36-53` create_book, persists all 4 fields, 201 |
| R2 | GET /books lists all | ✓ implemented | `main.py:55-73` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `main.py:57-61` filters by author |
| R4 | GET /books/{id} by id | ✓ implemented | `main.py:75-88` get_book, 404 if absent |
| R5 | PUT /books/{id} update | ✓ implemented | `main.py:90-110` update_book |
| R6 | DELETE /books/{id} delete | ✓ implemented | `main.py:112-122` delete_book, 204 |
| R7 | SQLite / embedded DB | ✓ implemented | `main.py:23-25` sqlite:///books.db via SQLAlchemy |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/404/400/204 across routes; jsonify used |
| R9 | Validation: title+author required | ✓ implemented | `main.py:39-40` abort(400) if missing |
| R10 | GET /health | ✓ implemented | `main.py:31-33` returns {"status":"ok"} |
| R11 | README.md setup/run instructions | ✗ missing | no README file in run_dir |
| R12 | ≥3 unit/integration tests | ~ partial | `tests/test_api.py` has only 2 test functions |

## Build & Test

Read from `scores.json` (not re-run):

```text
test_coverage = 0.77   (>0 ⇒ import + tests passed)
code_quality  = 0.8333
defect_rate   = 1.0    (build + test succeeded)
```

Tests: `test_health` (main.py:7), `test_crud_book` (main.py:14). No skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 207 (main 125, models 36, tests 46) |
| Files | 12 |
| Dependencies | flask, sqlalchemy, pydantic |
| Tests total | 2 |
| Tests effective | 2 |
| Skip ratio | 0% |

## Findings

1. [high] R11 — No README.md with setup and run instructions
2. [medium] R12 — Only 2 tests present; spec requires at least 3

## Reproduce

```bash
cd runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep5
ls README*                          # -> no matches (R11 confirmed missing)
grep -rEn "^def test_" tests/       # -> 2 test functions (R12 partial)
cat scores.json                     # test_coverage=0.77, code_quality=0.8333
```
