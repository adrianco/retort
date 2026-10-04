I now have the full lessons for every category (all `disclosure: "full"`, paid tier). The only empty result was the `releasability` topic (category G has no dedicated course lesson — I'll ground it in the skill's criteria and the trust framing in Lesson 306). Here is the review.

---

# ATDD Review — Brazilian Soccer MCP acceptance suite

## Overall assessment

This is a genuinely well-structured suite that already has the bones of Dave's approach in place — and that puts it ahead of most suites I review. The four-layer model is real, not aspirational: `acceptance/*.spec.ts` (specs) → `acceptance/dsl/soccerDsl.ts` (DSL) → `acceptance/drivers/mcpDriver.ts` (protocol driver) → `src` (SUT), with the driver explicitly owning the "this is MCP-over-stdio" knowledge (`mcpDriver.ts:1`). The specs mostly read in the language of Brazilian football, not the language of the code. The weaknesses are not structural — they're about what the tests *depend on* (a large bank of real-world fixture data) and how *precisely* a few of them say what they mean. Nothing here needs restructuring; it needs tightening.

## Strengths

- **The four layers are cleanly separated** and match Lesson 305's model. The DSL is decomposed by domain area — `Matches`, `Teams`, `Players`, `Competitions`, `Stats` (`soccerDsl.ts:7,40,71,83,96`) — which is exactly the "decompose the DSL so it doesn't become a giant hard-to-maintain piece" advice from Lesson 305.
- **Specs are outcome-focused and domain-worded.** `"should name Flamengo champion of the 2019 Brasileirão"`, `"should treat accented and unaccented team names as the same team"` — these say *what*, not *how*, and would survive the SUT being rebuilt behind a different interface. That is the core BDD test from Lesson 103b/203.
- **The DSL uses `confirm…` naming** (`confirmChampion`, `confirmRecordFor`) — the exact habit Dave describes in Lesson 305 ("I write assertions starting with the word `confirm` rather than `assert`… to make them seem less technical for non-technical readers").
- **Named parameters with defaults** (`venue = "any"`, `limit = 10`) match Lesson 301's DSL capabilities.
- **No sleeps or waits anywhere**, and the suite is honest about its state (category G) — no `.skip`/`.only`/`xit`, no swallowed exceptions, no CI exclusion filters, `npm test` builds and runs everything. That directly serves the releasability-as-trust principle Lesson 306 opens with.

## Priority issues

### 1. The suite is built on a large bank of pre-loaded real-world data — the anti-pattern Lesson 305 warns against

Every assertion reads against the full Kaggle CSVs loaded at startup (`src/server.ts:10-11`), and many assert *exact facts* from that data: `confirmChampion({ team: "Flamengo", points: 90 })` (`competitions.spec.ts:11`), `confirmRecord({ matches: 19 })` (`teams.spec.ts:11`), `confirmRelegated(["Chapecoense","Avaí","CSA","Cruzeiro"])` (`competitions.spec.ts:16`), `confirmFirstIs("Neymar Jr")` (`players.spec.ts:16`).

**Why it matters.** Lesson 305 is explicit: *"try to use only synthetic data, created by your DSL… Avoid starting up the SUT with lots of state — generate the state you want the SUT to be in within your test."* Lesson 306 names "changes in test data between test runs" as one of the five root causes of intermittency. Today the suite is accidentally safe on isolation — the SUT is read-only, so tests can't corrupt each other's state and the same test twice gives the same answer (temporal isolation satisfied for free). But it is brittle to the *fixture*: re-download a dataset, get a differently-versioned Kaggle export, or add a season, and `points: 90` or the relegated list breaks for reasons that have nothing to do with a code regression. A failing test should mean the system is broken (Lesson 306); here it can mean "someone refreshed a CSV."

**Direction.** Point the server at a small, committed, synthetic dataset for acceptance runs — the hook already exists: `SOCCER_DATA_DIR` (`src/server.ts:10`). Have the driver start the server against a fixtures directory the suite owns, and assert against facts *you* authored:

```ts
// mcpDriver.ts — start against a controlled dataset the suite owns
await this.client.connect(new StdioClientTransport({
  command: "node", args: ["dist/server.js"],
  env: { ...process.env, SOCCER_DATA_DIR: "acceptance/fixtures" },
}));
```

Then `confirmChampion({ team: "…", points: 90 })` is true because your fixture *makes* it true, not because this year's CSV happens to agree. You keep the real datasets for a separate, smaller "it loads real data" smoke check.

### 2. A few specs don't say what they check — accuracy leaks (Lessons 203, 103b)

Lesson 103b's four goals are concise, accurate, understandable, durable — and 203's test for coupling is *"imagine the spec fulfilled by a completely different system."* Three places fall short:

- **Name/behaviour mismatch.** `"should rank teams by home record"` calls `requestBestRecord({ venue: "away" })` and only checks `confirmRankingShown()` (`competitions.spec.ts:36-38`). The title says home, the call says away, and the assertion checks neither — only that *some* list came back. The spec is inaccurate about its own outcome.

  ```ts
  // before
  it("should rank teams by home record", async () => {
    await soccer.stats.requestBestRecord({ venue: "away" });
    await soccer.stats.confirmRankingShown();
  });
  // after — say what you mean, assert the ranking property
  it("should rank teams by home win rate, best first", async () => {
    await soccer.stats.requestBestRecord({ venue: "home" });
    await soccer.stats.confirmRankedByWinRateDescending();
  });
  ```

- **Implementation leak.** `"should include matches from the historical and extended statistics datasets"` (`matches.spec.ts:40`) leaks *how the system is built* (multiple CSV datasets) into the spec — precisely the leakage Lesson 103b tells you to strip out. The user's outcome is "I can find older Série B matches," not "two datasets were merged." Reword to the domain: `"should find Série B matches from the 2000s"`.

- **Two scenarios in one test.** That same test does find-Guarani-2003 *and then* find-Serie-B (`matches.spec.ts:40-45`) — Lesson 203's mistake #2 (long-running scenarios / testing more than one thing). Split into two.

### 3. Many confirmations assert existence, not behaviour — and fail with useless messages (Lesson 305)

`confirmRankingShown()` and `confirmProfileHasPlayers()` only check `length > 0` (`soccerDsl.ts:113,68`); several `confirm*` methods end in a bare `expect(ms.every(...)).toBe(true)` (`soccerDsl.ts:25,30,35,79`).

**Why it matters.** Lesson 305: *"Good error messages can help diagnose test failures more quickly… aim for these errors to be at a sensible level for spec writers — in the language of the problem domain."* When `confirmAllInSeason(2019)` fails, Vitest prints `expected false to be true` — which tells a spec reader nothing. And a `length > 0` check passes even if the ranking is in the wrong order or the profile returned the wrong club's players, so the test green-lights behaviour it never actually verified.

```ts
// before
confirmAllInSeason(season: number) {
  const ms = this.d.last.data.matches;
  expect(ms.length).toBeGreaterThan(0);
  expect(ms.every((m: any) => m.season === season)).toBe(true);
}
// after — name the offenders in the domain's language
confirmAllInSeason(season: number) {
  const ms = this.d.last.data.matches;
  expect(ms.length, `expected matches in ${season}, got none`).toBeGreaterThan(0);
  const wrong = ms.filter((m: any) => m.season !== season).map((m: any) => `${m.home} v ${m.away} (${m.season})`);
  expect(wrong, `matches outside ${season}: ${wrong.join(", ")}`).toHaveLength(0);
}
```

Dave puts assertions (and their good messages) in the protocol-driver layer; here they live in the DSL, which is a defensible variant *as long as* each `confirm` still makes the step pass-or-fail with a readable reason. Right now several don't.

## Further improvements

- **The timing assertion is an intermittency vector.** `confirmRespondsWithin(5000)` checks wall-clock `elapsedMs` (`soccerDsl.ts:115-118`, `competitions.spec.ts:55-57`). Lesson 306 §4 flags resource contention/environment as a flake cause — a hard 5 s bound on the first call after a cold start can fail under CI load for reasons unrelated to the code. If responsiveness matters, measure it as a separate perf check with generous headroom, or drop it from the acceptance gate.
- **The DSL knows the SUT's tool names.** DSL methods call `this.d.call("search_matches", …)`, `"team_record"`, etc. (`soccerDsl.ts:9,42`), and the driver is a single generic `call(tool, args)` transport (`mcpDriver.ts:15`). Lesson 303's model is `DSL.placeOrder → driver.placeOrder` at a *matching* abstraction, with the driver owning the SUT-specific translation. Here the protocol detail (tool names) has floated up into the DSL. It's a mild altitude blur, not a break — but giving the driver semantic, atomic methods (`driver.searchMatches(...)`) would restore the clean Lesson 305 layering and give you the natural home for the per-step assertions and good error messages from issue #3.
- **`limit: 500` / `limit: 50` in the DSL** (`soccerDsl.ts:9,73`) leak pagination mechanics into the domain layer. Fold them into driver defaults so specs never see them.

## Suggested next steps

1. **Switch the acceptance run to a small synthetic fixture dataset via `SOCCER_DATA_DIR`** (issue #1). This is the single highest-leverage change — it turns the suite from "true as long as the CSVs don't change" into "true because the test authored the world," and it's the prerequisite that makes every exact-fact assertion trustworthy.
2. **Fix the three accuracy leaks** (issue #2) — the home/away mismatch is a latent false-negative today.
3. **Strengthen the existence-only confirmations and give every `confirm` a domain-language failure message** (issue #3).
4. Then, if you want to go from "good" to "exemplary," give the protocol driver semantic methods so the DSL stops naming MCP tools (further improvements).

The structure is sound and the instincts are right — these changes are refinements on a suite that already follows the shape Dave teaches, not a rebuild.

---

*All criteria above were drawn from the full ATDD course lessons (paid tier, full disclosure): BDD 103b & 203 (categories A), the Four-Layer Model 305 (B), Test Isolation 302 (C), Building a DSL 301 (D), Protocol Drivers & Stubs 303 (E), Dealing With Intermittent Tests 306 (F). Category G has no dedicated course lesson (the `releasability` topic returned empty); it was assessed against the skill's releasability-truthfulness checklist and the trust-in-tests framing that opens Lesson 306 — and the suite passes it cleanly.*

```json
{"acceptance_tests_found": true, "ratings": {"A": 3, "B": 3, "C": 2, "D": 3, "E": 3, "F": 3, "G": 4}, "disclosure": "full"}
```