I now have full-disclosure content for every category. Here is the review.

---

# ATDD Review — `test_soccer.py` (Brazilian Soccer MCP)

## Overall assessment

This is a competent, working **pytest unit/integration suite** — but measured against Dave Farley's ATDD principles, it is structured as a set of *implementation scripts*, not *executable specifications*. The ~30 tests call the production functions in `soccer.py` directly (`soccer.search_matches(...)`, `soccer.champion(2019)`) and assert on **substrings of the formatted human-readable text** those functions return. There is no DSL layer, no protocol-driver layer, and no separation between "what the system should do" and "how this build happens to render it." The two MCP tests (`test_tools_list_and_call`, `test_stdio_server`) are the only ones that drive the system through its real deployed boundary — and the stdio subprocess test is the one genuine end-to-end test in the file. The suite is honest (nothing is skipped or hidden), but it is tightly coupled to both the current output format and a large fixed production-like dataset, which is the opposite of what Dave advocates. Good news: the four-layer model gives you a clear target, and the sample-question organisation is a solid starting point to refactor *toward* specifications.

## Strengths

- **The tests are organised around real user questions** (`test_q1_flaflu`, `test_q10_2019_champion`, `test_q12_relegated_2020`, `test_q19_derbies_2023`). This is exactly the right *instinct* — these read like acceptance criteria ("who won the 2019 Brasileirão?"), which is the raw material for domain-language specs (lesson 103b).
- **`test_stdio_server` is a true end-to-end test.** It spawns `server.py` as a subprocess and speaks real newline-delimited JSON-RPC over stdio, exactly as Claude Desktop would. Testing through the real protocol boundary is precisely what Dave means by testing to the SUT boundary (lesson 302).
- **The suite is releasability-honest.** No `@pytest.mark.skip`, no `xit`/`.only`, no `-k "not broken"` filters, no `continue-on-error`, no swallowed exceptions. Green means every test ran — the single most important property of a trustworthy suite (lesson 306: "a definitive statement of the releasability of our system").
- **No sleeps papering over races.** The system is synchronous and in-process, and the tests don't reach for `time.sleep()` to stabilise anything — they avoid the headline intermittency anti-pattern from lesson 306.

## Priority issues

### 1. Assertions are coupled to the implementation's output format, not to outcomes (category A)

This is the highest-leverage problem. Dave's central BDD principle (lesson 103b, *BDD: Defining the Behaviour of the System*) is that a good spec "remains true however we decide to make our calculator work" — it defines the *outcome*, never the rendering. These tests assert on the exact text the current build happens to print:

```python
# test_q11_standings_2019 — today
out = soccer.standings(2019, top=3)
assert "1. Flamengo - 90 pts (28W, 6D, 4L" in out
```

The *behaviour* here is "Flamengo won the 2019 Brasileirão with 90 points, 28 wins, 6 draws, 4 losses." The *test* is pinned to a one-line string format — the `"1. "` prefix, the literal ` pts `, the ` (28W, 6D, 4L`. Rename `pts` to `points`, reorder the record, or localise the output and the test fails even though the system is still correct. Dave: implementation-focused tests are "accurate, but only for the current version of our implementation — narrowly correct… As soon as you change the implementation the test fails." Lesson 203's test for coupling applies directly: *could a completely different system — say one returning JSON — satisfy this spec?* As written, no.

The problem is worst in `test_q4_corinthians_home_2022`, which re-reads the CSV inside the test and computes its own expected answer from the same data the SUT reads:

```python
rows = [r for r in csv.DictReader(open(HERE / "data/kaggle/Brasileirao_Matches.csv", ...)) ...]
wins = sum(float(r["home_goal"]) > float(r["away_goal"]) for r in rows)
assert f"Matches: {len(rows)}" in out and f"Wins: {wins}," in out
```

This is a tautology: the oracle is derived from the same source as the thing under test, so a shared bug in CSV parsing passes silently. It reaches *below* the SUT boundary into its data files — the exact inversion of lesson 302's "test only what you own."

**Direction (before/after).** Assert the outcome, and give the SUT a machine-readable answer to assert against so the spec survives reformatting. Even without a full DSL you can move this a long way:

```python
# after — outcome, not format. standings_data() returns structured rows; text rendering is a separate concern.
table = soccer.standings_data(2019)
champion = table[0]
assert champion.team == "Flamengo"
assert (champion.points, champion.wins, champion.draws, champion.losses) == (90, 28, 6, 4)
```

Now the human-readable `standings()` string can be reformatted freely, and `test_q4` asserts against an independently-known result (a fixed expected record for Corinthians at home in 2022) rather than against a re-derivation of the SUT's own input.

### 2. No DSL or protocol-driver layer — the suite is single-layer (categories B, D, E)

Dave's four-layer model (lesson 305) is *test case → DSL → protocol driver → SUT*. This suite collapses all of that: the test case reaches straight into `soccer.*` (and, in `test_q4`, into the CSV files). The MCP tests show the cost most clearly — the JSON-RPC envelope is hand-assembled inline and repeated:

```python
# test_tools_list_and_call / test_stdio_server — protocol plumbing duplicated in the test case
r = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                   "params": {"name": "champion", "arguments": {"season": 2019}}})
assert r["result"]["isError"] is False and "Flamengo" in r["result"]["content"][0]["text"]
```

The test case is drowning in protocol detail (`jsonrpc`, `id`, `result.content[0].text`) — this is Dave's "confusing UI interactions with behaviour" mistake (lesson 203), transplanted to a JSON-RPC wire format. Lesson 305: protocol drivers are "the only place that knows how the system actually works."

**Direction.** Introduce a thin protocol driver and a small DSL on top of it, so the spec speaks the domain and the wire format lives in one reusable place:

```python
# protocol driver (the ONLY code that knows the JSON-RPC/stdio wire format)
class McpDriver:
    def call(self, tool, **args):
        resp = server.handle({"jsonrpc": "2.0", "id": next(self._id),
                              "method": "tools/call",
                              "params": {"name": tool, "arguments": args}})
        assert resp["result"]["isError"] is False, resp["result"]["content"][0]["text"]
        return resp["result"]["content"][0]["text"]   # PD makes each step pass/fail (lesson 305)

# DSL — domain vocabulary, reused everywhere
class Soccer:
    def champion_of(self, season):      return self.driver.call("champion", season=season)
    def standings_for(self, season, top=3): ...

# test case — reads like the user's question
def test_2019_champion(soccer):
    assert_champion(soccer.champion_of(2019), team="Flamengo", points=90)
```

Lesson 305: "each step, each method in a PD, pass or fail" with "good error messages… in the language of the problem domain." Your current `assert "found" in out` (`test_q8`, `test_q9`) and `assert out.count("\n") == 5` (`test_q16`) fail that test — on breakage they tell a maintainer almost nothing. Routing assertions through a PD that reports in domain terms fixes this once for every spec. This is also the single change that unlocks lesson 303's payoff: the *same* DSL spec could then run through both the in-process `server.handle` driver and the stdio-subprocess driver, proving the system works through both channels from one test.

### 3. `test_performance` asserts wall-clock time — a built-in flaky test (category F)

```python
def test_performance():
    t = time.time()
    soccer.search_players(nationality="Brazil"); soccer.head_to_head("Flamengo", "Vasco")
    assert time.time() - t < 2
    ...
    assert time.time() - t < 5
```

Lesson 306 names resource contention and environment variation as root causes of intermittency, and is blunt that timing-dependent tests "just make it slower to fail." A hard `< 2s` / `< 5s` threshold is the mirror image of the sleep anti-pattern: it passes on your laptop and flakes on a loaded CI box or a cold cache, and when it fails it tells you nothing about *correctness* — only that today's machine was busy. That erodes exactly the trust lesson 306 is about: "when a test fails, we can trust the failure and reject the change."

**Direction.** Move performance out of the pass/fail acceptance suite. If you must guard against regressions, record timings as a benchmark/metric (e.g. `pytest-benchmark`) that trends over time and is reviewed, rather than a boolean gate on a wall clock. Keep the acceptance suite's failures meaning "the system is broken," never "the box was slow."

## Further improvements

- **Shared fixed-dataset coupling (category C).** Every test queries a large session-scoped, read-only `KB` loaded from fixed CSVs, and many assert on exact dataset values (`len(kb.players) == 18207`, `len(kb.sources["historical"]) == 6886`, `"90 points"`). Because the data is immutable there's no inter-test leakage and the suite *could* run in parallel — genuinely good. But this is the inverse of Dave's advice in lessons 302 and 305: "Avoid starting up the SUT with lots of state — generate the state you want the SUT to be in within your test," using synthetic data created by the DSL. The current approach means a data correction or a Kaggle re-download silently breaks dozens of specs — brittleness to *dataset version* in place of the run-to-run leakage functional isolation prevents. For a read-only reference dataset this is a defensible trade-off, but be aware you've bought determinism with a hard dependency on specific fixture values, and pin/version that dataset deliberately.
- **Weak existence assertions.** `assert "found" in out`, `assert "No matches" not in out` (`test_q3`), `assert out.startswith("Best away records")` (`test_q15`) assert that *something rendered*, not that the right thing happened. Tighten these to the actual expected outcome once structured accessors exist.
- **Document known data gaps as expected failures, not silent avoidance (category G).** The README notes the 2022 season is incomplete and FIFA data omits several clubs, but the suite just steers around these. Lesson 306's trust principle is better served by making known gaps *visible* — a strict expected-failure marker (`@pytest.mark.xfail(strict=True, reason="2022 Brasileirão incomplete in source data")`) runs every build, reports as XFAIL, and flips the build red the day the data is completed and the behaviour changes. That keeps the suite honest about what it does and doesn't currently cover.

## Suggested next steps

1. **Separate outcome from rendering first (issue 1).** Give the query functions structured return values (or add structured siblings) and re-point assertions at fields, not substrings. This is the foundation everything else builds on and immediately kills the format-coupling and the `test_q4` tautology.
2. **Extract a protocol driver and a thin DSL (issue 2),** starting with the MCP tests where the duplication is worst. Put all JSON-RPC/stdio knowledge in one `McpDriver`; let specs call domain methods. Then collapse the two MCP tests into one spec run through two drivers (lesson 303).
3. **Demote `test_performance` out of the pass/fail suite (issue 3).**
4. Leave the honest, nothing-skipped discipline exactly as it is — and extend it by marking the documented data gaps as strict xfails.

This suite does not need throwing away — the questions it encodes are the right specifications. The work is to lift the assertions up to the level of *outcomes* and introduce the DSL/PD layers so those outcomes stop depending on today's output format. The four-layer model gives you a precise target, and the existing stdio end-to-end test shows you already know where the real boundary is.

*(This review drew on the full lessons from Dave Farley's ATDD course — BDD 103b/203, Test Isolation 302, DSL 301, Protocol Drivers & Stubs 303, Four Layer Model 305, and Intermittent Tests 306 — served at full disclosure. The releasability category 'G' has no dedicated lesson in the knowledge base; that section applies the skill's own criteria.)*

```json
{"acceptance_tests_found": true, "ratings": {"A": 2, "B": 1, "C": 2, "D": 1, "E": 1, "F": 2, "G": 3}, "disclosure": "full"}
```