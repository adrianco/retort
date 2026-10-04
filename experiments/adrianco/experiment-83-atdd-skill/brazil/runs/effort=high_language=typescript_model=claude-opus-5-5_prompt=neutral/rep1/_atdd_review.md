I now have full lessons for every category. I've read all eight test files, the production code they exercise, and confirmed there are no hidden-failure patterns. Here is the review.

---

# ATDD Review — Brazilian Soccer MCP test suite

*Reviewed against Dave Farley's ATDD course. The course server returned **full lesson content** (paid tier), so the criteria below are drawn from the complete lessons, not summaries.*

I read all eight files in `tests/`, plus the production code under test (`tools.ts`, `server.ts`, `query.ts`, `data.ts`). The acceptance/end-to-end layer is real and identifiable:

- **`tests/sample-questions.test.ts`** — 27 natural-language questions mapped to tool calls. This is your executable-specification layer.
- **`tests/mcp.test.ts`** — true end-to-end: a real MCP SDK `Client` talking to your `server` over an in-memory transport.
- `csv` / `normalize` / `teams` / `data` / `performance` — supporting unit and non-functional tests.

So **yes, acceptance and end-to-end tests exist**, and the review focuses on the first two files.

## 1. Overall assessment

This is a competently engineered, genuinely honest test suite for an unusual system under test: a **read-only, synchronous query engine** over a frozen set of CSV files. That shape earns the suite a lot for free — there's no mutable state, no concurrency, no external systems, so whole classes of ATDD pain (data leakage, race conditions, flakiness) simply don't arise, and the suite is deterministic and parallel-safe as a result. The spec-first *intent* is visibly present: tests are organised and named by the real questions a user would ask. Where it falls short of Dave's model is in **coupling and layering**: the executable bodies assert against exact rendered output strings and internal tool/argument names, and there is no domain DSL or protocol-driver layer between the test cases and the system. The result reads closer to a set of characterization tests pinned to the current output format than to durable executable specifications.

## 2. Strengths (real ones — don't lose these)

- **The question *is* the test.** `it('Q1 "Show me all Flamengo vs Fluminense matches"')` and the file's own docstring ("Each test maps a natural-language question to the MCP tool call an LLM would make") show conscious spec-first thinking. Dave's whole lesson 103b is about keeping the *question* central — you've kept it, at least in the naming.
- **A clean, deliberate SUT seam.** `tools.ts` says handlers are "plain functions so they can be unit-tested without an MCP transport," and `mcp.test.ts` exercises the *same* behaviour through the real protocol. That separation is exactly the kind of testability seam Dave praises, and it gives you a free pass at his "one spec, multiple channels" idea (lesson 303) — you just haven't wired it up that way yet.
- **Error-as-behaviour.** The `returns tool errors (not protocol errors) for bad input` test (`mcp.test.ts:56`) checks a genuine user-facing outcome with good messages ("No team matching", "Seasons available: 2003-2023", "knockout competition"). Lesson 305 singles out good, domain-level error messages as a PD virtue — this is the right instinct.
- **Deterministic and honest** (see categories C, F, G below).

## 3. Priority issues

### Priority 1 — Specs assert the *rendering*, not the *outcome* (categories A, D)

This is the highest-leverage fix. Most acceptance assertions are pinned to exact output strings and to internal tool names/arguments:

```ts
// tests/sample-questions.test.ts:11-14
const out = ask("search_matches", { team: "Flamengo", opponent: "Fluminense", limit: 100 });
expect(out).toMatch(/^Flamengo vs Fluminense/);
expect(out).toContain("2023-11-11: Flamengo 1-1 Fluminense (Brasileirão Série A 2023)");
```

Two of Dave's named mistakes are present here. Lesson 103b (the calculator): a spec that says *"the result should be 120 **on the screen**"* leaks the implementation (the screen). Your `toMatch(/^Flamengo vs Fluminense/)` and the exact `"...1-1 Fluminense (Brasileirão Série A 2023)"` string are the screen — a presentation choice, not the behaviour. Reformat the answer text and the spec breaks though the system is still correct. And lesson 203 mistake #1: the executable line speaks *how* (`ask("search_matches", {team, opponent, limit})` — which tool, which snake_case args) while the *what* (the question) has been demoted to the test's name. Apply Dave's own test — *"imagine the spec fulfilled by a completely different system"*: a differently-worded but equally correct answer fails here, so the spec is coupled to the implementation.

The fix is the same one that closes category D: put a thin **domain DSL** between the test and the tool, and assert on structured outcomes, not on prose.

```ts
// A DSL that speaks the problem domain; tool names + output format live beneath it.
const meetings = soccer.matchesBetween("Flamengo", "Fluminense");

expect(meetings).toContainMatch({
  date: "2023-11-11", home: "Flamengo", away: "Fluminense",
  score: "1-1", competition: "Série A", season: 2023,
});
```

Lesson 301/305: a good DSL gives you domain vocabulary, default values ("test cases only specify the things they care about"), and *insulation from SUT detail so the vocabulary is stable even as the system changes*. `matchesBetween(...)` stays true whether the answer is rendered as a bullet list, a table, or JSON — which is the whole point.

### Priority 2 — No DSL / protocol-driver layer, so the two suites duplicate knowledge (categories B, E)

Right now the layering is effectively **test case → `ask()`/`queries()` passthrough → SUT**. `helpers.ts` is not a DSL in Dave's sense (lesson 305: "a small programming language whose vocabulary matches the problem domain") — its vocabulary is the tool API (`ask("head_to_head", {...})`), i.e. SUT-shaped, which lesson 308 explicitly warns against ("don't let SUT detail leak up"). There is no protocol-driver layer with a contract, and the atomic pass/fail-per-step pattern from lesson 305 is absent.

The tell is duplication: `sample-questions.test.ts` *and* `mcp.test.ts` each independently know that head-to-head output starts `"X vs Y"`:

```ts
// sample-questions.test.ts:86-88
expect(ask("head_to_head", { team_a: "Palmeiras", team_b: "Santos" }))
  .toMatch(/Head-to-head in dataset \(\d+ matches\): Palmeiras \d+ wins, Santos \d+ wins/);

// mcp.test.ts:41-43
const res = await client.callTool({ name: "head_to_head", arguments: { team_a: "Flamengo", team_b: "Fluminense", limit: 3 } });
expect(text(res)).toContain("Flamengo vs Fluminense (Fla-Flu derby):");
```

This is exactly the scenario lesson 303 is built for. Define one DSL (`soccer.matchesBetween(...)`) and give it **two protocol drivers** behind the same interface — one calling the handler directly (fast), one driving the real MCP client/transport (`mcp.test.ts`'s `Client` + `text()` is already 90% of this driver). Then a single spec proves the behaviour *through both channels*, the format knowledge lives in exactly one place, and the duplication disappears:

```ts
for (const driver of [handlerDriver, mcpProtocolDriver]) {
  const soccer = new SoccerDsl(driver);
  // the same specs run against both channels
}
```

### Priority 3 — Absolute wall-clock assertions are the one real flakiness risk (category F)

`performance.test.ts` and `data.test.ts` gate on hard elapsed-time budgets:

```ts
// performance.test.ts:27
expect(time(() => ask(tool, args))).toBeLessThan(2000);
// data.test.ts:73
expect(ds.loadMs).toBeLessThan(5000);
```

Lesson 306 lists **resource contention** and **environment changes** as root causes of intermittency — and absolute timing thresholds are precisely how those leak into a suite. Your margins are enormous (milliseconds against 2000 ms), so this rarely bites today, but on a loaded CI box it is the one thing here that can go red without anything being broken, which erodes the trust lesson 306 says is non-negotiable. Keep measuring performance, but don't let a shared-runner hiccup fail the *correctness* gate: either move these to a separate, non-gating performance job, or assert something stable (e.g. "all data loaded" / a relative regression check) rather than an absolute clock.

## 4. Further improvements

- **Mixed abstraction inside a single spec.** Several tests assert the rendered answer *and* then reach into internals — e.g. Q1 checks the text, then `queries().searchMatches(...)` and `res.matches.every(m => [m.homeId, m.awayId].sort().join() === "flamengo,fluminense")` (`sample-questions.test.ts:15-17`). That `homeId/awayId` check is a unit-level assertion about internal data structures sitting in an acceptance test. Lesson 203 mistake #2 (and 305: "be VERY skeptical about long, complex test cases") — push the fine-grained structural checks down to unit tests and let the acceptance spec assert one domain outcome.
- **Promote the question into the executable spec.** The NL question currently lives only in the `it(...)` title. If the DSL from Priority 1 reads in domain language, the spec body itself becomes the readable question, and the title stops being the only place the intent survives.
- **Brittle magic-number coupling to the frozen fixture.** `toBe(827)`, `toBe(63)`, `toBe(19)`, the exact row counts in `data.test.ts`. Fine while the dataset is frozen, but this is the shared-real-data fixture lesson 302 cautions against ("replaying production data … is ultimately a poor alternative"). Where the behaviour, not the datum, is the point, prefer invariants (`h.total === h.winsA + h.winsB + h.draws`, which Q9 already does well) over pinned totals.

## 5. Suggested next steps

The architecture doesn't need tearing down — it needs a **DSL inserted between the test cases and the tools**, which simultaneously fixes Priority 1 (assert outcomes, not strings) and Priority 2 (one spec, two drivers, no duplication). Do it in this order:

1. Extract a small `SoccerDsl` with domain methods (`matchesBetween`, `standingsFor`, `recordFor`, `playersAt`) returning **structured results**, and rewrite one describe-block (`match queries`) against it as a proof of concept.
2. Give the DSL two protocol drivers (direct handler + MCP client), and run the migrated specs through both — retiring the overlap between `sample-questions` and `mcp`.
3. Move the absolute timing gates out of the correctness path.
4. Roll the remaining question groups onto the DSL, pushing structural `homeId`/count assertions down to the unit layer as you go.

That lands you on Dave's four-layer model (lesson 305) with specs that stay true as the rendering and the transport evolve — which is the entire promise of the approach.

### Category ratings

| | Category | Rating | Rationale |
|---|---|---|---|
| A | Spec quality | 2 | Strong spec-first naming, but bodies couple to output format, tool names and internals; fails the "different system" test. |
| B | 4-layer architecture | 2 | Clean SUT/handler seam, but only a vestigial helper — no domain DSL, no PD contract. |
| C | Isolation | 3 | Fully deterministic, no interference, parallel-safe, no cleanup — but leans entirely on one big shared real-data fixture. |
| D | DSL quality | 1 | `ask()` is a passthrough to the tool API; SUT-shaped vocabulary, no domain language/defaults/decomposition. |
| E | Protocol drivers | 2 | Real in-memory-transport E2E and good error-as-tool-error checks, but no PD layer/atomic steps; two suites duplicate. |
| F | Intermittency | 3 | Inherently non-flaky; only blemish is absolute wall-clock perf/load assertions (resource/environment risk). |
| G | Releasability truthfulness | 4 | No skips, `.only`, exclusion filters or swallowed failures; suite reports its true state. |

```json
{"acceptance_tests_found": true, "ratings": {"A": 2, "B": 2, "C": 3, "D": 1, "E": 2, "F": 3, "G": 4}, "disclosure": "full"}
```