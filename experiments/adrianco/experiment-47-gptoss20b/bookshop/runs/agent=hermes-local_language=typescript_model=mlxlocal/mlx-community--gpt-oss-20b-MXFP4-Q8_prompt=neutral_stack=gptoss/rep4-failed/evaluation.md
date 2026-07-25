# Evaluation: typescript · gpt-oss-20b · rep 4 (SECOND OPINION)

## Summary

- **Factors:** language=typescript, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok — 11/12 requirements implemented
- **Requirements:** 11/12 implemented, 0 partial, 1 missing (R11 README.md)
- **Tests:** 5 tests, 0 skipped (test_coverage=0.8793 from scores.json ⇒ build + tests ran and passed)
- **Build:** pass — from scores.json (defect_rate=1.0, test_coverage=0.8793)
- **Lint:** code_quality=0.7333 from scores.json
- **Architecture:** Express + better-sqlite3, file-backed SQLite at `data/books.db`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 1 high)

## Second-opinion result

The first pass scored requirement_coverage=0.9167 (11/12) and recorded no specific
requirement findings. Re-checking the full checklist against the source confirms the
score: the single missing requirement is **R11 (README.md)**, and it is genuinely
absent — `find . -iname 'readme*'` returns nothing across the whole tree. No first-pass
claim was found to be wrong (there were no specific claims to overturn), and no
falsely-missing requirement was discovered. Score is **confirmed at 11/12 = 0.9167**.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `src/server.ts:14-23` INSERT + 201 |
| R2 | GET /books lists all | ✓ implemented | `src/server.ts:33-36` SELECT * |
| R3 | GET /books ?author= filter | ✓ implemented | `src/server.ts:29-32` WHERE author = ? |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `src/server.ts:41-49` 404 branch |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/server.ts:52-65` UPDATE + 404 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/server.ts:68-76` DELETE + 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/database.ts:1,8` better-sqlite3, file `data/books.db` |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/404/400/204 throughout `server.ts` |
| R9 | Validation: title & author required | ✓ implemented | `src/server.ts:16-18,55-57` 400 on missing |
| R10 | GET /health | ✓ implemented | `src/server.ts:9-11` returns `{status:'ok'}` |
| R11 | README.md with setup/run instructions | ✗ missing | no README file anywhere in tree |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `tests/api.test.ts` — 5 tests, 0 skips, test_coverage=0.8793 |

## Build & Test

Scores read from `scores.json` (not re-run):

```text
test_coverage=0.8793   -> build + tests executed and passed
defect_rate=1.0        -> build+test succeeded
code_quality=0.7333
maintainability=0.6167
idiomatic=0.38
```

5 tests in `tests/api.test.ts` (health, create+get, list+filter, update, delete); 0 skipped.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 162 (src 103 + tests 59) |
| Files (source) | 4 (.ts) |
| Dependencies | 13 (3 runtime + 10 dev) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |

## Findings

1. [high] R11 — No README.md with setup and run instructions (no readme file in tree)

## Reproduce

```bash
cd runs/agent=hermes-local_language=typescript_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep4
find . -iname 'readme*' -not -path '*/node_modules/*'   # empty -> R11 missing
grep -cE '^\s*(test|it)\(' tests/api.test.ts            # 5
cat scores.json                                          # test_coverage=0.8793
```
