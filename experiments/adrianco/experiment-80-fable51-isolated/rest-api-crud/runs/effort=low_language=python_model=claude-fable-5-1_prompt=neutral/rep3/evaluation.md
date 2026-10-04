# Evaluation: effort=low_language=python_model=claude-fable-5-1_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-fable-5-1, prompt=neutral, effort=low (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective)
- **Build:** pass — from scores.json (defect_rate=1.0, test_coverage=0.91)
- **Lint:** pass — code_quality=0.7889 (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Scores read from `scores.json` (inline gate); build/test/lint NOT re-run:
`test_coverage=0.91`, `defect_rate=1.0`, `maintainability=1.0`,
`code_quality=0.7889`, `idiomatic=0.68`, `token_efficiency=0.0717`.

A pinned `REQUIREMENTS.json` (12 entries) was found two levels up and used
verbatim as the checklist.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:82 create_book`, route `app.py:148-149` → 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:91 list_books`, route `app.py:142-147` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:145-146` parse_qs → `list_books(author)` `app.py:92-95` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:155-156` → `_get` raises `ApiError(404)` `app.py:76-80` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:157-158 update_book` `app.py:100-108`; test `test_update` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:159-161 delete_book` `app.py:110-113` → 204 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `app.py:58 sqlite3.connect`, table DDL `app.py:60-68` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `app.py:166-183 __call__`; STATUS map `app.py:9-17` (201/200/204/400/404/405/500) |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:30-52 validate_book`; test `test_create_validation` |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:136-139` → `{"status":"ok"}`; test `test_health` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:6-21` setup/env, `README.md:46-49` tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` — 9 tests, test_coverage=0.91 |

No requirement is partial or missing. Two info-level enhancement notes (year
range, ISBN format) are beyond-spec and not deductions.

## Build & Test

Not re-run per skill policy — scores read from `scores.json`:

```text
test_coverage = 0.91   # build + tests executed and passed (line coverage 91%)
defect_rate   = 1.0    # build + test succeeded
```

Tests (in-process WSGI against `:memory:` SQLite), 9 methods, 0 skips:
`test_health`, `test_create_and_get`, `test_create_optional_fields_omitted`,
`test_create_validation`, `test_invalid_json`, `test_list_and_author_filter`,
`test_update`, `test_delete`, `test_unknown_route_and_method`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 308 (app.py 200 + test_app.py 108) |
| Files | 2 source (app.py, test_app.py) + README.md |
| Dependencies | 0 (standard library only) |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [info] year accepts any integer with no plausibility bounds — `app.py:42-45`
2. [info] isbn is not format-validated — `app.py:46-49`

Both are beyond-spec enhancements, not defects. This is a clean, complete run.

## Reproduce

```bash
cd "/Users/adriancockcroft/code/retort/experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=low_language=python_model=claude-fable-5-1_prompt=neutral/rep3"
cat scores.json          # stored mechanical scores (build/test/lint not re-run)
grep -cE 'def test_' test_app.py
python3 -m unittest -v   # optional: re-run tests (9 tests)
```
