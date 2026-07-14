# Evaluation: agent=hermes-local · language=python · prompt=ATDD · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3.6-35B-A3B), prompt=ATDD, framework=Flask
- **Status:** failed (test gate) — the app is correct, but the ATDD acceptance suite fails 16/24 tests
- **Requirements:** 11/12 implemented, 0 partial, 1 missing (R11 README)
- **Tests:** 8 passed / 16 failed / 0 skipped (24 effective) — verified by one pytest run in a temp copy
- **Build:** pass — imports cleanly; defect_rate=1.0 from scores.json
- **Lint:** pass — code_quality=0.833 from scores.json (SQLAlchemy 2.0 deprecation warnings only)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 2 high, 0 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create | ✓ implemented | `app.py:32` create_book, persists 4 fields |
| R2 | GET /books list all | ✓ implemented | `app.py:64` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:66-68` filter_by(author=...) |
| R4 | GET /books/{id} | ✓ implemented | `app.py:84` get_book, 404 at `app.py:87` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:99` update_book, partial updates |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:138` delete_book, 404 handling |
| R7 | SQLite / embedded DB | ✓ implemented | `app.py:15` sqlite:///books.db; `models.py:7` Book model |
| R8 | JSON responses + status codes | ✓ implemented | jsonify + 201/200/400/404 throughout app.py |
| R9 | Validation: title & author required | ✓ implemented | `app.py:41-44` rejects empty title/author (400) |
| R10 | GET /health | ✓ implemented | `app.py:27` returns {"status":"ok"} 200 |
| R11 | README.md setup/run docs | ✗ missing | no README.md in run_dir |
| R12 | ≥3 unit/integration tests | ✓ implemented | 24 tests in test_app.py, coverage 0.65 > 0 |

### Prompt (ATDD) conformance

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Executable acceptance tests, client-only via REST API, atomic/independent, **passing** | ~ partial | Structure is correct — tests hit HTTP only, fresh in-memory DB per test (`test_app.py:12-28`). But the suite does **not** pass (16/24 fail), and "passing the acceptance suite" is the ATDD deliverable. |

## Build & Test

```text
python -m pytest test_app.py -q   (run once in an isolated temp copy)
16 failed, 8 passed, 3 warnings in 0.82s
```

Root cause of the 16 failures (not an app defect): the tests submit request
bodies with `data=<dict>, content_type="application/json"`. Werkzeug
form-encodes a dict body, so the API receives `title=...&author=...` with a JSON
content-type; `app.py:34 request.get_json()` cannot parse it and returns
400 / None, so create/update/read-after-write assertions fail. The 8 passing
tests are the pure GET/404 cases plus the two that use `json=payload`.

The agent detected this exact issue (`_agent_stdout.log`: "use `json=payload`
instead of `data=payload`") but its follow-up write to `test_app.py` was
**refused by the sandbox** ("Refusing to write to sensitive system path"), so the
broken suite was archived as-is.

Stored mechanical scores (`scores.json`) — kept for reference:
`test_coverage=0.65` (line coverage, not pass-rate), `defect_rate=1.0`
(import/build ok), `code_quality=0.833`, `maintainability=0.866`,
`idiomatic=0.82`, `token_efficiency=0.013`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, 3 files) | 615 |
| Files (excl. caches) | 13 (4 source + artifacts) |
| Dependencies | 4 (flask, flask-sqlalchemy, pytest, requests) |
| Tests total | 24 |
| Tests effective | 24 (0 skipped) |
| Tests passing | 8 (33%) |
| Skip ratio | 0% |
| Build duration | n/a (scored inline) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [high] ATDD acceptance suite fails 16/24 — tests send form-encoded bodies (`data=dict`) instead of `json=dict`; API rejects with 400.
2. [high] Required README.md deliverable is absent (R11).
3. [low] SQLAlchemy 2.0 legacy `Query.get()` usage (app.py:86,101,140).
4. [low] Inline serialization duplicated; `models.py:to_dict()` unused.

## Reproduce

```bash
run="/Users/adriancockcroft/code/retort/experiment-18-hermes-35b-lcm/bookshop/runs/agent=hermes-local_language=python_prompt=ATDD/rep2"
tmp=$(mktemp -d); cp "$run"/app.py "$run"/models.py "$run"/test_app.py "$run"/requirements.txt "$tmp"/
cd "$tmp" && python3 -m venv .venv && . .venv/bin/activate
pip install -q flask==3.1.0 flask-sqlalchemy==3.1.1 pytest==8.3.4 requests==2.32.3
python -m pytest test_app.py -q          # 16 failed, 8 passed
grep -c "def test_" test_app.py          # 24
ls "$run"/README.md                      # absent -> R11 missing
```
