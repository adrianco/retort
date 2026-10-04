I now have the full lessons for every category (paid tier, full disclosure). I've read both test files and the SUT. Here is the review.

---

# ATDD Review — Brazilian Soccer MCP test suite

Reviewed: `test/queries.test.ts` (31 tests) and `test/server.test.ts` (1 test). I assessed the acceptance/end-to-end tests — the 24 "sample question" cases (`Q1`–`Q24`) and the MCP round-trip. The CSV-parser, normalization and date tests are genuine unit tests and are correctly pitched at that level (exactly where Dave wants edge cases to live), so they're out of scope here except as a positive signal.

Criteria below are drawn live from Dave Farley's ATDD course (lessons 103b, 203, 301, 302, 303, 305, 306), fetched at full disclosure.

## 1. Overall assessment

This is a careful, genuinely useful test suite — it's deterministic, it's honest, and the *intent* of the acceptance cases is outcome-focused (each `Q` maps to a real user question). But as **ATDD acceptance tests** they are structurally shallow: there is no DSL and no protocol-driver layer, so the test cases reach straight into the system's internal functions (`q.champion(ds, …)`, `q.standingsData(ds, …)`) and assert against exact output-string formats. That couples the specifications to the current implementation in exactly the way Dave's course warns against. The good news: the *content* of what you assert is domain-shaped, so the gap is architectural, not conceptual — you have the right outcomes, you just need the two missing layers between them and the code.

## 2. Strengths

- **Honest about its state (Dave would single this out).** No `skip`/`xit`/`.only`, no test filters, no `continue-on-error`, no commented-out tests, no swallowed exceptions. The README's "32 tests" matches the actual count. The error path is *asserted*, not hidden — `server.test.ts:20` checks `bad.isError === true`. A green run here genuinely means green.
- **No sleeps or waits anywhere**, and `server.test.ts` awaits the real MCP response rather than sleeping — this is precisely the event-confirmation posture lesson 306 asks for.
- **Questions phrased in the domain.** `Q10 who won 2019 Brasileirão`, `Q12 relegated in 2020` — the test *names* speak the problem domain, which is the raw material for a good DSL.
- **The MCP round-trip (`server.test.ts`) is a real end-to-end test** through the actual public protocol, and its steps are atomic.

## 3. Priority issues

### Priority 1 — Specs assert implementation output, not durable outcomes (Category A)

**Lesson 103b / 203.** Dave's durability test: *"imagine the spec being fulfilled by a completely different system. If it can't be, it's coupled to the implementation."* A good acceptance test "ONLY defines outcomes" and stays true "however we decide to make our calculator work."

Your `Q10` asserts against the exact rendered sentence and internal function names:

```ts
// test/queries.test.ts:96
assert.match(q.champion(ds, 2019), /^Flamengo won the 2019 Brasileirão with 90 points/);
```

The *outcome* is "Flamengo were 2019 champions with 90 points." But this test also pins the exact wording, word order and punctuation of a formatted string, and calls the internal `champion()` function directly. Reword the output, or answer the same question through a different interface, and the test breaks even though the behaviour is unchanged — the "narrowly correct" failure mode from lesson 103b.

**Before → after (in the direction of a DSL):**

```ts
// now — coupled to output format + internal API
assert.match(q.champion(ds, 2019), /^Flamengo won the 2019 Brasileirão with 90 points/);

// toward an outcome through a stable vocabulary
const champ = soccer.champion({ season: 2019 });   // DSL call, not q.champion
soccer.confirmChampion(champ, { team: "Flamengo", points: 90 });
```

The `confirm…` naming is Dave's own habit (lesson 305) — assertions that read as domain statements, not technical `assert`s.

### Priority 2 — No DSL or protocol-driver layer; the suite is two layers, not four (Categories B, D, E)

**Lesson 305 / 301 / 303.** The four layers are test case → DSL → protocol drivers → SUT. Your acceptance tests collapse to two: the test case calls SUT functions directly. There's no reusable test vocabulary with defaults (lesson 301), and no protocol-driver layer owning the "how" and the assertions (lesson 303/305: *"protocol drivers are nearly always where assertions are made… make each step pass or fail"*).

Concretely, every acceptance test threads the raw `ds` singleton and positional args:

```ts
// test/queries.test.ts:47, 66, 72 …
q.headToHead(ds, "Flamengo", "Fluminense");
q.teamRecord(ds, "Corinthians", { season: 2022, competition: "Brasileirão", venue: "home" });
q.rankTeams(ds, { competition: "Serie A", season: 2019, sortBy: "goalsFor", limit: 1 });
```

That's the production API, used as if it were a test language. The shape to aim for (lesson 305, "every new feature follows the same recipe"):

```ts
// Layer 1 — test case (domain only, no ds, no formatting)
test("Corinthians' 2022 home league record", () => {
  const rec = soccer.teamRecord({ team: "Corinthians", season: 2022, venue: "home" });
  soccer.confirmHasWinRate(rec);          // assertion lives below the test case
});

// Layer 2 — DSL: defaults (competition defaults to Brasileirão), hides `ds`
// Layer 3 — protocol driver: calls q.teamRecord, parses, fails with a domain-language message
```

Notice you already have the seed of Layer 3 in `server.test.ts`: the MCP `Client` **is** a real protocol driver into the system. The highest-leverage move is to route the acceptance cases *through that MCP channel* (the actual way users reach this server) behind a small DSL, rather than calling `q.*` directly. Lesson 303's payoff — one spec, swappable drivers — then becomes available to you for free.

### Priority 3 — A wall-clock timing assertion is a built-in flaky test (Category F)

**Lesson 306.** Dave is blunt about timing-based tests: resource contention is a named root cause of intermittency, and an absolute time threshold "will fail again at some indeterminate point in the future."

```ts
// test/queries.test.ts:170-177
const t = Date.now();
q.rankTeams(ds, { venue: "away" }); /* … */
assert.ok(Date.now() - t < 2000);
```

On a loaded CI runner this can fail with nothing broken — the exact trust-destroying signal lesson 306 warns against. Performance is a real concern, but it belongs in a dedicated benchmark that's allowed to be noisy, not in the acceptance suite whose job is a "definitive statement of releasability." Either delete the wall-clock bound from the acceptance run, or move it to a separate benchmark that reports rather than asserts.

## 4. Further improvements

- **Single-outcome discipline (A / lesson 305: "be VERY skeptical about long, complex test cases").** Several cases bundle outcome + structural invariants, e.g. `Q1` asserts the h2h string *and* `aWins+bWins+draws === matches.length` *and* `matches.length > 30` (`queries.test.ts:47-52`), and `Q10` asserts a sentence *and* a table length *and* exact W/D/L. Split the data-structure invariants down into unit tests; let each acceptance case assert one outcome.
- **Coupling to a large real fixture (C / lesson 302, 305: "use only synthetic data… avoid starting up the SUT with lots of state").** The suite leans on a big pre-loaded dataset and exact counts — `ds.players.length === 18207` (`:37`), `[t[0].wins,…] === [28,6,4]` (`:99`). The read-only nature means tests don't *leak* into each other (good — no cleanup needed, which Dave likes), so isolation is safe; but these exact-value assertions are environment-sensitive (a changed CSV, a new data file, or `SOCCER_DATA_DIR`), which is the test-data-stability risk from lesson 306. Prefer deriving expectations or asserting ranges/known facts over brittle magic counts.
- **Assertion error messages (E / lesson 305).** Regex-match failures here report "expected match" with no domain context. When you add the PD layer, give it messages pitched "at a sensible level for spec writers… in the language of the problem domain."

## 5. Suggested next steps

1. **Introduce a thin DSL object** (`soccer.*`) with named-parameter calls and defaults (competition → Brasileirão), hiding the `ds` singleton. This alone fixes most of Category A and D with no change to the SUT.
2. **Make the MCP `Client` your protocol driver.** Route the acceptance cases through the real tool interface behind the DSL, and move assertions into PD-level `confirm…` methods with domain-language failures. This is the lesson-305 recipe and turns `server.test.ts` from a lone smoke test into the backbone of the suite.
3. **Pull the wall-clock perf check out of the acceptance run** (Priority 3).
4. Keep doing what you're doing on honesty and on no-sleeps — those are already at the standard Dave sets.

This is a "finish the architecture that's implied" job, not a rebuild: your outcomes are sound and the MCP client already gives you a real protocol driver to build on.

```json
{"acceptance_tests_found": true, "ratings": {"A": 2, "B": 1, "C": 2, "D": 1, "E": 1, "F": 3, "G": 4}, "disclosure": "full"}
```