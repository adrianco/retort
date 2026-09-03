# Evaluation: agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit_prompt=neutral_stack=q4 · rep 5

> **Second-opinion re-check.** A prior evaluation claimed R1/R4/R5/R6 were not met.
> Each claim was independently re-verified against the source before being accepted —
> see [Second-opinion verdict](#second-opinion-verdict). All four claims hold.

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit, prompt=neutral, stack=q4
- **Status:** failed — this is a REPAIR run (`_second_try=1.0`, retort.db run 11) that repaired nothing; all five defects listed in `FEEDBACK.md` are still present verbatim
- **Requirements:** 3/12 implemented, 8 partial, 1 missing → `requirement_coverage = 0.25`
- **Prompt factor:** P1 (`prompts/neutral.md`) not followed
- **Tests:** 2 passed / 8 failed / 0 skipped (10 effective) — and the 2 that pass contain no `assert` statements
- **Build:** pass (import-clean) — `defect_rate=1.0` from `scores.json`
- **Lint:** pass — `code_quality=0.8333` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 18 items in `findings.jsonl` (3 critical, 10 high, 2 medium, 3 low)

## Second-opinion verdict

The first evaluator's four "not met" claims were re-checked by grepping every route
declaration in the workspace, not by re-reading `main.py` alone:

```text
$ grep -rn -E "@app\.|@router\.|FastAPI|Flask|add_api_route|include_router|APIRouter" --include="*.py" .
main.py:1:from fastapi import FastAPI
main.py:4:app = FastAPI()
main.py:22:@app.get("/health")
main.py:26:@app.get("/books")
```

Those four lines are the **complete** set of routing constructs in the run. There is no
second app module, no router, no `include_router`, no `add_api_route`, and `book_api.py`
is a plain function module with no FastAPI import (`book_api.py:1-3` imports only
`sqlite3` and `typing`).

| Claim | Verdict | What I checked |
|----|----|----|
| R1 POST /books not exposed | **Confirmed** | Zero `@app.post` in the workspace. `book_api.py:24 create_book()` is complete and correct but unrouted; `main.py:1-2` imports only `fastapi` and `sqlite3`. |
| R4 GET /books/{id} not exposed | **Confirmed** | No path-parameter route exists at all. `book_api.py:57 get_book_by_id()` is unrouted, so the spec's 404 path cannot exist. |
| R5 PUT /books/{id} not exposed | **Confirmed** | Zero `@app.put` in the workspace. `book_api.py:70-112 update_book()` is unrouted. |
| R6 DELETE /books/{id} not exposed | **Confirmed** | Zero `@app.delete` in the workspace. `book_api.py:114-131 delete_book()` is unrouted. |

One refinement to the first evaluation's *wording*, not its score: because
`book_api.py` contains a full, working implementation of each of these four operations,
they are classified here as **partial** (the logic exists, the HTTP surface does not)
rather than **missing**. Partial does not count toward `requirement_coverage`, so the
score is unchanged at **0.25**, and it arrives at the same 3 implemented requirements
(R7, R10, R11).

A defect the first evaluation surfaced only in passing is promoted to critical here:
`main.py:7 init_db()` is **never called** (the only call site is `book_api.py:143`, to
`book_api`'s own copy), and no `books.db` exists in the archive — so even the one
non-trivial route that *does* exist, `GET /books`, raises
`sqlite3.OperationalError: no such table: books` on a fresh workspace.

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 entries), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ~ partial | `book_api.py:24 create_book` complete but unrouted; no `@app.post` anywhere |
| R2 | GET /books lists all books | ~ partial | `main.py:26` route exists, but `main.py:7 init_db()` never called and no `books.db` → 500; returns raw tuples (`main.py:31-33`) |
| R3 | GET /books ?author= filter | ~ partial | `main.py:27 get_books()` takes no params, `main.py:30` unconditional SELECT; filter lives unrouted at `book_api.py:42-55` |
| R4 | GET /books/{id} | ~ partial | `book_api.py:57 get_book_by_id` unrouted; no path-param route in workspace |
| R5 | PUT /books/{id} | ~ partial | `book_api.py:70 update_book` unrouted; no `@app.put` |
| R6 | DELETE /books/{id} | ~ partial | `book_api.py:114 delete_book` unrouted; no `@app.delete` |
| R7 | SQLite persistence | ✓ implemented | `main.py:8` / `book_api.py:10` `sqlite3.connect('books.db')`, CREATE TABLE at `main.py:10-18` |
| R8 | JSON + appropriate status codes | ~ partial | Only implicit 200s; zero `HTTPException`/`status_code` in app code; `book_api.py:40` raises bare `Exception` (→500, not 400) |
| R9 | Validation: title + author required | ✗ missing | No `BaseModel`/`pydantic` anywhere; no POST route to validate against |
| R10 | GET /health | ✓ implemented | `main.py:22-24` returns `{"status": "healthy"}` |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` has `pip install fastapi uvicorn` and `uvicorn main:app …` (its endpoint list is inaccurate — see `doc-inaccurate`) |
| R12 | ≥3 unit/integration tests | ~ partial | 10 test functions exist and executed (`test_coverage=0.25 > 0`), but 8 fail and the 2 passing ones contain no `assert` |

**Prompt factor** (`stack.json` has `prompt=neutral` → `prompts/neutral.md`):

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | "include tests that demonstrate the implementation meets the requirements" | ~ partial | The requirement-facing tests (`test_book_api.py`) all fail; the passing tests never touch `main.py` or `book_api.py` (0 covered lines for both in `.coverage`) |

## Build & Test

Per the skill, build/test/lint were **not re-run** — the stored scores were read from
`scores.json` (which matches retort.db run 11 exactly):

```text
$ cat scores.json
{"code_quality": 0.8333333333333334, "token_efficiency": 0.021993200882410132,
 "test_coverage": 0.25, "defect_rate": 1.0, "maintainability": 0.8508905798426268,
 "idiomatic": 0.48}
```

`test_coverage=0.25` means tests executed but did not all pass. The per-test outcome was
reconstructed from the archived `.coverage` line data rather than by re-running pytest:

```text
covered lines, test_book_api.py:
  [1-7, 10, 13, 15, 17,18, 22,23,24,25,26,27, 36,37, 44,45,46,47,48,49,
   63,64,65,66,67,68, 87,88,89,90,91,92, 105,106,107,108,109,110, 124,125]

In every one of the 8 tests the line issuing the first HTTP request is covered and the
assert on the following line (19, 29, 38, 51, 70, 94, 112, 126) is NOT — each test raised
before asserting.  book_api.py: 0 covered lines.  main.py: 0 covered lines.

test_db.py     [3,4,7,9,10,13,24,25,27,30,31,33,34,37,38,40]      -> ran to completion
test_simple.py [2,3,6,9,12,13,14,25,26,27,31,32,34,37,38,40,41,42,44,47,48,50] -> ran to completion
```

So: **2 passed, 8 failed, 0 skipped.** The stored `test_coverage=0.25` is whole-directory
line coverage carried entirely by the test files; **application coverage is 0%**.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, 6 .py files) | 433 |
| Application LOC (`main.py` + `book_api.py`) | 215 |
| Files (excl. `.git`, `__pycache__`) | 27 |
| Dependencies | 2 declared in README (`fastapi`, `uvicorn`); no requirements.txt / pyproject.toml |
| Tests total | 10 |
| Tests effective (passed + failed) | 10 |
| Skip ratio | 0% |
| Turns / duration / tokens | 12 turns · 41.5 s · 298,274 tokens (retort.db run 11) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. **[critical] repair-noop** — Repair run changed nothing; all five `FEEDBACK.md` defects still present (only 2 route decorators in the whole workspace, `_second_try=1.0`).
2. **[critical] test-fail-all** — All 8 tests in `test_book_api.py` fail; no HTTP request ever completes (`.coverage`: request lines covered, assert lines not).
3. **[critical] R2** — `GET /books` exists but `main.py:7 init_db()` is never called and no `books.db` ships → 500 on a fresh workspace.
4. **[high] R9** — No input validation anywhere; no `BaseModel`, no 400 path.
5. **[high] tests-no-assert** — The only 2 passing tests (`test_db.py:7`, `test_simple.py:6`) contain zero `assert` statements and pass unconditionally.

## Reproduce

```bash
cd "experiments/adrianco/experiment-64-quant-tier-30b/rest-api-crud/runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit_prompt=neutral_stack=q4/rep5"

# route inventory — the second-opinion check
grep -rn -E "@app\.|@router\.|FastAPI|Flask|add_api_route|include_router|APIRouter" --include="*.py" .
grep -rn -E "HTTPException|status_code|BaseModel|pydantic|on_event|lifespan|init_db" --include="*.py" .
ls *.db 2>/dev/null || echo "no books.db in archive"

# stored scores (build/test/lint NOT re-run)
cat scores.json

# per-test outcome from the archived coverage db
cp .coverage /tmp/cov.db
python3 - <<'PY'
import sqlite3
def nums(b):
    return [i*8+bit for i,byte in enumerate(b) for bit in range(8) if byte & (1<<bit)]
c = sqlite3.connect('/tmp/cov.db')
for path, nb in c.execute('select f.path, l.numbits from line_bits l join file f on f.id=l.file_id'):
    print(path.split('/')[-1], nums(nb))
PY
```
