I've read the full suite and fetched the full lessons (paid tier, `disclosure: full`) for every category A–G. Here is the review.

---

# ATDD Review — Brazilian Soccer MCP Server (Go test suite)

Course material was reachable and returned **full lessons** (paid tier), so the criteria below are Dave's own, not a generic checklist.

**What I reviewed as acceptance / end-to-end tests:**
- `tools_test.go` → `TestSampleQuestions` — the sample questions from the spec, driven through the tools. This is the suite's acceptance-test core.
- `mcp_test.go` → `TestServeStdioStream` (in-process over pipes) and `TestBinaryOverStdio` (builds the binary, talks JSON-RPC over real stdio + CLI mode). These are the true end-to-end tests.
- `mcp_test.go` → `TestMCP*` — JSON-RPC protocol integration tests.
- `data_test.go`, `normalize_test.go` — mostly data-layer unit/integration tests (loading, dedup, team-name resolution); `TestResolveUserQueries` is user-facing.

## 1. Overall assessment

This is a careful, genuinely well-engineered Go suite — but it is engineered as a *test suite*, not as *executable specifications* in Dave's sense. The strongest ATDD instinct is visible in `TestSampleQuestions`: it starts from real user questions ("Who won the 2019 Brasileirão?") and is driven by a data table. But underneath, the tests speak the SUT's own vocabulary — raw `Args{}` maps and exact rendered-output substrings — with no DSL layer between the test case and the system. The result is tests that will break when the *presentation* changes even though the *behaviour* is unchanged, which is precisely the coupling Dave's four-layer model exists to prevent. The good news: the async/intermittency discipline and the honesty of the suite are excellent, so the foundation to build a DSL onto is solid.

## 2. Strengths

- **The `ask` field is real domain language.** The `sampleQuestions` table is framed as user questions, which is exactly the right starting point (lesson 103b: specs in "the language of the problem domain"). Driving many cases through one loop is a legitimate form of reuse.
- **No sleeps anywhere.** `TestServeStdioStream` guards shutdown with `select { case <-done … case <-time.After(5*time.Second) }` (mcp_test.go:191-198) — event confirmation with a timeout, which is exactly the pattern lesson 306 prescribes *instead of* sleeps. This is the single most-often-botched thing in e2e suites and you got it right.
- **Honest about its state (category G).** The only skip, `TestBinaryOverStdio` → `t.Skip(... -short mode)` (mcp_test.go:203-205), is correctly gated on `testing.Short()` and runs by default; the in-process e2e test always runs. No swallowed errors, no CI exclusion filters, no commented-out tests, no `continue-on-error`. The build is green because it is green.
- **Real end-to-end coverage.** `TestBinaryOverStdio` builds the actual binary and drives it as a subprocess over stdio — that genuinely exercises the deployable artifact, not just in-process wiring.

## 3. Priority issues

### Priority 1 — There is no DSL layer; tests bind to the SUT's vocabulary (category B & D)

**What.** `TestSampleQuestions` executes with `CallTool(s, q.tool, q.args)` where `q.args` is a raw `Args{"team": "Corinthians", "season": 2022, "venue": "home", ...}` map (tools_test.go:39-42, 147). The human-readable `ask` string is decorative — it never drives anything. The actual spec is `tool name + argument map + output substrings`.

**Why it matters.** Lesson 305 defines four layers: test case → **DSL** → protocol driver → SUT. The DSL is the layer that gives tests "a stable interface that doesn't change as the SUT evolves," plus defaults and aliasing. Here that layer is simply missing: the test case reaches straight into the SUT's tool-call interface. Lesson 301's whole point — "keep the specs free of plumbing" — is unmet, because `tool: "team_record"` and the argument keys *are* the plumbing. Lesson 203's Mistake 5 ("programming by remote control") and Mistake 3 ("no reuse in the DSL") both bite: every case re-specifies the exact call shape.

**Before** (tools_test.go:39-42):
```go
{ask: "What is Corinthians' home record in 2022?", tool: "team_record",
    args: Args{"team": "Corinthians", "season": 2022, "venue": "home", "competition": "Brasileirão"},
    want: []string{"Corinthians home record (2022 Brasileirão)", "Matches: 19", "Wins: 12, Draws: 4, Losses: 3", ...}},
```

**After** — a thin internal DSL (lesson 301 prefers internal DSLs) that speaks the domain, with the tool name and arg marshalling hidden in a protocol driver beneath it:
```go
rec := dsl.TeamRecord("Corinthians").In(2022).AtHome().Competition("Brasileirão")
rec.ConfirmPlayed(19)
rec.ConfirmWinsDrawsLosses(12, 4, 3)
rec.ConfirmWinRate(63.2)
```
Now `team_record`, the `Args` keys, and the output format live in one protocol driver (lesson 303), reused by every record test. Change the tool's argument names and you fix one place, not 30 rows. The `confirm*` naming is Dave's own habit (lesson 305: "I write assertions in my DSL starting with the word `confirm`").

### Priority 2 — Assertions pin the exact rendered output ("on the screen") (category A)

**What.** The `want` substrings assert precise presentation: `"1. Flamengo - 90 pts (28W, 6D, 4L"`, `"Win rate: 63.2%"`, `"| 2018 | 380 | 2.18"`, `"827 found"` (tools_test.go:56, 82, 97, 109). The e2e checks do the same: `strings.Contains(text, "Grenal")`, `"Fla-Flu"` (mcp_test.go:187, 227).

**Why it matters.** This is the calculator mistake from lesson 103b exactly: the original bad spec asserts "the result should be 120 **on the screen**." Dave's fix is to assert the outcome and strip the presentation. Apply his test (lesson 203): *imagine the spec fulfilled by a completely different system.* If `team_record` returned structured JSON, or someone reworded "pts" to "points" or reformatted the table pipes, these specs would fail even though Flamengo still won the 2019 league with 90 points. The behaviour is unchanged; only the rendering moved — so the test is coupled to the implementation of the output, and gives you no safety when you refactor formatting (lesson 103b: "just when you could use reassurance … you break the tests meant to reassure you").

**Before** (tools_test.go:80-83):
```go
want: []string{"1. Flamengo - 90 pts (28W, 6D, 4L", ..., "Champion: Flamengo with 90 points"}
```

**After** — assert the domain outcome, let the protocol driver own the parsing:
```go
table := dsl.Standings(2019)
table.ConfirmChampion("Flamengo", points: 90)
table.ConfirmPosition(1, "Flamengo", won: 28, drawn: 6, lost: 4)
```
The driver parses the rendered line *once*; if the format changes, you update the driver's parser, and every standings spec keeps passing. The spec now states *what* ("Flamengo champion, 90 pts"), never *how it's printed*.

### Priority 3 — Wall-clock latency baked into functional assertions is an intermittency risk (category F)

**What.** `TestSampleQuestions` fails if a call takes `> 2s` (simple) or `> 5s` (aggregate): `if elapsed > limit { t.Errorf(...) }` (tools_test.go:162-168). `TestAllSixFilesLoad` fails if `loadTime > 5s` (data_test.go:66-68).

**Why it matters.** Lesson 306 lists "changes in the environment" and "resource contention" as direct causes of intermittency — and a shared/loaded CI box, a noisy neighbour, or a cold cache can push a correct run over a wall-clock threshold, failing a *functional* test for a non-functional reason. That is exactly the flakiness that "compromises our trust … the less we can rely on them as a definitive statement of releasability." A green/red functional result should mean the behaviour is right or wrong, never "the box was busy today."

**After.** Keep the correctness assertions in `TestSampleQuestions`; move latency to a Go benchmark (`func BenchmarkSampleQuestions(b *testing.B)`) or a clearly separated, non-gating performance check with a generous ceiling. Performance *is* worth guarding — just not inside the pass/fail of a behaviour spec. (Note this is the mirror image of what you did *right* in `TestServeStdioStream`: there the `time.After` is a safety timeout on a hang, not a latency assertion on the happy path — that one is correct and should stay.)

## 4. Further improvements

- **Isolation is satisfied by luck, not design (category C, rated generously).** The SUT is read-only over immutable CSVs and `testStore` loads once via `sync.Once` (data_test.go:19-30), so there's no writable shared state and re-runs are deterministic — functional/temporal isolation hold *by construction*. But lesson 302/305 prefer synthetic data created by the DSL over "starting up the SUT with lots of state," and the suite does the opposite: it asserts against a large fixed corpus (`"18207 rows"`, `"827 found"`, exact champions). That's fine while the dataset is frozen, but a data refresh would cascade failures across unrelated specs. If the data is ever versioned, treat the snapshot as a pinned fixture explicitly.
- **Protocol helpers are local, not reused (category E).** `rpc()` (mcp_test.go:16) is a decent thin driver, but `send()` is redefined inside `TestServeStdioStream` (mcp_test.go:165). Lesson 303: PDs "should be widely reused." Promoting one JSON-RPC driver that both e2e tests share would consolidate the protocol knowledge.
- **A few scenarios drift toward overload (lesson 203, Mistake 2/4).** The Flamengo–Fluminense case asserts a match line *and* a head-to-head summary in one go (tools_test.go:22-25). Prefer one asserted outcome per scenario; push the combinatorial cases down to unit level (you already have good unit coverage in `normalize_test.go`).

## 5. Suggested next steps

1. **Build a small internal DSL** (Priority 1) — start with the three busiest domains you already test: team records, standings, head-to-head. This is the highest-leverage change; B and D both rise from it, and it's the prerequisite for fixing Priority 2 cleanly.
2. **Move output parsing into protocol drivers** behind that DSL (Priority 2), so specs assert outcomes, not rendered strings.
3. **Lift the latency thresholds out of the functional specs** into benchmarks (Priority 3) — a quick, independent win you can do today.

You are not restructuring a broken suite — you're adding the one missing layer. The four-layer model gives you a precise target, and the async discipline and honesty already in place mean the hard parts are done.

```json
{"acceptance_tests_found": true, "ratings": {"A": 2, "B": 2, "C": 3, "D": 1, "E": 2, "F": 3, "G": 4}, "disclosure": "full"}
```