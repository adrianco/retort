# Evaluation: language=erlang · model=gpt-5.6-terra · agent=codex · prompt=neutral · rep 1

## Summary

- **Factors:** language=erlang, model=gpt-5.6-terra, agent=codex, prompt=neutral, effort=default, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective) — `3 tests, 0 failures` per suite, two suites
- **Build:** pass — `rebar3 compile` (test_coverage=1.0 from scores.json)
- **Lint:** pass — code_quality=1.0 from scores.json (only deprecation/unused-var warnings during dev, since resolved)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books — create (title, author, year, isbn) | ✓ implemented | `src/books_http.erl:42` → `books_store:create` `src/books_store.erl:20` |
| R2 | GET /books — list, `?author=` filter | ✓ implemented | `src/books_http.erl:41`, `query_author/1:47`, filter `src/books_store.erl:25` |
| R3 | GET /books/{id} — get one | ✓ implemented | `src/books_http.erl:41` `with_id`, `books_store:get` `:27` |
| R4 | PUT /books/{id} — update | ✓ implemented | `src/books_http.erl:43`, `books_store:update` `:30` |
| R5 | DELETE /books/{id} — delete | ✓ implemented | `src/books_http.erl:44`, `books_store:delete` `:36` (204/404) |
| R6 | Use specified language & framework | ✓ implemented | Erlang/OTP app; dependency-free, `rebar.config` |
| R7 | Store in SQLite or embedded-DB equivalent | ✓ implemented | OTP DETS `src/books_store.erl:17` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `books_json` codec; `send/3` `src/books_http.erl:57` (200/201/204/400/404) |
| R9 | Input validation (title & author required) | ✓ implemented | `valid/1`+`nonempty/1` `src/books_http.erl:52-53` → 400 |
| R10 | Health check GET /health | ✓ implemented | `src/books_http.erl:40` → `{"status":"ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` (build, run, API, test) |
| R12 | At least 3 unit/integration tests | ✓ implemented | 6 EUnit tests across `test/books_store_tests.erl` + `test/books_http_tests.erl` |

No `prompt` factor requirements (prompt=neutral is the base instruction; no `prompts/neutral.md` additions to verify).

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
scores.json: code_quality=1.0  test_coverage=1.0  defect_rate=1.0
             maintainability=0.780  idiomatic=0.38  token_efficiency=0.0
```

Final agent test run (`_agent_stdout.log`, item_18):

```text
rebar3 eunit
===> Compiling books_api
===> Performing EUnit tests...
......
Finished in 0.033 seconds
6 tests, 0 failures
```

The agent iterated through several compile errors (a `headers/2` syntax error, an
invalid binary-pattern in tests, and an `atom_to_binary/1` undef fixed to the
`/2` form) before reaching a green build — all resolved in the archived source.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, src/) | 177 |
| Lines of code (tests) | 40 |
| Files (src + test) | 8 |
| Dependencies | 0 (kernel, stdlib only) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | ~0.03s test phase |

## Findings

Full list in `findings.jsonl`. None are high/critical — all are robustness edge-cases:

1. [medium] JSON string escaping omits most control characters (`books_json.erl:17-19`)
2. [medium] Hand-rolled JSON decoder accepts only a narrow grammar (no `\t`/`\uXXXX`, ints only) (`books_json.erl:26-31`)
3. [low] Author query filter parses only a lone `author=` param, no percent-decoding (`books_http.erl:47-48`)
4. [low] Request body requires an explicit Content-Length header (`books_http.erl:24`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-56-terra-alllang/bookshop/runs/agent=codex_effort=default_language=erlang_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json                     # stored mechanical scores (build/test/quality)
rebar3 compile                      # build
rebar3 eunit                        # 6 tests, 0 failures
```
