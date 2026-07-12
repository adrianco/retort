# Evaluation: agent=hermes-local language=python prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local (model=Qwen3-Coder-Next), prompt=neutral, framework=unknown
- **Status:** **FAILED** — the archived workspace contains **no generated code**. Only `TASK.md` survives; there is no API source, no tests, no `README.md`, no `requirements.txt`. The agent's `write_file` calls were refused ("Refusing to write to sensitive system path" for the retort temp workspace under `/private/var/folders`), so nothing was persisted.
- **Requirements:** 0/12 implemented, 0 partial, 12 missing (no source to satisfy any)
- **Tests:** 0 present / 0 effective — `.coverage` instruments **0 files**
- **Build:** unverifiable — no source
- **Lint:** unverifiable — no source
- **Architecture:** no code to summarize
- **Findings:** 13 items in `findings.jsonl` (2 critical, 11 high)

> ⚠️ **`scores.json` is spurious.** It reports `test_coverage=0.96`, `defect_rate=1.0`, `code_quality=0.833`, but the workspace has zero source files and `.coverage` instrumented zero files. This run is also **absent from `retort.db`** (only replicate 1 is `completed`). The stored scores are not backed by any code and must not be read as a passing run. Per the evaluate-run test gate, a run with no executable tests fails; the high `test_coverage` number here is an artifact, not evidence.

## Requirements

All requirements are unmet because no source code was archived.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create | ✗ missing | no API source file |
| R2 | GET /books list | ✗ missing | no API source file |
| R3 | GET /books ?author= filter | ✗ missing | no API source file |
| R4 | GET /books/{id} | ✗ missing | no API source file |
| R5 | PUT /books/{id} | ✗ missing | no API source file |
| R6 | DELETE /books/{id} | ✗ missing | no API source file |
| R7 | SQLite/embedded persistence | ✗ missing | no API source file |
| R8 | JSON + correct status codes | ✗ missing | no API source file |
| R9 | Input validation (title/author) | ✗ missing | no API source file |
| R10 | GET /health | ✗ missing | no API source file |
| R11 | README.md setup/run | ✗ missing | no README.md in archive |
| R12 | ≥3 tests | ✗ missing | no test files; `.coverage` file-count=0 |

The agent's `_agent_stdout.log` *claims* it created `main.py`, `database.py`, `schemas.py`, `requirements.txt`, `README.md`, `test_main.py` and that "All 24 tests pass" — but the same log's file-mutation verifier flags the writes were refused, and none of those files exist in the archive. The claim is contradicted by the archive contents.

## Build & Test

```text
$ find . -type f \( -name '*.py' -o -name '*.md' -o -name '*.txt' \)
./TASK.md
# no source, no tests

$ python3 -c "import sqlite3; c=sqlite3.connect('.coverage'); print(len(list(c.execute('SELECT path FROM file'))))"
0   # coverage instrumented zero files
```

No build/test can be run — there is nothing to build. `scores.json` was produced by inline scoring but is unbacked (see warning above).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 0 |
| Files (excl. metadata) | 0 |
| Dependencies | n/a (no requirements.txt) |
| Tests total | 0 |
| Tests effective | 0 |
| Skip ratio | n/a |
| Build duration | n/a |
| Agent tokens (total) | 1,703,753 (in 94,709 / out 15,700 / cache-read 1,593,344) over 54 API calls |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [critical] Archive contains no generated code — all deliverables missing (writes refused to "sensitive system path").
2. [critical] `scores.json` misrepresents the run: `test_coverage=0.96` but zero code/coverage measured.
3. [high] R12 — no tests present.
4. [high] R11 — no README.md.
5. [high] R1 — POST /books endpoint absent (no source), and R2–R10 likewise.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-24-qwennext80b-cached/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep2
find . -type f \( -name '*.py' -o -name '*.md' -o -name '*.txt' \)   # only TASK.md
python3 -c "import sqlite3;print(len(list(sqlite3.connect('.coverage').execute('SELECT path FROM file'))))"  # 0
cat scores.json          # test_coverage=0.96 (spurious)
cat _agent_stdout.log    # 'Refusing to write to sensitive system path'
```
