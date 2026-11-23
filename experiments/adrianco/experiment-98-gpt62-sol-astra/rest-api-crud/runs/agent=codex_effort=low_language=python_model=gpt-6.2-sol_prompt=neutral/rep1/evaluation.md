# Evaluation: rest-api-crud · agent=codex effort=low language=python model=gpt-6.2-sol prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=gpt-6.2-sol, agent=codex, effort=low, prompt=neutral, framework=unknown (stdlib only)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 5 test methods passed / 0 failed / 0 skipped (5 effective) — `test_coverage=0.9`, `defect_rate=1.0` from `scores.json`
- **Build:** pass — not re-run (`test_coverage=0.9` ⇒ import + tests executed)
- **Lint:** pass — `code_quality=0.789` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Checklist from pinned `rest-api-crud/REQUIREMENTS.json` (fixed denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:63-70` INSERT, returns 201 + Location |
| R2 | GET /books lists all | ✓ implemented | `app.py:78-80` SELECT ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:72-77` WHERE author = ?; `test_app.py:88` |
| R4 | GET /books/{id} single | ✓ implemented | `app.py:95-98`, 404 when absent |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:87-93` UPDATE, 404 when rowcount 0 |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:82-86`, 204 / 404 |
| R7 | SQLite persistence | ✓ implemented | `app.py:103,135` sqlite3; `test_app.py:85` persistence test |
| R8 | JSON + proper status codes | ✓ implemented | `app.py:140-152` JSON body, 201/200/204/400/404/405/413/500 |
| R9 | title & author required | ✓ implemented | `app.py:39-42` nonblank-string check → 400 |
| R10 | GET /health | ✓ implemented | `app.py:120,132-133` → `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` run + test + endpoint table |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` 5 methods; `test_coverage=0.9` |

No enhancements beyond spec are penalized; validation robustness noted as info findings.

## Build & Test

Not re-run — stored scores used per the skill (do not re-run the toolchain).

```text
scores.json: {"test_coverage": 0.9, "defect_rate": 1.0, "code_quality": 0.789,
              "maintainability": 0.950, "idiomatic": 0.8, "token_efficiency": 0.0317}
test_coverage=0.9 ⇒ `python3 -m unittest` imported app.py and all tests passed
defect_rate=1.0  ⇒ build+test succeeded
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: app.py) | 173 |
| Lines of code (tests: test_app.py) | 119 |
| Delivered files | 3 (app.py, test_app.py, README.md) |
| External dependencies | 0 (Python stdlib only) |
| Tests total | 5 methods (multiple subTests) |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | not re-run |

## Findings

All 3 findings are info-level (no deductions). Full list in `findings.jsonl`:

1. [info] Validation hardened well beyond the spec — `app.py:44-57`
2. [info] Tests prove on-disk persistence and 405/Allow semantics — `test_app.py:85,110`
3. [info] One SQLite connection opened per request — `app.py:135`

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=python_model=gpt-6.2-sol_prompt=neutral/rep1"
cat scores.json                      # stored mechanical scores (build/test/lint)
cat ../../REQUIREMENTS.json          # pinned requirement checklist
grep -cE "def test_" test_app.py     # test count
# build/test NOT re-run — test_coverage=0.9, defect_rate=1.0 are authoritative
```
