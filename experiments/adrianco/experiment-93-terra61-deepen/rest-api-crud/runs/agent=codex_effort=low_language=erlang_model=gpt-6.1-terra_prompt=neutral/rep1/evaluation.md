# Evaluation: agent=codex effort=low language=erlang model=gpt-6.1-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=erlang, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** all passed / 0 failed / 0 skipped (test_coverage=1.0 ⇒ build + all tests passed)
- **Build:** pass — from `scores.json` (test_coverage=1.0, defect_rate=1.0)
- **Lint:** pass — code_quality=1.0 from `scores.json`
- **Architecture:** `run-summary` skill not available in this environment — summarized inline below.
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/books_handler.erl` dispatch(collection,POST) → `read_book` → `books_store:create`; returns 201 |
| R2 | GET /books lists all | ✓ implemented | `books_handler.erl` dispatch(collection,GET) → `books_store:list`; sorted by id in `books_store.erl` |
| R3 | GET /books ?author= filter | ✓ implemented | `books_handler.erl` reads `author` from `parse_qs`; `books_store:list/1` filters on `<<"author">>` |
| R4 | GET /books/{id} single (404) | ✓ implemented | dispatch(item,GET) → `books_store:get` → `result/2` maps not_found→404 |
| R5 | PUT /books/{id} updates | ✓ implemented | dispatch(item,PUT) → `books_store:update/2`; 404 if absent |
| R6 | DELETE /books/{id} deletes | ✓ implemented | dispatch(item,DELETE) → `books_store:delete/1`; 200 `{deleted:true}` / 404 |
| R7 | Stored in SQLite/embedded DB | ✓ implemented | `books_store.erl` uses Erlang DETS (`dets:open_file(books_data,...)`); survives restart (persistence test) |
| R8 | JSON responses + status codes | ✓ implemented | `reply/4` sets `application/json`, `jsx:encode`; 201/200/400/404/405/413 throughout |
| R9 | Validation: title & author required | ✓ implemented | `books_handler:validate/1` `nonempty/1` on title+author → 400; covered by `validation_test` |
| R10 | GET /health | ✓ implemented | dispatch(health,GET) → `{200,#{status=>ok}}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — rebar3 compile/shell, env config, API, curl examples |
| R12 | ≥ 3 tests | ✓ implemented | `test/books_tests.erl`: `validation_test` + generator (`lifecycle`, `filtering`, `persistence`) = 4 cases; test_coverage=1.0 |

Enhancements beyond spec (not deductions): 413 oversized-body guard with bounded `read_body`, 405 method-not-allowed with `Allow` header, `?author=` exact-match, DETS auto_save + explicit sync for durability.

## Build & Test

Scores read from `scores.json` (inline gate; not re-run per skill guidance):

```text
scores.json: {"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
              "maintainability": 0.802, "idiomatic": 0.62, "token_efficiency": 0.0}
```

```text
test_coverage=1.0  ⇒  rebar3 compile + rebar3 eunit succeeded, all EUnit cases passed, 0 skipped
```

Note: `_agent_stderr.log` records the sandbox rejecting an `rm -rf _build && rebar3 ...` command; the agent recovered and the run completed green. Harness policy event, not a code defect (info finding).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .erl) | 189 |
| Files (src + test) | 6 |
| Dependencies | 2 (cowboy 2.12.0, jsx 3.1.0) |
| Tests total | 4 (1 named + 3 generated) |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build | pass (test_coverage=1.0) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Agent's `rm -rf` rebuild command was rejected by the sandbox but the run recovered (test_coverage=1.0).

No correctness, requirement, or test-skip findings. Clean 12/12 pass.

## Reproduce

```bash
cd "experiments/adrianco/experiment-93-terra61-deepen/rest-api-crud/runs/agent=codex_effort=low_language=erlang_model=gpt-6.1-terra_prompt=neutral/rep1"
cat scores.json                       # build/test/lint scores (do not re-run)
cat ../../../REQUIREMENTS.json         # pinned R1–R12 checklist
grep -rEi skip src test --include='*.erl'   # 0 skipped tests
# Full build/test (optional, outside sandbox): rebar3 compile && rebar3 eunit
```
