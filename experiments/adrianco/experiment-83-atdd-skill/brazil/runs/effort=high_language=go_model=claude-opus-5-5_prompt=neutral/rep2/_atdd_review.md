I now have full disclosure (`full`) on every lesson across categories A–G. I've read all the test files and the system under test. Here is the review.

---

# ATDD Review — Brazilian Soccer MCP Server test suite

Tests reviewed: `questions_test.go`, `mcp_test.go`, `store_test.go`, `normalize_test.go` (with `main.go`, `mcp.go`, `tools.go`, `TASK.md` as context). Criteria drawn from Dave Farley's ATDD course lessons 102, 103b, 201, 202, 203, 301, 302, 303, 305 and 306 — full lessons, not summaries.

## 1. Overall assessment

This is a careful, honest, genuinely useful test suite — well above the average I review — but it is built on the wrong *axis* for acceptance testing. The clearest acceptance layer, `TestSampleQuestions` in `questions_test.go`, starts from exactly the right place (a table of natural-language questions a user would ask) and then, in the same breath, nails each one to the specific tool and argument-map an LLM "would" produce. The result reads as a specification in its left-hand column and an implementation script in its right-hand column. The suite is strongest where Dave is usually strongest-critical — releasability honesty — and weakest where most suites are weak: there is no DSL, so the "what" and the "how" are fused into every test case. The system is read-only, which quietly earns the suite a lot of isolation safety it didn't have to work for, but it also leans the whole suite against a single frozen snapshot of real production data.

## 2. Strengths

- **The acceptance layer is organised around user questions, not functions.** `sampleQuestions` (`questions_test.go:13-128`) is a table of real domain questions — "Who won the 2019 Brasileirão?", "Compare Palmeiras and Santos head-to-head" — and it asserts domain *facts* ("1. Flamengo - 90 pts (28W, 6D, 4L)", "Champion"). That instinct — specify by example, in the language of the problem domain — is the core of lesson 102 and lesson 111, and many suites never get this far.
- **Releasability honesty is exemplary** (category G, below). Zero skips, zero ignores, no CI exclusion filters, no swallowed exceptions — and the suite actively *guards* its own coverage.
- **No sleeps anywhere.** The single most common intermittency anti-pattern in lesson 306 is simply absent.
- **Two entry channels into the SUT** — in-process `CallTool` (`questions_test.go:138`) and real JSON-RPC-over-pipes (`mcp_test.go:162-200`) — which is a half-step toward Dave's "one spec, many protocol drivers" idea (lesson 303).
- **Good, diagnosable failure messages**: failures print the tool, the args and the full answer text (e.g. `questions_test.go:145`), which is exactly what lesson 202 §6 asks for.

## 3. Priority issues

### Priority 1 — The specs are coupled to the implementation (tool name + argument schema), not to user behaviour. *(Category A — lesson 103b, lesson 203)*

Lesson 203 gives a one-line test for this: *"imagine the spec being fulfilled by a completely different system. If it can't be, it's coupled to the implementation."* Every row in `sampleQuestions` fails that test. The user-facing artefact is the question string; but the executable content is the tool name and the exact argument map:

```go
// questions_test.go:81-83 — the question is domain language, but the spec is a tool call
{"Who won the 2019 Brasileirão?", "standings",
    map[string]any{"season": 2019, "top": 3},
    []string{"1. Flamengo - 90 pts (28W, 6D, 4L)", "- Champion", ...}},
```

Rename `standings`, rename the `top` parameter, or change the output format, and this spec goes red — even though "who won the 2019 Brasileirão?" is unchanged and the system still answers it perfectly. Worse, for an MCP server the *real* user is an LLM choosing a tool from a natural-language question; this test hard-codes the developer's guess at that choice and so never specifies the behaviour the user actually depends on. This is lesson 203's mistake #1 (confusing the interaction mechanism with the behaviour), transposed from "I click login" to "I call `standings` with these args."

The `want []string` assertions compound it: they match exact rendered strings (`"Head-to-head in selection: Flamengo 18 wins, Fluminense 14 wins, 12 draws"`, `questions_test.go:22`), so they also specify *how the answer is formatted*, not just what is true.

**Before / after** — separate what the user wants from how the tool delivers it, by pushing the tool name, the argument keys and the string-parsing down into a reusable layer, and asserting on facts:

```go
// after: the spec speaks the domain; the tool/arg plumbing lives in the DSL
standings := dsl.LeagueTable(season(2019))
confirmChampion(standings, "Flamengo", points(90), record(won(28), drawn(6), lost(4)))
```

Now `LeagueTable` is the *only* place that knows the tool is called `standings` and the parameter is `season`; `confirmChampion` is the only place that knows how a table row is rendered. Renaming the tool, or reformatting the row, touches one method — not 36 table rows. This is the whole point of lesson 202: *good tests have only two reasons to fail — a translation mistake in the infrastructure, or a genuine spec failure.* Right now these tests have a third and fourth reason: the tool got renamed, or the output got reformatted.

### Priority 2 — There is no DSL layer; the four-layer model is collapsed to two. *(Categories B & D — lesson 301, lesson 305)*

Lesson 305's model is test case → DSL → protocol driver → SUT. This suite has test cases and (thin) protocol-ish helpers, but **no DSL**. Test cases talk to the SUT through raw `map[string]any` literals and, in `mcp_test.go`, through hand-assembled JSON-RPC strings:

```go
// mcp_test.go:110-114 — protocol detail (raw JSON-RPC) living inside the test case
`{"jsonrpc":"2.0","id":"a","method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"top":3}}}`,
```

Lesson 203's mistake #3 is exactly this: *"no reuse in the DSL — every scenario implemented from scratch."* The argument maps for `search_matches` are rebuilt inline in `questions_test.go`, again in the `minimal` map in `mcp_test.go:205-220`, and again in `TestToolArgumentValidation`. A DSL would carry lesson 301's three capabilities — **named operations in the domain vocabulary, default values so a test states only what it cares about, and a single stable surface** that doesn't move when the SUT does.

**Before / after:**

```go
// before: raw tool + arg map, repeated across files
srv.CallTool("search_matches", map[string]any{"team": "Flamengo", "opponent": "Fluminense", "limit": 50})

// after: a reusable DSL verb at the level of the problem domain, with defaults
dsl.Matches(between("Flamengo", "Fluminense"))          // limit defaulted inside the DSL
dsl.Matches(between("Flamengo", "Corinthians"), mostRecent())
```

The existing helpers (`roundTrip`, `send`, `toolText`, `mustTeam`) are the seed of the *protocol-driver* layer, not a DSL — keep them, but put a domain-language DSL on top of them so that `questions_test.go` and `mcp_test.go` can drive the *same* specs through the in-process driver and the JSON-RPC driver (lesson 303's "one spec, many drivers"). You are one layer short of the arrangement Dave spends lesson 305 assembling.

### Priority 3 — Wall-clock and exact-data-count assertions give tests reasons to fail that aren't the spec. *(Category F — lesson 202, lesson 306)*

Several tests embed performance thresholds inside correctness tests:

```go
if elapsed > 2*time.Second { t.Errorf("took %s", elapsed) }   // questions_test.go:149-151
if d := time.Since(start); d > 2*time.Second { ... }          // mcp_test.go:237-239
case <-time.After(5 * time.Second): t.Fatal(...)              // mcp_test.go:197
if s.LoadTime > 5*time.Second { ... }                         // store_test.go:59
```

Lesson 306 §4 names resource contention and environment changes as direct causes of intermittency, and lesson 202 is blunt that a good test has *only two reasons to fail*. A correctness spec that also enforces a 2-second budget has a third: a busy or slow CI box. These will flake, and a flaky green-or-red erodes exactly the trust lesson 306 opens with. Move the performance budget into the existing `BenchmarkAggregateQueries` (`questions_test.go:156`) or a separately-tagged perf run; keep the behaviour specs about behaviour.

Related, and milder: the suite is welded to one frozen snapshot of the real dataset — `827` Brazilian players (`store_test.go:279`), `4180` Brasileirão rows (`store_test.go:38`), `44 matches found` (`questions_test.go:22`). Lesson 306 §2 lists "changes in test data between runs" as a top intermittency cause, and lesson 305 is explicit: *"use only synthetic data, created by your DSL… avoid starting up the SUT with lots of state."* Re-publish the Kaggle data with one more season and dozens of these go red at once. For a query-over-fixed-corpus system this is a real tension (the corpus arguably *is* part of the SUT), so I would not tear it out — but I'd (a) isolate the "is the data what we shipped?" checks (`TestAllSixFilesLoaded`) as explicit *data-fixture* guards, distinct from behaviour specs, and (b) where a fact is really about logic rather than this corpus (symmetry, dedup, filter-leak), prefer a small synthetic store so the logic spec survives a data refresh.

## 4. Further improvements

- **Push assertions into the driver as atomic pass/fail steps.** Lesson 305 recommends each protocol-driver step pass or fail itself, so the test case stays a clean statement of intent. `toolText` (`mcp_test.go:93-105`) half does this (it `t.Fatalf`s on a malformed envelope) — extend that so a `confirm…` verb owns the fact-checking rather than the test spelling out `strings.Contains` loops.
- **`store_test.go` is integration-level, not acceptance-level.** `TestStandings2019`, `TestTeamRecordCorinthiansHome2022`, `TestHeadToHeadIsSymmetric` reach past the tool boundary into `s.Standings(...)`, `TeamRecord(...)`, `s.FindMatches(...)`. These are good tests, but they're testing the engine, not specifying user behaviour — label and keep them as such, and don't let them stand in for the acceptance specs.
- **`normalize_test.go` is textbook unit testing** (table-driven, pure functions) — this is exactly where lesson 203's mistake #2 says edge cases *belong*. Leave it; just don't count it as acceptance coverage.
- **No stubs needed, correctly.** The SUT has no external dependencies, so lesson 303's stub guidance doesn't apply — there is nothing to fake, and the suite rightly fakes nothing.

## 5. Category ratings and the honesty check (G)

- **A — Spec quality: 2.** Domain-language questions and real-fact assertions (good instinct), but each spec is bolted to a tool name, an argument schema and an exact output string, and the natural-language question is decorative rather than driving.
- **B — Architecture: 2.** Server abstraction and two entry channels show the right instinct, but there's no DSL layer and raw JSON-RPC protocol detail leaks into the test cases.
- **C — Isolation: 3.** No cross-test interference, no cleanup, parallel-safe and deterministic within a run — but this is earned largely by the SUT being read-only, not by functional/temporal isolation, and the suite binds to one monolithic real-data fixture rather than per-test synthetic data.
- **D — DSL quality: 1.** Effectively no DSL; raw `map[string]any` calls repeated across files, little reuse, no defaults or domain vocabulary.
- **E — Protocol driver quality: 2.** `CallTool` / `roundTrip` / `send` / `toolText` form an emerging driver with good error messages and no sleeps, but it's thin, protocol detail leaks upward, and assertions aren't pushed down into atomic pass/fail steps.
- **F — Intermittency risks: 2.** Deterministic core and no sleeps, but wall-clock performance thresholds and exact-data-count assertions give tests failure reasons unrelated to the spec (lesson 202's "only two reasons to fail").
- **G — Releasability truthfulness: 4.** No `t.Skip`/ignore/`.only`, no CI exclusion filters, no `continue-on-error`, no swallowed exceptions (helpers `t.Fatalf` on bad shapes). The suite goes further and *guards* its own honesty: `TestSampleQuestions` fails if there are fewer than 20 questions (`questions_test.go:132-134`) and `TestEveryToolRunsWithMinimalArguments` fails if any tool lacks coverage (`mcp_test.go:224-227`). Green means green. (The only gap is no explicit expected-fail mechanism for in-progress features per lesson 201, and no CI pipeline at all — but nothing is hidden.)

## Suggested next steps

1. **Build the missing DSL layer first (Priority 2).** It unlocks everything else: once `LeagueTable`, `Matches`, `HeadToHead`, `Player` verbs exist with defaults and fact-level `confirm…` assertions, the Priority 1 decoupling falls out naturally and the two drivers (in-process, JSON-RPC) can run the same specs.
2. **Decouple the question specs from tool/args/format (Priority 1)** by rewriting `sampleQuestions` on top of that DSL, asserting domain facts rather than rendered substrings.
3. **Separate performance and data-fixture checks from behaviour specs (Priority 3)** so a slow CI box or a refreshed dataset can't turn a behaviour spec red.
4. Keep `normalize_test.go` as-is and keep G exactly as honest as it is today.

```json
{"acceptance_tests_found": true, "ratings": {"A": 2, "B": 2, "C": 3, "D": 1, "E": 2, "F": 2, "G": 4}, "disclosure": "full"}
```