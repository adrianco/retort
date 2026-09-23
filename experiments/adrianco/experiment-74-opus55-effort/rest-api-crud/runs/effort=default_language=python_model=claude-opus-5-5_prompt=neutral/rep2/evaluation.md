# Evaluation: effort=default_language=python_model=claude-opus-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-5-5, prompt=neutral, effort=default (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** pass (test_coverage=0.93 from scores.json) — 12 test functions (one parametrized ×5) / 0 failed / 0 skipped
- **Build:** pass — from scores.json (defect_rate=1.0, test_coverage=0.93; not re-run)
- **Lint:** pass — code_quality=0.79 from scores.json (idiomatic=0.65, maintainability=1.0)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:206` do_POST → `BookStore.create` (57); tests/test_app.py:73 |
| R2 | GET /books lists all | ✓ implemented | `app.py:195` → `store.list()` (66); tests/test_app.py:107 |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:196` parse_qs author → `list(author)` (68); tests/test_app.py:111 |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app.py:198-204`; tests/test_app.py:79,148 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:224` do_PUT → `store.update` (84); tests/test_app.py:122 |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:239` do_DELETE → `store.delete` (94); tests/test_app.py:139 |
| R7 | SQLite / embedded DB persistence | ✓ implemented | `app.py:32-97` `BookStore` on sqlite3, file DB `books.db`; tests/test_app.py:157 restart test |
| R8 | JSON + appropriate status codes | ✓ implemented | `app.py:152-166` JSON send; 201/200/204/404/405/422/400 used |
| R9 | Validation: title & author required | ✓ implemented | `app.py:111-116`,258 → rejected (422); tests/test_app.py:90. See low finding: code is 422, spec example says 400 |
| R10 | GET /health | ✓ implemented | `app.py:187-194` pings DB; tests/test_app.py:67 |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup, Run, Endpoints, env vars, examples |
| R12 | ≥3 tests | ✓ implemented | `tests/test_app.py` 12 test functions; test_coverage=0.93 |

## Build & Test

Not re-run (per skill Step 2 — stored scores used):

```text
scores.json: {"test_coverage": 0.93, "defect_rate": 1.0, "code_quality": 0.789,
              "maintainability": 1.0, "idiomatic": 0.65, "token_efficiency": 0.0184}
```

test_coverage=0.93 ⇒ build succeeded and all tests passed at 93% coverage.
No skipped/xfail tests (grep of tests/ → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 458 (app.py 289 + tests 169) |
| Files | 13 (incl. build artifacts: .coverage, caches) |
| Dependencies | 1 dev-only (`pytest>=8`); 0 runtime |
| Tests total | 12 functions (~16 cases with parametrize) |
| Tests effective | ~16 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] R9 validation returns 422, not the 400 named in the spec's how_to_verify — rejection is correct, only the code differs (`app.py:258`)
2. [info] Enhancement: ISBN-10/13 format validation beyond spec (`app.py:127-136`)
3. [info] Enhancement: unknown request fields rejected (`app.py:107-108`)
4. [info] Enhancement: cross-restart SQLite persistence explicitly tested (`tests/test_app.py:157`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-74-opus55-effort/rest-api-crud/runs/effort=default_language=python_model=claude-opus-5-5_prompt=neutral/rep2"
cat scores.json                                  # stored build/test/lint scores
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" tests/   # skip check → 0
python -m pytest -q                              # (optional) re-run tests
```
