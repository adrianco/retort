# Evaluation: agent=hermes-0205 · language=go · model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit · prompt=neutral · stack=q8 · rep 3

## Summary

- **Factors:** language=go, agent=hermes-0205, model=mlx-community/Qwen3-Coder-30B-A3B-Instruct-8bit, prompt=neutral, stack=q8, framework=unknown (stdlib `net/http`)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`); prompt instruction **P1 partial**
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `t.Skip` grep = 0
- **Build:** pass — from `scores.json` `defect_rate=1.0` (not re-run, per skill)
- **Lint:** pass — `code_quality=0.9556` from `scores.json`
- **Coverage:** `test_coverage=0.293`
- **Architecture:** see `summary/index.md`
- **Findings:** 8 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 5 low, 1 info)

Mechanical scores were read from `scores.json` — build, tests and lint were **not** re-run:

```json
{"code_quality": 0.9556, "token_efficiency": 1.0, "test_coverage": 0.293,
 "defect_rate": 1.0, "maintainability": 0.8857, "idiomatic": 0.7}
```

`retort.db` was locked (`unable to open database file`) at evaluation time, so `scores.json` is the sole score source — which is the skill's preferred path anyway.

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 items, fixed denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:94` `createBookHandler`; INSERT at `main.go:113`; routed `main.go:286` → `booksHandler` `main.go:60` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:134` `getBooksHandler`; `SELECT … FROM books ORDER BY id`; test `main_test.go:101` `TestGetBooks` |
| R3 | GET /books supports `?author=` | ✓ implemented | `main.go:144-148` — `r.URL.Query().Get("author")` → `WHERE author LIKE ?` |
| R4 | GET /books/{id} returns one book, 404 if absent | ✓ implemented | `main.go:175` `getBookByIdHandler`; `sql.ErrNoRows` → 404 at `main.go:186-187`; routed `main.go:287` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:199` `updateBookHandler`; existence check `main.go:220-229`; UPDATE `main.go:232` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:246` `deleteBookHandler`; existence check `main.go:254-263`; DELETE `main.go:266` |
| R7 | SQLite / embedded DB persistence | ✓ implemented | `main.go:31` `sql.Open("sqlite3", "./books.db")`; `CREATE TABLE IF NOT EXISTS books` `main.go:36-43`; `github.com/mattn/go-sqlite3 v1.14.16` in `go.mod` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201 `main.go:129`, 200 default, 400 `main.go:108`, 404 `main.go:187`, 405 `main.go:67`, 500 `main.go:116`; success bodies `json.NewEncoder`. Caveat: error bodies are plain text (finding F1). |
| R9 | Validation — title and author required | ✓ implemented | `main.go:107-110` (create) and `main.go:213-216` (update); test `main_test.go:81` `TestCreateBookMissingRequiredFields` asserts 400 |
| R10 | GET /health | ✓ implemented | `main.go:53` `healthHandler` → `{"status":"healthy"}`; routed `main.go:285`; test `main_test.go:26` `TestHealthCheck` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md:1-109` — setup (`go mod tidy`), run (`go run main.go`, `PORT=` override), test command, curl examples per endpoint |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 test funcs (`main_test.go:26,42,81,101`) plus `TestMain:13`; `test_coverage=0.293 > 0` ⇒ they executed |

### Prompt factor (`prompts/neutral.md`)

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | "include tests that demonstrate the implementation meets the requirements" | ~ partial | `main_test.go:133`: *"We'll skip the ID-based tests for now to avoid URL construction issues"* — R3–R6 (`?author=`, GET/PUT/DELETE by id) have zero test evidence. This is the direct cause of the 29.3% coverage. Counted once here rather than also downgrading R3–R6, which are demonstrably implemented in source. |

### Beyond spec

- `demo.sh` — an end-to-end curl walkthrough that boots the server and exercises health/create/list/filter. Not requested; not a deduction.
- `PORT` env override (`main.go:290-296`).

## Build & Test

Not re-run (skill §2). Evidence from `scores.json`:

```text
defect_rate    = 1.0   ⇒ build + `go test` succeeded
test_coverage  = 0.293 ⇒ tests executed; 29.3% statement coverage
code_quality   = 0.9556 (lint)
```

Skip scan (skill §5):

```text
$ grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
0
```

The untested routes were **never written**, not skipped — so there is no `skipped_test` finding, only the P1 gap.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 430 (`main.go` 296 + `main_test.go` 134) |
| Lines incl. README + demo.sh | 572 |
| Files (excl. .git) | 28 |
| Dependencies | 1 direct (`github.com/mattn/go-sqlite3`) |
| Tests total | 4 (+`TestMain`) |
| Tests effective | 4 |
| Skip ratio | 0% |
| Statement coverage | 29.3% |
| Build duration | n/a — not re-run |

## Findings

Full list in `findings.jsonl`. Top 5 by severity:

1. **[medium] P1** — prompt asked for tests demonstrating the requirements; ID-based routes (R3–R6) have none (`main_test.go:133`).
2. **[medium] F1** — error responses are plain text, not JSON, in a JSON API (`main.go:107-110`, and 6 other sites).
3. **[low] F2** — `GET /books` encodes an empty collection as `null` instead of `[]` (`main.go:159`, `main.go:171`).
4. **[low] F3** — tests open and then delete the production database file (`main_test.go:15,21` + `main.go:31`).
5. **[low] F4** — `rows.Err()` never checked after the scan loop (`main.go:160-171`).

Also: **[low] F5** unescaped LIKE wildcards in the `?author=` filter; **[low] F6** unreachable duplicate method guards; **[info] F7** harness anomaly (below).

### F7 — worth flagging separately

`_agent_stdout.log` reads *"Context length exceeded (39,728 tokens). Cannot compress further."*, yet `_effective_stack.json` configures `context_length=262144` at `context_threshold=0.9` — compaction should not have been exhausted until ~236K. `.hermes_usage.json` records `completed=false, failed=true` (70 api calls) while `_meta.json` records `succeeded=true`.

The deliverable was **not** damaged: `main.go` was last written 03:18 and the abort came at 03:31, with nothing produced in between. Filed as `info` so a harness limitation does not deduct from the model's score. It is nonetheless a live instance of the set-but-not-verified class this repo warns about — the effective context window for exp-64's local cells is worth confirming before the configured 262K is trusted. (Note `provenance.json` reports `serving.omlx.sampling.max_context_window=32768`, but this repo has already recorded that that value is not the real cap, and the observed ~39.7K ceiling exceeds it — so it does not explain the abort either.)

## Reproduce

```bash
cd "experiments/adrianco/experiment-64-quant-tier-30b/rest-api-crud/runs/agent=hermes-0205_language=go_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit_prompt=neutral_stack=q8/rep3"

cat scores.json                       # mechanical scores — build/test/lint NOT re-run
cat ../../../../REQUIREMENTS.json     # pinned 12-item checklist
cat ../../../../prompts/neutral.md    # prompt factor
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # → 0
grep -n "HandleFunc\|http.Error\|sql.Open" main.go
wc -l main.go main_test.go README.md demo.sh
find . -type f -not -path "*/.git/*" | wc -l
```
