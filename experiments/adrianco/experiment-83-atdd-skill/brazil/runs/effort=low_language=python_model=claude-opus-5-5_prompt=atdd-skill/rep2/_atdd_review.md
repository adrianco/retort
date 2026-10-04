I now have the full lessons for every category A–G (the server returned `disclosure: "full"` throughout). Here is the review.

---

# ATDD Review — Brazilian Soccer MCP acceptance suite

## Overall assessment

This is a genuinely good acceptance suite, and an unusually faithful rendering of Dave Farley's four-layer model in Python/pytest. The test cases in `tests/acceptance/test_brazilian_soccer_knowledge.py` read as executable specifications in the language of Brazilian football — teams, seasons, competitions, records — and say almost nothing about MCP, JSON-RPC or stdio. The plumbing is pushed down into a clean DSL (`dsl.py`) and a single protocol driver (`drivers.py`), exactly where Dave puts it. The weaknesses are not structural; they are a handful of places where the suite couples to things it doesn't need to: the real dataset's exact values, the server's rendered text output, and — in two tests — the wall clock. Fixing those is refinement of a sound design, not restructuring.

## Strengths

- **The specs say what, not how.** `soccer.ask_for_matches(team="Flamengo", opponent="Fluminense")` / `soccer.confirm_every_match_involves("Flamengo", "Fluminense")` is precisely the outcome-focused style of lesson 103b (*BDD: Defining the Behaviour of the System*). You could re-implement the SUT as a REST service or a GraphQL endpoint and almost every one of these 26 tests would remain true, unchanged — Dave's acid test for whether a spec is coupled to the implementation (lesson 203).
- **Clean four-layer separation** (lesson 305). Test case → DSL → protocol driver → SUT, wired through `conftest.py`. The driver is the *only* code that knows the server speaks JSON-RPC over stdio.
- **Atomic, self-reporting PD steps with domain-language error messages** (lesson 305 / 306). Every `confirm_*` in `drivers.py` passes or fails, and failures carry the answer and the domain fact: `f"{home} v {away} does not involve {team}"`, `f"no matches listed in:\n{self.last_answer}"`. This is exactly what Dave means by "make each step pass or fail, with a useful error message at the level of the spec writer."
- **A reusable DSL with defaults and named parameters** (lesson 301): `ask_for_team_record(team, season=None, venue="all", competition="Brasileirão")`, `ask_for_best_records(venue="all", limit=10, min_matches=19)`. Tests specify only what they care about.
- **The suite is honest about its state** (lesson 306's "definitive statement of releasability"). No `@skip`, no `xfail`, no `.only`, no `-k` filters, no `continue-on-error`, no swallowed exceptions in the DSL or PD. Better still, `docs/atdd-findings.md` openly records that 2022 aggregates were partial (unplayed fixtures with NA scores) and that the spec was *moved to 2019* rather than quietly skipped. That is the right instinct, transparently documented.

## Priority issues

### 1. The two timing tests are planted flakes and leak implementation vocabulary (`test_brazilian_soccer_knowledge.py:124-129`)

`TestServiceQuality` asserts a wall-clock budget:

```python
def test_should_answer_aggregate_questions_promptly(self, soccer):
    soccer.confirm_answered_within(seconds=5, question="standings", season=2015)
def test_should_answer_lookups_promptly(self, soccer):
    soccer.confirm_answered_within(seconds=2, question="players", name="Casemiro")
```

**Why it matters.** Lesson 306 lists *changes in the environment* and *resource contention* as two of the five root causes of intermittency — and a hard `< 2 seconds` assertion is sensitive to exactly those. On a loaded CI box this is the one test in the suite most likely to go red for a reason that has nothing to do with the system being broken, which is precisely the trust-eroding failure Dave warns against: *"when a test fails, we can trust the failure… no agonising over whether to run it again."* Separately, `question="standings"` is implementation vocabulary leaking up into the test case — `confirm_answer_time` maps that string straight onto a tool name (`drivers.py:116`), the one spot where a test case knows how the server is wired.

**Direction.** Dave's view is that acceptance tests prove behaviour, and that *"a passing test doesn't prove performance"* belongs with production monitoring, not the releasability gate. Either lift these into a separate, clearly-labelled performance suite that isn't a release blocker, or — if a latency budget must be a spec — make it generous and phrase it in domain terms so no tool name appears in the spec:

```python
# before — brittle threshold, tool name in the spec
soccer.confirm_answered_within(seconds=2, question="players", name="Casemiro")

# after — behaviour stays in the spec; the budget is advisory and lives in the DSL/PD,
# expressed as a domain action rather than a tool name
soccer.ask_for_players(name="Casemiro")
soccer.confirm_a_player_lookup_is_not_noticeably_slow()
```

### 2. The PD parses rendered display text and the specs assert exact dataset values (`drivers.py:11-12, 62-113`; `test_...py:88, 39, 51-53`)

The driver reverse-engineers the server's *human-readable* output with regexes:

```python
MATCH_LINE = re.compile(r"^- (\d{4}-\d{2}-\d{2}): (.+?) (\d+)-(\d+) (.+?) \((.+?) (\d{4})(?:, .*)?\)$")
```

and specs pin exact aggregates from the live CSVs: `confirm_champion_is("Flamengo", points=90)`, `confirm_record_has(matches=19)`, `confirm_record_has(matches=38)`.

**Why it matters.** This is the same fragility class Dave names in lesson 203's "bus edit" anti-pattern (assertions bound to the rendered presentation) and in lesson 306's *test-data stability* cause. Your own `docs/atdd-findings.md` is the evidence: a data quirk already forced the 2022→2019 move. Any re-wording of the server's output lines, or any refresh of the Kaggle datasets, breaks the suite for reasons unrelated to behaviour. The *encapsulation* is correct — this brittleness is sealed inside the PD, which is the right layer to absorb SUT change (lesson 303) — so this is the least-bad form of the problem. But parsing display strings is still a standing liability.

**Direction.** Have the MCP tools return *structured* content (a `data` payload alongside the human text) and let the PD assert against the structure rather than scraping prose. Where exact aggregates must be asserted, prefer invariants over magic numbers — Dave's synthetic-data principle (lesson 305: *"use only synthetic data, created by your DSL"*) doesn't fully apply to a fixed reference-data server, but you can still reduce snapshot-coupling:

```python
# before — couples to a specific dataset snapshot
soccer.ask_for_team_record("Grêmio", season=2018)
soccer.confirm_record_has(matches=38)

# after — asserts the behavioural invariant (a full Brasileirão season is 38 rounds)
soccer.confirm_record_is_a_complete_league_season()   # wins+draws+losses == rounds, etc.
```

### 3. One session-scoped driver with shared `last_answer` blocks parallelism, and the RPC has no timeout (`conftest.py:7-12`; `drivers.py:47-52`)

```python
@pytest.fixture(scope="session")
def driver():
    d = McpStdioDriver(); d.start(); yield d; d.stop()
```

Every test shares one subprocess, one stdin/stdout pipe, and one mutable `self.last_answer`.

**Why it matters.** Because the SUT is read-only reference data, functional and temporal isolation (lesson 302) come essentially for free — running a test twice gives the same answer, and no test can corrupt another's data. That's a real strength and why this suite is deterministic today. But Dave's payoff for isolation is *"now we can run them in parallel too, so we get our test results really quickly"* — and this suite can't. Point `pytest-xdist` at it and the shared pipe and shared `last_answer` collide. Second, `_rpc` does a blocking `self.proc.stdout.readline()` with no timeout (`drivers.py:50`); if the server dies or stalls, the test hangs or fails with an opaque `json.loads("")` rather than a clean, timed-out failure — the opposite of lesson 306's *"believe it's broken when it is"* poll-and-timeout guidance.

**Direction.** Nothing here needs data aliasing (the SUT is immutable), so the fix is modest: make the driver per-test (or at least per-xdist-worker) so each has its own subprocess and `last_answer`, and wrap the read in a timeout so a stalled server fails fast and legibly.

## Further improvements

- **Two assertions live in the DSL instead of the PD.** `confirm_answer_equals` (`dsl.py:68`, `assert self.driver.last_answer == previous`) and the raw `last_answer()` accessor (`dsl.py:42`) pull a comparison and the rendered answer up into the DSL layer. Lesson 305: *"protocol drivers are nearly always where assertions are made."* Move the equality check behind a `driver.confirm_same_answer_as(previous)` so the DSL stays declarative and the PD owns the assertion and its error message.
- **`test_should_search_every_match_source` (`test_...py:32-35`) loops five competitions in one test.** Mild scenario-overload (lesson 203, mistake #2/#4). Consider `pytest.mark.parametrize` so each competition is its own scenario with its own pass/fail line.
- **No formal PD contract.** Lesson 305 notes an interface for the driver is optional and only pays off when you want swappable channels (web/mobile/voice). You have one channel, so this is genuinely optional — flagged only for completeness.
- **No stubs, correctly.** The SUT reads local CSVs and has no external dependencies, so there is nothing outside the boundary to fake (lesson 303). The absence of stubs is the right call, not a gap.

## Suggested next steps

1. **De-risk the release gate first:** pull the two timing assertions out of the blocking suite (priority 1). This is a few minutes' work and removes the most likely false red.
2. **Attack snapshot fragility next** (priority 2): add structured output to the MCP tools and reassert against structure, so neither a wording change nor a data refresh can break behavioural tests. This is the change that will pay back most over the life of the suite.
3. **Then unlock parallelism** (priority 3): per-test/per-worker driver plus an RPC timeout. Once done, this suite is parallelisable, deterministic and fast — the full lesson-302 payoff.

The architecture is already right. These are refinements to an honest, well-layered suite — not a rebuild.

```json
{"acceptance_tests_found": true, "ratings": {"A": 4, "B": 3, "C": 3, "D": 4, "E": 3, "F": 3, "G": 4}, "disclosure": "full"}
```