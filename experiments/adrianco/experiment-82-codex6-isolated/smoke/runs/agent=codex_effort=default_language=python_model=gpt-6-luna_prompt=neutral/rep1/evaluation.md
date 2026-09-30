# Evaluation: agent=codex effort=default language=python model=gpt-6-luna prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=gpt-6-luna, agent=codex, framework=unknown (stdlib), prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — `test_coverage=0.85` from `scores.json`
- **Build:** pass (`defect_rate=1.0`, `test_coverage=0.85` from `scores.json` — not re-run)
- **Lint:** pass — `code_quality=0.79` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

The prompt factor is `neutral` (`prompts/neutral.md`): it prescribes no methodology and only asks for tests demonstrating the requirements — no additional checkable instructions beyond R12, so the P-list is empty.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:79-89` do_POST → INSERT → 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:62-69` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:63-68` WHERE author = ? |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `app.py:70-77` fetchone → 404/200 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:91-104` UPDATE → re-SELECT |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:106-114` DELETE, 404 on rowcount 0 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:13-25` sqlite3 CREATE TABLE books |
| R8 | JSON responses + status codes | ✓ implemented | `app.py:29-35` send_json; 201/200/400/404 used |
| R9 | Validation: title & author required | ✓ implemented | `app.py:46-49` → 400 on empty/missing |
| R10 | GET /health | ✓ implemented | `app.py:60-61` → 200 {status: ok} |
| R11 | README with setup/run | ✓ implemented | `README.md:1-31` run + endpoints + tests |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `test_app.py` 3 methods; `test_coverage=0.85` |

## Build & Test

Scores read from `scores.json` (mechanical scorers already ran; not re-executed per skill guidance):

```text
test_coverage = 0.85   # build + tests ran and passed (>0)
defect_rate   = 1.0    # build+test succeeded
code_quality  = 0.7889 # lint/quality
maintainability = 0.9697
idiomatic     = 0.72
token_efficiency = 0.0259
```

```text
python -m unittest -v   # (not re-run) — 3 tests, 0 failures, 0 skips
test_health
test_create_get_filter_update_delete
test_required_fields_and_missing_book
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 208 (app.py 139 + test_app.py 69) |
| Files | 4 (app.py, test_app.py, README.md, TASK.md) |
| Dependencies | 0 (stdlib only) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Error-handling branches unexercised by tests (coverage 0.85) — no cases for malformed JSON, year/isbn type validation, or unrouted-path 404.
2. [info] Zero third-party dependencies — full CRUD + validation on `http.server` + `sqlite3`.

No critical/high/medium findings: every pinned requirement is implemented with cited evidence, tests pass, and no tests are skipped or disabled.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-82-codex6-isolated/smoke/runs/agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral/rep1
cat scores.json                     # mechanical scores (source of build/test/lint signal)
grep -rE "skip|xfail" . --include="*.py"   # skip detection (none)
grep -cE "def test_" test_app.py    # 3
python -m unittest -v               # optional re-run (skill uses stored scores)
```
