# Evaluation: agent=qwen3-coder-local language=typescript prompt=neutral · rep 2

## Summary

- **Factors:** language=typescript, agent=qwen3-coder-local, framework=unknown, prompt=neutral
- **Status:** ok (functional, tests pass) — with one factor-conformance defect: delivered JavaScript, not TypeScript
- **Requirements:** 11/12 implemented, 1 partial (R7), 0 missing — coverage per pinned `REQUIREMENTS.json`
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective)
- **Build:** pass — `test_coverage=0.767`, `defect_rate=1.0` from `scores.json` (not re-run)
- **Lint:** n/a — `code_quality=0.733`; `idiomatic=0.0` (not TypeScript), `maintainability=0.202`
- **Architecture:** run-summary skill unavailable — see inline notes below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 1 high, 1 medium, 1 low)

## Requirements

Checklist is the pinned `bookshop-256k/REQUIREMENTS.json` (R1–R12), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.js:29` route; validated + persisted; test.js:29 |
| R2 | GET /books lists all | ✓ implemented | `server.js:65`; test.js:66 |
| R3 | GET /books ?author= filter | ✓ implemented | `server.js:71-74` WHERE author=?; test.js:179 asserts length==1 |
| R4 | GET /books/{id} + 404 | ✓ implemented | `server.js:88`, 404 at :99; test.js:87 & :172 |
| R5 | PUT /books/{id} updates | ✓ implemented | `server.js:109`, existence check + 404; test.js:111 |
| R6 | DELETE /books/{id} | ✓ implemented | `server.js:167`, 404 when changes==0; test.js:146 |
| R7 | Data stored in SQLite | ~ partial | `server.js:10` uses sqlite3 but `':memory:'` — engine yes, persistence no |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/400/404/500 throughout server.js |
| R9 | Validation: title & author required | ✓ implemented | `server.js:33` (POST) & :114 (PUT) → 400; test.js:50 |
| R10 | GET /health | ✓ implemented | `server.js:24` returns 200 {status:'OK'}; test.js:19 |
| R11 | README with setup/run | ✓ implemented | README.md documents install / npm start / npm test |
| R12 | ≥3 unit/integration tests | ✓ implemented | 9 supertest tests, `test_coverage=0.767 > 0` |

**Prompt factor (neutral):** `prompts/neutral.md` prescribes no methodology and only asks for tests demonstrating the requirements — no additional checkable `P*` requirements. Satisfied (9 tests present).

**Factor-conformance defect (not an R-item):** the `language=typescript` cell was implemented in plain JavaScript (no `.ts`, no tsconfig, no types) — see finding `lang-mismatch`. This is why `idiomatic=0.0`.

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.7671   (tests ran and passed; 0.767 = statement coverage of server.js)
defect_rate   = 1.0      (build + test succeeded)
code_quality  = 0.7333
idiomatic     = 0.0      (JavaScript, not the required TypeScript)
maintainability = 0.2023
token_efficiency = 1.0
```

Test suite (`test.js`, jest + supertest): 9 tests — health, create, missing-field rejection, list, get-by-id, update, delete, 404, author filter. 0 skipped.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 491 (server.js 194, test.js 205, demo.js 92) |
| Files (excl node_modules) | 13 |
| Dependencies | 4 (express, sqlite3, jest, supertest) |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Statement coverage (server.js) | 76.7% |

## Findings

Top items (full list in `findings.jsonl`):

1. [high] Delivered JavaScript, not the specified TypeScript — `lang-mismatch`
2. [medium] SQLite used but `:memory:` only — data not persisted (R7) — `R7`
3. [low] POST/PUT echo raw `year` instead of the persisted value — `resp-year`

## Reproduce

```bash
cd experiment-16-qwen3coder/bookshop-256k/runs/agent=qwen3-coder-local_language=typescript_prompt=neutral/rep2
cat scores.json                              # stored build/test/quality scores
grep -cE "^\s*test\(" test.js                # test count (9)
grep -rE "\.skip\(|xit\(|it\.todo\(" test.js # skips (0)
find . -name '*.ts' -not -path '*/node_modules/*'  # TypeScript sources (none)
```
