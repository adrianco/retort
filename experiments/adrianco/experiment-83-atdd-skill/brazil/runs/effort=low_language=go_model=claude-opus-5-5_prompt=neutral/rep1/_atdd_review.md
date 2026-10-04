I now have the full lessons for every category and have inspected the code, the data fixtures, and the (absent) CI configuration. Here is the review.

---

# ATDD Review — `soccer_test.go` (Brazilian Soccer MCP server)

*Reviewed against Dave Farley's ATDD course material. All lessons were retrieved at **full** disclosure (paid tier), so the criteria below are Dave's full articulation, not summaries.*

## What this suite is

`soccer_test.go` is a Go `testing` suite for an MCP server that answers questions about Brazilian football from six bundled CSV datasets. Two kinds of test live here:

- **Acceptance / end-to-end tests** — the ones that drive the system through its public surface: the `call(t, "standings", Args{…})` family (going through `Server.Call`, the tool-dispatch entry point) and especially `TestMCPProtocol`, which drives the real JSON-RPC stdio protocol via `s.Serve(...)`. These assert domain outcomes ("Flamengo champion, 90 pts, 2019"; "four teams relegated in 2020"; "Fla-Flu is a derby").
- **Unit/integration tests** — `TestTeamKeyNormalization`, `TestParseDate`, `TestAllFilesLoaded`, `TestDateRange`, `TestNoDoubleCounting`, and the parts that reach directly into `db(t).Filter`, `HeadToHead`, `Standings`.

The review below judges the acceptance/e2e tests. Because the SUT is a **read-only query engine over static data** — no users, no mutable state, no external systems, no asynchrony — several of Dave's mechanisms (functional/temporal aliasing, stubs, poll-with-timeout) are legitimately not needed here, and I've assessed accordingly rather than penalising their absence.

## Overall assessment

The suite is **honest, deterministic and genuinely useful**, and its *intent* is well aligned with ATDD: the tests are named and organised around domain outcomes, not code paths. But structurally it sits a long way from Dave's four-layer model. There is no DSL layer; test cases speak the SUT's **raw wire vocabulary** (`Args{"season": 2019.0}` — the JSON `float64` leaks straight into the spec), and they assert against the **exact formatted output string** (`"1. Flamengo - 90 pts (28W, 6D, 4L"`). In Dave's terms the specs are *coupled to the implementation*: narrowly correct for today's rendering, fragile the moment the presentation changes. The biggest wins are available by inserting a thin DSL between the test cases and `Server.Call`, so the specs can state facts ("Flamengo won the 2019 league with 90 points") instead of substrings.

## Strengths

- **Outcome-oriented naming and structure.** `TestStandings2019`, `TestRelegated2020`, `TestFlaFlu`, `TestCorinthiansHome2022` read as specifications of behaviour, which is exactly the framing lesson 103b argues for (specs, not tests).
- **A real end-to-end test exists.** `TestMCPProtocol` exercises the actual JSON-RPC protocol — initialize, `tools/list`, `tools/call`, unknown-tool `isError`, unknown-method error. That's a true e2e proof the wire contract works, not just the handlers.
- **`call()` is an embryonic protocol driver done right in one respect.** It makes each step **pass-or-fail**: `t.Fatalf("%s(%v): %v", tool, args, err)` on any error, with the tool and args in the message. That is precisely Dave's advice in lesson 305 — "make each step, each method in a PD, pass or fail… if control returns from that step, you know it happened."
- **Determinism and no teardown.** Nothing mutates; `testDB` is loaded once and shared read-only. The suite needs none of the "database-rollback gymnastics" lesson 302 warns against, and running any test twice gives the same answer — the *goal* of temporal isolation, achieved for free here.
- **Fully honest about its state (category G).** No `t.Skip`, no `-run`/`-short` exclusions, no `continue-on-error`, no commented-out or `.only` tests, no CI filter hiding anything (there is no CI config at all). The suite is a truthful statement of releasability — directly in the spirit of lesson 306.

## Priority issues

### 1. Specs are coupled to the output format, not the behaviour (categories A, B)

**Why it matters.** Lesson 103b: good specs are *durable* — "true in a way that doesn't change as the system evolves." Lesson 203's test for coupling is "imagine the spec being fulfilled by a completely different system. If it can't be, it's coupled to the implementation." Asserting `"1. Flamengo - 90 pts (28W, 6D, 4L"` is the equivalent of Dave's "the result should be 120 **on the screen**": it bakes the renderer's layout (`"- %d pts (%dW, %dD, %dL"` from `toolStandings`) into the specification. Change "pts" to "points", or reorder the parenthetical, and the spec breaks though Flamengo still won.

**Before** (`soccer_test.go:104`):
```go
func TestStandings2019(t *testing.T) {
	out := call(t, "standings", Args{"season": 2019.0, "limit": 3.0})
	mustContain(t, out, "1. Flamengo - 90 pts (28W, 6D, 4L", "Champion", "Santos - 74 pts", "Palmeiras - 74 pts")
}
```

**After** — assert the domain fact, letting a DSL decode the result so the renderer can change freely:
```go
func TestStandings2019(t *testing.T) {
	table := soccer(t).Standings(Season(2019))       // DSL returns structured rows
	table.Champion().Is("Flamengo").With(Points(90), Record(28, 6, 4))
	table.Runners("Santos", "Palmeiras").Each(Points(74))
}
```
The spec now survives any change to how standings are printed — only the protocol driver that parses `Server.Call` output (or, better, a structured result mode) needs touching.

### 2. There is no DSL layer, and the wire format leaks into the test cases (categories D, B)

**Why it matters.** Lesson 301/305: the DSL is "a small programming language whose vocabulary matches the problem domain," providing **default values** and a **stable interface** insulated from SUT detail. Here the test cases pass `Args{"season": 2019.0, "limit": 3.0}` — raw map keys and JSON `float64`s, the SUT's own input shape. That is the SUT's vocabulary, not the domain's, and the `2019.0` is implementation plumbing (JSON decoding) surfacing in the spec. Defaults live in the production handlers, not in reusable test infrastructure, so every test re-specifies plumbing it doesn't care about.

**Before** (repeated across the suite):
```go
out := call(t, "team_record", Args{"team": "Corinthians", "season": 2022.0, "venue": "home", "competition": "Brasileirão"})
mustContain(t, out, "Matches: 19", "Win rate:")
```

**After** — a small internal DSL (lesson 301's preferred style) with named params and defaults; the protocol driver owns the `Args`/`float64` marshalling and the `Server.Call` plumbing:
```go
rec := soccer(t).TeamRecord("Corinthians", Season(2022), Home) // competition defaults to Brasileirão
rec.Confirm(Matches(19))
```
This is lesson 305's "keep the call from DSL to PD at the same level of abstraction as the call from the test case to the DSL." `call()` grows into the protocol-driver layer; the new `soccer(t)` facade is the DSL; the test case is left speaking pure domain language.

### 3. Scenario overload and layer-mixing in individual tests (category A; lesson 203 mistakes #2 and #4)

**Why it matters.** Lesson 203: keep scenarios short and assert a single outcome; don't "try to test everything at once." And the legacy case study in lesson 308 warns against tests that "mix together what the system needs to do with the technicalities of testing." Two tests do both:

- `TestPlayers` (`soccer_test.go:184`) packs five unrelated queries — nationality ranking, name lookup, club filter, position filter, `players_by_club` — plus a hand-rolled position-parsing loop, into one function. This is scenario overload; a single failure anywhere obscures which behaviour broke.
- `TestFlaFlu` (`soccer_test.go:128`) first checks the tool output (acceptance level), then reaches **past** the public surface into `db(t).HeadToHead(...)` to assert on internal struct fields (`h.AWins+h.BWins+h.Draws == len(h.Matches)`, source diversity). That invariant is worth testing — but as a unit test of `HeadToHead`, not inside an acceptance spec, where it couples the spec to internals.

**After:** split `TestPlayers` into one spec per behaviour (`TestTopBrazilianByRating`, `TestPlayerNameLookup`, `TestClubFilterExcludesSantosLaguna`, …), each asserting one outcome; and move the `HeadToHead` invariant checks into a dedicated unit test, leaving `TestFlaFlu` to assert only the user-visible head-to-head outcome through the DSL.

## Further improvements

- **The 2-second wall-clock assertion is a latent flake** (category F; lesson 306). `if d := time.Since(start); d > 2*time.Second` in `call()` is a timing assertion sensitive to exactly the causes lesson 306 names — "resource contention" and "changes in the environment." It will pass on your laptop and fail on a loaded CI box without anything being broken. (The one-time `LoadDB` is correctly excluded, since `db(t)` runs before `start`.) Prefer a benchmark, or a much larger ceiling used only as a smoke guard, rather than a per-call correctness gate.
- **`TestMCPProtocol` has no protocol driver** (categories B, E). The raw JSON-RPC strings and the deep type assertions (`resp[0]["result"].(map[string]any)["serverInfo"]`) sit directly in the test case — the opposite of lesson 303's "hide the technical detail… from everything above them." Extract an `mcpClient` driver that sends a request and returns a decoded response, so the test reads `client.Call("standings", …).Text().Contains("Flamengo")`.
- **Heavy coupling to specific fixture values** (categories C, F). Counts and results are pinned to the exact CSVs (`>= 4000`, `Flamengo - 90 pts`, exactly four relegated). Lesson 306 lists "changes in test data between runs" as a prime intermittency cause; if a dataset is ever refreshed, large swathes break at once. This is acceptable for a historical-data tool, but worth isolating the magic numbers behind named DSL expectations so the coupling is explicit and in one place.
- **Swallowed errors in test bodies** (category G). `h, _ := db(t).HeadToHead(...)` and `ms, _ := db(t).Filter(...)` discard production errors and then assert on the zero value. It's a mild muted-failure smell — assert `err == nil` first so a real error reports as itself.
- **No `t.Parallel()`** (category C). Because the SUT is read-only and shared safely, these tests *could* run in parallel — lesson 302's payoff for good isolation. You're leaving that speed-up on the table.

## Suggested next steps

This suite does not need restructuring from scratch — it needs **a DSL inserted between the test cases and `Server.Call`**. In order:

1. **Build a thin `soccer(t)` DSL facade** over `call()`, with domain methods (`Standings`, `TeamRecord`, `HeadToHead`, `SearchPlayers`), named parameters and sensible defaults (lesson 301). Have it **parse the tool output into structured results** so assertions target facts, not substrings — this fixes priority issues 1 and 2 together.
2. **Promote `call()` into an explicit protocol-driver layer** and add an `mcpClient` driver so `TestMCPProtocol` stops hand-assembling JSON-RPC.
3. **Split the overloaded tests** (`TestPlayers`, `TestFlaFlu`) and move internal-invariant checks down to unit tests.
4. **Replace the 2s wall-clock gate** with a benchmark, and add `t.Parallel()` once the DSL is in place.

Keep what's already good: the honest, no-skips posture (category G) and the pass-or-fail discipline in `call()` are exactly right — carry both into the new layers.

```json
{"acceptance_tests_found": true, "ratings": {"A": 2, "B": 2, "C": 3, "D": 1, "E": 2, "F": 3, "G": 3}, "disclosure": "full"}
```