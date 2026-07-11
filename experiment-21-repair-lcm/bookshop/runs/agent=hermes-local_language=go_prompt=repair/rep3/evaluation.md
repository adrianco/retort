# Evaluation: agent=hermes-local language=go prompt=repair · rep 3

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown, prompt=repair
- **Status:** ok — repair succeeded; the FEEDBACK.md defect (SQLite `:memory:`) is fixed
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 test funcs (13 counting subtests) passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass — `defect_rate=1.0` from scores.json (build+test succeeded)
- **Lint:** pass — `code_quality=0.956` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 2 low, 2 info)

This is a repair run. FEEDBACK.md flagged that persistence ran in `:memory:` mode.
The diff against `main_test.go.bak` and `main.go:342` confirm the fix was applied:
the server opens `books.db` and each test opens a unique file-based temp DB with
`t.Cleanup` removal. (The agent stdout's file-mutation verifier warning is a false
alarm — the on-disk files show the fixed content.)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:228 createBook`, `main.go:64 CreateBook`; `TestCreateBook_Valid` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:254 listBooks`, `main.go:103 ListBooks`; `TestListBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:107-111` author-filtered query; `TestListBooks_AuthorFilter` |
| R4 | GET /books/{id} (+404) | ✓ implemented | `main.go:267 getBook` → 404 at `main.go:281`; `TestGetBookByID_NotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:289 updateBook`, `main.go:141 UpdateBook`; `TestUpdateBook` |
| R6 | DELETE /books/{id} | ✓ implemented | `main.go:325 deleteBook`, `main.go:169 DeleteBook`; `TestDeleteBook` |
| R7 | SQLite / embedded persistence | ✓ implemented | `main.go:342 NewBookStore("books.db")` file-based (was `:memory:`) |
| R8 | JSON responses + status codes | ✓ implemented | `main.go:220 writeJSON`; 201/200/404/400/409/204 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `main.go:207-211 validateBook`; `TestCreateBook_Invalid` |
| R10 | GET /health | ✓ implemented | `main.go:351-354`; `TestHealthCheck` |
| R11 | README with setup/run | ✓ implemented | `README.md` — endpoints, setup, run instructions |
| R12 | ≥3 tests that run | ✓ implemented | 12 test funcs / 13 tests, `test_coverage=0.658` (>0) |

Note beyond spec (not a deduction): `validateBook` also requires `year` (`main.go:213-215`)
— R9 only mandates title+author, so this is over-validation (see `findings.jsonl`).

## Build & Test

Not re-run — mechanical scores were read from `scores.json` per the evaluate-run skill.

```text
scores.json
  test_coverage   = 0.658   (>0 ⇒ tests executed & passed; value is coverage fraction)
  defect_rate     = 1.0     (build + tests succeeded)
  code_quality    = 0.956
  maintainability = 0.979
  idiomatic       = 0.8
  token_efficiency= 0.017
```

```text
grep -c "^func Test" main_test.go   -> 12  (TestCreateBook_Invalid adds 3 subtests = 13)
grep t.Skip / t.Skipf               -> 0 skips
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 756 (main.go 361 + main_test.go 395) |
| Files (source) | 2 .go + README.md + go.mod/go.sum |
| Dependencies | 51 (go.sum lines) |
| Tests total | 13 (12 funcs + subtests) |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] Create over-validates — `year` required though spec (R9) only mandates title+author (`main.go:213-215`)
2. [low] 14MB compiled `book-api` binary committed into the workspace
3. [info] Persistence fix applied — SQLite now file-based (R7 defect resolved)
4. [info] Leftover `main_test.go.bak` backup file

No high or critical findings.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-21-repair-lcm/bookshop/runs/agent=hermes-local_language=go_prompt=repair/rep3
cat scores.json                                  # mechanical scores (source of build/test truth)
diff main_test.go.bak main_test.go               # confirm the :memory: -> temp-file repair
grep -n 'NewBookStore' main.go                   # main.go:342 -> books.db
grep -c '^func Test' main_test.go                # 12 test funcs
grep -rEn 't\.Skip' . --include='*.go'           # 0 skips
```
