I now have the full lessons for every category (all returned `disclosure: "full"` at the paid tier). Here is the review.

---

# ATDD Review — Brazilian Soccer MCP acceptance suite

I reviewed every file under `tests/acceptance/` — the nine `test_*.py` spec files, the DSL (`dsl/questions.py`, `dsl/archive.py`, `dsl/sample_questions.py`), and the protocol-driver layer (`drivers/soccer_drivers.py`, `drivers/mcp_connection.py`, `drivers/archive_driver.py`), wired together in `conftest.py`. I also checked the repo for silently-disabled tests. Criteria below are drawn from the full ATDD course lessons, not summaries.

## Overall assessment

This is, frankly, one of the most faithful implementations of Dave's four-layer model I've reviewed. It is not "on the right track" — it has arrived. The specs read as behaviour in the language of Brazilian football ("Flamengo 2-1 Santos", "confirm champion", "confirm relegated"); the DSL is decomposed by domain area with sensible defaults; the protocol-driver layer is the *only* place that knows the MCP tool names, JSON-RPC wire format and answer shapes; and the SUT is exercised through its real external interface (a subprocess speaking JSON-RPC over stdio, "exactly as an AI assistant's host application would"). The suite is honestly green — nothing is skipped, filtered or swallowed. The handful of things I'd change are refinements, not restructuring.

## Strengths

- **Specs define outcomes, not mechanics (lesson 103b / 203).** `test_should_calculate_the_average_goals_per_match` sets up matches, requests an overview, and confirms "2.00" — it says nothing about MCP, JSON, or CSV. Apply Dave's decoupling test ("imagine the spec fulfilled by a completely different system"): every one of these specs would remain true against a REST API or a voice assistant. The `test_should_*` naming even mirrors Dave's "start with *should*" tactic, and the Given/When/Then three-line shape is consistent throughout.
- **Textbook four-layer separation (lesson 305).** Test case → DSL (`questions.py`) → protocol driver (`soccer_drivers.py` / `mcp_connection.py`) → SUT. DSL-to-PD calls stay at the same abstraction level (`Matches.search` → `driver.search_matches`), exactly as Dave recommends.
- **The DSL does what Dave says a DSL is for (lesson 301).** Decomposed by area (Matches, Teams, Rivalries, Players, Competitions, Statistics, Assistant) "to avoid a giant, hard-to-maintain piece"; rich defaults in `archive.has_match`/`has_player` so specs state only what they care about; strong reuse (`has_matches`→`has_match`, `search_between`→`search`, sample questions calling the same DSL). It even adopts Dave's personal `confirm_*` convention for assertions — "to make them seem less technical for non-technical readers."
- **Functional isolation, done the way Dave teaches it (lesson 302).** Each spec gets its own `tmp_path` archive *and* its own server subprocess (`conftest.py:53-62`), so "specs cannot see each other's matches or players." No teardown/rollback gymnastics — the SUT is simply thrown away. The shared `provided_session` is explicitly read-only ("the same test data can be shared… but no writable data"), which is the correct exception.
- **Assertions and diagnostics live in the PD, in domain language (lesson 305).** Every `confirm_*` fails with a message a spec-writer can read: `"Expected the champion to be {expected} but found {found}"`, `"An assistant cannot ask about {category}: '{tool}' is not offered"`. When the server crashes, `mcp_connection._receive` surfaces its captured stderr — excellent failure diagnosis.
- **No sleeps; response-waiting is poll-with-timeout (lesson 306).** `mcp_connection` blocks on a queue with a 60s timeout keyed to the matching JSON-RPC id, then fails cleanly — Dave's "wait for the concluding event, time out if it never comes," not a dumb `sleep`.
- **Honest about its state (releasability).** No `@pytest.mark.skip`, `xfail`, `.only`, `-k`/`--ignore` filters, `continue-on-error`, or commented-out specs anywhere. The two `try/except` blocks in `mcp_connection.py` are legitimate timeout/EOF handling that *re-raise* with diagnostics — not swallowed failures.

## Priority issues

These are the only changes I'd prioritise, and both are small.

### 1. Wall-clock performance assertions are the suite's one real intermittency risk (lesson 306)

`test_should_answer_sample_questions_promptly` gates pass/fail on `answer.seconds < 2.0` (or `5.0`) via `confirm_answered_promptly` → `confirm_last_answer_within` (`soccer_drivers.py:274-279`).

**Why it matters.** Dave's intermittency lesson lists "changes in the environment" and "resource contention" as root causes of flaky tests. A hard wall-clock threshold couples the verdict to the speed of the machine, not the correctness of the system — on a loaded CI runner or under `pytest-xdist` (where many per-test subprocesses contend for CPU), these can go red while the system is perfectly correct. That's precisely the kind of non-deterministic failure that erodes trust in the suite: "No agonising over… should we run it again in case it's an intermittent failure."

**Fix.** Split the deterministic behaviour (the question gets a real answer) from the performance concern, and don't let the latter gate releasability in the functional suite:

```python
# Before — correctness and speed entangled, environment-sensitive
@pytest.mark.parametrize("question", SAMPLE_QUESTIONS.keys())
def test_should_answer_sample_questions_promptly(provided, question):
    provided.assistant.ask_sample_question(question)
    provided.assistant.confirm_answered_promptly()       # answer.seconds < 2 / 5

# After — the acceptance suite asserts the deterministic outcome
@pytest.mark.parametrize("question", SAMPLE_QUESTIONS.keys())
def test_should_answer_every_sample_question(provided, question):
    provided.assistant.ask_sample_question(question)
    provided.assistant.confirm_answered()                # non-empty, not an error
```

Keep the timing check if response time is a genuine acceptance criterion — but as a clearly-labelled performance tier run on controlled infrastructure (lesson 306's "Infrastructure as Code… run your acceptance tests in a close clone of production"), so contention can't masquerade as a functional failure. `confirm_answered` already almost exists in the non-timing half of `confirm_last_answer_within` (the non-empty / not-error checks).

### 2. A few specs assert presentation detail rather than pure outcome (lesson 103b / 203)

Most specs are impeccably decoupled, but three lean on how the answer is *rendered*:

- `test_should_answer_in_readable_text` asserts the exact string `"2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)"`.
- `test_should_load_every_provided_dataset` asserts literal filenames (`"Brasileirao_Matches.csv"`, …).
- `confirm_can_answer` checks specific tool names exist.

**Why it matters.** Dave's durability test: a spec should stay true "however we decide to make our calculator work." An exact rendered line couples the spec to a formatting decision; if the display format changes (say the round moves to the front), the spec breaks without the behaviour being wrong — the "narrowly correct" trap from lesson 103b.

**How to weigh it.** These are *mostly justified* and I would not force them all to change:
- The filename and tool-name assertions map to genuine stated requirements ("all six provided files load", "an assistant can discover every category"), and the coupling is at least hidden behind the `CAPABILITIES` map and the `datasets` structure rather than scattered through specs. Leave them, but know they are the spots that will move if packaging changes.
- The *exact-text* readability assertion is the one worth softening — assert the salient facts are present rather than pin the whole line:

```python
# Before — pins one formatting decision
assistant.confirm_answer_reads("2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)")

# After — asserts the readable answer carries the outcome, not its exact layout
assistant.confirm_answer_mentions("Flamengo 2-1 Fluminense", "2023-09-03", "Round 22")
```

(`confirm_answer_contains` already exists in the driver; a `confirm_answer_mentions(*parts)` that loops it is a two-line addition.)

## Further improvements

- **A fresh SUT subprocess per test is the "extravagant" strategy Dave gently cautions about (lesson 302/306).** Isolation here is genuinely excellent, so this is purely about feedback speed: "the cost of deployment and startup [should be] shared out between" tests. Because the server reads per-test CSVs from `tmp_path`, you can't trivially share one instance across synthetic specs today — but if the suite grows and start-up cost dominates, consider a data-source abstraction (e.g. a per-request data directory, or the aliasing pattern below) that lets many specs share one long-lived SUT. Not worth doing until wall-clock feedback actually hurts.
- **Temporal isolation is achieved structurally, not by aliasing (lesson 302).** That's a legitimate choice — Dave offers "a dedicated version of the SUT" as an equal alternative to aliasing — but it's worth recording *why*, because it's the thing that would break first if anyone later switches synthetic specs to a shared SUT for speed. The one-line note in `conftest.py` already hints at this; making it explicit ("shared-SUT would require name aliasing") would protect the next maintainer.
- **`confirm_last_answer_within` reads `connection().last_answer` rather than the driver's own `self._answer`.** Minor, but it reaches around the `QueryDriver` abstraction into connection state; routing it through the same `_answer`/`_data()` path the other confirmations use would keep the PD contract uniform.

## Suggested next steps

1. **Address the timing assertion first (Priority 1).** It's the single change that most improves trust in the suite, and it's small — `confirm_answered` is almost already there.
2. **Soften the one exact-text readability assertion (Priority 2); leave the filename/tool-name checks as justified by requirements.**
3. Everything else is optional polish. The architecture is sound and needs no restructuring — when you add the next feature, the recipe Dave describes already applies here cleanly: write the `should` spec, extend the area DSL, add the `confirm_*`/`_ask` methods to the driver, watch it go green.

This is a suite to keep, and a good reference for the rest of the team on what the four-layer model looks like in practice.

```json
{"acceptance_tests_found": true, "ratings": {"A": 4, "B": 4, "C": 4, "D": 4, "E": 4, "F": 3, "G": 4}, "disclosure": "full"}
```