# Evaluation: agent=hermes-0205 · language=go · model=mlxlocal/Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ · prompt=neutral · stack=dwq4 · rep 4

> **Second-opinion pass.** A first evaluation scored `requirement_coverage=0.9167` (11/12), downgrading **R3** to *partial*. That downgrade is **overturned** — see [R3](#r3-second-opinion) below. Re-scored at **12/12 = 1.0**.

## Summary

- **Factors:** language=go, agent=hermes-0205, model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ, prompt=neutral, stack=dwq4, framework=unknown
- **Status:** ok — this was a **REPAIR** run (`TASK.md` opens "REPAIR TASK"; `FEEDBACK.md` reports the prior attempt failed the build/test gate). The repair succeeded.
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 total, 0 skipped (7 effective) — all passing (`defect_rate=1.0`)
- **Build:** pass — from stored `scores.json` (`defect_rate=1.0`, `test_coverage=0.507`); not re-run
- **Lint:** pass — `code_quality=0.9556` from stored `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 7 items in `findings.jsonl` (0 critical, 0 high, 4 medium, 2 low, 1 info)

## Mechanical scores (read, not re-run)

`scores.json` was present, so per the skill the build/test/lint toolchain was **not** re-executed:

| Metric | Value | Reading |
|--------|-------|---------|
| `test_coverage` | 0.507 | tests executed (> 0 ⇒ test gate passed); 50.7 % statement coverage |
| `defect_rate` | 1.0 | build + tests succeeded |
| `code_quality` | 0.9556 | lint clean |
| `maintainability` | 0.9202 | — |
| `idiomatic` | 0.58 | — |
| `token_efficiency` | 0.0028 | — |

## Requirements

Scored against the **pinned** `rest-api-crud/REQUIREMENTS.json` (12 entries, fixed denominator). `how_to_verify` from that file is the verification standard.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:72` `createBookHandler`; INSERT of all four columns at `main.go:91-92`; `main_test.go:40` `TestCreateBook` asserts 201 + echoed fields |
| R2 | GET /books lists all books | ✓ implemented | `main.go:113` `getBooksHandler`; unfiltered SELECT at `main.go:130`; `main_test.go:104` `TestGetBooks` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `main.go:120` reads `r.URL.Query().Get("author")`; `main.go:125-127` takes a `WHERE author LIKE ?` path when non-empty — see note below |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `main.go:155` `getBookHandler`; id parsed at `main.go:162-163`; `sql.ErrNoRows` → 404 at `main.go:173-174`; `main_test.go:69` `TestGetBook` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:186` `updateBookHandler`; existence check `main.go:214-223`, UPDATE `main.go:226-227`; `main_test.go:120` `TestUpdateBook` asserts the mutated fields |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:241` `deleteBookHandler`; DELETE `main.go:269-270`, 204 at `main.go:276`; `main_test.go:167` `TestDeleteBook` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `main.go:13` imports `github.com/mattn/go-sqlite3`; `main.go:31` `sql.Open("sqlite3", "./books.db")`; schema DDL `main.go:37-44`; `go.mod:5` pins v1.14.16 |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201 `main.go:108`, 200 `main.go:236`, 204 `main.go:276`, 400 `main.go:86`, 404 `main.go:174`; `Content-Type: application/json` set on every success path (`main.go:54,107,150,181,235`). Error *bodies* are text/plain — filed as `err-body-not-json` (medium), not a requirement failure, since codes and success payloads conform |
| R9 | Validation: title and author required | ✓ implemented | `main.go:85-88` (create) and `main.go:207-210` (update) reject empty title/author with 400; `main_test.go:196` `TestCreateBookWithMissingRequiredFields` asserts 400 |
| R10 | GET /health | ✓ implemented | `main.go:53` `healthHandler` → `{"status":"healthy"}` with 200; registered `main.go:286`; `main_test.go:24` `TestHealthEndpoint` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — endpoint list, Go 1.21+/SQLite3 prerequisites, `go mod tidy`, `go run main.go`, `PORT` override, `go test`, and curl examples per route |
| R12 | At least 3 unit/integration tests | ✓ implemented | 7 `func Test*` in `main_test.go`; 0 `t.Skip`/`t.Skipf` anywhere; `test_coverage=0.507 > 0` confirms they executed |

### <a id="r3-second-opinion"></a>R3 — second-opinion correction

The first evaluation marked R3 *partial*. **That is wrong on the implementation question:** the filter exists and is functional. `main.go:120` reads the `author` query parameter; when it is non-empty `main.go:127` runs

```go
rows, err = db.Query("SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?", "%"+author+"%")
```

and only otherwise falls through to the unfiltered SELECT at `main.go:130`. The pinned `how_to_verify` for R3 is *"The list route filters by author query param"* — that is satisfied at `main.go:125-131`, and the query is parameterised (no injection).

What the first pass actually observed is that **no test exercises the branch** (`main_test.go:107` requests `/books` with no query string). That is a genuine test gap and is filed as `test-gap-r3` (medium). It is not a missing implementation, and the pinned checklist scores test *quantity* separately under R12, so it does not reduce R3. Substring `LIKE` matching rather than exact equality is a widening of the filter, not an absence of one.

## Build & Test

Not re-run — stored scores used, per the skill:

```text
$ cat scores.json
{"code_quality": 0.9555555555555556, "token_efficiency": 0.00278736869211921,
 "test_coverage": 0.507, "defect_rate": 1.0, "maintainability": 0.9202279202279202,
 "idiomatic": 0.58}
```

`defect_rate=1.0` ⇒ `go build` + `go test` succeeded. `test_coverage=0.507` ⇒ tests executed; the uncovered half is the `main()` route-dispatch block (`main.go:280-317`), which tests bypass by calling handlers directly — filed as `router-untested` (medium).

Skip scan:

```text
$ grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 531 (`main.go` 317 + `main_test.go` 214) |
| Files (incl. archive metadata) | 28 |
| Direct dependencies | 2 (`mattn/go-sqlite3`, `stretchr/testify`) + 3 indirect |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0 % |
| Statement coverage | 50.7 % |
| Build duration | not re-run (stored score used) |

## Findings

All 7 in `findings.jsonl`; none reach `high`:

1. `[medium]` `test-gap-r3` — the `?author=` filter branch is implemented but never exercised by a test (`main.go:125-127` vs `main_test.go:104-118`)
2. `[medium]` `err-body-not-json` — `http.Error` makes every error body text/plain while success bodies are JSON (`main.go:80,86,165,174,261`)
3. `[medium]` `test-db-leak` — `setupTestDB` reopens the global pool without closing the previous one (`main_test.go:16-22`)
4. `[medium]` `router-untested` — the `/books/{id}` method dispatch has no coverage (`main.go:288-308`)
5. `[low]` `empty-list-null` — `GET /books` encodes `null`, not `[]`, when empty (`main.go:139,151`)
6. `[low]` `dead-method-guards` — per-handler method checks duplicated by the dispatchers
7. `[info]` `enh-extra-tests` — 7 tests against a minimum of 3

No security concern: every SQL statement is parameterised (`main.go:91,127,130,170,214,226,257,269`).

## Reproduce

```bash
cd "experiments/adrianco/experiment-68-quant-scheme-dwq/rest-api-crud/runs/agent=hermes-0205_language=go_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ_prompt=neutral_stack=dwq4/rep4"
cat scores.json                                              # stored build/test/lint scores
cat ../../../../REQUIREMENTS.json                            # pinned 12-entry checklist
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0
grep -c '^func Test' main_test.go                            # 7
sed -n '113,152p' main.go                                    # R3 ?author= filter
```
