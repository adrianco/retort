I now have full lessons for every category A–G (all `disclosure: "full"`, paid tier). I've read the complete test suite. Here is the review.

---

# ATDD Review — Brazilian Soccer MCP Server test suite

Files reviewed: `acceptance_test.go` (27 specs), `dsl_test.go` (the `soccerDSL`), `driver_test.go` (the `mcpDriver` protocol driver). Criteria drawn live from Dave Farley's ATDD course — lessons 103b & 203 (BDD), 301 (DSL), 302 (Test Isolation), 303 (Protocol Drivers & Stubs), 305 (Four Layer Model), 306 (Intermittent Tests). All content returned in full (paid tier), so this review is against the full lessons, not summaries.

## 1. Overall assessment

This is a genuinely good, deliberately-built ATDD suite — well above average, and clearly written by someone who knows the four-layer model rather than someone who stumbled into it. The three files map almost exactly onto Dave's layers: domain-language test cases → a reusable `soccerDSL` → a real protocol driver that talks to the system *only* through its genuine public interface (MCP JSON-RPC over a pipe) → the SUT. The specs read in the language of the problem, test names use the "Should" tactic, there are no sleeps, no hidden skips, and errors are surfaced loudly. The weaknesses are real but narrow: the assertions are coupled to the *presentation format* and to *specific fixture values* in a way Dave warns against, isolation is essentially absent (mitigated, but not excused, by the read-only data), and one spec encodes a wall-clock timing threshold that is a classic intermittency risk. None of this is structural — the architecture is sound and the fixes are refinements, not a rebuild.

## 2. Strengths

- **Textbook four-layer separation (lesson 305).** `acceptance_test.go` says nothing about MCP or CSV; the DSL carries domain verbs; `mcpDriver` is the only layer that knows the wire protocol. The code comments even state this intent, and the implementation honours it.
- **The protocol driver talks to the SUT through its real interface (lesson 303).** `driver_test.go:27-50` performs the actual MCP `initialize` handshake and drives `tools/call` over a JSON-RPC pipe. This is exactly Dave's "talk to the SUT via its natural interfaces" — not reaching into internal functions. It means these specs would stay true against a completely different implementation behind the same MCP contract.
- **Atomic steps with pass/fail in the PD (lesson 305 / 306).** `callTool` (`driver_test.go:86-103`) fails the test on an RPC error or `IsError`, so if control returns, the step happened. `assertMentions`/`assertNotMentions` live in the driver and produce good diagnostic messages (`"expected answer to mention %q, got:\n%s"`) — precisely the "good error messages at the level of the spec writer" Dave calls for.
- **Reuse in the DSL (lesson 203, mistake #3; lesson 301).** `WhenAskingForMatches`, `WhenAskingForStandings`, etc. are shared across many specs rather than reimplemented per test, and the DSL is decomposed by domain area (matches, players, standings, statistics) — the decomposition Dave recommends to avoid "a giant, hard-to-maintain" DSL.
- **Releasability honesty (category G).** No `t.Skip`, no `//go:build ignore`, no commented-out tests, no swallowed errors, no CI exclusion filters (and `docs/atdd-findings.md` shows failing specs were used to *drive* fixes, not suppressed). The suite tells the truth about its state.

## 3. Priority issues

### Priority 1 — Assertions are coupled to the output format and to data-source internals (lessons 103b, 203)

This is the highest-leverage problem. Dave's calculator example (lesson 103b) is explicit: `Then the result should be 120` is a durable outcome; `...120 on the screen` leaks the implementation. Several specs here assert the *rendered string*, not the outcome:

- `acceptance_test.go:78` — `ThenAnswerMentions("1. Flamengo - 90 pts", "Champion")`
- `acceptance_test.go:66` — `ThenAnswerMentions("Matches: 19", "Win rate:")`
- `acceptance_test.go:102` — `ThenAnswerMentions("1. Neymar Jr - Overall: 92")`

The *values* (Flamengo champion, 90 points, 19 matches) are good domain outcomes. What's coupled is the exact rendering — the leading `"1. "`, the `" - 90 pts"` suffix, the `"Matches: "` label. Change a formatter and green tests go red though nothing is broken — the "narrowly correct" trap lesson 103b names.

The clearest violation is `TestShouldCoverEveryProvidedDataset` (`acceptance_test.go:161-166`), which asserts CSV filenames:

```go
s.ThenAnswerMentions("Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", ...)
```

Apply Dave's test (lesson 203): *imagine this spec fulfilled by a completely different system* — say, the same data served from Postgres. It can't be; it's hard-wired to the CSV implementation. That makes it a design assertion, not a behaviour spec.

**Before → after.** Push the formatting knowledge down into the DSL/PD and assert outcomes. For standings:

```go
// before (acceptance_test.go:75-79)
s.WhenAskingForStandings("season: 2019")
s.ThenAnswerMentions("1. Flamengo - 90 pts", "Champion")

// after — asserts the outcome, not the rendering
s.WhenAskingForStandings("season: 2019")
s.ThenChampionIs("Flamengo")
s.ThenPointsFor("Flamengo", 90)
```

…where `ThenChampionIs`/`ThenPointsFor` parse the response inside the DSL/PD (the layer Dave says is allowed to know the format). For coverage, assert the domain fact rather than the filenames:

```go
// after — true against any backing store
s.WhenAskingWhatDataIsAvailable()
s.ThenDataCovers("Brasileirão", "Copa do Brasil", "Libertadores")
s.ThenPlayerDataIsAvailable()
```

### Priority 2 — No functional or temporal isolation; specs are pinned to a large shared fixture (lesson 302)

Lesson 302's core advice: *"Avoid starting up the SUT with lots of state — generate the state you want the SUT to be in within your test,"* using functional isolation entities and temporal aliasing. This suite does the opposite: every spec queries one large, pre-loaded dataset (`Load("data/kaggle")`, `driver_test.go:30-34`) and asserts specific values that exist in that fixture today — `"Neymar Jr - Overall: 92"`, `"90 pts"`, `"Matches: 19"`.

In fairness, the SUT is a **read-only** reference-data service, so Dave's *write*-isolation concern (tests corrupting each other's data) doesn't bite — the suite is deterministic and the tests cannot interfere, which satisfies the *spirit* (trust/repeatability) of lesson 302. That is why this is Priority 2, not Priority 1. But the mechanism Dave prescribes is entirely absent, and the consequence he warns about is real here: the assertions are a maintenance liability keyed to a specific dataset snapshot. Refresh the Kaggle CSVs and specs break for reasons unrelated to system correctness.

Because you can't "create" historical matches, the practical move is to *narrow each spec's dependence to the one fact it is about* and assert relationships rather than exact leaderboard positions:

```go
// before (acceptance_test.go:99-103) — pinned to one row's exact value & rank
s.WhenSearchingForPlayers("nationality: Brazil", "limit: 3")
s.ThenAnswerMentions("1. Neymar Jr - Overall: 92")

// after — asserts the behaviour (sorted, filtered) without pinning the fixture
s.WhenSearchingForPlayers("nationality: Brazil", "limit: 3")
s.ThenResultsAreAllBrazilian()
s.ThenResultsAreRankedByRatingDescending()
s.ThenTopResultIs("Neymar Jr") // the one fact this spec is really about
```

This keeps each spec true to a single outcome (lesson 305's "assert a single outcome") and shrinks the blast radius when the dataset changes.

### Priority 3 — A wall-clock timing assertion is an intermittency risk (lesson 306)

`TestShouldAnswerAggregateQuestionsQuickly` (`acceptance_test.go:174-178`) asserts `ThenAnswerArrivedWithinSeconds(5)` via elapsed wall-clock (`dsl_test.go:81-86`). Lesson 306 lists *environment changes* and *resource contention* among the handful of root causes of intermittency — and a fixed wall-clock threshold inside a functional acceptance test is exactly environment-sensitive: on a loaded CI box, this flakes while nothing is actually broken. It is the mirror image of the sleep anti-pattern Dave condemns — instead of waiting a fixed time, it *fails* on a fixed time — and it couples a non-functional performance requirement into the behaviour suite.

Dave's principle is that a failing acceptance test must be a trustworthy, definitive statement of releasability. A test that goes red because CI was busy erodes exactly that trust. Options, in order of preference:

- **Move performance out of the behaviour suite** into a separate, explicitly-tagged performance check where a threshold is the point and the environment is controlled (lesson 306's Infrastructure-as-Code/controlled-environment advice).
- If you keep a smoke-level guard here, make it a generous ceiling that only catches catastrophic regressions (e.g. tens of seconds), and name it so its intent is unmistakable — not a 5-second SLA masquerading as a functional spec.

## 4. Further improvements

- **DSL has no explicit defaults (lessons 301, 305).** Dave singles out default values as a primary thing the DSL adds, "so test cases only specify the things they care about." Here `params()` (`dsl_test.go:23-33`) just forwards whatever string pairs are passed; defaults live implicitly in the SUT. Consider giving the DSL real defaults (e.g. a default competition/season) so specs read even closer to intent.
- **Stringly-typed parameters.** `"season: 2023"`, `"venue: home"` are parsed from strings. This works and is reusable, but loses the type-safety and code-completion that lesson 301 cites as a key advantage of an *internal* DSL. Typed helper constructors would strengthen it.
- **A couple of specs assert two outcomes** (`TestShouldFindCopaDoBrasilFinals` :20-26, `TestShouldCompareTwoSeasons` :129-135). Minor, but lesson 305's "be VERY sceptical of long, complex test cases / assert a single outcome" suggests splitting these.
- **Stubs: not applicable (lesson 303)** — the SUT has no external dependencies to fake, so the absence of stubs is correct, not a gap. Noting it so it's clearly a considered N/A, not an oversight.

## 5. Suggested next steps

1. **Start with the assertion coupling (Priority 1).** Add outcome-level `Then…` methods to the DSL (`ThenChampionIs`, `ThenPointsFor`, `ThenDataCovers`, `ThenResultsAreRankedBy…`) that parse the response in the DSL/PD layer, and replace the format-string and CSV-filename `ThenAnswerMentions` calls. This is the biggest durability win and it reinforces the layering you already have.
2. **Then narrow the fixture dependence (Priority 2)** by reworking each pinned-value spec to assert the single relationship it's about, so dataset refreshes don't cause spurious failures.
3. **Relocate the timing assertion (Priority 3)** out of the behaviour suite.
4. Leave the architecture, the protocol driver, and the releasability discipline as they are — they're strong, and they're what makes the above refinements cheap to apply.

```json
{"acceptance_tests_found": true, "ratings": {"A": 3, "B": 4, "C": 2, "D": 3, "E": 4, "F": 3, "G": 4}, "disclosure": "full"}
```