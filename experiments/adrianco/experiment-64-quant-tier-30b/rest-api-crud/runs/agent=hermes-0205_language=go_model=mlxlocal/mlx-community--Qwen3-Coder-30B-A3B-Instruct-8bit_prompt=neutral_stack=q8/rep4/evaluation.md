# Evaluation: agent=hermes-0205 language=go model=mlxlocal/Qwen3-Coder-30B-A3B-Instruct-8bit prompt=neutral stack=q8 · rep 4

*Second-opinion re-evaluation.* A prior pass scored `requirement_coverage=0.8333`
(10/12) by marking **R3** and **R8** partial. R3 is overturned below — the
`?author=` filter is implemented in the list route exactly as `how_to_verify`
requires. R8 is confirmed partial.

## Summary

- **Factors:** language=go, agent=hermes-0205, model=mlx-community/Qwen3-Coder-30B-A3B-Instruct-8bit, prompt=neutral, stack=q8, framework=unknown
- **Status:** ok
- **Requirements:** 11/12 implemented, 1 partial (R8), 0 missing — against the pinned `rest-api-crud/REQUIREMENTS.json` (fixed denominator of 12)
- **Prompt factor:** `prompts/neutral.md` → P1 (no methodology prescribed; include tests demonstrating the requirements) — **followed** (9 test functions, no methodology imposed)
- **Tests:** 9 test functions + `TestMain`, 0 skipped (9 effective)
- **Build:** pass — from `scores.json` (`defect_rate=1.0`); not re-run, per skill step 2
- **Lint:** pass — `code_quality=0.9556` from `scores.json`
- **Architecture:** see [`summary/index.md`](summary/index.md)
- **Findings:** 9 items in [`findings.jsonl`](findings.jsonl) — 0 critical, 0 high, 3 medium, 4 low, 2 info

## Second-opinion verdict on the prior pass

| Claim | Verdict | Basis |
|----|----|----|
| **R3 partial** — `?author=` filter not exercised by a test | **Overturned → implemented** | The filter *is* implemented: `main.go:63` reads `r.URL.Query().Get("author")` and `main.go:68-69` builds `SELECT … WHERE author LIKE ?` with `"%"+author+"%"`. `REQUIREMENTS.json` R3's `how_to_verify` is *"The list route filters by author query param"* — it says nothing about tests, and R12 already carries the test requirement, so demoting R3 for a coverage gap double-counts. `test_api.sh:34` also curls `?author=Donovan`. Logged instead as a low-severity coverage finding (F4). |
| **R8 partial** — error bodies are not JSON | **Confirmed** | Every handler sets `Content-Type: application/json` (`main.go:61,97,124,159,208`), but all 21 failure paths call `http.Error`, which unconditionally overwrites that header with `text/plain; charset=utf-8` and rewrites the body as a bare string. Status codes themselves are all correct (201/200/400/404/405/500), and success bodies are proper JSON — so this is a genuine partial, not a miss. |

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:123-155` `createBook`; INSERT at `main.go:139-140`; routed at `main.go:253` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:60-93` `getBooks`; `main.go:71` unfiltered SELECT; routed at `main.go:251` |
| R3 | GET /books supports ?author= | ✓ implemented | `main.go:63` reads the query param; `main.go:68-69` `WHERE author LIKE ?` with `%…%` |
| R4 | GET /books/{id} returns one book, 404 if absent | ✓ implemented | `main.go:96-120` `getBook`; 404 at `main.go:111-112`; test `main_test.go:304` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:158-204` `updateBook`; UPDATE at `main.go:195-196`; test `main_test.go:192` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:207-240` `deleteBook`; DELETE at `main.go:232`; test `main_test.go:261` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `main.go:31` `sql.Open("sqlite3","./books.db")`; DDL `main.go:37-44`; driver `main.go:13`, `go.mod:4` |
| R8 | JSON responses with appropriate status codes | ~ partial | Success paths correct (`main.go:153` 201, `main.go:55` 200) and codes right throughout, but all error paths use `http.Error` (`main.go:76,103,112,128,134,142,165,171,177,187,198,213,225,234,256,269`), which replaces the JSON content type with `text/plain` |
| R9 | Validation: title and author required | ✓ implemented | `main.go:133-136` (create) and `main.go:176-179` (update) → 400; test `main_test.go:89` `TestCreateBookMissingFields` |
| R10 | GET /health | ✓ implemented | `main.go:53-57` `healthCheck` returns `{"status":"healthy"}` with 200; routed `main.go:248`; test `main_test.go:26` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Setup (`go mod tidy`), Running (`go run main.go`, `PORT=`), Testing (`go test -v`), plus curl examples for all 6 routes |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 9 test functions in `main_test.go` (`TestHealthCheck`, `TestCreateBook`, `TestCreateBookMissingFields`, `TestGetBooks`, `TestGetBook`, `TestUpdateBook`, `TestDeleteBook`, `TestGetNonExistentBook`, `TestDeleteNonExistentBook`), 0 skips, `test_coverage=0.592 > 0` |

| ID | Prompt instruction | Status | Evidence |
|----|----|----|----|
| P1 | No methodology prescribed; include tests demonstrating the implementation meets the requirements | ✓ implemented | `prompts/neutral.md`; 9 handler-level `httptest` tests cover health, create, validation, list, get, update, delete and two 404s |

**Enhancements beyond spec (not deductions):** `test_api.sh` — an end-to-end curl smoke script covering all 7 routes including `?author=`; `PORT` env override (`main.go:274-277`); 405 Method Not Allowed dispatch (`main.go:256,269`).

## Build & Test

Not re-run — read from `scores.json`, per skill step 2:

```text
{"code_quality": 0.9555555555555556, "token_efficiency": 0.007419737792918345,
 "test_coverage": 0.5920000000000001, "defect_rate": 1.0,
 "maintainability": 0.923076923076923, "idiomatic": 0.67}
```

`defect_rate=1.0` ⇒ build + tests succeeded. `test_coverage=0.592` here is Go
**statement coverage**, not a pass-rate gate: the uncovered statements are the
`?author=` LIKE branch, `updateBook`'s 404 path, and the invalid-id /
invalid-JSON / 500 error branches. `code_quality=0.9556` ⇒ lint clean.

Skip scan:

```text
$ grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 601 (`main.go` 280 + `main_test.go` 321) |
| Files (excl. build artifacts, harness logs) | 7 (`main.go`, `main_test.go`, `README.md`, `test_api.sh`, `go.mod`, `go.sum`, `TASK.md`) |
| Dependencies | 1 direct (`github.com/mattn/go-sqlite3 v1.14.50`) |
| Tests total | 9 (+ `TestMain`) |
| Tests effective | 9 |
| Skip ratio | 0% |
| Statement coverage | 59.2% |
| Build duration | n/a — not re-run (scores read from `scores.json`) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. `[medium]` **R8** — error responses are `text/plain`, not JSON, despite handlers setting `Content-Type: application/json` (`http.Error` overwrites it)
2. `[medium]` **F1** — `GET /books` encodes a nil slice, so an empty collection serialises as `null` rather than `[]` (`main.go:81,92`)
3. `[medium]` **F2** — tests share the production `./books.db` with no reset, so `TestGetBooks` can pass on rows other tests inserted (`main_test.go:15,21`)
4. `[low]` **F3** — `rows.Err()` unchecked after the scan loop; a driver error silently truncates the list behind a 200 (`main.go:82-90`)
5. `[low]` **F4** — the `?author=` filter has no Go test; only `test_api.sh:34` exercises it

Nothing at critical or high severity.

## Reproduce

```bash
cd experiments/adrianco/experiment-64-quant-tier-30b/rest-api-crud/runs/agent=hermes-0205_language=go_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-8bit_prompt=neutral_stack=q8/rep4

cat scores.json                       # build/test/lint scores — not re-run
cat ../../../../REQUIREMENTS.json     # pinned 12-item checklist
cat ../../../../prompts/neutral.md    # prompt factor -> P1
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
grep -cE "^func Test" main_test.go
wc -l main.go main_test.go
```
