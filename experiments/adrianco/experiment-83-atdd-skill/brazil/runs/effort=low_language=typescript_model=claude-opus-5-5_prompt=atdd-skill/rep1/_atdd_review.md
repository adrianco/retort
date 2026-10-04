I now have full lessons for every category (paid tier, `disclosure: full`). I've read the complete suite — a four-layer internal DSL in TypeScript/vitest over a self-contained, read-only MCP server. Here is the review.

---

# ATDD Review — Brazilian Soccer Knowledge acceptance suite

**Files reviewed:** `test/acceptance/soccer-knowledge.spec.ts` (24 specs), `test/dsl/SoccerDsl.ts`, `test/drivers/McpSoccerDriver.ts`, with `src/server.ts` and `src/data.ts` as the SUT. I worked from the **full** course lessons (103b, 203, 301, 302, 303, 305, 306, 308), not summaries.

## 1. Overall assessment

This is a genuinely well-structured suite — one of the cleaner four-layer implementations I've reviewed. Whoever wrote it understood Dave's model and executed it: the spec file reads in the language of Brazilian football with no MCP, CSV or JSON anywhere; the DSL is a real reusable language with named parameters and defaults; and the protocol driver is the single place that knows the system is an MCP server over stdio. The infrastructure is complete and coherent — every DSL verb maps to a real tool, nothing is half-wired or bypassing to the SUT. It is on the right track and needs refinement, not restructuring. The two things holding it back from exemplary are both about **determinism**: wall-clock performance assertions that can flake, and a wholesale dependence on a large fixed dataset that runs against Dave's "synthetic data, created by your DSL" advice.

## 2. Strengths

- **The spec file is a real specification, not a script.** `askForMatchesBetween({ team: "Flamengo", opponent: "Fluminense" })` / `confirmMatchesListed({ atLeast: 10 })` says *what*, not *how*. This is exactly the "say nothing about how the system works" test from lesson 103b — you could re-implement the service behind a REST API or a chat UI and these specs stay true.
- **Clean four-layer separation (lesson 305).** Test case → DSL → protocol driver → SUT, with the technical knowledge (stdio transport, `callTool`, `isError`) quarantined in `McpSoccerDriver`. This is the model done properly.
- **Assertions live in the protocol driver** (`assertMatchesListed`, `assertChampion`, …), and each step is atomic — `ask()` throws on `isError` with the tool name in the message. That's precisely Dave's "make each step in a PD pass or fail… if control returns, you know it happened" (lesson 305).
- **No sleeps, no waits anywhere.** For a suite talking to an async transport, resisting the `sleep(2000)` anti-pattern (lesson 306) is the single most important thing, and this suite gets it right for free because the protocol is synchronous request/response.
- **Honest about its state (category G).** No `.skip`/`.only`/`xit`, no excluded tests, no `continue-on-error`, no swallowed exceptions. `src/server.ts` converts errors to `isError`, and the driver re-throws them — failures propagate to the build. Nothing is hidden.
- **Good DSL hygiene:** named params with sensible defaults (`venue = "all"`, `limit = 20`, `competition = "Brasileirão"`), decomposed by domain area (match/team/player/competition/stats), and lower-bound assertions (`atLeast`) where exactness isn't the point.

## 3. Priority issues

### Priority 1 — Wall-clock performance assertions are an intermittency vector (category F)

`soccer-knowledge.spec.ts:133-139`:

```ts
it("should answer simple lookups within two seconds", async () => {
  await soccer.confirmAnsweredWithin(2000, () => soccer.askForPlayer({ name: "Casemiro" }));
});
it("should answer aggregate queries within five seconds", async () => {
  await soccer.confirmAnsweredWithin(5000, () => soccer.askForBestRecord({ venue: "home" }));
});
```

**Why it matters.** Lesson 306 names *resource contention* as a root cause of intermittency: "Not enough CPU, not enough RAM — these things can make our tests behave differently." A hard 2000ms / 5000ms threshold is a bet on the machine, not on the system. On a loaded CI box, or when vitest runs several test files in parallel against their own spawned `tsx` processes, these will occasionally fail for reasons that have nothing to do with a broken system — which is exactly the trust-destroying failure Dave warns about: "when a test fails, we can trust the failure and reject the change… no running it again in case it's intermittent."

**Fix.** A latency budget is a legitimate thing to care about, but it's an operational/NFR concern, not an executable spec that gates every release. Either move it out of the acceptance suite into a separate, tolerant performance check, or — if it stays — assert a *correctness* outcome and treat timing as a generous guard-rail rather than the point of the test:

```ts
// Before: the test's verdict is a stopwatch reading.
await soccer.confirmAnsweredWithin(2000, () => soccer.askForPlayer({ name: "Casemiro" }));

// After: the spec asserts behaviour; latency is a loose safety net, not the assertion.
it("should answer a player lookup", async () => {
  await soccer.askForPlayer({ name: "Casemiro" });
  await soccer.confirmAnswerMentions("Casemiro");
});
```

### Priority 2 — The suite depends on a large fixed production-like dataset, not synthetic data it owns (category C)

Every spec queries the pre-loaded Kaggle CSVs, and several assert exact figures drawn from them:

- `soccer-knowledge.spec.ts:52` — `confirmRecord({ matches: 19 })`
- `soccer-knowledge.spec.ts:97` — `confirmRelegatedCount(4)`
- `soccer-knowledge.spec.ts:92` — `confirmChampion({ team: "Flamengo", points: 90 })`

**Why it matters.** Lesson 305 is explicit: "try to use only synthetic data, created by your DSL… Avoid starting up the SUT with lots of state — generate the state you want the SUT to be in within your test." Lesson 302 frames the goal as each test *owning* its data. This suite does the opposite: it leans entirely on a big shared reference corpus, so the specs are coupled to the contents of six CSV files. Refresh `fifa_data.csv` or `Brasileirao_Matches.csv` and `matches: 19`, `points: 90`, `confirmTopPlayerIs("Neymar Jr")`, `confirmTopPlayerIs("Ederson")` can all break even though nothing in the service regressed.

**The honest caveat.** This is a *read-only knowledge service over a fixed historical dataset* — you cannot "register a new user" or "create a hospital" as Dave's functional-isolation examples do, and the dataset *is* the domain. So functional/temporal aliasing largely doesn't apply, and because the SUT is read-only the suite does achieve isolation's real goals — determinism and repeatability — for free. The deviation that remains is the brittleness of binding assertions to exact dataset values.

**Fix.** Where the behaviour is "the standings are calculated correctly," prove it against a *small fixture you control* rather than the full historical table — a handful of synthetic matches fed to the standings logic, asserting the computed champion and points from first principles. Keep the full-dataset specs for coverage/smoke, but don't let a Kaggle re-export be able to turn the build red. Where you must assert against real data, prefer structural/lower-bound checks (`atLeast`, "champion has more points than second place") over pinned magic numbers.

### Priority 3 — Assertions scrape formatted text, and the PD mixes action into assertion (categories A & E)

The protocol driver asserts by regex over the SUT's human-readable output:

- `McpSoccerDriver.ts:33` — `/^\s*(- |\d+\. )\d{4}-\d{2}-\d{2}/`
- `McpSoccerDriver.ts:46-47` — `Matches: N`, `^1\. ${name} - Overall`

and the spec asserts on literal presentation strings:

- `soccer-knowledge.spec.ts:15` — `confirmAnswerMentions("Head-to-head")`
- `soccer-knowledge.spec.ts:109` — `confirmAnswerMentions("Average goals per match", "Home win rate")`

**Why it matters.** Lesson 103b's calculator lesson strips "on the screen" because it's a presentation assumption. Asserting the literal label `"Average goals per match"` couples the spec to the *wording of the output format*, not the outcome — reword the response and the spec fails though the behaviour is unchanged. In the PD this is less serious (lesson 303 allows the driver to know SUT detail), but scraping display text is fragile; Dave's advice (lesson 306) is to look for the *concluding outcome*, ideally a structured one. Separately, `assertSameMatchCount` (`McpSoccerDriver.ts:57-62`) issues its own `ask()` calls inside an assertion method — blending "act" and "confirm" in one step, which muddies the atomic-step contract.

**Fix.** If the MCP tools can return structured content alongside the prose, assert against the structure and let the text be presentation. Short of that, assert on durable domain facts rather than format labels — e.g. confirm the head-to-head result *contains both team names and a win/draw tally* (which `confirmAnswerMentions("Palmeiras", "Santos", "wins", "draws")` at line 57 already does well — copy that pattern) rather than the literal section heading `"Head-to-head"`.

## 4. Further improvements

- **Shared mutable `lastAnswer` on a single driver (`McpSoccerDriver.ts:9`).** The `ask…`/`confirm…` split relies on `lastAnswer` persisting between two calls on one shared driver instance. It's safe today because vitest runs tests within a file sequentially — but flip any of these to `it.concurrent` and tests will clobber each other's `lastAnswer`. It's a latent isolation hazard (lesson 302); consider returning the answer and asserting on the returned value, or scoping a fresh context per test.
- **`confirmAnsweredWithin` puts timing logic in the DSL (`SoccerDsl.ts:73-77`).** Measuring elapsed time is SUT-interaction concern — it belongs in the protocol driver to keep the DSL/PD abstraction levels matched (lesson 305). Minor.
- **No CI configuration present.** The suite is honest, but there's no pipeline wiring it to a "you may release" signal. Lesson 306's whole point is the suite as "a definitive statement of releasability" — worth wiring up, keeping tests and SUT in one repo (which they already are — good).
- **`it("should treat team name variations as the same team")` (line 38)** is a nice behavioural spec, but it asserts via `assertSameMatchCount` which re-queries with `limit: 10000` — a presentation/implementation number leaking into test intent. Consider a DSL-level `confirmSameTeam(a, b)` that hides the limit.

## 5. Suggested next steps

1. **Deal with the two timing specs first** (Priority 1) — they're the most likely to flake and the cheapest to fix. Move them out of the release-gating suite or demote timing to a loose guard-rail.
2. **Introduce one synthetic-fixture spec for a calculated outcome** (Priority 2) — pick `standings`/`confirmChampion`, feed a small controlled set of matches, and assert the computation from first principles. This proves the pattern without rewriting everything, and shows the team how to stop binding the build to a Kaggle export.
3. **Then refine assertions toward structure/domain facts** (Priority 3) over scraped format strings, and tidy the `assertSameMatchCount` action/assertion blend.

The architecture is sound and the discipline is already here — this is polishing a good suite, not rebuilding a bad one.

```json
{"acceptance_tests_found": true, "ratings": {"A": 3, "B": 4, "C": 2, "D": 3, "E": 3, "F": 2, "G": 4}, "disclosure": "full"}
```