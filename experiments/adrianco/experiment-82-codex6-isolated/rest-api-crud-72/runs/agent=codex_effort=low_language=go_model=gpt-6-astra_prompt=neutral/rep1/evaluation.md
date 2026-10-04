# Evaluation: rest-api-crud-72 · agent=codex effort=low model=gpt-6-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — coverage 75.2%
- **Build:** pass — from `test_coverage=0.752` in `scores.json` (build + all tests passed; not re-run)
- **Lint:** pass — `code_quality=0.9556` in `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Checklist from the pinned `REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:80,160` `save()` INSERT → 201 + Location; `main_test.go:35` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:131` `list()` returns `[]Book`; `main_test.go:63` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `main.go:134-137` param filter; `main_test.go:72` |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `main.go:96-107` 200/404; `main_test.go:44,103` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:108-109,200` UPDATE, 404 if none; `main_test.go:48` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:110-125` 204/404; `main_test.go:53` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `main.go:15,28-47` `modernc.org/sqlite`; `main_test.go:120` persistence test |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `main.go:49-53` `writeJSON`; 201/200/204/400/404/405/413/500/503 used |
| R9 | Input validation: title and author required | ✓ implemented | `main.go:178-183` trim + reject empty → 400; `main_test.go:83` |
| R10 | GET /health health-check | ✓ implemented | `main.go:63-73` pings DB, 200/503; `main_test.go:107,117` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:5-56` run, config, API, build/test |
| R12 | At least 3 unit/integration tests | ✓ implemented | `main_test.go` 5 `Test*` functions; `test_coverage=0.752` |

No prompt-factor requirements: `prompts/neutral.md` prescribes no methodology, so the P-list is empty.

## Build & Test

Build/test/lint were **not re-run** — scores read from `scores.json` (inline gate; run not yet in `retort.db`).

```text
scores.json
test_coverage   = 0.752   -> build OK, all tests pass, 75.2% coverage
defect_rate     = 1.0     -> build + test succeeded
code_quality    = 0.9556  -> lint/quality
maintainability = 0.9430
idiomatic       = 0.68
token_efficiency= 0.0338
```

```text
grep -cE "^func Test" main_test.go  -> 5
grep t.Skip / t.Skipf               -> 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main.go, source only) | 246 |
| Lines of code (main_test.go) | 139 |
| Files (excl .git) | 13 |
| Dependencies (go.sum lines; 1 direct, rest indirect) | 41 |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings by severity (full list in `findings.jsonl`) — no requirement gaps, failures, or skips; all items are info-level:

1. [info] Hardening beyond spec — body size cap, strict JSON decoding, DB CHECK constraints (`main.go:167,169,174,37-38`)
2. [info] Tests probe SQL injection via parameterized author filter (`main_test.go:72`, `main.go:136`)
3. [info] `?author=` filter is case-sensitive exact match (acceptable; R3 unspecified)

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-72/runs/agent=codex_effort=low_language=go_model=gpt-6-astra_prompt=neutral/rep1"
cat scores.json            # authoritative build/test/lint scores (do not re-run)
cat ../../../REQUIREMENTS.json   # pinned R1–R12 checklist
grep -cE "^func Test" main_test.go
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
# Optional independent verification:
go test ./...
```
