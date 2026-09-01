# Evaluation: effort=low_language=python_model=claude-fable-5-1_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-fable-5-1, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass (n/a — pure stdlib import; test_coverage=0.91 from scores.json ⇒ tests executed)
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create | ✓ implemented | `src/app.py:90` do_POST → `src/db.py:32` create |
| R2 | GET /books list | ✓ implemented | `src/app.py:78` → `src/db.py:40` list |
| R3 | ?author= filter | ✓ implemented | `src/app.py:80`; `src/db.py:42` WHERE author=? |
| R4 | GET /books/{id} (404) | ✓ implemented | `src/app.py:82-87` BOOK_ID_RE, 404 branch |
| R5 | PUT /books/{id} | ✓ implemented | `src/app.py:100` do_PUT → `src/db.py:58` update |
| R6 | DELETE /books/{id} | ✓ implemented | `src/app.py:113` do_DELETE → `src/db.py:69` delete |
| R7 | SQLite storage | ✓ implemented | `src/db.py:1-25` sqlite3 + schema |
| R8 | JSON + HTTP codes | ✓ implemented | `_send`/`_error`; 201/200/404/422/400/204 |
| R9 | title/author required | ✓ implemented | `src/validation.py:17-22`; see low finding re 422 vs 400 |
| R10 | GET /health | ✓ implemented | `src/app.py:76-77` returns `{"status":"ok"}` |
| R11 | README setup/run | ✓ implemented | `README.md` Setup/Run/Endpoints/Tests |
| R12 | ≥3 tests | ✓ implemented | `tests/test_api.py` 8 tests, test_coverage=0.91 |

## Build & Test

No re-run — mechanical scores read from `scores.json`:

```text
test_coverage = 0.91   ⇒ build + tests executed and passed
code_quality  = 0.8333
defect_rate   = 1.0    ⇒ build+test succeeded
maintainability = 0.8137, idiomatic = 0.80
```

8 test functions, 0 skipped (`grep pytest.skip|xfail` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source+tests) | 374 |
| Files | 7 |
| Dependencies | 0 runtime (stdlib), pytest for tests |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (stdlib) |

## Findings

Full list in `findings.jsonl`:

1. [low] R9 — validation failures return 422 where REQUIREMENTS.R9 how_to_verify cites 400 (R8 permits appropriate 4xx; malformed JSON is 400).
2. [info] Enhancement — year-range/ISBN validation, 1 MiB body cap, thread-safe SQLite repo.
3. [info] Enhancement — unknown-route and non-numeric-id 404s explicitly tested.

## Reproduce

```bash
cd "$(git rev-parse --show-toplevel)/experiments/adrianco/experiment-65-fable51-effort/rest-api-crud/runs/effort=low_language=python_model=claude-fable-5-1_prompt=neutral/rep3"
cat scores.json                               # mechanical scores (no re-run)
grep -rE "pytest\.skip|xfail" tests/ | wc -l  # skip count
find src tests -name '*.py' | xargs wc -l     # LOC
```
