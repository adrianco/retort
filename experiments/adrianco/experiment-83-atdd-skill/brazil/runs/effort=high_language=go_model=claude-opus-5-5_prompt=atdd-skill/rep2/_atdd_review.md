I now have the full lessons for every category (A–G), all returned at `disclosure: full` on the paid tier, plus the TASK.md that establishes the domain and the explicit performance requirements. Here is the review.

---

# ATDD Review — Brazilian Soccer MCP Server acceptance suite

*Reviewed against Dave Farley's ATDD course. All criteria below are drawn from the course knowledge base, fetched live for this review (lessons 103b, 201, 202, 203, 301, 302, 303, 305, 306). Full lesson content was available — this is not a free-tier summary review.*

## 1. Overall assessment

This is one of the cleanest four-layer acceptance suites you will see outside Dave's own examples. The specs in `acceptance/*_test.go` speak pure Brazilian-football domain language and say nothing about MCP, JSON-RPC, CSV files or tool names; the DSL in `acceptance/dsl/` supplies defaults and domain vocabulary; the protocol driver in `acceptance/drivers/mcp_driver.go` is the *only* place that knows the system is an MCP server; and `RecordsStub` fakes the data source by translation, not simulation. Isolation is handled structurally (a dedicated SUT process per test over its own temp data). The author has clearly internalised the model — right down to naming the `Params` class after Dave's and commenting "It translates; it does not simulate." The suite is not mis-structured in any way; the feedback below is refinement, plus one genuine flakiness risk worth taking seriously.

## 2. Strengths

- **The specs are executable specifications, not scripts.** `TestCompetitions_ShouldCalculateTheChampionFromResults` (competition_test.go:10) reads as Given results / When standings / Then champion, entirely in domain terms. This passes Dave's acid test from lesson 203: *"imagine the spec being fulfilled by a completely different system."* These would hold if the system took voice input. Test names begin with **"Should"**, exactly the habit lesson 103b prescribes.
- **Textbook four-layer separation** (lesson 305). Test case → DSL (`dsl/`) → protocol driver (`drivers/mcp_driver.go`) → SUT, with a `SystemDriver` interface (`drivers/contracts.go:50`) that is precisely the pluggable-PD seam Dave describes ("an interface… defining the contract for any PD, so we could plug different versions"). The DSL is decomposed by domain area (matches, teams, players, competitions, statistics) — Dave: *"I nearly always decompose the DSL like this."*
- **Functional isolation done right** (lesson 302). `NewScenario` (dsl/scenario.go:28) gives every test its own `RecordsStub` (`t.TempDir()`) and its own server process, calls `t.Parallel()`, and relies on no teardown/cleanup of data — the SUT is simply thrown away. This is Dave's "dedicated SUT per test" strategy, which doubles as temporal isolation (the same test re-run always sees fresh data), so aliasing is correctly *unnecessary* here.
- **Atomic steps with assertions in the PD** (lessons 305, 202). Every `ask()` (mcp_driver.go:30) fails the step on any error, and `contracts.go:49` states the principle outright: "if control returns, the step happened." Failure messages are in domain language and include the readable answer (`:\n%s`, d.last.Text) — Dave's "good error messages at a sensible level for spec writers."
- **Stubs as translators** (lesson 303). `RecordsStub` writes the records a spec describes into the real dataset formats and starts a real system over them — a programmable translator, not a behavioural simulation.
- **Honest about its state** (category G / lesson 201). There are **no** skipped tests, `t.Skip`, `@Ignore`, `.only`, commented-out tests, `continue-on-error`, or swallowed exceptions anywhere in the suite (grep-verified). Green means green — nothing is hidden from the next reviewer.

## 3. Priority issues

### Priority 1 — Wall-clock timing assertions are an environment-sensitive flake vector (category F)

`Fan.ConfirmAnsweredWithin` (dsl/datasets.go:33 → mcp_driver.go:571) asserts a hard real-time threshold (`d.last.Duration > limit`). It is used throughout `provided_data_test.go` (e.g. lines 35, 60, 78) with 2s/5s limits.

**Why it matters.** Lesson 306 names *"changes in the environment"* and *"resource contention"* as root causes of intermittency — "not enough CPU, not enough RAM… these things can make our tests behave differently." A pass/fail gate on wall-clock time is exactly that: on a loaded CI runner a healthy system can breach 2s and fail the build for a reason unrelated to the SUT being broken. That violates the property from lesson 202 that *a good acceptance test has only two reasons to fail — a translation mistake or a genuine spec failure.* "Slow" is a third reason.

To be fair, the thresholds come straight from TASK.md's success criteria, so performance *is* a real requirement worth specifying — and the measurement correctly excludes process startup (duration is taken per round-trip in connection.go:98). The issue is only that a single hard threshold conflates "the feature is wrong" with "the box was busy."

**Direction.** Keep the performance spec, but make it resistant to one-off environmental blips rather than asserting on a single sample — e.g. have the driver take the best (or median) of a few calls against the threshold, so a transient scheduling stall doesn't red-build an otherwise-correct system:

```go
// protocol driver — confirm the answer is reliably fast, not fast on one lucky/unlucky sample
func (d *MCPDriver) ConfirmAnsweredWithin(limit time.Duration) {
    d.t.Helper()
    best := d.last.Duration
    for i := 0; i < 2 && best > limit; i++ {
        d.repeatLastCall()        // re-issue the same tool call
        if d.last.Duration < best {
            best = d.last.Duration
        }
    }
    if best > limit {
        d.t.Fatalf("%s took %v to answer; expected under %v", d.tool, best, limit)
    }
}
```

Dave's underlying point in 306 — *"set my thresholds higher, because there is no cost to it when everything is working normally"* — applies: generous thresholds plus resistance to a single bad sample give you a performance spec that fails only when the SUT is genuinely slow.

### Priority 2 — One scenario bundles six behaviours and six outcomes (category A)

`TestProvidedData_ShouldAnswerAggregateQuestionsQuickly` (provided_data_test.go:119-134) fires six unrelated queries (competition stats, biggest wins, ranking, season comparison, derbies, team overview) with a timing confirm after each.

**Why it matters.** Lesson 203's mistake #2 (long-running scenarios "that try to test everything at once") and lesson 202's *"assert a single outcome"* both push against this. If this test fails, the name tells you almost nothing about which of six interactions regressed — the diagnosis problem lesson 202 §6 warns about.

**Direction.** The real single outcome here is a cross-cutting NFR ("aggregate questions answer within 5s"), which is awkward to express one-per-test. Two reasonable options: (a) table-drive it so each query is a named sub-case (`t.Run(name, …)`) and a failure points at the culprit; or (b) attach the timing confirm to the existing per-behaviour specs rather than re-querying in a combined test. Either keeps every outcome individually diagnosable.

```go
func TestProvidedData_ShouldAnswerAggregateQuestionsQuickly(t *testing.T) {
    for _, q := range []struct{ name string; ask func(*dsl.Scenario) }{
        {"competition statistics", func(s *dsl.Scenario){ s.Statistics.ForCompetition("competition: Brasileirão") }},
        {"biggest wins",          func(s *dsl.Scenario){ s.Statistics.BiggestWins() }},
        // …
    } {
        t.Run(q.name, func(t *testing.T) {
            s := dsl.ProvidedDataScenario(t)
            q.ask(s)
            s.Fan.ConfirmAnsweredWithin("seconds: 5")
        })
    }
}
```

### Priority 3 — The honest suite isn't yet wired as a releasability gate (categories G / lesson 201)

Category G is about honesty, and on honesty the suite scores top marks — nothing is skipped or swallowed. But the surrounding releasability story from lesson 201 is incomplete: there is **no CI/pipeline configuration of any kind** in the repo (no workflow, no Makefile), and the environment reports this is **not a git repository**. Lesson 201 is explicit that "the combined set of passing acceptance tests… determines whether a release candidate can ship" and that you should "store your acceptance tests alongside the code… in version control."

**Why it matters.** A perfectly honest suite that no pipeline runs as the gate, and that isn't under version control, can't yet play the role Dave assigns it — the automated definition of done. It also means there's no `SOCCER_SYSTEM_BINARY`-driven pipeline job exercising the seam that connection.go:194 already thoughtfully provides for.

**Direction.** Put the project under version control with the tests beside the code, and add a pipeline step that runs `go test ./acceptance/...` as a release gate. When you next build an in-progress feature, prefer Dave's expected-failure handling (201: "a way of disabling these tests… during a pipeline run," re-enabled when the feature lands) over `t.Skip`, so an incomplete feature never silently turns the gate green.

## 4. Further improvements

- **ProvidedData specs are coupled to live dataset values** — e.g. `ConfirmChampion("Flamengo", "points: 90", …)` (provided_data_test.go:33), `"matches: 41"` (line 176). Lesson 306 lists *"changes in test data between runs"* as an intermittency cause. These are read from committed, read-only CSVs so they're stable in practice, and the file header honestly explains why these few tests exist — but be aware that any dataset refresh will break them for data reasons, not behaviour reasons. That's the price of the handful of genuine end-to-end "the provided data really loads and answers" checks, which is a legitimate thing to want.
- **`confirmTeamFacts` suffix-parsing** (mcp_driver.go:606-630) pulls apart `"Flamengo wins"` into fields. This is defensible translation logic for the PD, but it's edging toward business logic in the driver; if it grows, consider pushing the "which team is which" resolution into a small typed helper so the PD stays a thin translator (lesson 303).
- **`Params.Criteria()` passes a loosely-typed `map[string]string`** from DSL to PD (e.g. teams.go:17). It works and the abstraction levels still match (lesson 305), but typed DSL methods would catch a mistyped criterion at compile time rather than as a runtime `t.Fatalf`. Minor.

## 5. Suggested next steps

1. **Soften the timing assertion first (Priority 1)** — it's the one change that removes a real red-build-for-no-reason risk, and it's a few lines in one PD method.
2. **Split the "answer quickly" mega-scenario (Priority 2)** — cheap, and it restores per-behaviour diagnosability.
3. **Get the project into git and add a CI job that runs the acceptance suite as the gate (Priority 3)** — this is what turns an already-excellent, honest suite into the releasability specification Dave intends.
4. Leave the architecture alone. The four-layer model, the DSL decomposition, the stub-as-translator, and the functional-isolation strategy are all right where Dave would put them — extend that shape for new features (spec → DSL → PD → SUT) rather than changing it.

```json
{"acceptance_tests_found": true, "ratings": {"A": 4, "B": 4, "C": 4, "D": 4, "E": 4, "F": 3, "G": 4}, "disclosure": "full"}
```