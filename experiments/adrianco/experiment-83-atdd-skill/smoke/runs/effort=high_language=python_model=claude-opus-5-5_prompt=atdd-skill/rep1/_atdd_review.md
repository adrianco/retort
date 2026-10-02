All criteria fetched at `disclosure: full` (paid tier), across every category A–G. The suite runs **71 passed, 0 skipped, in 1.67s** — genuinely green. Here is the review.

---

# ATDD Review — `tests/acceptance/` (Brazilian Soccer MCP)

## Overall assessment

This is a genuinely strong, deliberately-crafted ATDD suite — one of the cleanest four-layer implementations I've reviewed. The test cases read as executable specifications in the language of Brazilian football and say nothing about the fact that the system under test is an MCP server; a layered DSL + protocol-driver infrastructure sits underneath; each test owns its own data and its own SUT instance. It is not greenfield scaffolding or abandoned infrastructure — all four layers are present, consistent, and finished. The feedback below is refinement, not restructuring: the architecture is already the target Dave points teams toward in *The Four Layer Model* (Module 305).

## Strengths

- **Specifications, not scripts (Module 103b, 203).** `test_match_search.py` etc. speak pure domain language: `given.brasileirao_match(home="Flamengo", away="Fluminense", score="2-1")` → `matches.search(team="Flamengo", opponent="Fluminense")` → `matches.confirm_found(count=2)`. Apply Dave's litmus test from Module 203 — "imagine the spec fulfilled by a completely different system" — and these pass effortlessly: nothing mentions MCP tools, JSON-RPC, or result shapes. Method names start with `should_`, and each follows Given/When/Then. This is exactly the calculator-example discipline from Module 103b.
- **Textbook four-layer separation (Module 305).** Layer 1 `*Spec` classes → Layer 2 `dsl/` → Layer 3 `drivers/mcp_driver.py` (which the docstring correctly calls "the only layer that knows the system is an MCP server") → Layer 4 the server subprocess. Assertions live in the protocol driver, in domain language, and every PD method passes or fails — Dave's exact advice ("make each step in a PD pass or fail… now each step is atomic").
- **Functional isolation done right (Module 302).** Each synthetic spec creates its own data via `given.*` and gets its own `tmp_path` dataset and its own server process (`conftest.py`). No teardown, no database rollback — the SUT is simply thrown away, precisely the "no cleanup required" pattern. This is the "dedicated SUT per test" option Dave lists in Module 306, so the suite is parallelisable and deterministic by construction.
- **DSL decomposition and reuse (Module 301/305).** The DSL is split by domain area (`matches`, `teams`, `players`, `statistics`, `competitions`, `dataset`) rather than one giant class — Dave's explicit recommendation in 305. `ProvidedData` composes those same sub-DSLs so a question reads identically whether asked of synthetic or real data. Defaults everywhere (`score="1-0"`, `season=None`), and higher-level builders like `season_finishing_in_order` (a double round-robin) are lovely domain vocabulary.
- **Intermittency largely engineered out (Module 306).** No `sleep`s anywhere; `mcp_client.py` reads responses on a background thread with a bounded `queue.get(timeout=…)` and id-matching — a genuine poll-with-timeout rather than a dumb wait. Dates come from a deterministic per-test sequence (`itertools.count`), avoiding the classic `now()` flake. Synthetic data is written in the exact file layout the SUT reads (`kaggle_files.py`), matching Dave's "use only synthetic data, created by your DSL… through the same path as production" guidance in 305.
- **Honest about its state (Module 201/202).** No `@skip`, no `xfail`, no `.only`, no CI test-exclusion filters, no `continue-on-error`, and no swallowed exceptions in the DSL/PD (the only `try/except`, in `mcp_client`, re-raises as `McpError` with server stderr). The green build is a true green build — I ran it to confirm. This is the releasability gate behaving as a gate.

## Priority issues

### 1. Wall-clock performance assertions are an environment-sensitive intermittency risk (Module 306)

`test_provided_datasets.py` asserts raw elapsed time against the real 18k-row datasets:

```python
def should_answer_a_simple_lookup_within_two_seconds(self, real_data):
    real_data.within_seconds(2).search_matches(team="Flamengo", opponent="Corinthians")

def should_answer_an_aggregate_question_within_five_seconds(self, real_data):
    real_data.within_seconds(5).rank_teams(by="win rate", venue="home")
```

Why it matters: Module 306 names *resource contention* and *environment changes* as root causes of intermittency — "not enough CPU, not enough RAM… these things can make our tests behave differently." A hard 2-second budget is exactly that kind of variable. On a loaded CI box or a shared runner these two tests can go red without the system being broken, which is precisely the trust-eroding false negative Dave warns against. Note the `_TimeLimited` helper also measures *after* the one-off subprocess connect on first use, making the first timed call doubly sensitive.

The requirement ("quick enough to be used conversationally") is legitimate — the fix is to stop it being a flaky gate:

```python
# Before: a hard wall-clock gate mixed into the acceptance suite
real_data.within_seconds(2).search_matches(team="Flamengo", opponent="Corinthians")

# After: tag performance budgets so they run separately, with generous, documented bounds,
# and warm the connection first so you measure the query, not process start-up.
@pytest.mark.performance            # deselected from the releasability gate; run on a controlled host
def should_answer_a_simple_lookup_quickly(self, real_data):
    real_data.search_matches(team="Flamengo", opponent="Corinthians")   # warm
    real_data.within_seconds(2).search_matches(team="Flamengo", opponent="Corinthians")
```

This mirrors Dave's treatment of time-sensitive tests in *Testing With Time* (304): tag them and isolate them from the regular run rather than letting them destabilise the main suite.

### 2. The 24-way sample-question test can't fail on a wrong answer (Module 202, 203)

```python
@pytest.mark.parametrize("question, ask", SAMPLE_QUESTIONS, ids=[q for q, _ in SAMPLE_QUESTIONS])
def should_answer_sample_question(real_data, question, ask):
    ask(real_data)
    real_data.confirm_answered()   # only checks: no error, text non-empty, data present
```

Why it matters: Module 202 says good tests "assert a single *outcome*" and have "only 2 reasons to fail — a translation mistake, or a genuine failure in the SUT." `confirm_answered` asserts neither a translation nor a spec outcome — it asserts merely that *something came back*. A regression that returns the wrong champion, the wrong match count, or an empty-but-well-formed result would sail through green. In Dave's framing (Module 203) this is closer to a smoke/coverage net than a specification. That's a reasonable thing to have — it proves all 24 phrasings route to a tool — but it shouldn't be mistaken for behavioural coverage.

Suggestion: keep it explicitly as a breadth net (rename to signal that, e.g. `should_route_every_sample_question`), and lean on the dedicated specs for truth — several of these questions *already* have outcome-asserting twins (`should_name_flamengo_champion_of_the_2019_brasileirao`, `should_identify_the_teams_relegated_in_2020`). Promote a handful more of the high-value ones to confirm a real outcome rather than just non-emptiness.

## Further improvements

- **Shared last-answer state in the read-only driver.** `McpSoccerDriver` stores `self._answer`/`self._text` from the most recent call, and the session-scoped `provided_data_driver` is shared across the `ProvidedDatasetsSpec` tests. It's safe today because those tests run sequentially and are read-only, but the mutable "last answer" field means the driver can't be interleaved. A short comment noting the sequential assumption (or carrying the answer on a per-call handle) would prevent a future parallelisation from introducing a subtle race — consistent with the determinism emphasis in Module 306.
- **No pipeline / expected-failure scaffolding yet (Module 201).** There's no CI workflow in the repo and no demonstrated expected-failure convention. Nothing is hidden today, so this isn't a truthfulness problem — but when in-progress features arrive, follow Module 201: colocate the new spec with the code (already the habit here) and mark it `@pytest.mark.xfail(strict=True)` rather than `skip`, so it runs every build, reports XFAIL, and flips the build red the moment it's accidentally satisfied. Add a pipeline that runs `tests/acceptance` as the releasability gate.
- **Dataset-name vocabulary in a few specs.** `should_find_matches_from_every_provided_source` and `should_not_count_a_match_twice_when_datasets_overlap` lean on data-source names (`historical_brasileirao_match`, `extended_stats_match`). This is defensible — cross-dataset reconciliation and dedup are genuine *user-facing* requirements here, and the specs still say nothing about *how* reconciliation works, so they don't breach Module 203. Just keep an eye that this vocabulary stays about "what sources the user expects covered," not about implementation.

## Suggested next steps

1. Move the two wall-clock tests behind a `performance` marker (and warm the connection), so the main acceptance run is a clean, environment-insensitive releasability gate. *(Priority 1 — the only real intermittency vector in the suite.)*
2. Relabel the 24-way sample test as a routing/smoke net and promote a few high-value questions to outcome-asserting specs. *(Priority 2.)*
3. Add a CI pipeline that runs `tests/acceptance` as the gate, and adopt `xfail(strict=True)` as the convention for in-progress specs.

Everything else is already exemplary — this suite is a good reference for what Dave's four-layer model looks like when it's actually finished.

```json
{"acceptance_tests_found": true, "ratings": {"A": 4, "B": 4, "C": 4, "D": 4, "E": 4, "F": 3, "G": 4}, "disclosure": "full"}
```