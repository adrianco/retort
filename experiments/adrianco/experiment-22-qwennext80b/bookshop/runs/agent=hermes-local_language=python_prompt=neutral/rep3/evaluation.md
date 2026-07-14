# Evaluation: agent=hermes-local_language=python_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local (model=Qwen3-Coder-Next), framework=unknown, prompt=neutral
- **Status:** failed — deliverables were written to the user's home directory, not the run workspace; the archived run contains no source, README, or tests. The service that *was* produced is functional only under test (all CRUD endpoints 500 at runtime).
- **Requirements:** 5/12 implemented, 7 partial, 0 missing (partials all stem from one runtime DI defect)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — per stored `scores.json` `test_coverage=0.97`, but only because tests override the broken `get_db` dependency
- **Build:** pass (import/collection) — from `scores.json` `defect_rate=1.0`; NOT reproducible from this archive (no source present)
- **Lint:** derived — `code_quality=0.7889` from `scores.json`
- **Architecture:** run-summary not applicable — no source in workspace (produced files live outside the archive)
- **Findings:** 5 items in `findings.jsonl` (1 critical, 2 high, 1 medium, 1 low)

## Requirements

Pinned checklist from `../../../REQUIREMENTS.json` (task `rest-api-crud`, 12 requirements). Code assessed as the agent produced it (leaked to `/Users/adriancockcroft/`). "partial" = route/logic present and passes tests, but returns 500 in the shipped app due to the `get_db` DI defect (F3).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ~ partial | `main.py` `create_book` (201) — 500 at runtime (F3) |
| R2 | GET /books lists books | ~ partial | `main.py` `list_books` — 500 at runtime (F3) |
| R3 | GET /books ?author= filter | ~ partial | `list_books` filters `Book.author`; tested — 500 at runtime (F3) |
| R4 | GET /books/{id} (404 if absent) | ~ partial | `get_book` raises 404; tested — 500 at runtime (F3) |
| R5 | PUT /books/{id} updates | ~ partial | `update_book` (exclude_unset) — 500 at runtime (F3) |
| R6 | DELETE /books/{id} | ~ partial | `delete_book` (204) — 500 at runtime (F3) |
| R7 | Data stored in SQLite | ✓ implemented | `sqlite:///./books.db` via SQLAlchemy ORM `Book` model |
| R8 | JSON responses + status codes | ~ partial | Codes 201/200/404/422/204 declared — endpoints 500 at runtime (F3) |
| R9 | Validation: title & author required | ✓ implemented | Pydantic `BookCreate` `min_length=1`; `test_validation_errors` (422) |
| R10 | GET /health | ✓ implemented | `health_check` returns `{"status":"healthy"}`; works at runtime (verified 200) |
| R11 | README with setup/run | ✓ implemented | README (in home dir) documents install + uvicorn run — but NOT delivered to workspace (F2) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 5 tests in `test_api.py`; `test_coverage=0.97` |

## Build & Test

Not re-run — stored scores used (per skill). Source is absent from the workspace, so the archive itself is not buildable.

```text
scores.json (authoritative — scored inline, no retort.db row present):
  test_coverage=0.97   defect_rate=1.0   code_quality=0.7889
  maintainability=0.9835   idiomatic=0.83   token_efficiency=0.0053
```

Runtime verification of the produced `main.py` (TestClient without dependency overrides):

```text
GET  /health  -> 200  {"status":"healthy","database":"connected"}
POST /books   -> 500  (AttributeError: '_GeneratorContextManager' object has no attribute 'throw')
GET  /books   -> 500
```

`test_api.py` passes because it injects `app.dependency_overrides[get_db] = override_get_db` (a correct plain generator), bypassing the buggy production `get_db`.

## Metrics

Measured on the produced source (in `/Users/adriancockcroft/`; the workspace has none).

| Metric | Value |
|--------|-------|
| Lines of code (main.py) | 173 |
| Lines of code (test_api.py) | 202 |
| Files (source, in workspace) | 0 |
| Dependencies (requirements.txt) | 3 (fastapi, uvicorn, sqlalchemy) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] F1 — Agent wrote all deliverables into the user's home directory (`~/main.py`, `~/test_api.py`, `~/README.md`, `~/requirements.txt`), outside the sandbox.
2. [high] F2 — Workspace archive contains no source/README/tests; run is not reproducible from the archive and stored scores reflect out-of-workspace files.
3. [high] F3 — All CRUD endpoints 500 at runtime: `get_db` is decorated `@contextmanager` yet used as a `Depends`; tests mask it via `dependency_overrides`.
4. [medium] F4 — `requirements.txt` omits `pytest` and `httpx`; tests can't run from a clean env per the README.
5. [low] F5 — Duplicate/mid-file imports in `main.py`.

## Reproduce

```bash
run_dir=/Users/adriancockcroft/code/retort/experiment-22-qwennext80b/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep3
find "$run_dir" -type f            # only logs/metadata — no deliverables
cat "$run_dir/scores.json"         # stored mechanical scores
cat "$run_dir/_agent_stdout.log"   # agent reports writing to /Users/adriancockcroft/
ls -la /Users/adriancockcroft/main.py /Users/adriancockcroft/test_api.py   # leaked deliverables

# Runtime DI defect (F3): copy produced main.py to a scratch dir and, without overrides:
python3 -c "from fastapi.testclient import TestClient; import main; c=TestClient(main.app, raise_server_exceptions=False); print(c.get('/health').status_code, c.post('/books', json={'title':'t','author':'a'}).status_code)"
# -> 200 500
```
