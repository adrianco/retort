# Evaluation: effort=default_language=python_model=claude-haiku-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, prompt=neutral, effort=default (agent/framework=unknown — stdlib only)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list from `REQUIREMENTS.json`)
- **Tests:** 51 passed / 0 failed / 0 skipped (51 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.67` (scores.json); no concrete lint issue found in review
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Scores read from `scores.json` (inline gate output; not re-run):
`test_coverage=0.94`, `defect_rate=1.0`, `code_quality=0.67`, `maintainability=0.92`,
`idiomatic=0.82`, `token_efficiency=0.026`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `server.py:103` `_create_book` → `validate_book` → `database.py:45` `create`; `test_api.py:7` |
| R2 | GET /books lists all books | ✓ implemented | `server.py:94` `_list_books` → `database.py:53` `find`; `test_api.py:79` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `server.py:97-101`, `database.py:60-62` `LOWER(author)=LOWER(?)`; `test_api.py:89` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `server.py:108-112` (404 at :111); `test_api.py:116`, `:125` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.py:114-119` → `database.py:73` `update`; `test_api.py:138`, `:158` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.py:121-124` (204) → `database.py:84` `delete`; `test_api.py:173` |
| R7 | Data stored in SQLite | ✓ implemented | `database.py:1-35` `sqlite3` + schema; `test_repository.py:74` persistence across connections |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `_send_json` `server.py:140`; 201/200/404/400/405/409/413/503 across `_dispatch`; `test_api.py` asserts codes |
| R9 | Validation: title and author required | ✓ implemented | `validation.py:34-35,44-56` `_required_text`; `test_api.py:27` (400, per-field) |
| R10 | GET /health health check | ✓ implemented | `server.py:52-54,86-92` (200 ok / 503 unavailable); `test_api.py:1` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Setup / Run / Test / Endpoints / Examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 40 test functions → 51 cases, all pass (`test_coverage=0.94`) |

No prompt-factor requirements: `prompt=neutral` is a tone selector, not an added-instruction file.

## Build & Test

Not re-run — stored scores used per skill policy.

```text
scores.json
defect_rate = 1.0   → build + tests succeeded
test_coverage = 0.94
```

```text
pytest (from agent run log)
51 passed in 1.31s
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, books_api/) | 425 |
| Lines of code (tests) | 391 |
| Files (excl. caches/.git/logs) | 19 |
| Dependencies (runtime) | 0 (stdlib only; pytest for tests) |
| Tests total | 51 |
| Tests effective | 51 |
| Skip ratio | 0% |
| Build/test (from scores) | pass |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] `code_quality=0.67` despite clean, idiomatic code — mechanical scorer is the only signal; hand review found no concrete lint issue.
2. [info] Error handling / status codes exceed spec (405/409/413/500/503, 1 MiB body cap).
3. [info] ISBN-10/13 checksum validation beyond the required title/author checks.

No critical, high, or medium findings. All 12 pinned requirements implemented and tested; no skipped tests.

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=default_language=python_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                   # stored mechanical scores (not re-run)
grep -rE "def test_" tests/ --include="*.py" | wc -l    # 40 functions (51 cases w/ parametrize)
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l   # 0 skips
# optional: python -m pytest   # 51 passed
```
