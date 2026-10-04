I've read the full test suite and SUT, and fetched the full ATDD course lessons (paid tier, full disclosure) behind every category: BDD (103b, 203), Four-Layer Model (305), Test Isolation (302), DSL (301), Protocol Drivers & Stubs (303), and Intermittent Tests (306). Here is the review.

---

# ATDD Review — Brazilian Soccer acceptance suite

## 1. Overall assessment

This is a genuinely good acceptance suite that already embodies the core of Dave's approach — and that's not faint praise. The four-layer model is in place and clean: test cases speak pure problem-domain language, a DSL sits beneath them, and a single protocol driver is the only thing that knows the system is an MCP server. Most reviews start by explaining why the suite needs restructuring; this one doesn't. The work left to do is refinement, not rebuild. The two things holding it back are both about **determinism**: the suite asserts against a large pile of real third-party data it doesn't own, and it bakes wall-clock timing assertions into functional specs — and these are exactly the two of Dave's five root causes of intermittency that the architecture otherwise avoids.

## 2. Strengths

- **Textbook four-layer separation** (`four-layer-model`, lesson 305). Test case → DSL (`dsl.py`) → protocol driver (`mcp_driver.py`) → SUT (`server.py`), with each layer at its own abstraction. The PD is "the only test layer that knows the system is an MCP server" — precisely Dave's layer-three definition.
- **Specs are real specifications, not scripts** (`bdd`, lesson 103b). `test_should_find_matches_between_two_rivals` reads in the language of a fan, not of tools and JSON. Every test name starts with *should*, which is exactly the framing device Dave recommends to "focus our minds on WHAT the system should do." Given/When/Then shows through as ask→confirm.
- **Assertions live in the protocol driver** (lesson 305: "Protocol drivers are nearly always where assertions are made"), and the SUT's text-format knowledge (the regexes) is correctly confined there — the right single place to fix integration drift.
- **Excellent error messages.** `_fail` (`mcp_driver.py:34`) dumps the message *and* the full answer. That's Dave's "good error messages can help diagnose test failures more quickly… at a sensible level for spec writers."
- **Defaults and reuse in the DSL** (`dsl`, lesson 301): `venue="all"`, `competition="Brasileirão"`, `limit=20` let specs state only what they care about; `ask_for_matches` / `ask_for_players` are reused across many tests.
- **Honest suite** (releasability). No `@skip`, no `xfail`, no `-k`/`--ignore` filters, no `continue-on-error`, no commented-out tests, no swallowed exceptions — `ask` asserts on `is_error` and every `confirm_*` raises. Green means green. This is the thing reviewers are uniquely placed to verify, and it's clean.

## 3. Priority issues

### Priority 1 — The suite asserts against real external data instead of synthetic data it owns

*(categories C and F; `test-isolation`/`four-layer-model` lessons 302, 305)*

Every assertion is pinned to the live contents of the Kaggle CSVs: `confirm_champion("Flamengo", points=90)` (`:85`), `confirm_match_count(38)` (`:17`, `:27`, `:44`), `confirm_record(matches=19)` (`:62`). Dave is unusually direct here:

> "I recommend that you try to use only synthetic data, created by your DSL, and overridden in your test cases. Avoid starting up the SUT with lots of state — generate the state you want the SUT to be in within your test." (lesson 305)

And in the intermittency lesson, "changes in test data between test runs" is one of the five named root causes. Your own `docs/atdd-findings.md` is the evidence: "Brasileirao_Matches.csv has only 299 of 380 matches for 2022; merged with BR-Football-Dataset.csv (deduped…)". The ground truth behind `confirm_match_count(38)` is a product of merge-and-dedup logic. The day that logic — or the upstream file — changes, this test goes red for a reason that has nothing to do with whether the *behaviour* works.

This is the hardest one to fully resolve because the system's whole purpose is to answer questions about a fixed historical corpus, so I won't pretend there's a clean one-liner. But the direction is clear: separate **behaviour** tests (run against a small synthetic dataset the DSL seeds, asserting exact values) from a **small number** of real-data smoke checks (assert on shape/relationships, not brittle magic numbers).

```python
# Before — asserts a value derived from third-party merge logic
def test_should_report_a_teams_home_record(soccer):
    soccer.ask_for_team_record("Corinthians", season=2022, competition="Brasileirão", venue="home")
    soccer.confirm_record(matches=19)   # breaks if dedup/source data shifts

# After — behaviour proven against data the test owns; the "19" is a fact the test established
def test_should_report_a_teams_home_record(soccer):
    soccer.given_season_with(team="Corinthians", home_matches=19, away_matches=19)
    soccer.ask_for_team_record("Corinthians", venue="home")
    soccer.confirm_record(matches=19)
```

That mirrors Dave's invoice example: the test *puts the SUT into the state it needs*, then measures. It also unlocks temporal isolation (lesson 302) you can't currently express because no test creates data.

### Priority 2 — Wall-clock timing assertions inject intermittency into functional specs

*(category F; `intermittent-tests`, lesson 306)*

`test_should_answer_aggregate_questions_quickly` → `confirm_answered_within(seconds=5)` (`:177`) and `…lookups_quickly` → `confirm_answered_within(seconds=2)` (`:183`). `confirmed_answered_within` (`mcp_driver.py:81`) is a hard pass/fail on elapsed time. This is precisely the resource-contention root cause Dave lists — "Not enough CPU, not enough RAM — these things can make our tests behave differently." Run these two under load, or in parallel with the other 33, and a 2-second threshold will flake. A flaky test "compromises our trust… as a definitive statement of releasability."

Dave's test suite is meant to answer one question — is this releasable? — deterministically. A latency SLO is a real requirement, but it belongs where it won't produce non-deterministic red: a performance check that runs separately (and ideally reports a trend), or production monitoring, which lesson 302 explicitly points to for "stuff that integrated end-to-end testing will find."

```python
# Before — green/red of the acceptance suite now depends on machine load
def test_should_answer_lookups_quickly(soccer):
    soccer.ask_about_player("Casemiro")
    soccer.confirm_answered_within(seconds=2)

# After — keep the behaviour here; move the latency budget to a perf job that
# can tolerate variance (percentiles over N runs), not a single-shot assertion.
def test_should_find_a_player_by_name(soccer):
    soccer.ask_about_player("Casemiro")
    soccer.confirm_answer_mentions("Casemiro")
```

Note this is *not* the sleep anti-pattern (you have no sleeps anywhere — good); it's the inverse failure mode, but it flakes for the same environmental reasons.

### Priority 3 — The generic `ask("tool_name", …)` bridge leaks SUT names into the DSL and breaks the DSL↔PD symmetry

*(categories B and D; `protocol-drivers`/`four-layer-model`, lessons 303, 305)*

Every DSL method funnels through `self.driver.ask("search_matches", …)` / `"team_record"` / `"standings"` (`dsl.py:14`, `:25`, `:37`). Those strings are the MCP server's tool names — SUT implementation detail — living in layer two. Dave's PD is "the only place that knows how the system actually works," and his recommended shape is a symmetric mapping:

> "`DSL.placeOrder` maps to `driver.placeOrder`, but the parameters are different: default values added, functional aliasing for isolation applied… keeping the call from DSL to PD at the same level of abstraction." (lessons 303/305)

Right now the PD is a generic conduit and the domain→endpoint mapping has floated up into the DSL. Give the PD domain-named, atomic methods and the layering snaps back into Dave's pattern (and the brittle regex parsing concentrates behind named methods rather than a single stringly-typed funnel):

```python
# DSL (before)                         # DSL (after)
self.driver.ask("team_record",         self.driver.team_record(
    team=team, season=season,              team=team, season=season,
    competition=competition, venue=venue)  competition=competition, venue=venue)

# PD (after) — the only layer naming the tool, one atomic step, pass/fail
def team_record(self, team, season=None, competition=None, venue="all"):
    self._call("team_record", team=team, season=season,
               competition=competition, venue=venue)
```

This also future-proofs the "one DSL, many protocol drivers" move Dave prizes (lesson 303): a second channel (e.g. a REST driver) could satisfy the same DSL without the specs knowing.

## 4. Further improvements

- **CSV filenames in a spec** (category A). `test_should_load_every_provided_dataset` (`:169`) asserts `confirm_answer_mentions("Brasileirao_Matches.csv", …)`. Apply Dave's coupling test (lesson 203): "imagine the spec being fulfilled by a completely different system." Load the same data from a database and this spec wrongly fails though behaviour is identical. Assert on the *competitions/coverage* the data provides, not the filenames.
- **Weak substring assertions.** `confirm_answer_mentions` (`mcp_driver.py:41`) is case-insensitive substring containment, so a test can pass on a coincidental match (e.g. "Santos" appearing anywhere). Fine as a smoke check; tighten the ones standing in for exact outcomes.
- **DSL is one growing class.** `SoccerDsl` is still readable, but Dave decomposes the DSL by domain area "to avoid ending up with a giant, hard-to-maintain piece" (lesson 305). The comment banners (matches / team / player / stats) are natural seams if it keeps growing.
- **Clean SUT boundary — keep it.** The in-process, read-only SUT means no external systems and no stubs, so the `stubs` guidance ("translators, not simulations") simply doesn't apply here, and no poll-with-timeout is needed (synchronous, single-threaded — no races). That's a legitimately good fit, not a gap.

## 5. Suggested next steps

1. **Don't restructure — you're on the model.** Start with Priority 2: it's a few lines and removes your only genuine source of flakiness today. Split the two timing tests out of the acceptance suite into a separate perf/monitoring check.
2. **Then Priority 3**, the DSL→PD rename. Mechanical, low-risk, and it restores Dave's abstraction symmetry while containing the regex brittleness behind named methods.
3. **Then Priority 1**, the longest-horizon item: introduce a small synthetic dataset the DSL can seed so behaviour tests assert against data the test owns, keeping only a thin layer of real-data smoke checks. This is the change that makes the suite durable against upstream data churn — and it's the one your `atdd-findings.md` is already quietly warning you about.

All criteria above were drawn from the full ATDD course lessons (full disclosure, paid tier) — not a generic checklist.

```json
{"acceptance_tests_found": true, "ratings": {"A": 3, "B": 3, "C": 2, "D": 3, "E": 3, "F": 2, "G": 3}, "disclosure": "full"}
```