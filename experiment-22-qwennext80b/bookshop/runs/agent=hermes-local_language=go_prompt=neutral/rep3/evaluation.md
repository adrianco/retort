# Evaluation: agent=hermes-local language=go prompt=neutral · rep 3

## Summary

- **Factors:** language=go, agent=hermes-local (model=Qwen3-Coder-Next), framework=unknown, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 9 pass / 0 fail / 0 skipped (9 effective; 10 `Test*` funcs incl. `TestMain`)
- **Build:** pass — from `defect_rate=1.0`, `test_coverage=0.643` in scores.json
- **Lint:** pass — `code_quality=1.0` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.go:createBook` (170); `TestCreateBook` |
| R2 | GET /books lists all books | ✓ implemented | `server.go:listBooks` (149); `TestListBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `server.go:153-156`; `TestListBooks` (256) |
| R4 | GET /books/{id} single book | ✓ implemented | `server.go:getBook` (227), 404 handled; `TestGetBook` |
| R5 | PUT /books/{id} update | ✓ implemented | `server.go:updateBook` (245); `TestUpdateBook` |
| R6 | DELETE /books/{id} delete | ✓ implemented | `server.go:deleteBook` (323); `TestDeleteBook` |
| R7 | Data stored in SQLite | ✓ implemented | `server.go:InitDB` gorm sqlite (67); `main.go` `InitDB("books.db")` |
| R8 | JSON responses + status codes | ✓ implemented | JSON encoders throughout; 200/201/204/400/404/405/409/500 |
| R9 | Validation: title & author required | ✓ implemented | `server.go:180-190` (also year/isbn); `TestCreateBook` (94,99) |
| R10 | GET /health | ✓ implemented | `server.go:handleHealth` (101); `TestHealthCheck` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — install, `go run .`, endpoints, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | 9 tests pass; `test_coverage=0.643` (>0) |

No prompt-factor requirements (`prompt=neutral` adds no extra checkable instructions).

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
{"code_quality": 1.0, "token_efficiency": 0.0078, "test_coverage": 0.643,
 "defect_rate": 1.0, "maintainability": 0.632, "idiomatic": 0.52}
```

`defect_rate=1.0` and `test_coverage=0.643` (>0, coverage 64.3%) ⇒ build succeeded and all tests passed. Agent stdout log confirms: "All 9 tests pass". No skipped/disabled tests (`grep t.Skip` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (go, source+test) | 724 |
| Files (excl. .git) | 15 (incl. compiled `book-api` binary, `books.db` absent) |
| Dependencies (go.sum lines) | 21 |
| Tests total | 9 (+ TestMain) |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build | pass |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] Test builds path via `string(rune('0'+bookID))` — only valid for IDs 1-9 (`server_test.go:137`)
2. [low] Year required (`year>0`) beyond spec, which mandates only title/author (`server.go:192`)
3. [info] Vestigial gin-style `binding:"required"` tags unused under net/http (`server.go:28`)
4. [info] Uses Go 1.22 `{id}` route but parses id via `TrimPrefix`+`Atoi` not `r.PathValue` (`server.go:127`)
5. [info] ISBN uniqueness enforced with 409 Conflict — enhancement beyond spec (`server.go:211`)

## Reproduce

```bash
cd experiment-22-qwennext80b/bookshop/runs/agent=hermes-local_language=go_prompt=neutral/rep3
cat scores.json                       # stored mechanical scores (build/test/lint)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
wc -l main.go server.go server_test.go                       # LOC
go test -v                            # optional re-verify (build + 9 tests)
```
