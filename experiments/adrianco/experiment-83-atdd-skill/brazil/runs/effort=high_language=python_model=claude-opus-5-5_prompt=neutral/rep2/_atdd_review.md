I've read all seven test files, the SUT (`server.py`), the spec (`TASK.md`), and the query engine, and I've fetched the full lessons (paid tier, full disclosure) behind every category: **103b** (BDD), **203** (Acceptance Tests & BDD), **301** (Building a DSL), **302** (Test Isolation), **303** (Protocol Drivers & Stubs), **305** (The Four Layer Model), **306** (Intermittent Tests), and **308** (Four Layer Model in Gherkin). Here is the review.

---

# ATDD Review — Brazilian Soccer MCP test suite

## What I'm treating as acceptance / end-to-end tests

- **`tests/test_sample_questions.py`** — the spec's 27 natural-language sample questions, each run through an in-process MCP `Client(server.mcp)`. This is the real acceptance suite.
- **`tests/test_server.py`** — MCP protocol contract plus a genuine out-of-process end-to-end test (`test_stdio_transport_end_to_end` launches `python server.py` and talks MCP over stdio).
- **`tests/test_performance.py`** — the spec's non-functional targets (<2 s / <5 s).

`test_queries.py`, `test_data_loader.py`, and `test_team_names.py` are unit/integration tests against the engine directly — I've read them for context but they're not the subject here.

## 1. Overall assessment

This is a careful, honest, genuinely deterministic pytest suite — and that's not faint praise; it clears bars most suites fail. But measured against Dave's model it is **architecturally not an ATDD suite**. The single biggest thing is structural: the two middle layers of the four-layer model — the **DSL** and the **protocol drivers** — don't exist. Test cases talk straight to the SUT in the vocabulary of the transport (`client.call_tool("head_to_head", {...})`, `.content[0].text`, `.is_error`), and they assert on exact rendered output strings. The instinct toward specifications is clearly present — the natural-language question column is excellent — but it's welded to the current tool decomposition and output formatting, which is exactly the coupling Dave warns about. The good news, as Dave says of the legacy-migration client in lesson 308: the target shape is clear, and you already have a seam (the `SAMPLE_QUESTIONS` table) to grow it from.

## 2. Strengths

- **The question column is real domain language.** `"Show me all Flamengo vs Fluminense matches"`, `"Which teams were relegated in 2020?"` — these are outcome-focused and say nothing about implementation. This is precisely the `Given/When/Then`-in-domain-terms instinct from **lesson 103b** ("Good acceptance tests ONLY define outcomes"). Most suites never get this far.
- **Honest about state (category G — exemplary).** No `@skip`, no `xfail`, no `.only`, no commented-out tests, no swallowed exceptions in tests, no CI exclusion filters or `continue-on-error`, no `addopts` hiding anything. `test_at_least_twenty_questions` even asserts the suite can't silently shrink below the spec's 20-question floor, and the data-gap cases (Gabriel Barbosa, no Flamengo FIFA squad) are asserted truthfully rather than skipped. This is the releasability truthfulness **lesson 306** calls for.
- **Deterministic by construction (category F).** No sleeps or waits anywhere (the anti-pattern **lesson 306** is bluntest about), no network, set-based comparisons for order-independence, a self-contained SUT. `test_performance.py` even uses `fresh = SoccerQueries()` to dodge the warm-cache coupling — someone was thinking about determinism.
- **SUT boundary respected.** The optional external APIs in `TASK.md` aren't dialled; tests read local data only. That's the "stub/avoid everything outside the boundary" discipline from **lesson 302**, achieved by simply not reaching outside.
- A true transport-level end-to-end test (`test_stdio_transport_end_to_end`) proves the system works through the real channel.

## 3. Priority issues

### Priority 1 — No DSL or protocol-driver layer; test cases are fused to the MCP transport (categories B, D, E)

Every acceptance test carries the transport in its own body:

```python
# test_sample_questions.py
@pytest.fixture(scope="module")
def answers():
    async def run_all():
        async with Client(server.mcp) as client:
            out = []
            for _, tool, args, _ in SAMPLE_QUESTIONS:
                out.append(await client.call_tool(tool, args))   # protocol detail, inline
            return out
    return asyncio.run(run_all())
```

and `test_server.py` repeats the `async with Client(...) / asyncio.run` dance in every test. **Lesson 305** (The Four Layer Model) and **lesson 308** name this exactly: putting the code that interacts directly with the SUT into the test/step layer gives you "no real reuse… every test case is a chore," and "lots of places for problems to hide." There is no layer two (a domain DSL) and no layer three (a protocol driver that owns the MCP mechanics, the `asyncio.run`, the `.is_error` check, and the `.content[0].text` unwrap).

**Why it matters:** per **lesson 301**, the DSL is what keeps the vocabulary "stable even as the underlying system changes" and the PD (**lesson 303**) is "the only place that knows how the system actually works." Today, if the MCP client API shifts, or a tool is renamed, or the output-unwrapping changes, you edit every test.

**Before → after** — lift a protocol driver and a thin DSL out of the inline plumbing:

```python
# protocol driver: the ONLY code that knows about MCP, asyncio, is_error, content unwrap
class SoccerDriver:
    def __init__(self, server): self._server = server
    def ask(self, tool, **args) -> str:
        async def go():
            async with Client(self._server) as c:
                r = await c.call_tool(tool, args)
                assert not r.is_error, r.content[0].text   # atomic: each step passes or fails here
                return r.content[0].text
        return asyncio.run(go())

# DSL: domain language, decomposed by area, defaults supplied (lesson 301 / 305)
class Soccer:
    def __init__(self, driver): self._d = driver
    def head_to_head(self, a, b):            return self._d.ask("head_to_head", team_a=a, team_b=b)
    def home_record(self, team, season):     return self._d.ask("team_record", team=team, season=season,
                                                                 competition="Brasileirão", venue="home")
    def relegated_in(self, season):          return self._d.ask("standings", season=season)
```

A test case then reads in the problem domain, and the `async with Client` never appears in it. **Lesson 305**'s recipe becomes available to you: new feature → extend the DSL → add a driver method → green.

### Priority 2 — Specs are coupled to tool choice and to exact output strings (category A)

Each entry hard-codes *which* tool the system "would" call and asserts on the rendered text:

```python
("What is Corinthians' home record in 2022?",
 "team_record", {"team": "Corinthians", "season": 2022, "competition": "Brasileirão", "venue": "home"},
 ["Corinthians home record (2022, Brasileirão Série A)", "- Matches: 19", "Win rate:"]),
```

Two leaks, both from **lesson 203**. First, applying Dave's coupling test ("imagine the spec fulfilled by a completely different system"): the *question* survives a reorganisation of the tool surface, but the test does not — it's pinned to `team_record` with these exact args. Second, asserting `"- Matches: 19"` with that exact dash-and-spacing is checking presentation, a milder form of the "bus edit" scenario-overload anti-pattern where the real requirement drowns in rendered detail. (Note also the comment says these are "the tool call an LLM would make," but no LLM is in the loop — the human-written mapping *is* the thing under test, so the NL→tool behaviour isn't actually exercised.)

**Before → after** — assert a domain outcome, let the driver parse the rendered text into facts:

```python
record = soccer.home_record("Corinthians", season=2022)   # DSL owns the tool choice
assert record.matches == 19
assert record.wins + record.draws + record.losses == record.matches   # a real invariant, format-independent
```

The driver does the one-time job of turning the answer string into a small value object; the spec then states *what* is true, not *how it's printed* — "concise, accurate, understandable and durable," per **lesson 103b**. (Your own `test_head_to_head_is_consistent` in the unit suite already asserts invariants like `a + b + d == total` — that's the mindset to bring up into the acceptance layer.)

### Priority 3 — Wall-clock assertions in the releasable suite (category F)

```python
# test_performance.py
def test_simple_lookups_under_two_seconds(q, method, kwargs):
    assert _timed(getattr(q, method), **kwargs) < 2
```

**Lesson 306** lists "resource contention" and "environment changes" as root causes of intermittency, and absolute timing assertions are precisely resource-sensitive — on a loaded CI runner these flip red for no behavioural reason. Two smaller coupling notes: the simple-lookup cases run on the shared warm-cache `q` fixture, so their timing depends on test order, while the aggregate cases correctly use `fresh = SoccerQueries()`.

**Fix direction (don't skip — that would break your excellent category-G honesty):** keep these, but move them out of the pass/fail releasability gate — mark them (`@pytest.mark.perf`) and run them as a separate benchmark job, so a noisy host can't make a green build look red. If you keep a hard assertion, make the thresholds explicitly generous headroom, not tight bounds. The spec's <2 s/<5 s are functional *targets*; **lesson 203** is clear that this kind of edge/non-functional checking usually belongs at a different level from the acceptance scenarios.

## 4. Further improvements

- **Golden-dataset dependency (category C).** The suite is welded to one fixed data snapshot (`827` Brazilian players, `raw_counts["fifa_data.csv"] == 18207`, exact standings). Isolation-in-the-small is fine because the SUT is read-only — but **lesson 305** advises "use only synthetic data, created by your DSL… avoid starting the SUT with lots of state." You get determinism by immutability-by-accident rather than by functional/temporal isolation technique, and any data refresh breaks hundreds of assertions at once. Not urgent given the demo scope, but it's why C isn't higher.
- **Shared mutable cache.** `SoccerQueries._standings_cache` is shared through the session-scoped `q` fixture; `test_performance` already has to defend against it. Worth making explicit rather than incidental.
- **Error-message quality is close.** `assert not result.is_error, result.content[0].text` and the `f"{question!r}: expected {fragment!r} in:\n{text}"` message are the right instinct from **lesson 305** ("good error messages… at the language of the problem domain"); once a driver exists, centralise them there so every step fails loudly and atomically.

## 5. Suggested next steps

1. **Extract the protocol driver first** (Priority 1). Pull the `async with Client` / `asyncio.run` / `is_error` / `content[0].text` out of all three acceptance files into one `SoccerDriver`. This is pure refactor, low risk, and immediately removes the duplicated plumbing. The `test_stdio_transport_end_to_end` test gives you a second driver (stdio) behind the same interface — exactly the "one interface, many drivers" payoff from **lesson 303**.
2. **Grow a thin DSL** from the `SAMPLE_QUESTIONS` table (Priority 2): one domain method per question shape, defaults for competition/venue, returning parsed value objects. Then rewrite assertions onto domain facts and invariants rather than rendered substrings.
3. **Relocate the timing tests** out of the pass/fail gate (Priority 3) without skipping them.
4. Leave category G exactly as it is — the coverage-floor guard and the refusal to hide anything are a genuine strength; protect them as you refactor.

This needs restructuring, not rescue. You have an honest, deterministic suite with a real domain-language seam already in place — the four-layer model (lesson 305) gives you the target, and step 1 above is where to start.

```json
{"acceptance_tests_found": true, "ratings": {"A": 2, "B": 1, "C": 2, "D": 1, "E": 1, "F": 3, "G": 4}, "disclosure": "full"}
```