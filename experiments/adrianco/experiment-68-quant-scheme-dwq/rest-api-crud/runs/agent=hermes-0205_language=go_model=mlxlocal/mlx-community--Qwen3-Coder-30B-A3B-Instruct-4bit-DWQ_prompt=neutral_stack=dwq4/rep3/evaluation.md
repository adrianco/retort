# Evaluation: agent=hermes-0205 · language=go · model=mlxlocal/Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ · prompt=neutral · stack=dwq4 · rep 3

## Summary

- **Factors:** language=go, agent=hermes-0205, model=`mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ`, prompt=neutral, stack=dwq4 (temp 0.6, top_p 0.95, top_k 20, rep_penalty 1.0, ctx 262144 @ threshold 0.9)
- **Task type:** REPAIR — `TASK.md` is the repair wrapper; `FEEDBACK.md` reports the prior attempt failed because the mux never routed `/books/{id}` (GET/PUT/DELETE unreachable), requirement_coverage 0.75.
- **Status:** ok — the repair succeeded. `main.go:267-301` now registers a `/books/` subtree handler that dispatches `{id}` requests by method, alongside the exact `/books` handler at `main.go:304-317`.
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list from `REQUIREMENTS.json`). Prompt instruction P1 also satisfied.
- **Tests:** 12 test functions, 0 skipped (12 effective). Suite passed — `defect_rate=1.0`.
- **Build:** pass — from `scores.json` (`defect_rate=1.0`; a Go coverage number can only exist if the package built and `go test` ran). Toolchain NOT re-run, per skill step 2.
- **Lint:** pass — `code_quality=0.9556` from `scores.json`.
- **Coverage:** `test_coverage=0.553` (Go statement coverage — tests executed and passed).
- **Architecture:** see `summary/index.md`
- **Findings:** 7 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 5 low, 1 info)

**Caveat worth recording:** the agent *session* did not end cleanly. `.hermes_usage.json`
has `"completed": false, "failed": true` after 36 API calls and `_agent_stdout.log` reads
`API call failed after 3 retries: Connection error.` The workspace was already
spec-complete and passing at that point, and `_meta.json` records `succeeded: true`,
so the scored result stands — but this cell's turn/token accounting is truncated.

## Requirements

Pinned checklist from `../../../../REQUIREMENTS.json` (used verbatim; denominator fixed at 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:125 createBookHandler` — INSERT at `main.go:147`, 201 at `main.go:162`; `main_test.go:114 TestCreateBook` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:58 getBooksHandler` (`main.go:73` SELECT all); `main_test.go:141 TestGetAllBooks` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `main.go:63,70` — `WHERE author LIKE ?`; `main_test.go:269 TestGetBooksByAuthorFilter`. Substring rather than exact match — see finding `R3-substring` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `main.go:97 getBookHandler`, 404 at `main.go:114`; routed at `main.go:285-287`; `main_test.go:188`, `main_test.go:343 TestGetNonExistentBook` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:167 updateBookHandler` — UPDATE at `main.go:209`, 404 at `main.go:201`; routed at `main.go:288-290`; `main_test.go:221`, `main_test.go:353` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:221 deleteBookHandler` — DELETE at `main.go:251`, 204 at `main.go:257`; routed at `main.go:291-293`; `main_test.go:246`, `main_test.go:376` |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:11` imports `github.com/mattn/go-sqlite3`; `main.go:29` `sql.Open("sqlite3","./books.db")`; DDL at `main.go:35-42`; `go.mod:5` pins v1.14.50 |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201 `main.go:162`, 200 default, 204 `main.go:257`, 400 `main.go:142`, 404 `main.go:114/201/243`, 500 `main.go:77`. Success bodies are JSON; error bodies are text/plain — see finding `R8-error-json` |
| R9 | Validation: title and author required | ✓ implemented | `main.go:141-144` (create) and `main.go:191-194` (update) return 400; `main_test.go:319 TestCreateBookValidation` asserts 400 |
| R10 | GET /health | ✓ implemented | `main.go:51 healthHandler` → `{"status":"healthy"}`, registered `main.go:266`; `main_test.go:94 TestHealthCheck` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Setup (`go mod tidy`), Run (`go run main.go`), PORT override, per-endpoint examples, `go test -v` |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `main_test.go` — 12 `func Test*`, 0 skips; `test_coverage=0.553 > 0` |

### Prompt-factor instructions (`prompts/neutral.md`)

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | No methodology prescribed; include tests demonstrating the implementation meets the requirements | ✓ implemented | 12 tests covering every CRUD route, the author filter, health, validation, and all three 404 paths (`main_test.go:94-384`) |

### Repair-specific check (`FEEDBACK.md`)

| Prior defect | Fixed? | Evidence |
|----|----|----|
| GET /books/{id} unreachable — mux never routes it | ✓ | `main.go:267` registers the `/books/` subtree; `main.go:285-287` dispatches GET |
| PUT /books/{id} unreachable — same defect | ✓ | `main.go:288-290` |
| DELETE /books/{id} unreachable — same defect | ✓ | `main.go:291-293` |

Both `/books` (exact, `main.go:304`) and `/books/` (subtree, `main.go:267`) are
registered, so Go's ServeMux does not 301-redirect `/books` → `/books/`, and
`/books/{id}` lands on the subtree handler.

**Empirically verified** the same way the prior attempt's defect was — `main.go`,
`go.mod`, `go.sum` were copied to a scratchpad (run_dir untouched), built, and probed
live on port 8791:

```text
health:    {"status":"healthy"}                                              [200]
create:    {"id":1,"title":"T","author":"A","year":2020,"isbn":"x"}          [201]
list:      [{"id":1,"title":"T",...}]                                        [200]
filter:    GET /books?author=A -> [{"id":1,...}]                             [200]
getbyid:   GET /books/1 -> {"id":1,"title":"T",...}                          [200]   <- was 404 before
put:       PUT /books/1 -> {"id":1,"title":"T2","year":2021,...}             [200]   <- was 404 before
delete:    DELETE /books/1 -> (empty)                                        [204]   <- was 404 before
validation:POST /books {"title":"","author":""} -> text "Title and author..." [400]
missing:   GET /books/999 -> text "Book not found"                           [404]
emptylist: GET /books -> null                                                [200]
```

All three previously-unreachable routes now answer correctly. The repair is
correct — but no test drives the mux, so a regression would not be caught
(finding `test-gap-mux`).

## Build & Test

Not re-run — mechanical scores were read from the archive, per skill step 2.

```text
$ cat scores.json
{"code_quality": 0.9555555555555556, "token_efficiency": 1.0,
 "test_coverage": 0.5529999999999999, "defect_rate": 1.0,
 "maintainability": 0.8974358974358975, "idiomatic": 0.7}
```

`defect_rate=1.0` ⇒ build + tests succeeded. `test_coverage=0.553` is Go statement
coverage, so the package compiled and the suite ran to completion.

```text
$ grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
0
$ grep -cE "^func Test" main_test.go
12
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 722 (`main.go` 326 + `main_test.go` 396) |
| Files (workspace, excl. `summary/`, `_judge/`) | 17 |
| Dependencies | 1 direct (`github.com/mattn/go-sqlite3` v1.14.50) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Statement coverage | 55.3% |
| code_quality | 0.956 |
| maintainability | 0.897 |
| idiomatic | 0.700 |
| token_efficiency | 1.000 |
| Agent API calls | 36 (session ended on connection error) |

## Findings

All 7 in `findings.jsonl`; top 5 by severity:

1. `[medium]` **test-gap-mux** — the repaired mux routing is exercised by no test; every test calls handler funcs directly (`main_test.go:48,79,253`), so the defect `FEEDBACK.md` asked to fix could regress silently.
2. `[low]` **R3-substring** — `?author=` is a `LIKE %…%` substring (and case-insensitive) match, not an author equality filter (`main.go:70`).
3. `[low]` **R8-error-json** — `http.Error()` overwrites the JSON Content-Type, so 400/404/500 bodies are text/plain (`main.go:104,114,142,201,243`).
4. `[low]` **empty-list-null** — an empty collection serializes as `null`, not `[]` (`main.go:82,93`).
5. `[low]` **shared-db-file** — tests and the server share `./books.db`, so a stale file makes `TestGetBooksByAuthorFilter`'s exact-count assertion flaky (`main.go:29`, `main_test.go:388,290`).

Plus `[low]` **rows-err-unchecked** (`main.go:83-91`) and `[info]` **agent-session-failed**.

## Reproduce

```bash
cd experiments/adrianco/experiment-68-quant-scheme-dwq/rest-api-crud/runs/agent=hermes-0205_language=go_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ_prompt=neutral_stack=dwq4/rep3

cat scores.json                                    # mechanical scores (build/test/lint) — not re-run
cat ../../../../REQUIREMENTS.json                   # pinned 12-requirement checklist
cat FEEDBACK.md                                     # what the prior attempt got wrong
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
grep -cE "^func Test" main_test.go
sed -n '260,320p' main.go                           # the repaired mux registration

# runtime check of the repaired routes (copy out first — never build in run_dir)
cp main.go go.mod go.sum "$SCRATCH/muxcheck/" && cd "$SCRATCH/muxcheck"
go build -o bookapi main.go && PORT=8791 ./bookapi &
curl -s -w ' [%{http_code}]' http://localhost:8791/books/1
lsof -ti:8791 | xargs kill
```
