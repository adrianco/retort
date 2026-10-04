I now have everything I need: full-disclosure course lessons for every category, and a complete reading of the suite. Here is the review.

---

# ATDD Review — Brazilian Soccer MCP server test suite

I reviewed every test in `tests/` against Dave Farley's ATDD principles, fetching the relevant course lessons for each category before assessing. All course content came back at **full disclosure** (paid tier) — these are Dave's full lessons, not summaries.

**What counts as an acceptance / end-to-end test here.** This is an MCP server whose product surface *is* its set of tools. The genuine acceptance/E2E tests are:
- **`tests/server.test.ts`** — drives the server end-to-end through a real MCP client over an in-memory transport (tool discovery, 29 sample questions, cross-file queries, error handling).
- **`tests/stdio.test.ts`** — launches the built server as a child process and talks MCP over stdio, exactly as Claude Desktop/Code would.

`queries.test.ts`, `teams.test.ts`, `data.test.ts`, `csv-dates.test.ts` are unit/integration tests against the library internals — valuable, but not acceptance tests, so they inform the review (especially isolation and intermittency) without being graded as the acceptance layer.

---

## 1. Overall assessment

This is a **genuinely good, honest, deterministic suite that is on the right track** — notably better than most E2E suites I review. It drives the system through its real public interface (the MCP protocol, twice — in-memory and over stdio), the scenario *names* are written in the language of the problem domain, there are no sleeps, no shared mutable state, and nothing is silently skipped. The central ATDD weakness is **a missing DSL layer**: the scenarios read like executable specifications on the surface, but each one bypasses straight to raw tool names, raw argument maps, and assertions pinned to exact output-format strings. So the suite gets the *spec vocabulary* right while leaving the *four-layer separation* that keeps specs durable half-built. That, plus wall-clock latency assertions baked into functional tests, are the two things worth fixing.

## 2. Strengths (don't skip these)

- **Tested at the real boundary, through the real protocol.** `server.test.ts` goes through an actual `Client` over `InMemoryTransport` (`helpers.ts:17-24`), and `stdio.test.ts` spawns the compiled server and speaks MCP over stdio (`stdio.test.ts:20-27`). This is exactly Dave's SUT-boundary discipline from **Test Isolation** (302): "define the SUT boundary clearly… our test infrastructure is a kind of harness into which we can plug our SUT." You even run the same specification through two different transports — a lightweight version of the "one test, multiple protocol drivers" idea from **Protocol Drivers & Stubs** (303).
- **Scenario names are problem-domain language.** "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?", "Show me all derbies in 2023" (`server.test.ts:80,84,93`) are phrased as a user/stakeholder would ask — the heart of **BDD** (103b). Apply Dave's test from lesson 203 — "imagine the spec being fulfilled by a completely different system" — and these questions pass: any Brazilian-soccer knowledge base could answer them.
- **Naturally isolated with no cleanup.** The SUT is read-only over static CSVs, so there's no shared *writable* state, no teardown, and tests are parallelisable and repeatable by construction. Dave explicitly warns against cleanup-based approaches ("rolling back database transactions… it's not a great strategy", 302) — you avoid that whole class of problem.
- **No sleeps anywhere, and a clean thin driver.** `callTool` (`helpers.ts:32-36`) is atomic, reused across the sample loop, measures timing, and crucially surfaces the server's own text on failure: `expect(r.isError, r.text).toBe(false)` (`server.test.ts:111`). That "good error messages… at a sensible level for spec writers" point from the **Four Layer Model** (305) is satisfied.
- **The suite is honest about its state** — see category G below. This is rarer than it should be and deserves explicit credit.

## 3. Priority issues

### Priority 1 — There is no DSL layer; scenarios bypass straight to tool-name + raw-args + exact-string assertions

**What.** Every sample is a record of `{ question, tool, args, expect }` (`server.test.ts:39-101`) executed by one generic line, `callTool(client, s.tool, s.args)` (`server.test.ts:110`). The human-readable `question` is only the test's *name*; what actually executes is the raw tool id (`"league_standings"`), a raw argument map (`{ season: 2019, limit: 3 }`), and assertions pinned to exact rendered strings like `"1. Flamengo - 90 pts (28W, 6D, 4L)"` (`server.test.ts:81`).

**Why it matters.** This is the single most common way Dave sees acceptance testing go wrong. From **Building a DSL for Testing** (301): the DSL should keep tests "isolated completely from the technicalities of our solution" and give a vocabulary that "stays stable even as the underlying system changes." And from **Acceptance Tests & BDD** (203), *Mistake 3 — No reuse in the DSL*: "they are implementing nearly every spec from scratch… If you can't see a need for reuse, you are not thinking in terms of the problem domain." Right now the tool id, the argument shape, and the exact output format are all welded into each scenario. The moment `format.ts` changes a label ("90 pts" → "90 points"), or a tool is renamed, dozens of unrelated scenarios break for reasons that have nothing to do with whether the behaviour is correct — the brittleness Dave attributes to leaking implementation detail in **BDD** (103b). This is also the "DSL that bypasses to direct SUT calls" half-built-infrastructure smell: the `question` field *looks* like a spec layer, but nothing routes through a reusable domain language — the execution goes straight to the protocol.

**Before** (`server.test.ts:80-81`):
```ts
{ question: "Who won the 2019 Brasileirão?", tool: "league_standings", args: { season: 2019, limit: 3 },
  expect: ["1. Flamengo - 90 pts (28W, 6D, 4L)", "2. Santos - 74 pts (22W, 8D, 8L)", /* … */ "Champion: Flamengo"] },
```

**After** — introduce a small internal DSL between the scenario and `callTool`, with domain verbs, defaults, and assertions that speak outcomes rather than rendered rows:
```ts
// tests/dsl.ts — the reusable domain language (layer 2)
export class Soccer {
  constructor(private client: Client) {}
  async leagueTable(season: number, { competition = "Brasileirão" } = {}) {
    const r = await callTool(this.client, "league_standings", { season, competition });
    return new Standings(r);               // a domain view, not a raw string
  }
}
class Standings {
  // parses the response once, exposes domain questions
  champion(): string { /* … */ }
  positionOf(team: string): number { /* … */ }
}

// the scenario (layer 1) now says WHAT, not HOW:
it("Flamengo won the 2019 Brasileirão", async () => {
  const table = await soccer.leagueTable(2019);
  expect(table.champion()).toBe("Flamengo");
});
```
`leagueTable` is now the single place every standings scenario goes through (Dave: "if your tests place orders, they should go through the same DSL call every time", 203), the exact wording of a row lives in one parser, and the scenario asserts a single domain outcome. Keep `callTool` as your protocol driver underneath — you already have layers 1, 3 and 4; this adds the missing layer 2.

### Priority 2 — Wall-clock latency assertions give the tests a third reason to fail

**What.** Each sample asserts `expect(r.ms).toBeLessThan(s.aggregate ? 5000 : 2000)` (`server.test.ts:116`), and `data.test.ts:57` asserts `stats.loadMs < 5000`.

**Why it matters.** **Properties of Good Acceptance Tests** (202) is explicit: a good acceptance test has *only two reasons to fail* — "a translation mistake in the test infrastructure, or a genuine failure in the SUT." A latency threshold adds a third, environment-dependent reason: on a loaded CI box or slow hardware the functional behaviour is perfectly correct but the test goes red. That's exactly the *resource contention* cause of intermittency catalogued in **Dealing With Intermittent Tests** (306). It also conflates a performance requirement with a behavioural specification inside one test. Your margins are generous (2 s for an in-memory lookup), which shows you sensed the risk — but the right move is to separate the concern.

**Before** (`server.test.ts:112-116`):
```ts
for (const e of s.expect) { /* content assertions */ }
expect(r.ms).toBeLessThan(s.aggregate ? 5000 : 2000);
```
**After** — keep the behavioural spec pure, and move performance into its own clearly-labelled, tagged check (the same way Dave isolates time-sensitive tests in **Testing With Time**, 304):
```ts
// functional spec: only behavioural assertions, two reasons to fail
for (const e of s.expect) { /* … */ }

// a separate, explicitly-named performance guard (own describe block / tag),
// with a budget you can relax on CI without touching any behavioural test:
it.concurrent(`${s.question} responds within budget`, async () => {
  const r = await callTool(client, s.tool, s.args);
  expect(r.ms).toBeLessThan(PERF_BUDGET[s.aggregate ? "aggregate" : "lookup"]);
});
```

### Priority 3 — Specifications are coupled to exact rendered output, not to outcomes

**What.** Assertions routinely pin the exact formatting of the answer: `"1. Flamengo - 90 pts (28W, 6D, 4L)"` (`:81`), `"- Grêmio: 20 players (avg rating: …"` regexes (`:78`), `"2019-11-23: Flamengo 2-1 River Plate (Copa Libertadores Final)"` (`:50`).

**Why it matters.** **BDD** (103b): implementation-focused tests "will be accurate, but only for the current version of our implementation — narrowly correct. As soon as we change our implementation, those tests no longer make sense." The *answer* ("Flamengo were champions with 90 points") is the durable outcome; the *rendered string* is a presentation detail owned by `format.ts`. Pinning the string means a cosmetic formatting change breaks the spec even though the behaviour is unchanged — and, as Dave notes, breaks it "just at the time when you could use reassurance that your software still delivers on its goals." This is the same root cause as Priority 1 and is fixed by the same DSL move: parse the response once in the DSL, then assert on domain values (`table.champion()`, `table.points("Flamengo") === 90`) rather than on the formatted line. Reserve exact-string checks for one or two dedicated "the output is formatted like this for the LLM" presentation tests, where the format genuinely *is* the behaviour under test.

## 4. Further improvements

- **`stdio.test.ts` duplicates the protocol driver instead of reusing it.** It hand-rolls the client/transport and casts the result inline — `(await client.callTool(...)) as { content: { text: string }[] }` (`stdio.test.ts:33-36`) — rather than going through `helpers.ts`. Factor the stdio connection into `helpers.ts` so both transports share one driver interface; that's precisely the "same DSL, swappable protocol drivers" pattern from **Protocol Drivers & Stubs** (303), and it's most of the way there already.
- **`stderr: "ignore"` (`stdio.test.ts:22`)** silences the child server's diagnostics. Failures still surface through assertions, but a startup error becomes hard to diagnose. Consider capturing stderr and printing it on failure.
- **Exact fixture counts** (`"827 found"` `:66`, `stats.rowsPerSource[...] === 4098` `data.test.ts:11`) are deterministic but brittle to any data refresh. For a read-only reference SUT this is a reasonable trade-off; just be aware these are reference-data assertions, not behavioural ones, and will need updating in lockstep with the CSVs. Dave's synthetic-data guidance (305) — "generate the state you want the SUT to be in within your test" — is hard to apply to a read-only dataset, so this is an acceptable deviation, noted rather than condemned.
- **Error-handling scenarios are good domain specs** (`server.test.ts:138-162`) — "returns a tool error for unknown teams", "explains ambiguous team names". Route these through the DSL too (`soccer.expectUnknownTeam("Nonexistent United")`) so the error contract has one home.

## 5. Category G — releasability truthfulness (a clear strength)

I checked specifically for a suite that reports green while hiding state, because that's worse than a red build. This suite is **honest**:

- **No skipped/ignored/`.only`/`xit` tests** anywhere in `tests/` (grep confirmed none).
- **No CI test-exclusion filters, no `continue-on-error`, no `.only`** — there is no CI workflow at all, and `vitest.config.ts`/`package.json` carry no `exclude`/filter.
- **No swallowed exceptions in the test infrastructure.** The one `try/catch` is in *production* code (`src/server.ts:33-41`, the `guard()` wrapper that converts thrown errors into MCP tool errors) — and it's a *tested contract*: the error scenarios assert `isError` is `true`/`false` (`server.test.ts:138-161`). Nothing is hidden.
- **Self-verifying coverage.** `it("covers at least 20 questions (${SAMPLES.length})")` (`server.test.ts:104`) makes the scenario count visible in the test output rather than asserting it silently.

This maps directly to **Test First** (201) — "the combined set of passing acceptance tests is the system specification… determines whether a release candidate can ship" — and **Dealing With Intermittent Tests** (306): acceptance tests should be "a definitive statement of the releasability of our system." A green run here means what it says. The only nuance: with no CI pipeline, nothing yet *enforces* the green gate, and there are no known-failing features needing expected-failure markers (so there was nothing to mark wrongly). If in-progress features arrive later, use strict expected-failure markers (`xfail(strict=true)`-equivalent) rather than `.skip`, per lesson 201's "disable so results are ignored during a pipeline run, then enable when the feature lands."

## 6. Suggested next steps

1. **Build the missing DSL layer first (Priority 1).** It's the highest-leverage change and it dissolves Priority 3 at the same time. You already have clean layers 1, 3 and 4 — add `tests/dsl.ts` with a handful of domain verbs (`leagueTable`, `headToHead`, `squad`, `derbies`), give them defaults, and have scenarios assert domain outcomes. Start with the standings/league scenarios, since they have the most duplicated exact-string assertions.
2. **Split performance out of the functional specs (Priority 2).** Move the `r.ms` budgets into a separate tagged block so a slow CI run can never fail a behavioural spec.
3. **Unify the two transports behind the shared driver**, then — if you ever add a non-stdio channel (HTTP/SSE) — the same scenarios can run against it unchanged, which is the real pay-off of the four-layer model.

This is not a restructuring job — it's finishing an architecture that's already three-quarters built. The scenario vocabulary and the honesty are already where Dave would want them; the work is extracting the domain language that currently sits inlined in the data table into a reusable layer of its own.

```json
{"acceptance_tests_found": true, "ratings": {"A": 2, "B": 2, "C": 3, "D": 1, "E": 3, "F": 2, "G": 3}, "disclosure": "full"}
```