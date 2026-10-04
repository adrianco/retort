I now have full disclosure (`"full"`, paid tier) on every lesson I need for categories A–F, and for category G the criteria are specified directly in the review approach (which I checked against the code: no skips, no exclusion filters, no swallowed exceptions, no CI config). Here is the review.

---

# ATDD Review — `test_soccer.py` (Brazilian Soccer MCP)

## What I reviewed

One test file, `test_soccer.py` (219 lines, pytest), exercising a stdlib MCP server (`server.py`) backed by a CSV-loading data layer (`soccer_data.py`). The suite has five bands:

- **Unit-level** — `test_normalize_team`, `test_display`, `test_parse_date` (pure functions).
- **Data coverage** — `test_all_files_loaded`, `test_utf8`, `test_dedup_overlapping_sources`.
- **Acceptance-level** — `test_q01`…`test_q25`, the "20+ sample questions via MCP tools".
- **Performance** — `test_performance`.
- **End-to-end** — `test_mcp_stdio`, which spawns `server.py` as a subprocess and drives the real JSON-RPC-over-stdio MCP protocol.

**Acceptance and end-to-end tests are present.** The `q01–q25` band is acceptance-level (real user questions answered through the server's tools), and `test_mcp_stdio` is a genuine end-to-end test through the real transport. So this review applies. The grounding for each category below comes from Dave's lessons on the MSEC course server (full lessons, paid tier — not summaries).

---

## 1. Overall assessment

This is a conscientious, broad suite — 25 behaviour-named scenarios plus a real protocol-level end-to-end test — written by someone who clearly thought about *what questions users would ask*. That domain-question framing is the seed of good acceptance testing. But as *executable specifications* in Dave's sense, the tests are implementation scripts, not specifications: they bind directly to the implementation's Python functions (`server.search_matches`, `db.head_to_head`), assert on exact output-string fragments and internal data structures, and depend on a large pile of pre-loaded real-world data. There is no DSL layer and no protocol-driver layer — the two middle layers of Dave's four-layer model are simply absent. The encouraging news: the end-to-end `test_mcp_stdio` already talks to the system through its *real* public interface, which is exactly the right seam to grow a protocol driver from. The suite's honesty is a genuine strength.

---

## 2. Strengths

- **Behaviour-named scenarios from real questions.** `test_q10_champion_2019`, `test_q12_relegated_2020`, `test_q25_historical_2003` are framed as domain outcomes ("Flamengo won… 90 points, 28 wins"; "Cruzeiro champion in 2003"). This is the BDD instinct — start from what a user wants to know.
- **A true end-to-end test.** `test_mcp_stdio` (lines 199–218) spins up the server as a subprocess and speaks real MCP: `initialize`, `tools/list`, `tools/call`, plus error paths. It asserts the server rejects an unknown tool (`isError`), returns `-32601` for an unknown method, and — nicely — that a *notification* produces no response (`len(resp) == 5`). Testing through the real protocol boundary is exactly what Dave means by respecting the SUT's natural interface.
- **Exemplary releasability honesty (category G).** Zero `@pytest.mark.skip` / `xfail` / `.only`, no exclusion filters, no `try/except` swallowing failures in the tests, and the negative/error paths are asserted rather than ignored. Nothing is hidden; a green run means every claim held. This is precisely what Dave demands in *Dealing With Intermittent Tests* ("a definitive statement of the releasability of our system").
- **Read-only determinism.** Because no test writes to the SUT, tests can't corrupt each other's state — the suite is repeatable and parallel-safe in practice.

---

## 3. Priority issues

### Priority 1 — The tests are implementation scripts, not specifications (Category A)

**What.** Assertions are string-matching against the implementation's current output format, and many tests reach *below* the SUT into the data layer's internal dictionaries.

- Format coupling: `assert "Matches: 19" in out and "Win rate" in out` (line 82); `assert out.splitlines()[1].startswith("1. Neymar Jr - Overall: 92")` (line 96); `assert out.startswith("Most recent match:")` (line 141).
- Reaching into internals: `h = db.head_to_head("Palmeiras", "Santos"); assert h["a_wins"] + h["b_wins"] + h["draws"] == len(h["matches"]) > 20` (lines 89–91) — this asserts on the shape of an internal dict, not a user-visible outcome.

**Why it matters.** In *BDD: Defining the Behaviour of the System* (lesson 103b), Dave's four goals for a spec are **concise, accurate, understandable, durable**, and the route to all four is "use the language of the problem domain rather than the language of the implementation." His decisive test, repeated in *Acceptance Tests & BDD* (lesson 203): *"imagine the spec being fulfilled by a completely different system. If it can't be, it's coupled to the implementation."* Rename the output label from `Matches:` to `Games:`, or make the server emit JSON instead of formatted text, and these tests break even though the behaviour is identical — they are "narrowly correct… as soon as we change our implementation, those tests no longer make sense" (103b). Asserting on `h["a_wins"]` is the data-layer equivalent of Dave's Mistake 1 — checking *how* the answer is assembled, not *what* the answer is.

**Before / after.** Today:

```python
def test_q04_corinthians_home():
    out = server.team_record("Corinthians", 2022, "Brasileirão", "home")
    assert "Matches: 19" in out and "Win rate" in out
```

Express the outcome in the domain, through a stable vocabulary, so it survives a format change:

```python
def test_corinthians_2022_home_record():
    record = soccer.home_record(team="Corinthians", season=2022)   # DSL call
    assert record.matches_played == 19
    assert record.win_rate is not None
```

Here `soccer.home_record(...)` is a DSL method (Priority 3) returning a small result object the test can assert against in domain terms — not a substring of today's print format.

### Priority 2 — No four-layer separation: tests bind straight to the implementation (Categories B, D, E)

**What.** The suite has only "test case → implementation." There is no DSL layer (Category D: absent) and no protocol-driver layer (Category E). Tests call `server.*` (the Python module API) or `db.*` (one layer *below* the public SUT) directly. The one place that genuinely speaks the SUT's real protocol — `test_mcp_stdio` — hand-rolls the JSON-RPC envelopes inline (lines 200–209) and parses raw responses inline (line 212), rather than extracting that into a reusable driver.

**Why it matters.** In *The Four Layer Model* (lesson 305), the four layers are **test case → DSL → protocol drivers → SUT**, and "the four-layer architecture… gives us a lot of freedom to make our specifications easy to write, readable, scalable and durable as the SUT evolves." The DSL is "a stable interface that doesn't change as the SUT evolves"; the protocol drivers are "the only place that knows how the system actually works." With no middle layers, every test is welded to the implementation's current function signatures and output strings — the churn Dave's architecture exists to absorb lands directly on all 25 tests. In *Protocol Drivers & Stubs* (lesson 303), the payoff of the PD seam is explicit: one DSL call can be serviced by different drivers — "one test, three protocol drivers, three different channels." You already have *two* channels here — the in-process `server.*` functions and the stdio JSON-RPC protocol — and they are tested by **entirely separate, duplicated code** (`q01–q25` vs `test_mcp_stdio`) instead of one spec behind two drivers.

**Before / after.** Extract the protocol interaction the stdio test already performs into a driver, and sit a thin DSL on top so a single spec can run through *either* channel:

```python
# protocol driver — the ONLY code that knows the transport
class StdioMcpDriver:
    def call(self, tool, **args):
        # spawn server.py, do the initialize handshake, send tools/call,
        # read the response, and FAIL HERE with a clear message if isError
        ...
        return text

class InProcessDriver:
    def call(self, tool, **args):
        return server.TOOLS[tool][0](**args)

# DSL — domain vocabulary, stable across both drivers
class SoccerDSL:
    def __init__(self, driver): self.driver = driver
    def champion(self, season):
        return self.driver.call("champion", season=season)

# one spec, runs through every driver
@pytest.mark.parametrize("driver", [InProcessDriver(), StdioMcpDriver()])
def test_flamengo_champion_2019(driver):
    soccer = SoccerDSL(driver)
    assert "Flamengo" in soccer.champion(2019)
```

That single spec now proves the same behaviour through both the in-process API and the real MCP protocol — collapsing the duplication between `q10` and the `champion` branch of `test_mcp_stdio`.

### Priority 3 — Reliance on a large pile of pre-loaded real data, and a wall-clock timing test (Categories C, F)

**What.** Every test reads a static, globally-cached real dataset (`get_db()` is `lru_cache`-d over six real CSVs). Nothing is created by the test; assertions pin exact magic numbers from that data: `len(db.players) == 18207` (line 52), `r["matches"] == 19` (line 61), `>= 38` (line 72), "Neymar Jr - Overall: 92" (line 96), "Cruzeiro" 2003 champion (line 182). Separately, `test_performance` (lines 186–195) asserts wall-clock budgets: `assert time.time() - t < 2` and `< 5`.

**Why it matters.** In *Test Isolation* (lesson 302), Dave's rule is that "each test creates and owns its own data… synthetic data, created by your DSL," and he is explicit: *"Avoid starting up the SUT with lots of state — generate the state you want the SUT to be in within your test."* This suite does the opposite — it depends entirely on a big external fixture and asserts exact values from it, so a data refresh (a new FIFA edition, an extra season of match CSVs) breaks tests that describe behaviour that is still correct. That maps to a named intermittency cause in *Dealing With Intermittent Tests* (lesson 306): "changes in test data between test runs." The suite survives today only because the data happens to be frozen — isolation here is accidental, not designed. And the timing assertions are a textbook flake vector from the same lesson: Dave lists "resource contention" and "changes in the environment" as root causes, and warns against baking fixed time budgets into tests — on a loaded CI box or a cold cache, `< 2s` will fail while nothing is actually broken.

To be clear, there is a real positive here: the suite uses **no `sleep`s to paper over races** (there are none to hide — the core is synchronous and in-process), which is exactly what lesson 306 asks for. The weakness is the data coupling and the clock.

**Direction.** Two moves:
1. Treat the loaded dataset as a *fixed reference corpus* and assert on *relationships and invariants* rather than brittle exact magic numbers where the exact number isn't the point — e.g. `assert record.matches_played == record.wins + record.draws + record.losses` rather than hard-coding `19` in multiple places. Keep a *few* golden-fact assertions (champion of 2019, 2003) where the specific value *is* the behaviour under test, and name them as such.
2. Move the performance budget out of the correctness suite. As lesson 306 puts it, resource limits "may be telling you that you have a more serious resource problem in the SUT itself" — but a hard clock assertion inside `pytest` turns an environment hiccup into a red build. Track latency as a separate, non-gating benchmark, or assert a far looser bound with an explicit note that it only guards against pathological regressions.

---

## 4. Further improvements

- **Assertion messages (Category E).** Lesson 305: "Good error messages can help diagnose test failures more quickly… in the language of the problem domain." Bare `assert "Flamengo" in out` gives an unhelpful failure. When you introduce drivers, make each driver step pass-or-fail with a domain-level message ("expected Flamengo as 2019 champion, got: …") so "if control returns from that step, you know it happened."
- **Mixed abstraction levels in one file.** Pure-function unit tests (`normalize_team`, `parse_date`) sensibly live close to the code, but Dave (lesson 203, Mistake 2) wants edge cases pushed *down* to unit level and acceptance scenarios kept few and high-level. The `q01–q25` band is doing some work unit tests should own (e.g. position-set membership in `test_q09`). Keep acceptance scenarios about outcomes; let the parametrised unit tests carry the combinatorics.
- **No stubs needed — and that's fine.** The SUT reads local files with no external systems, so the lesson-303 stub guidance ("stubs are translators, not simulations") doesn't bite here. Worth noting only so it isn't mistaken for a gap.
- **No CI gate.** The README runs `pytest` by hand. The suite is honest (Category G), but "green = releasable" isn't actually wired to anything. Wiring it into CI would turn this honest suite into a real releasability gate (lesson 306).

---

## 5. Suggested next steps

1. **Carve out a protocol-driver layer from `test_mcp_stdio`.** That test already does the real protocol work — extract it into a `StdioMcpDriver` (and a trivial `InProcessDriver`). This is the highest-leverage move: it removes the duplication between `q01–q25` and the stdio test, and gives you the seam everything else hangs off. (Priority 2)
2. **Put a thin DSL on top** so specs read in domain terms and assert on small result objects, not output substrings or internal dicts. Re-express the `q*` tests through it. (Priorities 1 & 2)
3. **De-brittle the data assertions and remove the clock.** Prefer invariants over scattered magic numbers, keep a named handful of golden facts, and move `test_performance` out of the gating suite. (Priority 3)
4. **Keep doing what's already right:** the behaviour-named scenarios, the real end-to-end protocol test, and — especially — the total absence of skipped/hidden tests. Don't regress on that honesty as you refactor.

The structure here needs the two missing middle layers, but the four-layer model gives you a clear target and you already have the hardest part — a real end-to-end interface — in hand. Grow the driver from there.

```json
{"acceptance_tests_found": true, "ratings": {"A": 2, "B": 1, "C": 2, "D": 0, "E": 1, "F": 2, "G": 4}, "disclosure": "full"}
```