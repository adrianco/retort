# Evaluation: cpp · hermes-local · Qwen3-Coder-Next-4bit · m80 · rep 1 (SECOND OPINION)

## Summary

- **Factors:** language=cpp, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok (REPAIR task — two FEEDBACK-named defects re-checked)
- **Requirements:** 10/12 implemented, 2 partial/missing (R8, R9), 0 fully missing
- **requirement_coverage:** 0.833 (10/12)
- **Tests:** test_coverage=0.5 (from scores.json) — partial; harness is toothless (see findings)
- **Build:** pass (implied — binaries present in build-warn/; test_coverage=0.5 > 0 means tests executed)
- **Lint/quality:** code_quality=0.93, maintainability=0.86, idiomatic=0.60 (scores.json)
- **Findings:** 6 items in `findings.jsonl` (0 critical, 2 high, 2 medium, 2 low)

## Second-opinion verdict on the two disputed claims

Both first-evaluator claims are **CONFIRMED**. The first evaluator was right; the defects are genuinely present in the code.

### Claim R8-json: GET /books emits malformed JSON — CONFIRMED

- `src/handler.cpp:228` (list path): `... << ", \"isbn\": \"" << jsonEscape(book.isbn) << "}";`
  The isbn value is opened with `\"` but the element is closed with the literal `}` — **not** `\"}`. Output per element is `...,"isbn": "VALUE}`: the isbn string is never terminated and the closing brace is swallowed into the string. Invalid JSON.
- The three single-book serializers all close correctly with `<< "\"}"`:
  - POST create `src/handler.cpp:210`
  - PUT update `src/handler.cpp:258`
  - GET-by-id `src/handler.cpp:281`
- `FEEDBACK.md:22` explicitly named this bug ("GET /books emits malformed JSON — isbn string is unterminated"). The repair fixed nothing in the list path — it remains a one-character regression relative to the other three paths.

### Claim R9-status: validation errors return HTTP 200 instead of 400 — CONFIRMED

- Validation itself works and blocks persistence: `BookValidator::validate` (`src/model.cpp:4-30`) returns false when title/author are empty; the handler then returns an error body and never calls `db_.createBook` (`src/handler.cpp:189-200`). So the create is *rejected* (no book stored).
- But the HTTP status is 200, not 400. The error body is `{"errors": [{"field": "...", "message": "..."}]}`. The server's default-handler status inference (`src/server.cpp:178-193`) sets `status_code = 200` for any body containing the substring `"message":` (`src/server.cpp:182`) — which this error body contains. The `"error":`→400 branch (`src/server.cpp:184`) is never reached for validation errors (they use `"errors"`/`"message"`, not `"error"`).
- R9's `how_to_verify` requires "rejected (**400**)". The status code is wrong ⇒ R9 not fully met (partial: rejection happens, status is wrong).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book | ✓ implemented | `src/handler.cpp:179-213`, `src/database.cpp:50-68` (INSERT) |
| R2 | GET /books lists all | ✓ implemented | `src/handler.cpp:216-238`, `src/database.cpp:70-105` (JSON defect tracked under R8) |
| R3 | ?author= filter | ✓ implemented | `src/handler.cpp:217`, `src/database.cpp:74-84` (`WHERE author = ?`) |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `src/handler.cpp:272-284`, `src/database.cpp:107-136` |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/handler.cpp:242-261`, `src/database.cpp:138-155` |
| R6 | DELETE /books/{id} | ✓ implemented | `src/handler.cpp:264-269`, `src/database.cpp:157-170` |
| R7 | SQLite / embedded DB | ✓ implemented | `src/database.cpp:13-30` real sqlite3, prepared statements, CREATE TABLE |
| R8 | JSON + correct status codes | ✗ partial | Malformed list JSON `src/handler.cpp:228`; status codes string-sniffed `src/server.cpp:174-193` (POST returns 200 not 201) |
| R9 | Validation title/author → 400 | ✗ partial | Rejects create (`src/model.cpp:4-30`) but returns 200 not 400 (`src/server.cpp:182`) |
| R10 | GET /health | ✓ implemented | `src/handler.cpp:158-160` |
| R11 | README with setup/run | ✓ implemented | `README.md` (119 lines, features + build + run) |
| R12 | ≥3 tests, coverage>0 | ✓ implemented | `tests/test_server.cpp` (7 server tests), `tests/test_database.cpp`; test_coverage=0.5>0 (harness toothless — see findings) |

## Build & Test

Per skill Step 2, mechanical scores read from `scores.json` (not re-run):

```text
test_coverage=0.5  code_quality=0.9333  defect_rate=0.9311
maintainability=0.8599  idiomatic=0.60  token_efficiency=0.0040
```

test_coverage=0.5 ⇒ tests executed (partial). Note: `tests/test_server.cpp:runAllTests` always `return 0;` and prints PASS/FAIL rather than asserting, so the test signal is weak — `testListBooks` passes despite the malformed JSON because it only greps for `"books":`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (src+include+tests) | 1400 |
| Files (excl. build-warn/) | 28 |
| Dependencies | sqlite3, libcurl (tests) |
| Tests total | 7 server + DB tests |
| Skips | 3 conditional self-skips (test_server.cpp) |
| Test coverage (stored) | 0.5 |

## Findings

Top items (full list in `findings.jsonl`):

1. [high] R8 — GET /books malformed JSON, isbn unterminated (FEEDBACK regression NOT fixed) — `src/handler.cpp:228`
2. [high] R9 — validation errors return 200 not 400 — `src/server.cpp:182`
3. [medium] Status codes inferred by body string-matching (POST returns 200 not 201) — `src/server.cpp:174-193`
4. [medium] Toothless server test harness — runAllTests always returns 0 — `tests/test_server.cpp:252-272`
5. [low] Validator over-restricts (isbn/year required beyond spec) — `src/model.cpp:18-27`

## Architecture

`run-summary` skill not invoked (not available in this session). Structure: `src/main.cpp` wires `HTTPServer` (raw BSD sockets, thread-per-connection) → `RequestHandler` (hand-rolled JSON parse/emit) → `Database` (sqlite3 prepared statements). Status codes are (incorrectly) derived in the server layer by sniffing the handler's response body.

## Reproduce

```bash
cd experiments/adrianco/experiment-43-morelangs/bookshop/runs/agent=hermes-local_language=cpp_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep1
cat scores.json
sed -n '206,232p' src/handler.cpp     # compare single-book (210) vs list (228) closers
sed -n '178,193p' src/server.cpp       # status inference: "message:" -> 200
sed -n '4,30p'   src/model.cpp          # validator
```
