I now have the full lessons for every category (A–G) at the `paid` tier with `full` disclosure. Here is the review.

---

# ATDD Review — Brazilian Soccer MCP acceptance suite

**Scope reviewed:** `acceptance/specs_test.go`, `acceptance/dsl_test.go`, `acceptance/driver_test.go` — a three-file Go suite that drives the real MCP server binary over JSON-RPC/stdio against the Kaggle datasets. (Review grounded in the full ATDD course lessons 103b, 203, 301, 302, 303, 305, 306.)

## 1. Overall assessment

This is a genuinely good acceptance suite — in the top tier of what I usually see, and clearly written by someone who has internalised the four-layer model rather than bolted it on. The layering is explicit and clean, the specs read in the language of Brazilian football rather than the language of JSON-RPC, and there are no sleeps, no skipped tests, and no hidden exclusions. The headline BDD sin — specs coupled to the mechanics of the system — has largely been designed out. Where it falls short of Dave's principles is concentrated in two places: **isolation** (the suite leans on a large, shared, production-like dataset and asserts exact real-world values from it, the opposite of functional/temporal isolation) and **intermittency** (explicit wall-clock timing assertions plus a non-deterministic tie-break in the SUT that the tests are exposed to). Neither is structural; both are fixable without disturbing the architecture.

## 2. Strengths

- **Textbook four-layer separation** (lesson 305). `specs_test.go` is pure test case, `dsl_test.go` is a domain DSL with defaults, `driver_test.go` is the only layer that knows the system is "an MCP server speaking JSON-RPC over stdio" — the file comments even name the layers. This is the model as Dave assembles it.
- **Specs speak the problem domain** (lesson 103b). `s.Matches.Find(Team("Flamengo"), Opponent("Fluminense"))` / `s.Competitions.Standings(Season(2019))` would survive a wholesale swap of the SUT to a REST or GraphQL backend — Dave's "imagine the spec fulfilled by a completely different system" test passes.
- **DSL reuse and decomposition** (lessons 301, 203 mistake #3). One `Find` is reused across eight match specs; the DSL is split by domain area (`Matches`, `Teams`, `Players`, `Competitions`, `Stats`) exactly as Dave decomposes his `accounts` DSL to "help spec readers navigate what's there."
- **Named parameters with defaults** (lesson 305) — `args(map[string]any{"limit": 500}, ps)`, `by:"points"` — so specs state only what they care about.
- **Assertions live in the protocol driver** (lesson 305: "protocol drivers are nearly always where assertions are made"), each step is pass-or-fail/atomic, and failure messages carry the actual answer for diagnosis ("good error messages… at a sensible level for spec writers").
- **Honest about its state** (category G). No `t.Skip`, no build-tag exclusions, no commented-out tests, no CI filter hiding failures, and `docs/atdd-findings.md` transparently records every data-driven spec adjustment. Nothing is green-by-concealment.

## 3. Priority issues

### Priority 1 — Wall-clock timing assertions will flake (intermittency)

`specs_test.go:160-165`, driven by `ShouldTakeLessThan` at `driver_test.go:186-193`:

```go
s.Stats.ShouldAnswerWithin(5, func() { s.Stats.Summary() })
s.Stats.ShouldAnswerWithin(2, func() { s.Players.Find(Name("Casemiro")) })
```

**Why it matters.** Lesson 306 lists *resource contention* and *environment changes* as root causes of intermittency, and is blunt that timing is the classic non-deterministic axis: a 2-second budget that passes on your laptop will fail under load on a shared CI box — not because anything is broken, but because the box was busy. That is exactly the failure that "compromises our trust… the more we tolerate intermittency, the less we can rely on them as a definitive statement of releasability." A performance budget is a real requirement (it's in TASK.md), but it does not belong as a hard assertion inside the behaviour suite, where a false red undermines every other result.

**Fix.** Move performance out of the pass/fail acceptance path — run it as a separate, clearly-labelled benchmark/monitoring check that can be tracked for trend and allowed to be noisy, and keep the acceptance suite asserting *behaviour*:

```go
// before — a timing budget masquerading as an acceptance test
t.Run("shouldAnswerAggregateQuestionsQuickly", func(t *testing.T) {
    s.Stats.ShouldAnswerWithin(5, func() { s.Stats.Summary() })
})

// after — behaviour here; performance tracked separately (go test -bench, or a monitored SLO)
t.Run("shouldSummariseWithoutError", func(t *testing.T) {
    s := NewSoccer(t)
    s.Stats.Summary()
    s.Stats.ShouldShow("Average goals per match")
})
```

### Priority 2 — The suite depends on a large shared fixture it doesn't own (isolation)

Throughout `specs_test.go`: `ShouldHaveChampion("Flamengo", 90)` (`:117`), `ShouldRelegate("Avaí", "Vasco", "Goiás", "Joinville")` (`:132`), `ShouldRankFirst("Ederson")` (`:104`).

**Why it matters.** Lesson 302 is categorical: "no writable data should be shared between tests," each test should "create and own its own data," and Dave recommends "use only synthetic data, created by your DSL." This suite does the inverse — every assertion is pinned to exact values derived from one big production-like dataset that no test owns. The consequence is already visible in `docs/atdd-findings.md`: five separate occasions where a data correction forced a spec to be "corrected to the data" (Ederson overtaking Alisson, the 377-of-380 match gap, relegation corruption). That churn *is* the shared-fixture fragility Dave warns about, surfacing as spec maintenance.

I want to be fair: this is a read-only query system, so there is no *write* leakage between tests, and each test spawns its own fresh server process (`NewMCPDriver`, `driver_test.go:51`) — genuinely strong process isolation. You cannot fully "create your own" historical match data; the domain is real history. But you can stop asserting on volatile exact values and assert on the stable, domain-meaningful invariant instead:

```go
// before — brittle: one data fix and this breaks (and has, per the findings log)
s.Competitions.Standings(Season(2019))
s.Competitions.ShouldHaveChampion("Flamengo", 90)

// after — the durable truth the spec actually cares about
s.Competitions.Standings(Season(2019))
s.Competitions.ShouldCrownChampionTopOfTable()   // champion == rank 1, points == max(points)
// assert the *relationship*, not the magic number 90
```

Where a concrete value is the point of the test (e.g. a known historic scoreline), keep it — but reserve exact-value assertions for genuinely immutable facts, not computed aggregates that shift when the dataset is cleaned.

### Priority 3 — Non-deterministic tie-breaking in the SUT, asserted on by the specs (intermittency)

`soccer/queries.go:344-352` ranks records with a **non-stable** `sort.Slice` over records gathered from a Go **map** (randomised iteration order). The specs assert on the resulting order: `ShouldRankFirst` (`driver_test.go:171`) and especially `ShouldMarkRelegated`, which asserts an **exact ordered list** of four teams (`driver_test.go:195-204`).

**Why it matters.** Lesson 306: non-determinism "is nearly always about concurrency" — but map-iteration-order + non-stable-sort is the same class of defect, an uncontrolled variable in the SUT. When two teams tie (your own findings note Santos and Palmeiras both on 74 pts in 2019), the order flips run-to-run, and `ShouldRelegate("Avaí", "Vasco", "Goiás", "Joinville")` will intermittently fail on a comma-joined order mismatch even though nothing is broken. Dave: "if your tests are intermittent now, the chances are they're telling you about a real intermittent bug in your system" — here the fix is a definite secondary sort key in the SUT (name, say), after which the test becomes trustworthy. This is a case where the acceptance test has correctly found a determinism gap; honour it by fixing the SUT's ordering rather than loosening the test.

## 4. Further improvements

- **Weak substring assertions dilute the specs** (lesson 103b: specs should be *accurate*). `ShouldShow("1. ")` (`specs_test.go:156`), `ShouldShow("2019")` (`:151`), `ShouldShow("Relegated")` (`:127`), `ShouldInclude("Flamengo", "Corinthians", "-")` (`:53`) assert almost nothing about the outcome — `"1. "` or `"-"` would pass on wildly wrong output. Tighten these to assert the actual domain fact (e.g. that the most-recent meeting returns a dated scoreline between those two teams).
- **Implementation vocabulary leaking into specs** (lesson 103b). `By("goals_for")`, `By("home_win_rate")` (`:75`, `:80`) and `Position("GK")` (`:103`) push column-name / code strings up into the test case. Prefer domain phrasing in the DSL (`By(TopScorers)`, `Position(Goalkeeper)`) so the spec stays in the language of football, not of the data schema.
- **Inconsistent DSL shape** (lesson 301, same-abstraction principle). Most methods take `...Param`, but `HeadToHead(a, b string)`, `FindLastMeeting(a, b string)` and `FindFinals(competition string)` take positional strings and build maps inline (`dsl_test.go:56-61, 72-74`). Unifying on the `Param` style keeps one consistent vocabulary and makes defaults/aliasing uniformly available.
- **`ShouldContain` as the dominant assertion primitive** (`driver_test.go:111`) couples many specs to exact output text; combined with the format-coupled `matchLine` regex (`:120`), a cosmetic change to the server's rendering ripples into the suite. Consider asserting against a lightly-parsed structured view rather than rendered prose.
- **Swallowed decode error** (category G, minor). `Ask` ignores the error from `json.Unmarshal(raw, &res)` (`driver_test.go:104`); a malformed response would surface only as a confusing downstream assertion. A checked unmarshal with a clear Fatalf keeps failures honest at the point they occur.
- **No `t.Parallel()`.** The process-per-test design is already parallel-safe (read-only SUT, isolated processes); lesson 302 prizes parallelisability, so this is free speed once the timing assertions in Priority 1 are gone.

## 5. Suggested next steps

The architecture is right — do **not** restructure it. Work in this order:

1. **Pull the timing assertions out of the acceptance path** (Priority 1) — the single biggest win for trust, and quick.
2. **Fix the SUT's tie-break ordering** (Priority 3): add a stable secondary sort key and switch `sort.Slice`→`sort.SliceStable`, then the ordered relegation/ranking assertions become reliable.
3. **Shift computed-aggregate assertions from magic numbers to invariants** (Priority 2), which will stop the recurring "correct the spec to the data" churn your findings log is tracking.
4. Then mop up the weak assertions and DSL-consistency items at leisure.

Do these and this moves from "a good suite with two flaky seams" to one you can genuinely treat, in Dave's words, as "a definitive statement of the releasability of our system."

---

```json
{"acceptance_tests_found": true, "ratings": {"A": 3, "B": 4, "C": 2, "D": 3, "E": 3, "F": 2, "G": 3}, "disclosure": "full"}
```