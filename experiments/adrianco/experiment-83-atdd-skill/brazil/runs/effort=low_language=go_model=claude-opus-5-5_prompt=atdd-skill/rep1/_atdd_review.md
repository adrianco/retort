I now have Dave's material for every category (all returned `disclosure: "full"` from the paid tier). Here's the review.

---

# ATDD Review — Brazilian Soccer MCP Server acceptance suite

I reviewed the three files in `acceptance/` (`specs_test.go`, `dsl_test.go`, `driver_test.go`), which together form the acceptance / end-to-end suite — they drive the **real** MCP server in-process over JSON-RPC pipes. (`soccer/soccer_test.go` and `mcp/server_test.go` are unit/integration tests and sit outside this review.) All criteria below are drawn from Dave's lessons fetched live: *Acceptance Tests & BDD* (203), *Building a DSL* (301), *Protocol Drivers & Stubs* (303), *Test Isolation* (302), *The Four Layer Model* (305), and *Dealing With Intermittent Tests* (306).

## Overall assessment

This is a genuinely well-structured suite — the kind you rarely see. It implements Dave's four-layer model deliberately and cleanly: specs in the language of Brazilian football, a reusable DSL with defaults and named parameters, and a single protocol driver that is the only thing that knows the system speaks MCP. It is on the right track, not mis-structured. Its one deep deviation from Dave's principles is that every spec asserts against a large, fixed, *externally-owned* dataset rather than data the test creates — which the read-only nature of the SUT mostly rescues in practice, but which leaves the specs coupled to a corpus they don't control. A handful of assertions also check rendered formatting rather than behaviour.

## Strengths

- **Textbook four-layer separation** (lesson 305). Test case → DSL → protocol driver → SUT, each at the right abstraction. Layer 1 (`specs_test.go`) says *nothing* about MCP, JSON-RPC or stdio; only `driver_test.go` knows those exist. This is exactly Dave's "layer three is the only place that knows how the system actually works."
- **Would survive a completely different system.** Applying Dave's coupling test from lesson 203 — "imagine the spec fulfilled by a completely different system" — `s.Matches.Find(Team("Palmeiras"), Season(2023))` would hold just as well over REST or GraphQL. The specs are not coupled to the implementation.
- **Protocol driver does the right things** (lesson 303/305): every step is atomic and pass-or-fail (`Ask` fails hard on an error or empty answer), assertions live in the PD, and the error messages are excellent — they report the expected value *and* the actual answer (`"expected answer to mention %q, got:\n%s"`). Dave explicitly calls for "good error messages… at a sensible level for spec writers."
- **Honest about its state** (category G / the trust theme in lesson 306). No `t.Skip`, no build tags excluding tests, no commented-out tests, no CI test-exclusion filters, no swallowed exceptions — every check ends in `t.Fatalf`. The suite is a truthful statement of releasability; nothing green is hiding something red.
- **No sleeps, deterministic by construction** (lesson 306). Synchronous request/response over pipes plus an immutable dataset means whole classes of intermittency simply can't arise.

## Priority issues

### 1. Tests depend on a large external fixture instead of owning their data (lesson 302 & 305) — highest impact

Every spec asserts against exact values baked into the Kaggle CSVs loaded once into a shared read-only `db` (`driver_test.go:28-34`). Nothing is created by the test:

```go
s.Competitions.Standings(Season(2003))
s.Competitions.ShouldHaveChampion("Cruzeiro", 100)          // specs_test.go:121-122
s.Competitions.ShouldRelegate("Avaí", "Vasco", "Goiás", "Joinville")  // :132
```

Dave's guidance in lesson 305 is blunt: *"try to use only synthetic data, created by your DSL… Avoid starting up the SUT with lots of state — generate the state you want the SUT to be in within your test."* And in lesson 302 he puts replaying a fixed external corpus in the "ultimately a poor alternative" bucket. Two concrete costs here: (a) a spec reader can't tell *why* Cruzeiro-100 or those four relegated clubs are the right answer — the "Given" is invisible, living in a CSV; (b) if the dataset is ever re-pulled or corrected, dozens of specs break for reasons that have nothing to do with the system's behaviour.

The mitigation worth acknowledging: because the SUT is read-only, the *interference* and *determinism* goals of functional/temporal isolation are met by accident of immutability — tests can't corrupt each other and re-runs are stable. But the isolation *patterns* Dave teaches (a functional-isolation entity per test, aliasing for temporal isolation) are entirely absent, and the coupling to uncontrolled data is real.

Direction (no change applied — this is a non-interactive review): make each spec's "Given" explicit and test-owned. The strongest version has the DSL seed a small synthetic corpus into the SUT so the spec reads as a self-contained statement:

```go
// before — magic constants from an external CSV
s.Competitions.Standings(Season(2003))
s.Competitions.ShouldHaveChampion("Cruzeiro", 100)

// after — the test owns the facts it asserts on
s.Given.Season(2003, "Brasileirão Série A").
    TeamFinished("Cruzeiro", points(100), top()).
    TeamFinished("Avaí", relegated())
s.Competitions.Standings(Season(2003))
s.Competitions.ShouldHaveChampion("Cruzeiro", 100)
s.Competitions.ShouldRelegate("Avaí")
```

That requires the SUT to accept injected data. If that's genuinely out of scope and the fixed corpus *is* the product boundary, the lighter move is at least to name the givens — a per-spec comment or helper stating the expected standing — so the spec documents its own premise rather than relying on knowledge locked in a CSV.

### 2. Several assertions check rendering, not behaviour (lesson 203)

Dave's first and most common BDD mistake is "confusing UI interactions with behaviour." A few assertions here check the *formatting* of the answer rather than the fact:

```go
s.Matches.FindLastMeeting("Flamengo", "Corinthians")
s.Matches.ShouldInclude("Flamengo", "Corinthians", "-")   // specs_test.go:52-53  ("-" is a score separator)
...
s.Stats.BiggestWins()
s.Stats.ShouldShow("1. ")                                  // :156  (asserts a numbered-list artifact)
```

Asserting on `"-"` or `"1. "` ties the spec to the presentation layer — the exact thing the four-layer model exists to keep out of the top layer. Related, the season-comparison spec asserts something trivially true:

```go
s.Stats.Summary(Competition("Brasileirão Série A"), Season(2018))
s.Stats.Summary(Competition("Brasileirão Série A"), Season(2019))
s.Stats.ShouldShow("2019")                                 // :149-151
```

`"2019"` is present simply because you queried 2019; the spec's stated intent ("compare two seasons") isn't actually asserted. Rewrite these to assert the *behaviour*:

```go
// before
s.Stats.BiggestWins(); s.Stats.ShouldShow("1. ")
// after — a domain fact, not a list artifact
s.Stats.BiggestWins(); s.Stats.TopResult().ShouldBe("Santos 8-0 Bolívar")

// before — trivially true
s.Stats.ShouldShow("2019")
// after — the actual comparison outcome
s.Stats.ShouldReportHigherScoringSeason(2019, Than(2018))
```

The `By("goals_for")` / `By("home_win_rate")` parameters (`specs_test.go:75,80`) leak a snake_case data-column name into the spec — prefer a domain term (`By(Goals)`, `By(HomeWinRate)`).

### 3. The DSL leaks SUT protocol detail that belongs in the protocol driver (lessons 301/303/305)

Dave's DSL should present "a stable interface that doesn't change as the SUT evolves," insulated from SUT detail. But the DSL layer names the MCP tool strings and raw wire argument keys directly:

```go
func (m *Matches) FindFinals(competition string) {
    m.d.Ask("search_matches", map[string]any{"competition": competition, "finals_only": true, "limit": 500})
}   // dsl_test.go:56-58
func (m *Matches) FindLastMeeting(a, b string) {
    m.d.Ask("last_meeting", map[string]any{"team_a": a, "team_b": b})
}   // :59-61
```

`"search_matches"`, `"last_meeting"`, `"finals_only"`, `"team_a"` are the *SUT's* vocabulary — per lesson 305 that knowledge belongs one layer down, in the protocol driver. Today a tool rename ripples into the DSL. Push the mapping into the PD so the DSL speaks only domain terms:

```go
// DSL
func (m *Matches) FindLastMeeting(a, b string) { m.d.LastMeeting(a, b) }
// PD (driver_test.go) — the only place that knows the MCP tool names
func (d *MCPDriver) LastMeeting(a, b string) {
    d.Ask("last_meeting", map[string]any{"team_a": a, "team_b": b})
}
```

That said, the DSL is otherwise good: real reuse (`Find` serves many specs), defaults (`limit:500`, `by:"points"`), named parameters via functional options, and decomposition by domain area (Matches/Teams/Players/Competitions/Stats) exactly as lesson 305 recommends.

## Further improvements

- **Timing assertions are the one genuine flakiness risk** (lesson 306). `shouldAnswerAggregateQuestionsQuickly` (`specs_test.go:161-165`) asserts wall-clock budgets (5s/2s). Dave lists resource contention and environment as core intermittency causes; a loaded CI box can blow a 2s budget and go red for no real defect. In-process timing also isn't representative of production latency. Consider moving performance budgets to a dedicated performance check rather than the correctness suite.
- **No read timeout in the PD.** `rpc` blocks on `ReadBytes('\n')` (`driver_test.go:69`); a server that never answers hangs the test instead of failing it. Dave's poll-with-timeout philosophy (lesson 306) favours a bounded wait that *fails* — "believing our software is broken when it isn't is a lot better than thinking it works when it doesn't."
- **Parallel-safe but not parallelised.** Because the data is immutable, these tests could safely `t.Parallel()` for the fast feedback lesson 302 prizes — the isolation that normally blocks parallelism is already (accidentally) present.
- **Inconsistent DSL parameter style.** Most methods take `...Param`, but `FindFinals`, `FindLastMeeting`, `HeadToHead`, `Competitions` take raw strings. Harmonising on the `Param` pattern would make the DSL more uniform to read and extend.

## Suggested next steps

The architecture does **not** need restructuring — the four-layer model is already in place and clean, which is the hard part. Focus effort here:

1. **Decide the data story (issue 1)** — this is the highest-leverage change. Either give the SUT a way to accept test-seeded synthetic data so specs own their givens, or, if the fixed corpus is the product, make each spec's premise explicit and self-documenting.
2. **Re-point rendering assertions at behaviour (issue 2)** — cheap, high-value, removes brittle couplings to output text.
3. **Move the SUT tool-name/arg mapping down into the PD (issue 3)** — a mechanical refactor that restores the layer boundary.
4. Then mop up the timing-assertion flakiness and add a PD read timeout.

```json
{"acceptance_tests_found": true, "ratings": {"A": 3, "B": 4, "C": 2, "D": 3, "E": 3, "F": 3, "G": 4}, "disclosure": "full"}
```