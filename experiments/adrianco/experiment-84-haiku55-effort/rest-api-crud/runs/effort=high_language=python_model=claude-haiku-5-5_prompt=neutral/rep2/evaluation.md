# Evaluation: effort=high_language=python_model=claude-haiku-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, effort=high, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 38 test functions (more after parametrization), 0 skipped — all effective; `test_coverage=0.94`, `defect_rate=0.963` from `scores.json` ⇒ build + tests passed
- **Build:** pass (not re-run; `test_coverage=0.94 > 0` ⇒ import/build succeeded and tests executed)
- **Lint:** `code_quality=0.667` from `scores.json` (not re-run; no concrete style defect found on manual review)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 5 info — 4 enhancements + 1 lint note)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.py:_create_book` → `store.py:create`; `tests/test_api.py:58 test_create_book_returns_201_with_location` |
| R2 | GET /books lists all | ✓ implemented | `server.py:_list_books` → `store.py:list_books`; `tests/test_api.py:103 test_list_all_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `server.py:84-89`; `store.py:60-62` `WHERE author COLLATE NOCASE`; `tests/test_api.py:111 test_list_filters_by_author` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `server.py:_get_book:97-99`; `tests/test_api.py:90,97 test_get_book_by_id / returns_404` |
| R5 | PUT /books/{id} updates | ✓ implemented | `server.py:_replace_book` → `store.py:update`; `tests/test_api.py:123 test_put_replaces_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `server.py:_delete_book` → `store.py:delete`; `tests/test_api.py:145 test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `store.py:5,27 sqlite3.connect`; `tests/test_store.py:43 test_data_persists_across_connections` |
| R8 | JSON responses + proper status codes | ✓ implemented | `server.py:_send:161-170`, 201/200/204/400/404/405/413/503; `tests/test_api.py` asserts codes throughout |
| R9 | Validation: title & author required | ✓ implemented | `validation.py:_required_text:38-50`; `tests/test_api.py:72`, `tests/test_validation.py:26,32` |
| R10 | GET /health | ✓ implemented | `server.py:_health:74-80`; `tests/test_api.py:46 test_health_check` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — Setup, Run, CLI flags, curl examples, layout, design notes |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 38 test functions across 3 files; `test_coverage=0.94 > 0` |

No prompt-factor requirements (`prompt=neutral` is a stock instruction, not a checkable prompts/ file).

## Build & Test

Build and tests were **not re-run** per the evaluate-run policy — stored scores stand in:

```text
scores.json (this run)
test_coverage = 0.94      # > 0 ⇒ build/import OK and tests executed; 94% line coverage
defect_rate   = 0.963     # ⇒ build + tests succeeded
code_quality  = 0.667     # lint/quality score
maintainability = 0.914   idiomatic = 0.90   token_efficiency = 0.023
```

```text
skip scan: grep -rE "pytest.skip|@pytest.mark.skip|xfail" tests/  →  0 matches
test functions: 21 (test_api) + 6 (test_store) + 11 (test_validation) = 38, parametrized further
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, `bookapi/`) | 378 |
| Lines of code (tests) | 346 |
| Files (source + tests) | 9 |
| Runtime dependencies | 0 (stdlib only) |
| Dev dependencies | 1 (`pytest>=8`) |
| Tests total (functions) | 38 |
| Tests effective | 38 (0 skipped) |
| Skip ratio | 0% |
| Build duration | not re-run (scores cached) |

## Findings

Top findings by severity (full list in `findings.jsonl`) — all info-level; no defects against spec:

1. [info] E1 — Oversized request body rejected with 413 without reading it (beyond-spec hardening)
2. [info] E2 — ISBN format validation/normalisation beyond required title/author checks
3. [info] E3 — Concurrency-safe store + 40-way concurrent-create test
4. [info] E4 — 405 with `Allow` header and 404 JSON for unknown routes
5. [info] LINT1 — `code_quality=0.667` noted; no concrete style defect found on manual review

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=high_language=python_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                   # cached mechanical scores (no re-run)
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l   # 0
grep -rEc "def test_" tests/*.py                  # test function counts
wc -l bookapi/*.py tests/*.py                     # LOC
# optional, to re-verify locally (not part of scoring): python -m pytest
```
