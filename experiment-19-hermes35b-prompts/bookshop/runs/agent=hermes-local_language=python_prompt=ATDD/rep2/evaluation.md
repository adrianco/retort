# Evaluation: agent=hermes-local · language=python · prompt=ATDD · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3.6-35B-A3B), prompt=ATDD, framework=Flask
- **Status:** ok (builds/imports) — but the ATDD acceptance suite does not self-host, so it fails to verify the service under scoring
- **Requirements:** 11/12 implemented, 1 partial (R12), 0 missing
- **Tests:** 25 defined / 0 effectively passing under scoring / 0 skipped (25 require a manually-started live server)
- **Build:** pass — `defect_rate=1.0` from scores.json (app imports, schema init runs)
- **Lint:** pass — `code_quality=0.83` from scores.json
- **Coverage:** `test_coverage=0.14` from scores.json (app.py ~0% — tests never hit the running app)
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 3 high, 2 medium, 1 info)

## Requirements

Pinned checklist from `bookshop/REQUIREMENTS.json` (constant denominator, 12 items).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:100-130` create_book |
| R2 | GET /books lists all | ✓ implemented | `app.py:134-150` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:139-145` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:154-163` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:167-194` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:198-210` |
| R7 | SQLite storage | ✓ implemented | `app.py:40-53`, `books.db` |
| R8 | JSON + correct status codes | ✓ implemented | jsonify + 201/200/400/404 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:67-89` validate_book_data |
| R10 | GET /health | ✓ implemented | `app.py:93-96` |
| R11 | README with setup/run | ✓ implemented | `README.md` (but documents wrong port — see findings) |
| R12 | ≥3 tests that run (coverage>0) | ~ partial | 25 tests in `test_app.py` but they need a manually-started server on the wrong port; `test_coverage=0.14`, no behavior actually verified |

The implementation is complete, correct, and idiomatic Flask/SQLite. The single
gap is **test executability**: the acceptance suite is pure black-box HTTP and
never self-hosts.

## Prompt adherence (ATDD)

The tests do follow the ATDD prompt in style — external-client perspective,
Given/When/Then docstrings, atomic scenarios, domain language, per-test clean
collection (`conftest.py` autouse fixture). What the prompt's "let those tests
drive… until they pass" does **not** guarantee here is a runnable harness: the
suite passes only when a human manually starts a server on 5001, and `app.py`
binds 5000, so in the automated scoring context every test connection-errors.

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
code_quality      = 0.8333
token_efficiency  = 0.0088
test_coverage     = 0.14      # app.py essentially uncovered
defect_rate       = 1.0       # build/import ok
maintainability   = 0.8200
idiomatic         = 0.88
```

Why coverage is 0.14: `.coverage` instruments app.py, test_app.py, conftest.py.
The tests (`test_app.py:13`, `conftest.py:17`) drive the API over HTTP to
`127.0.0.1:5001`; nothing starts that server and `app.py` binds 5000, so under
`pytest --cov` every test errors on connection. Only import-time/def lines are
counted → ~14% overall, app.py ~0%.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 217 |
| Lines (test_app.py) | 395 |
| Lines (conftest.py) | 20 |
| Files (source) | 4 (app.py, test_app.py, conftest.py, README.md) |
| Dependencies | flask, requests |
| Tests total | 25 |
| Tests effective (pass under scoring) | 0 |
| Skipped tests | 0 |
| Skip ratio | 0% |
| Coverage | 14% |
| Tokens (in/out) | 67,182 / 19,954 (37 API calls) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [high] Acceptance suite never validates the app under scoring — tests need a live server that nothing starts (`test_app.py:13`, `conftest.py:17`; test_coverage=0.14).
2. [high] Port mismatch — app.py binds 5000 but tests/conftest/README target 5001 (`app.py:217` vs `test_app.py:13`).
3. [high] R12 partial — 25 tests exist but none effectively run/pass.
4. [medium] Flask `debug=True` on `0.0.0.0` (`app.py:217`) — RCE-capable debugger.
5. [medium] README run instructions inaccurate (wrong port) (`README.md:73`).

## Reproduce

```bash
cd experiment-19-hermes35b-prompts/bookshop/runs/agent=hermes-local_language=python_prompt=ATDD/rep2
cat scores.json                              # stored mechanical scores (not re-run)
grep -n "500[01]" app.py test_app.py conftest.py README.md   # port mismatch
grep -cE "def test_" test_app.py             # 25 tests
python3 -m coverage report                   # app.py ~0% covered
```
