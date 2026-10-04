I now have full lesson content (paid tier, `disclosure: "full"`) for every category A–G. Here is the review.

---

# ATDD Review: `brsoccer` acceptance suite

I reviewed the complete acceptance suite under `acceptance/` — eight spec files (`*_test.go`), the seven-area DSL (`acceptance/dsl/`), and the protocol-driver layer (`acceptance/driver/`) that reaches the Brazilian-soccer MCP server as a separate process. Criteria were drawn live from Dave Farley's ATDD course (lessons 103b, 203, 301, 302, 303, 305, 306); all content returned at full disclosure.

## Overall assessment

This is a reference-quality acceptance suite — one of the cleanest implementations of Dave's four-layer model I've reviewed. The specs are written entirely in the language of the problem domain, the DSL and protocol driver are cleanly separated with an explicit contract, isolation is achieved by the strongest strategy Dave offers (a dedicated SUT per test with no cleanup), and the suite is honest about its own state. There is almost nothing structural to fix. The feedback below is refinement, not repair — and I want to be explicit that I'm *not* manufacturing problems to seem thorough: the handful of genuine soft spots are concentrated in one category (intermittency), and I've said so in the ratings.

## Strengths

- **The specs are pure outcome, zero implementation leakage** (lesson 103b, 203). `match_search_test.go:15` reads `s.Matches.Played("home: Flamengo", "away: Fluminense", "score: 2-1", "date: 2023-09-03")` … `s.Matches.ConfirmFound("Flamengo 2-1 Fluminense on 2023-09-03")`. Apply Dave's acid test — *"imagine the spec being fulfilled by a completely different system"* — and every one of these holds against a REST service, a GraphQL API or an in-memory library. Nothing in the test cases knows the server is MCP, speaks JSON-RPC, or reads CSV. Test names all begin with `Should`, exactly Dave's tactic for keeping the mind on *what*, not *how*.
- **Textbook four-layer architecture** (lesson 305). Test case → DSL (`acceptance/dsl/`) → protocol driver (`acceptance/driver/`) → SUT (the built binary). You even define the PD *contract* as an interface — `SoccerDriver` in `driver/driver.go:35` — which is precisely the step Dave describes ("I have even created an interface at this point, defining the contract for any PD, so we could plug different versions"). The package doc comments state the boundary explicitly.
- **A genuinely well-designed DSL** (lesson 301, 305). It is decomposed by domain area (Matches, Teams, Players, Competitions, Statistics, Datasets, Assistant) — Dave: *"I nearly always decompose the DSL like this, to avoid ending up with a giant, hard-to-maintain piece of code."* Named parameters with defaults via the `Params` helper (`dsl/params.go`) mirror Dave's own Params class and default-value advice almost line for line. And the confirmations are named `Confirm…` rather than `assert…` — which is the exact habit Dave describes in lesson 305 ("I tend… to write assertions in my DSL starting with the word `confirm`").
- **Isolation is exemplary** (lesson 302). `NewSyntheticDriver` (`driver/mcp_driver.go:53`) gives each synthetic spec its own server over its own `t.TempDir()`, holding only the facts that spec recorded. This is Dave's *dedicated-SUT-per-test* strategy — the strongest form — so there is no shared writable state, no teardown, no database-rollback gymnastics. The SUT is simply thrown away. Running the same test twice is inherently safe.
- **Assertions live in the protocol driver, and every step is atomic** (lesson 305, 303). `confirmFigures` (`mcp_driver.go:1071`) and the `Confirm*` methods fail via `t.Fatalf`/`t.Errorf`, and the error messages are in domain language with the full found-set printed (`mcp_driver.go:271`) — *"good error messages… at a sensible level for spec writers… in the language of the problem domain."*
- **The suite is honest about its state** (releasability). No `t.Skip`, no build-ignore tags, no `.only`, no `continue-on-error`, no swallowed `recover()`, no CI test-exclusion filters. `docs/atdd-findings.md` records cases where the *system* was found wrong (Grêmio named champion when Palmeiras actually won the 2023 season) and a spec was *added* to pin the limitation, rather than quietly deleted. The blank-import of `internal/app` in `main_test.go:15` exists specifically to stop `go test` caching stale greens after a server change — an act of releasability honesty in itself.

## Priority issues

These are the few places worth attention, ordered by impact.

### 1. Wall-clock latency assertions are a resource-contention flake vector (lesson 306)

`provided_data_test.go:53-67` asserts response times directly:

```go
s.Matches.FindLastMeeting("Flamengo", "Corinthians")
s.ConfirmAnsweredWithin("2s")
...
s.Teams.Rank("by: win rate", "venue: home")
s.ConfirmAnsweredWithin("5s")
```

**Why it matters.** Lesson 306 lists *resource contention* as one of the five root causes of intermittency, and warns that not-enough-CPU/RAM "can make our tests behave differently." A fixed wall-clock threshold on a shared CI box will occasionally blow 2s under load and produce a **false red** — and a failure you can't trust is as corrosive to releasability as a false green: *"when a test fails, we can trust the failure and reject the change. No agonising over… should we run it again in case it's an intermittent failure."* This is the one place in the suite that can lie to you.

**Direction.** Keep the NFR — it's a real requirement — but make the failure trustworthy. Either (a) run these performance checks as a separate, explicitly-tagged suite in a controlled/dedicated environment (Dave's "close clone of production", provisioned the same way each time), rather than inline with the functional specs; or (b) give the threshold real headroom and treat a near-miss as a signal to re-measure rather than a hard fail. The principle from 306: a timing failure should mean *the system is genuinely too slow*, never *the box was busy*.

### 2. Exact-count assertions couple the provided-data specs to a dataset snapshot (lessons 302, 306)

`provided_data_test.go:124` asserts `s.Players.ConfirmTotal(827)` ("all Brazilian players in the dataset"); several siblings assert exact champions, relegated sets and aggregate counts drawn from the external Kaggle files under `data/kaggle`.

**Why it matters.** Lesson 306 is blunt that *changes in test data between runs* and *version misalignment between tests and SUT* are top causes of intermittency, and that the fix is to *"keep tests and the code they test in the same repository."* Where `827` is not itself the behaviour under test (the behaviour is "find Brazilian players"), pinning the exact snapshot count makes the spec brittle to any refresh of the dataset, and the failure wouldn't tell you the *system* broke.

**Direction.** Two complementary moves. First, confirm the `data/kaggle` snapshot is version-controlled *alongside* the tests (or pinned by checksum) so test and data move together — Dave's version-alignment rule. Second, where the exact number isn't the point, assert a durable range (`ConfirmFoundAtLeast`, already used elsewhere) and reserve exact-count assertions for the genuinely load-bearing facts (e.g. "Flamengo won 2019" — a durable historical truth, which is exactly the right thing to pin). The synthetic specs already model this well; the provided-data specs are where the coupling creeps in.

### 3. Some sample-question confirmations check "an answer exists", not "the right answer" (lesson 203)

In the 23-question harness (`provided_data_test.go:79-169`), several confirmations are smoke-level — `s.Teams.ConfirmSomeTeamRankedFirst()` (line 109, 118, 121), `s.Players.ConfirmFoundAtLeast(1)` (line 133).

**Why it matters.** Lesson 203 pushes specs to *assert a single, precise outcome*. "Some team was ranked first" verifies the query returned *something*, not that it returned the *correct* thing — so a ranking bug could pass. This is a lower-priority note because the harness is explicitly a requirements-coverage net ("every question must produce a substantive answer"), and each entry is a named subtest in pure domain language, which is good. But where a precise, durable answer exists, prefer it.

**Direction.** For the questions where a historically-known answer exists (best home record, top scorer in a known season), tighten `ConfirmSomeTeamRankedFirst()` to `ConfirmRankedFirst("team: …")`. Leave the genuinely open-ended ones (which don't have a single stable answer) as coverage checks, but consider a comment marking them as such so the weaker assertion is a conscious choice, not an oversight.

## Further improvements

- **`confirmFigures` compares numeric figures with the name-folding comparator** (`mcp_driver.go:1083`, `sameName`). It works, but using an accent/case-folding function to compare points, counts and percentages is a small abstraction smell — a dedicated figure comparison would read truer to intent. Minor.
- **The dual-read fallbacks in `headToHead()` (`mcp_driver.go:288`) and `record()` (`mcp_driver.go:411`)** — trying a structured shape, then falling back to a second shape — hint the server returns the same concept under two JSON shapes. Not a test bug, but if the server response were normalised, the PD would simplify.
- **Consider `t.Parallel()`.** Your isolation already supports it — each test owns its own process and temp dir — and lesson 302/306 both stress that fast feedback is a core goal ("now we can run them in parallel too, so we get our test results really quickly"). You've paid for the isolation; you could collect the speed dividend.

## Suggested next steps

Nothing here requires restructuring — the architecture is already the target other suites aim for. In order:

1. **Make the latency checks trustworthy** (priority 1) — move them to a tagged performance suite or widen the thresholds so a failure always means "too slow", never "busy box".
2. **Pin the provided dataset and relax non-load-bearing exact counts** (priority 2) — align test and data in version control; reserve exact assertions for durable facts.
3. **Tighten the sample-question confirmations that have a known answer** (priority 3), leaving genuinely open-ended ones as explicit coverage checks.

Then, if you want the feedback speed, turn on parallel execution.

---

```json
{"acceptance_tests_found": true, "ratings": {"A": 4, "B": 4, "C": 4, "D": 4, "E": 4, "F": 3, "G": 4}, "disclosure": "full"}
```