I now have the full lesson content for every category and have scanned the suite for releasability signals. Here is the review.

---

# ATDD Review — `tests/soccer.test.ts` (Brazilian Soccer MCP)

I reviewed the single test file `tests/soccer.test.ts` against Dave Farley's ATDD principles, pulling the criteria from the course knowledge base (all lessons returned **full** disclosure — this is not a summary-only review). The file mixes four kinds of test: unit tests (parsing/normalization), data-coverage checks, a 25-case "sample questions" block, a performance test, and one genuine end-to-end test over the MCP protocol. The acceptance/end-to-end material is the "sample questions" block and the `MCP server` test — those are what I assessed hardest.

## 1. Overall assessment

The suite has a genuinely promising surface and a mis-structured interior. The "sample questions" are titled in exactly the language Dave asks for — *"Who won the 2019 Brasileirão?"*, *"Which teams were relegated in 2020?"* — and the final `MCP server` test proves the system through its real external protocol, which is the kind of thing Dave celebrates. But underneath the titles there is no DSL and no layered test infrastructure (four-layer model, 305). Roughly half the "specifications" reach straight into the service's internals (`svc.filterMatches(...).every(m => m.homeKey === "palmeiras")`), and most of the rest assert against the exact formatted output string of a tool. In Dave's terms (BDD, 103b) these are *tests* — written after the code, narrowly correct for the current implementation — rather than *specifications* that would survive a reimplementation. This isn't a rewrite-from-scratch situation; the domain-language titles and the `runTool`/MCP seam give you most of a protocol-driver layer already. The work is to insert a real DSL between the titles and the system, and to assert outcomes instead of output strings.

## 2. Strengths

- **The test titles speak the problem domain.** `"Find all Copa Libertadores finals"`, `"Compare Palmeiras and Santos head-to-head"` — these read as specifications of user intent, not UI scripts. That is the single hardest habit to instil (103b: *"Good acceptance tests ONLY define outcomes"*), and it's already here.
- **There is a real end-to-end path.** The `MCP server` test (lines 174–186) stands up the actual server, connects a real `Client` over `InMemoryTransport`, lists tools and calls one. That is a true protocol-driver interaction (303) exercising the same behaviour through the system's real external channel — the echo of Dave's "one interface, multiple channels" idea.
- **The suite is honest about its state (category G).** No `.skip`/`xit`/`.only`, no commented-out tests, no CI exclusion filters, no `continue-on-error`, and the one `try/catch` (`src/server.ts:14`) is legitimate production error-surfacing, not a swallowed test failure. Everything runs every time and fails loudly.
- **No sleeps, deterministic core.** The SUT is synchronous and read-only, so there are no race conditions and no `sleep`-to-paper-over-asynchrony anti-pattern (306).

## 3. Priority issues

### Priority 1 — Specifications assert on implementation, not outcomes (A; lessons 103b, 203)

Dave's test for coupling (203): *"imagine the spec being fulfilled by a completely different system. If it can't be, it's coupled to the implementation."* Many cases fail that test two different ways.

**(a) Reaching into internal data structures.** Example, test #2 (lines 54–58):

```ts
it("2. What matches did Palmeiras play in 2023?", () => {
  const ms = svc.filterMatches({ team: "Palmeiras", season: 2023 });
  expect(ms.length).toBeGreaterThan(30);
  expect(ms.every((m) => m.homeKey === "palmeiras" || m.awayKey === "palmeiras")).toBe(true);
});
```

This asserts on the internal field names `homeKey`/`awayKey` and a vague count. Rename a field and the "specification" breaks though the behaviour is unchanged — Dave's *"narrowly correct"* trap (103b).

**(b) Matching the exact formatted output string.** Example, test #6 (lines 73–78):

```ts
expect(ask("standings", { season: 2019 })).toMatch(/1\. Flamengo - 90 pts \(28W, 6D, 4L.*Champion/);
```

The behaviour being specified is *"Flamengo won the 2019 Brasileirão with 90 points."* The regex instead pins the precise text layout (`"- 90 pts ("`, `"28W, 6D, 4L"`, the word `Champion`). Reword the tool's output and it fails. This is the calculator example from 103b — the spec has baked in *how the answer is displayed*.

**Before / after**, in the spirit of the 103b rewrite (strip the implementation assumptions, keep the outcome):

```ts
// before: couples to formatted string and internal fields
expect(ask("standings", { season: 2019 })).toMatch(/1\. Flamengo - 90 pts \(28W, 6D, 4L.*Champion/);

// after: a DSL call returning domain values; assert the outcome
const table = soccer.leagueTable({ season: 2019 });          // Brasileirão is the default
soccer.confirmChampion(table, "Flamengo");                   // confirm* reads naturally (305)
soccer.confirmRecord(table, "Flamengo", { points: 90, wins: 28, draws: 6, losses: 4 });
```

The `after` says nothing about *"- 90 pts ("* or `homeKey`; it would still pass if you reformatted every tool string or restructured the match record. Apply the same move to #1, #4, #8, #9, #15, #16, #18, #20, #22 (string-regex coupling) and #2, #3, #5, #6, #7, #10, #21, #24, #25 (internal-structure coupling).

### Priority 2 — There is no DSL layer; the suite is effectively two layers (B, D; lessons 305, 301)

The four-layer model (305) wants: test case → DSL → protocol driver → SUT. What's here is:

- `const ask = (tool, args) => runTool(svc, tool, args)` (line 11) — a one-line pass-through keyed by a **stringly-typed tool name** and taking the **raw MCP argument object**. That is the abstraction level of the SUT's API, not the problem domain.
- Everything else calls `svc.*` directly — the SUT's own service surface.

So there is no layer providing what Dave says a DSL must provide (301): domain vocabulary, **default values** so a test states only what it cares about, **aliasing**, and **insulation from SUT detail**. And because there's no DSL, there's no reuse of intent — each test re-specifies the tool name and argument shape inline, the "no reuse in the DSL" mistake from 203.

**Before / after:**

```ts
// before: SUT-level vocabulary, raw args, inline everywhere
ask("head_to_head", { teamA: "Flamengo", teamB: "Fluminense" });
ask("team_record", { team: "Corinthians", venue: "home", season: 2022, competition: "Brasileirão" });

// after: a small internal DSL at domain level, with defaults
const h = soccer.headToHead("Flamengo", "Fluminense");        // no competition arg needed
const r = soccer.homeRecord("Corinthians", { season: 2022 }); // Brasileirão is the default
```

`soccer` is a thin DSL object; underneath, its methods call the existing `runTool`/`SoccerService` — which is exactly the protocol-driver role (305: *"keeping the call from DSL to PD at the same level of abstraction"*). You already have the bottom two layers (`runTool`, and the MCP client in the e2e test); this is about adding the missing layer above them, not rebuilding.

### Priority 3 — A wall-clock timing assertion and exact external-data counts are intermittency and data-stability risks (F, C; lessons 306, 302)

The `performance` test (lines 164–172) asserts `performance.now() - t < 2000`. Dave lists **resource contention** as a named cause of intermittency (306) — a wall-clock bound inside the correctness suite will flake under CI load, and a flaky test *"compromises our trust... should we run it again?"* It is measuring the wrong thing in the wrong place.

Separately, the data-coverage and standings tests pin exact values from the vendored Kaggle CSVs: `toBe(10296)`, `toBe(18207)` (lines 39–41), `points: 90` (line 76). Dave's root-cause list (306) includes *"changes in test data between runs."* These files came from Kaggle; the day anyone refreshes them, a batch of green tests turns red for a reason that has nothing to do with a regression. This is also the shared-fixture coupling from 302 — every test depends on one global, externally-sourced dataset loaded in `beforeAll` (line 10) rather than owning the small slice of data it needs.

**Direction:** move the timing check out of the pass/fail acceptance suite into a separate performance budget that doesn't gate releasability. For the data coupling, the ATDD-native fix (302) is for each spec to create the data it asserts on — load a small, fixed synthetic fixture for the standings/coverage specs so *"Flamengo, 90 pts"* is true because the test put those matches there, not because today's Kaggle download happens to agree.

## 4. Further improvements

- **Assertions belong in the driver, not scattered across tests (E; 305).** Dave: *"Protocol drivers are nearly always where assertions are made... make each step pass or fail."* Right now every assertion sits in the test body against a returned string. Pull them into `confirm*` methods on the DSL/driver (`soccer.confirmChampion(...)`) so each step is atomic and failures report in domain language.
- **Weak assertions (`toBeGreaterThan(30)`, `toBeGreaterThanOrEqual(10)`, line 56/61/100/105).** These are hedges against data drift. Once specs own synthetic data (above), you can assert the exact expected outcome — *accurate*, in the 103b sense.
- **Separate the unit tests from the specifications.** The `parsing & normalization` block (lines 13–31) is good unit testing and should stay — but Dave (203, "long-running / over-testing") wants edge cases tested *at the unit level* and acceptance specs kept few and outcome-focused. Keeping them in separate files makes the acceptance layer legible as specification.
- **Stubs: correctly N/A.** The SUT owns all its data with no external systems, so there is nothing to stub (303) — testing to your boundary here is right; no action needed.

## 5. Suggested next steps

1. **Introduce a `soccer` DSL object** (internal DSL, Dave's preferred flavour, 301) with domain methods and sensible defaults, sitting on top of the existing `runTool`. Migrate the "sample questions" to call it. This is the highest-leverage change — it unlocks Priorities 1 and 2 together.
2. **Convert string/structure assertions to `confirm*` methods** that return and check domain values, so a reimplementation or a reformatted output string leaves the specs green.
3. **Give the standings/coverage specs their own synthetic fixtures** instead of the full real dataset, and **move the timing test out** of the releasability suite.
4. Keep the `MCP server` end-to-end test — it's your proof that the same specs hold through the real protocol, and it's the seed of a second protocol driver behind the same DSL.

The target is Dave's four-layer model, and you are closer than most suites: the intent language and a real protocol path already exist. The missing piece is the DSL in the middle and the discipline of asserting outcomes rather than output.

```json
{"acceptance_tests_found": true, "ratings": {"A": 2, "B": 1, "C": 2, "D": 1, "E": 2, "F": 2, "G": 4}, "disclosure": "full"}
```