I now have the full lessons for all seven categories (`full` disclosure, paid tier). I've read every acceptance test, the DSL, and all protocol drivers. Here is the review.

---

# ATDD Review — Brazilian Soccer MCP acceptance suite

## 1. Overall assessment

This is, frankly, one of the cleanest applications of Dave Farley's four-layer model I could hope to review. The suite in `tests/acceptance/` has a genuine, disciplined separation of test case → DSL → protocol driver → SUT; the specs speak Brazilian-football language and almost nothing about MCP, JSON-RPC, tools or CSV columns; isolation is done the way Dave recommends (each test owns a fresh SUT and its own data); there are no sleeps; and the suite is honest — nothing is skipped, filtered or swallowed. This is not a suite that needs restructuring. It needs a small number of refinements, and the most substantive one is a classic intermittency trap hiding inside the otherwise-excellent performance specs. I'll be honest about where it falls short of exemplary, but the scale of the work here is "polish," not "rebuild."

## 2. Strengths

- **The specs are durable, outcome-focused, and would survive a complete reimplementation of the SUT.** `test_finding_matches.py:13` reads `given.match("Flamengo 2-1 Fluminense")` … `matches.confirm_meetings("Flamengo", "Fluminense", count=2)`. Apply Dave's own test from *Acceptance Tests & BDD* (203) — "imagine the spec being fulfilled by a completely different system" — and these pass effortlessly. If the SUT stopped being an MCP server tomorrow and became a REST API or a voice interface, not one line of these specs would change. The file docstrings even name this explicitly (`test_finding_matches.py:7`: "how the answers are produced is hidden behind the DSL").
- **Textbook four-layer architecture.** Test cases hold no plumbing; `dsl/` is the domain vocabulary; `drivers/soccer_server.py` is the only place that knows the SUT is MCP; `drivers/mcp_client.py` is pure transport. This is exactly the layering described in *The Four Layer Model* (305).
- **Functional isolation done the right way.** `conftest.py:22` gives every `soccer` test its own `tmp_path` dataset directory and its own server process — Dave's "dedicated SUT per test" strategy from *Test Isolation* (302) — so there is no cleanup, no DB rollback gymnastics, and the suite is safe to parallelise.
- **Assertions live in the protocol driver, every step is atomic, and failures speak football.** `soccer_server.py:49` etc. fail with messages like "Expected 2 meetings of Flamengo and Fluminense, found 3". That is precisely Dave's advice in 305 ("make each step in a PD pass or fail… good error messages at the language of the problem domain").
- **The datasets driver is a translator, not a simulation.** `datasets.py` takes football facts and writes each dataset in its *own native format* (column names, date formats, `NA` vs blank goals, accented names) — the stub-as-translator principle from *Protocol Drivers & Stubs* (303), and it's programmed before the SUT starts via the `before_start` hook (`conftest.py:25`).
- **No sleeps.** `mcp_client.py` waits for responses with a reader-thread-plus-queue poll-with-timeout (`_request`, line 65), exactly the pattern *Dealing With Intermittent Tests* (306) prescribes in place of `sleep`.
- **The suite is releasability-truthful.** No `@skip`, no `xfail`, no `-k`/`--ignore` filters, no `continue-on-error`, no commented-out tests, and the PD *asserts* on `isError` rather than swallowing it (`soccer_server.py:293`). Nothing is green-while-hiding.

## 3. Priority issues

### Priority 1 — Wall-clock performance thresholds are an intermittency vector (category F)

**Where:** `test_provided_datasets.py:77-84`, implemented in `soccer_server.py:272-278`.

```python
def confirm_answered(self, question, ask, within_seconds):
    self._connection()
    started = time.perf_counter()
    answer = ask()
    elapsed = time.perf_counter() - started
    assert answer.text.strip(), f"No answer to {question!r}"
    assert elapsed < within_seconds, f"{question!r} took {elapsed:.2f}s (limit {within_seconds}s)"
```

**Why it matters:** *Dealing With Intermittent Tests* (306) names "resource contention in our test environments" as one of the short list of root causes of intermittency, and the whole lesson is built on the idea that a failing acceptance test must be a *trustworthy, definitive statement of releasability* — "No agonising over 'should we run it again in case it's an intermittent failure'." A bare `elapsed < 2` assertion is exactly the kind of check that passes on a quiet laptop and fails on a loaded CI box, through no change in the SUT's correctness. The first time this flakes, the team learns to re-run the suite — and that habit, Dave argues, is what erodes trust in *every* test, not just this one.

Credit where due: you've already avoided the worst version of this by excluding start-up/load time from the measurement (`self._connection()` is called *before* the timer). The problem is only the absolute threshold.

**A direction to fix it (two honest options):**

- *Preferred — make it a monitoring concern, not a pass/fail spec.* Responsiveness of real queries over real data is a property that genuinely varies with the host; Dave's guidance in 302 is that end-to-end timing is better observed by "monitoring production" than asserted in an acceptance gate. Keep a spec that asserts the question is *answered correctly and non-empty* (deterministic), and record the elapsed time as an emitted metric rather than an assertion.
- *If the latency guarantee must stay a gate,* make the threshold express the behaviour rather than the environment — e.g. assert the aggregate is not pathologically slower than a simple lookup measured in the same run (a ratio), which cancels out host speed, rather than a fixed wall-clock bound. It's still imperfect, but it removes the raw environment sensitivity.

Either way, the correctness of "the question is answered" should be a separate, deterministic assertion from "it was fast" — right now a slow-but-correct answer reports as a behaviour failure.

### Priority 2 — A few specs assert fully-formatted presentation strings (category A)

**Where:** e.g. `test_finding_matches.py:27-30`:

```python
listed=[
    "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)",
    "2023-05-28: Fluminense 1-0 Flamengo (Brasileirão Série A, Round 8)",
],
```
and the biggest-wins / last-meeting specs (`test_statistics.py:34`, `test_finding_matches.py:101`).

**Why it matters:** *BDD: Defining the Behaviour of the System* (103b) wants specs that are durable — true "in a way that doesn't change as the system evolves." Asserting the exact rendered line, down to punctuation, the parenthesised competition label and "Round 22", couples the spec to a *presentation* decision. The day someone reorders that line to "Round 22 · Brasileirão Série A" the behaviour is unchanged but the spec breaks — the hallmark of an implementation-coupled assertion. This is a mild case, not the "bus edit" overload of lesson 203: the content being asserted (date, teams, score, ordering) *is* genuine domain behaviour, and the ordering check is legitimate. It's only the exact string shape that's over-specified.

**Before/after (spirit of it):** keep what's behavioural — the two meetings, most-recent-first, with their scores — and let the DSL confirm those *fields* rather than one frozen string:

```python
soccer.matches.confirm_meetings(
    "Flamengo", "Fluminense",
    in_order=[
        {"date": "2023-09-03", "score": "Flamengo 2-1 Fluminense", "round": 22},
        {"date": "2023-05-28", "score": "Fluminense 1-0 Flamengo", "round": 8},
    ],
)
```

The ordering guarantee is preserved; the cosmetic layout is no longer load-bearing. (Your PD already has the structured data to do this — `data["matches"]` carries `competition`, etc. — so this is a DSL/PD refinement, not a SUT change.) If you deliberately *want* to pin the human-readable rendering, that's a reasonable thing to test — but make it one explicit "answers read naturally" spec, not a coupling threaded through many behaviour specs.

## 4. Further improvements

- **Temporal isolation / aliasing isn't present, and that's fine — but worth a conscious note.** *Test Isolation* (302) offers two valid strategies; you've chosen "dedicated SUT per test," which removes the *need* for name aliasing, so the absence of aliasing is not a defect. The one place to stay alert: the `provided` fixture (`conftest.py:30`) is `scope="session"` and shared. That's sanctioned *because it's read-only*. Keep it strictly read-only — the moment a `provided` spec mutates state, you lose the isolation guarantee for every spec after it.
- **Real-data specs pin exact row counts and historical facts** (`test_provided_datasets.py:16-32`: `"brasileirão": 4180`, Flamengo "90 points"). This is inherent to testing provided data and is honest, but it's brittle to any dataset refresh. Consider whether these are "the datasets loaded fully" assertions (where an exact count is right) versus facts that a dataset update could legitimately shift.
- **No CI configuration is present in the repo.** Nothing is hidden (category G is clean), but 306 stresses that the value of this suite is realised only when it runs "frequently… as a definitive statement of releasability." A committed CI workflow that runs `tests/` with no exclusions would lock in the honesty the suite already has, and is the natural home for resolving Priority 1 (metrics vs. gate).

## 5. Suggested next steps

1. **Fix the timing assertions first** (Priority 1) — split "answered correctly" from "answered quickly," and move the latency bound to a metric or a host-independent ratio. This is the only issue that will actually flake a green build.
2. **Relax the frozen presentation strings** (Priority 2) to assert domain fields + ordering, keeping at most one explicit rendering spec if you want to guard the human-readable output.
3. Leave the architecture alone. The four-layer separation, functional isolation, poll-with-timeout transport, and translator-style datasets driver are all exemplary — extend new features by following the same recipe the suite already demonstrates (new spec → extend DSL → add PD method), which is exactly Dave's workflow in 305.

*(This review was grounded in the full ATDD course lessons 103b, 203, 301, 302, 303, 305, 306 and 308, fetched at paid tier — full lesson text, not summaries.)*

```json
{"acceptance_tests_found": true, "ratings": {"A": 4, "B": 4, "C": 4, "D": 4, "E": 4, "F": 3, "G": 4}, "disclosure": "full"}
```