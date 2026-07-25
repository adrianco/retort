# Evaluation: hermes-local · python · gpt-oss-20b · neutral · rep 3 (SECOND OPINION)

## Summary

- **Factors:** language=python, agent=hermes-local, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, prompt=neutral, stack=gptoss
- **Task:** REPAIR task (fix a prior attempt so all requirements are met **and tests run and pass**)
- **Status:** failed (repair goal unmet — R12: tests do not run/pass)
- **Requirements:** 11/12 implemented, 1 partial (R12), 0 missing → **requirement_coverage = 0.9167**
- **Tests:** 4 present / 0 effective (async test bodies never execute — see below)
- **Build:** pass (module imports; app logic correct per direct ASGITransport probe recorded in `summary/index.md`)
- **Lint:** n/a — code_quality=0.8333 (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (1 high, 2 low, 1 info)

## Second-opinion verdict on the prior evaluation

The first evaluation scored **requirement_coverage=0.9167** and claimed **R12 was NOT met**
("4 tests exist but all fail (0 pass) — repair goal unmet").

**CONFIRMED — the first evaluator was right.** I independently verified the tests do not run:

- **Coverage artifact (`.coverage`, coverage 7.15.2) is decisive.** Decoding `line_bits`:
  - `tests/test_api.py` executed only lines `[1,2,3,5,6,12,13,27,28,46,47]` — the imports and
    the `@pytest.mark.asyncio`/`def` header lines. **Every test body** (7-10, 14-25, 29-44,
    48-64) has **zero** coverage → no assertion ever ran.
  - `app/main.py` executed only import- and route-registration lines; **every endpoint body**
    (61-70, 74-82, 86-93, 97-109, 113-121, and the `/health` return at 126) has **zero**
    coverage → no endpoint was ever hit by a test.
- **Root cause (two independent breakages, either one fatal):** the tests are `async def`
  coroutines marked `@pytest.mark.asyncio`, but the workspace has **no async test support** —
  `grep` finds no `pytest-asyncio`, `anyio`, or `asyncio_mode` config, and there is no
  `requirements.txt`. On top of that they call httpx's **removed** `AsyncClient(app=...)`
  shortcut. So the coroutines are collected but never awaited; their bodies never execute.
- **`test_coverage=0.33` (scores.json) is import-only line coverage, not a pass rate** — exactly
  as the first evaluator stated. R12's pinned `how_to_verify` asks for tests that "exist **and
  run**"; they exist (4 ≥ 3) but do not run, and `FEEDBACK.md` explicitly required the repair to
  make them pass. R12 stays **not met**.

I could not re-run pytest to cross-check because this host's environment is incompatible
(Python 3.14 + pydantic v1 vs. the FastAPI in-tree), which raises an unrelated
`pydantic.errors.ConfigError` at import. The coverage artifact from the actual scoring run is
authoritative and settles it without a re-run.

The other 11 requirements are genuinely implemented (verified against `app/main.py` below), so
the first evaluator's overall **0.9167 is reproduced exactly**.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app/main.py:59-70` — inserts (title,author,year,isbn), returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app/main.py:72-82` |
| R3 | ?author= filter | ✓ implemented | `app/main.py:76-77` `WHERE author = ?` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app/main.py:84-93` raises 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app/main.py:95-109` (404 if absent) |
| R6 | DELETE /books/{id} | ✓ implemented | `app/main.py:111-121` (204; 404 if absent) |
| R7 | SQLite persistence | ✓ implemented | `app/main.py:4,12-32` raw `sqlite3`, `books` table |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404 across routes |
| R9 | title/author required | ✓ implemented | `app/main.py:44-45` required fields → 4xx reject (returns **422**, spec said 400 — see finding) |
| R10 | GET /health | ✓ implemented | `app/main.py:124-126` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — venv, install, uvicorn, pytest |
| R12 | ≥3 tests that run & pass | ~ partial | 4 tests in `tests/test_api.py` but **0 execute** — see verdict above |

## Build & Test

```text
# Coverage artifact from the scoring run (.coverage, coverage 7.15.2) — decoded line_bits
tests/test_api.py executed lines: [1,2,3,5,6,12,13,27,28,46,47]   # imports + def headers only
app/main.py       executed lines: [..., 59,60,72,73,84,85,95,96,111,112,124,125]  # registration only, no bodies
=> no test body ran; no endpoint body ran. test_coverage=0.33 = import-only coverage.
```

```text
# Could not re-run pytest on this host (unrelated env mismatch):
pydantic.errors.ConfigError: unable to infer type for attribute "name"   # Python 3.14 + pydantic v1 vs FastAPI
# The coverage artifact above is authoritative for the scored run.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, `app/main.py`) | 110 |
| Test lines (`tests/test_api.py`) | 60 |
| Files (excl. summary/coverage/session) | ~14 |
| Tests total | 4 |
| Tests effective (passed+failed) | 0 |
| Skip ratio | 0% (0 skip markers; all 4 silently un-run) |
| requirement_coverage | 0.9167 (11/12) |

## Findings

Top items (full list in `findings.jsonl`):

1. [high] R12 — 4 tests exist but none execute; repair goal (tests must pass) unmet.
2. [low] R9 — validation rejects with 422, spec asked for 400.
3. [low] DELETE returns 204 with a JSON body.
4. [info] Deprecated pydantic v1 idioms (`orm_mode`, `Field(example=)`).

## Reproduce

```bash
cd experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep3
# Decode the coverage artifact (authoritative — shows no test/endpoint body ran):
python3 - <<'PY'
import sqlite3
def nums(b):
    return [i*8+bit for i,byte in enumerate(b) for bit in range(8) if byte & (1<<bit)]
c=sqlite3.connect('.coverage'); names={1:'tests/test_api.py',2:'app/__init__.py',3:'app/main.py'}
for fid,_,nb in c.execute('select file_id,context_id,numbits from line_bits'):
    print(names[fid],'->',nums(nb))
PY
# Confirm no async-test support exists in the workspace:
grep -rn "asyncio_mode\|pytest_asyncio\|pytest-asyncio\|anyio" . | grep -v _hermes_session || echo "none"
```
