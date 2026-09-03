# Evaluation: agent=hermes-0205_language=go_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit_prompt=neutral_stack=q8 · rep 5

## Summary

- **Factors:** language=go, agent=hermes-0205, model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit, prompt=neutral, stack=q8, framework=unknown
- **Status:** ok (`_meta.json` `succeeded: true`)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 6 test functions, 0 skipped (6 effective); `defect_rate=1.0` ⇒ build + `go test` passed; statement `test_coverage=0.426`
- **Build:** pass — from stored `scores.json` (`defect_rate=1.0`), not re-run
- **Lint:** pass — `code_quality=0.9556` from stored `scores.json`, not re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 7 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 5 low, 2 info)

Scores read from `{run_dir}/scores.json` per the skill's "do not re-run the toolchain" rule:
`test_coverage=0.426`, `code_quality=0.9556`, `defect_rate=1.0`, `maintainability=0.8994`,
`idiomatic=0.58`, `token_efficiency=0.00103`.

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (12 entries, fixed denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:56 createBookHandler` — decodes all four fields, `INSERT INTO books` at `main.go:78`, returns 201 with the new id |
| R2 | GET /books lists all books | ✓ implemented | `main.go:95 getBooksHandler` — `SELECT id,title,author,year,isbn FROM books` (`main.go:112`), JSON-encoded at `main.go:133` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `main.go:105-110` — `r.URL.Query().Get("author")` drives `WHERE author LIKE ?` (substring match; see finding `like-filter-1`) |
| R4 | GET /books/{id} returns one book, 404 if absent | ✓ implemented | `main.go:136 getBookHandler`; `sql.ErrNoRows` → `404` at `main.go:161-162` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:170 updateBookHandler` — existence check `main.go:210`, `UPDATE books SET ...` `main.go:219` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:230 deleteBookHandler` — `DELETE FROM books WHERE id = ?` `main.go:267`, `204` at `main.go:274` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `main.go:30` `sql.Open("sqlite3", "./books.db")` with `mattn/go-sqlite3` (`go.mod:5`); schema created at `main.go:34-41` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201 `main.go:90`, 200 (default) `main.go:132`, 204 `main.go:274`, 400 `main.go:67,73`, 404 `main.go:161`, 405 `main.go:58`, 500 `main.go:80`. Success bodies set `application/json`; error bodies are plain text — see finding `json-errors-1` |
| R9 | Validation: title and author required | ✓ implemented | `main.go:72-75` (create) and `main.go:203-206` (update) → 400; asserted by `main_test.go:55 TestCreateBookMissingFields` |
| R10 | GET /health health check | ✓ implemented | `main.go:49 healthHandler` → `{"status":"healthy"}`, registered `main.go:288`; asserted by `main_test.go:15 TestHealthCheck` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Requirements / Setup (`go mod tidy`) / Build (`go build -o book-api main.go`) / Run / per-endpoint curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `main_test.go` — 6 `func Test*`, 0 `t.Skip`; `defect_rate=1.0` and `test_coverage=0.426` confirm they executed and passed |

No enhancements beyond spec were found; the implementation is scoped tightly to TASK.md.
No `prompt`-factor requirements apply — `prompt=neutral` carries no additional checkable instructions beyond the task spec.

## Build & Test

Not re-run (per skill step 2). Stored results:

```text
scores.json
{"code_quality": 0.9555555555555556, "token_efficiency": 0.0010320314088651764,
 "test_coverage": 0.426, "defect_rate": 1.0, "maintainability": 0.8993589743589743,
 "idiomatic": 0.58}
```

```text
defect_rate = 1.0   ⇒ go build + go test succeeded
test_coverage = 0.426 ⇒ 42.6% statement coverage (list/filter handler untested)
grep -cE "t\.Skip\(|t\.Skipf\(" *.go  ⇒ 0
grep -c "^func Test" main_test.go     ⇒ 6
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 512 (main.go 319 + main_test.go 193) |
| Files (excluding harness logs/.git) | 6 tracked project files (main.go, main_test.go, go.mod, go.sum, README.md, TASK.md) |
| Dependencies | 2 direct (`mattn/go-sqlite3`, `stretchr/testify`), 3 indirect |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Statement coverage | 42.6% |
| Build duration | not measured (build not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl` — 7 items, none above `low`):

1. [low] Tests run against the production on-disk `./books.db` with no isolation or cleanup (`main.go:30`, `main_test.go:30,58,78,117,167`)
2. [low] Repeated `initDB()` reassigns the global `*sql.DB` without closing it — 4 leaked pools per test binary (`main.go:28-32`)
3. [low] `GET /books` encodes `null` instead of `[]` when empty (`main.go:122,133`)
4. [low] Error responses are `text/plain` via `http.Error`, not JSON (`main.go:67,73,158,198,204`)
5. [low] List-all and `?author=` filter are implemented but never exercised by a test (`main.go:95-134`) — the bulk of the 57% uncovered statements

Also [info]: unanchored substring `LIKE` author match (`main.go:109-110`); `{id}` parsing duplicated across three handlers (`main.go:144-155,182-192,242-252`).

## Reproduce

```bash
cd experiments/adrianco/experiment-64-quant-tier-30b/rest-api-crud/runs/agent=hermes-0205_language=go_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit_prompt=neutral_stack=q8/rep5
cat scores.json                                    # stored build/test/lint scores — not re-run
cat ../../../../REQUIREMENTS.json                  # pinned 12-requirement checklist
grep -c "^func Test" main_test.go                  # 6
grep -rEc "t\.Skip\(|t\.Skipf\(" main.go main_test.go   # 0
wc -l main.go main_test.go                         # 319 / 193
grep -cE '^\s+github|^\s+gopkg' go.mod             # 5 (2 direct + 3 indirect)
```
