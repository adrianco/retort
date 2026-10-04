I now have the full lessons for every category A–F (full disclosure, paid tier), category G's checklist from the skill itself, plus the code facts: no skipped/ignored tests, no CI exclusions, no swallowed errors. Here is the review.

---

# ATDD Review — Brazilian Soccer MCP Server (`server_test.go`)

I reviewed all tests in the working directory against Dave Farley's ATDD principles, fetching the relevant course lessons for each category first. Two of the tests are genuinely acceptance/end-to-end in character:

- **`TestSampleQuestions`** — maps 26 real end-user questions to a tool call and asserts on user-visible output. This is your acceptance surface.
- **`TestMCPProtocol`** — drives the full JSON-RPC wire protocol through `Serve` (initialize → notifications → tools/list → tools/call → error cases). This is a real end-to-end test.

The remainder (`TestNormalization`, `TestParseDate`, `TestStandings`, `TestPlayers`, etc.) are unit/integration tests and I've treated them as the supporting pyramid, not acceptance tests.

## 1. Overall assessment

This is a careful, honest, deterministic test suite — and that honesty is its single biggest strength against Dave's principles. But structurally it is **not** built the ATDD way: there is no four-layer separation. The acceptance tests reach straight into the system under test (`db.CallTool`, `db.Serve`) and assert on tool names, raw JSON-RPC envelopes, and output substrings. The good news is that the *raw material* for a proper ATDD suite is already here — the natural-language questions in `TestSampleQuestions` are exactly the domain-language specs Dave wants — they're just relegated to a comment-like label while the test asserts the implementation underneath. The work ahead is less "rewrite everything" and more "extract the DSL and protocol driver that your tests are currently inlining."

## 2. Strengths (don't lose these)

- **The suite is scrupulously honest about its state (category G — exemplary).** No `t.Skip`, no `//go:build ignore`, no `-run`/`-skip` exclusions, no CI `continue-on-error`, no commented-out tests, no swallowed errors anywhere. Every test runs and asserts every build. It even asserts a *known limitation* openly — the Flamengo case expects the output `"does not include"` because the FIFA dataset omits some Brazilian clubs. That is precisely the releasability truthfulness Dave cares about: the build is green because things work, not because failures are hidden.
- **Real domain-language intent is captured.** Each `TestSampleQuestions` case carries a question like *"Who won the 2019 Brasileirão?"* — the language of the problem domain, free of implementation. Lesson 103b ("BDD: Defining the Behaviour of the System") would applaud these as the starting point of good specs.
- **`TestMCPProtocol` is a genuine end-to-end test** and checks the unhappy paths (unknown tool → `isError`, unknown method → JSON-RPC error), not just the happy path.
- **No sleeps or waits anywhere** — the instinct Dave is bluntest about in lesson 306 is already right.
- **Deterministic, read-only, cleanup-free data** — the `sync.Once` in-memory DB means tests can't leak into each other and would be parallel-safe.

## 3. Priority issues

### Priority 1 — The specs assert *how* the system answers, not *what* the answer is (category A)

`TestSampleQuestions` pairs each domain-language question with a hard-coded tool and argument set, then checks weak substrings:

```go
// server_test.go:190
{"Show me all Flamengo vs Fluminense matches", "head_to_head",
    `{"team1":"Flamengo","team2":"Fluminense"}`, []string{"Fla-Flu", "Head-to-head", "Flamengo"}},
```

The question is the specification; `"head_to_head"` + `{team1,team2}` is the *design*. This is exactly Dave's **mistake #1 — confusing UI/implementation interactions with behaviour** (lesson 203): the test says *"I press the `head_to_head` button with these args"* rather than *"when I ask for the matches between these teams, I should see their head-to-head record."* Apply Dave's own litmus test (lesson 203): *imagine a completely different system fulfilling this spec.* If your LLM router answered the same question via `search_matches` with both teams set — identical answer to the user — this test would break. That means it's coupled to the implementation, not the behaviour. The whole point of this server is LLM-driven routing, and the acceptance test bypasses it.

The expected outcomes are also implementation/format leakage — `"Found"`, `"1. "`, `"/match"` are presentation artefacts, not domain outcomes.

**Before → after** (the shape, using an internal DSL per lesson 301):

```go
// Before: couples the spec to a tool name, JSON args, and output format
{"Who won the 2019 Brasileirão?", "standings", `{"season":2019}`, []string{"Champion: Flamengo"}},

// After: the spec states the outcome; the DSL decides how to get it
ask("Who won the 2019 Brasileirão?").
    confirmChampion("Flamengo", season(2019))
```

`ask(...)` lives in a DSL that owns the routing (eventually even the real LLM dispatch); `confirmChampion` asserts the domain outcome. Now the spec stays true "even if the system later takes voice input" (lesson 103b) — or routes the question differently.

### Priority 2 — No four-layer separation; tests inline the protocol driver (categories B, D, E)

Lesson 305 lays out the four layers: test case → DSL → protocol drivers → SUT. Your acceptance tests collapse all of this into the test body. The clearest symptom is in `TestMCPProtocol`, where the test case itself does the protocol driver's job — hand-building JSON-RPC strings and spelunking through raw `map[string]any`:

```go
// server_test.go:273
text := resps[2]["result"].(map[string]any)["content"].([]any)[0].(map[string]any)["text"].(string)
if !strings.Contains(text, "Flamengo") {
    t.Errorf("standings call: %s", text)
}
```

Per lesson 303, the JSON-RPC framing, encoding, and response-unwrapping are *protocol driver* responsibilities — "the only place that knows how the system actually works." Per lesson 305, "protocol drivers are nearly always where assertions are made … make each step in a PD pass or fail." Right now there is no DSL (category D — absent) and no protocol driver (category E — absent); the test is both.

**Before → after:**

```go
// Before: test case owns JSON-RPC framing + nested type assertions
in := strings.Join([]string{`{"jsonrpc":"2.0","id":3,"method":"tools/call",...}`}, "\n")
// ...parse 5 lines, assert resps[2]["result"].(map[string]any)...["text"]...

// After: a protocol driver hides the wire format; the DSL speaks the domain
mcp := newMCPDriver(db)                       // layer 3: owns framing + parsing + pass/fail
table := mcp.standings(season(2019), top(1))  // returns a domain object, fails on protocol error
table.confirmChampion("Flamengo")             // layer 2/1: domain-level assertion
```

The same `newMCPDriver` seam is what later lets you run the *same* specs through a second driver (lesson 303's "one interface, many drivers") — e.g. an in-process driver for speed and the real stdio driver for the end-to-end run. You already have both call paths (`db.CallTool` and `db.Serve`); a thin PD interface over them would unify `TestSampleQuestions` and `TestMCPProtocol` into one spec set with two drivers.

### Priority 3 — Wall-clock timing assertions inside the acceptance tests (category F)

Two tests fail on elapsed time:

```go
// server_test.go:224
if el := time.Since(start); el > 2*time.Second {
    t.Errorf("%q took %v", c.q, el)
}
// server_test.go:291
if el := time.Since(start); el > 5*time.Second {
    t.Errorf("aggregate queries took %v", el)
}
```

Lesson 306 names **resource contention** as one of the few root causes of intermittency. A loaded CI box or a cold machine can blow a 2-second budget on perfectly correct code — and because the budget is embedded in the *acceptance* test, a slow run reports "behaviour is broken" when nothing is. This is the same family as the sleep anti-pattern: coupling pass/fail to the clock.

**Before → after:** keep the acceptance assertion purely about correctness; move the performance budget to a dedicated gate that is allowed to be environment-sensitive:

```go
// After: correctness test asserts only the outcome (no timing)
//        performance lives in a benchmark, run under controlled conditions
func BenchmarkAggregateQueries(b *testing.B) {
    db := loadTestDB(b)
    for i := 0; i < b.N; i++ {
        db.TeamRankings("win_rate", 0, "", "home", 0, 10)
        db.CompareSeasons([]int{2015, 2016, 2017, 2018, 2019}, "")
    }
}
```

## 4. Further improvements

- **Synthetic per-test data vs. one large shared corpus (category C).** Every assertion is pinned to the exact bundled CSVs — Flamengo on 90 points, Neymar Jr as top-rated, "Matches: 19". Lesson 302 and 305 are explicit: *"use only synthetic data, created by your DSL … avoid starting up the SUT with lots of state."* A dataset refresh will break a swathe of specs at once — the shared-fixture fragility functional isolation is meant to cure. For a read-only reference engine this is partly inherent (and your determinism is genuinely good), so it's lower priority — but consider a small curated fixture dataset for the behavioural specs, kept separate from the full corpus, so a spec says *"given a season where team X finished on 90 points…"* rather than depending on which rows happen to be in `data/kaggle`.
- **`TestMCPProtocol` asserts response *count* and positional indexing** (`len(lines) != 5`, `resps[2]`). That's brittle to any reordering. A driver keyed by request `id` would be more robust and read at the domain level.
- **Assertion granularity.** The `want` substring lists mix domain outcomes (`"Champion: Flamengo"`) with formatting (`"1. "`, `"Found"`). As you build the DSL, promote the domain ones to real assertions and drop the formatting ones.

## 5. Suggested next steps

1. **Extract a protocol driver** behind the two call paths you already have (`CallTool`, `Serve`). This is the highest-leverage move: it's where `TestMCPProtocol`'s inline JSON-RPC parsing belongs, and it unblocks everything else.
2. **Introduce a thin internal DSL** (`ask(...)`, `confirmChampion(...)`, `showsHeadToHead(...)`) that sits on the driver. Start with the handful of questions already in `TestSampleQuestions` — you don't need Gherkin; lesson 301 endorses an internal DSL in your production language (Go here).
3. **Rephrase the specs as outcomes**, letting the DSL own tool routing, so the questions in `TestSampleQuestions` become the actual assertions rather than labels.
4. **Move the timing budgets out** into benchmarks so the acceptance suite fails only for behavioural reasons.
5. **Keep doing what you're doing on honesty (G)** — whatever you restructure, preserve the no-skips/no-exclusions discipline. It's the part that's already exemplary.

The structure needs real work, but the target is clear and the foundations — honest reporting, domain-language questions, a working end-to-end path, no sleeps — are already in place. That's a good position to build the four layers from.

*(All criteria above were drawn from the full ATDD course lessons 103b, 203, 301, 302, 303, 305, and 306, returned at full disclosure.)*

```json
{"acceptance_tests_found": true, "ratings": {"A": 2, "B": 1, "C": 2, "D": 1, "E": 1, "F": 2, "G": 4}, "disclosure": "full"}
```