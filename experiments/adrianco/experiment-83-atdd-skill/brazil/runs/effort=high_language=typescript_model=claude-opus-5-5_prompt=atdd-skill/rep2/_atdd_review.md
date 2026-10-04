I now have the full lessons for every category A–G. The suite is clean — no skipped tests, no filters, no swallowed exceptions (the single `catch` re-throws with an enriched message), and unit-level edge cases are pushed down to `test/`. Here is the review.

---

# ATDD Review — Brazilian Soccer MCP acceptance suite

*Reviewed against Dave Farley's ATDD course. Content server returned **full** lessons at the paid tier, so the criteria below are Dave's articulated principles, not summaries.*

## 1. Overall assessment

This is one of the most faithful implementations of Dave's four-layer model I've reviewed. It is not "on the right track" — it has largely arrived. The specs read as executable specifications in the language of Brazilian football (`given.brasileiraoMatch(...)`, `competitions.confirmChampion(...)`), a clean DSL sits beneath them decomposed by domain area, a single protocol driver speaks the system's real interface (MCP over stdio), and a stub translates test intent into the exact CSV dialects of the shipped Kaggle files. There is no abandoned scaffolding, no DSL methods bypassing to the SUT, and no implementation leakage to speak of. The one genuine weakness is a pair of performance tests that assert on absolute wall-clock time — exactly the intermittency vector Dave warns about. Everything else is at or near exemplary.

## 2. Strengths

- **The specs say nothing about how the system works.** `acceptance/specs/match-queries.spec.ts:13` reads "list every meeting between two rivals, most recent first" and asserts on `'2023-09-03: Flamengo 2-1 Fluminense'` — not on MCP tool names, JSON shapes, or CSV columns. This passes Dave's acid test ("imagine the spec being fulfilled by a completely different system", *Acceptance Tests & BDD, 203*) perfectly: swap stdio for HTTP and every spec stays true.
- **Textbook four-layer separation**, including the explicit protocol-driver *contract* (`SoccerSystemDriver` interface) that Dave himself adds in the worked example (*The Four Layer Model, 305*: "I have even created an interface at this point, defining the contract for any PD").
- **Assertions live in the protocol driver, in domain language.** `expect(data, \`record of ${criteria.team}\`)` (`mcp-soccer-driver.ts:154`) is exactly Dave's "make each step in a PD pass or fail… good error messages at a sensible level for spec writers."
- **The stub is a translator, not a simulation** (`dataset-stub.ts`) — it writes `"Palmeiras-SP"`, `"Atlético - MG"`, `29/03/2003`, FIFA headers and Brazilian `Vencedor` columns so the SUT meets the same mess it meets in production. This is precisely the stance of *Protocol Drivers & Stubs, 303*.
- **Edge cases pushed down to unit tests** (`test/teams.test.ts`, `test/dates-and-competitions.test.ts`) rather than crammed into scenarios — Dave's remedy for "long-running scenarios" and "scenario overload" (*203*).
- **The suite is honest about its state** (category G): no `.skip`/`.only`/`xit`, no test filters in `package.json`, no `continue-on-error`, no commented-out files, and the sole `catch` (`mcp-soccer-driver.ts:90`) enriches and re-throws rather than swallowing. Nothing is hidden from the team.

## 3. Priority issues

### (1) Performance specs assert on absolute wall-clock time — the one real intermittency risk

`acceptance/specs/provided-datasets.spec.ts:128-134` asserts simple lookups finish "in under 2 seconds" and aggregates "under 5 seconds", implemented in the PD by timing each call and comparing elapsed wall-clock against the threshold (`mcp-soccer-driver.ts:348-355`).

**Why it matters.** *Dealing With Intermittent Tests (306)* lists "resource contention… not enough CPU, not enough RAM" as a root cause of flakiness, and the whole point of the suite — per the same lesson — is to be "a definitive statement of the releasability of our system." A test whose pass/fail depends on how loaded the CI box is undermines exactly that: a green-elsewhere build can fail here for reasons unrelated to the software being broken. These two tests are the only place the suite's determinism is at the mercy of the environment.

**Direction.** Dave's guidance is to assert on *outcomes*, and treat performance as a property measured and trended, not a hard wall-clock gate inside the functional acceptance suite. Options, roughly in order of fidelity to his principles:
- Move the latency budget out of the pass/fail acceptance suite into a separate performance check that runs on a controlled, IaC-provisioned host (306's "run your acceptance tests in a close clone of your production environment"), where a threshold is meaningful.
- If kept here, assert the *answer is correct* and only warn on timing, so an overloaded runner never reports the software as broken.

```ts
// Before (provided-datasets.spec.ts) — pass/fail hinges on the machine's load
it('should answer simple lookups in under 2 seconds', async () => {
  await performance.confirmSimpleLookupsWithin({ seconds: 2 });
});

// After — the acceptance suite asserts the behaviour; latency is a separate,
// environment-controlled concern rather than a wall-clock gate mixed in here.
it('should answer every simple lookup correctly', async () => {
  await performance.confirmSimpleLookupsAnswered();  // asserts results, not milliseconds
});
```

### (2) Minor: a few specs name the dataset the data was "recorded in"

In `team-queries.spec.ts:73-90` the name-reconciliation scenarios pass `recordedIn: 'serie-a-dataset'` / `'historical-dataset'`. This is the mildest brush with *BDD: Defining the Behaviour (103b)*'s "strip out implementation assumptions."

**Why it's largely forgivable, and how to decide.** These particular scenarios are *about* cross-dataset provenance — "count a match once even when several datasets record it" is genuinely domain behaviour, so naming the sources is arguably part of the specification, not leakage. The line to hold: `recordedIn` should name a *domain* source ("the official league record" vs "a historical archive"), never a *file* (`Brasileirao_Matches.csv`). It currently stays on the right side of that line; just keep it there as the suite grows.

### (3) Minor: exact record-count assertions couple the data-coverage spec to the shipped files

`provided-datasets.spec.ts:16-25` asserts file-level counts (`'Brasileirao_Matches.csv': 4180`, etc.). This is deliberate and documented (a data-coverage proof), and it isn't *intermittent* — but it is brittle to any data refresh and is the most implementation-aware spec in the suite (it knows file names and row counts). That's an acceptable trade for a coverage canary; just be aware it will need updating whenever the Kaggle files change, and don't let that pattern spread to behavioural specs.

## 4. Further improvements

- **Isolation strategy trade-off (not a defect).** The synthetic suite gives every test its own temp dataset dir *and* its own SUT process (`soccer-dsl.ts:84-88`), lazily started on first question. This is full functional + temporal isolation and depends on no teardown for correctness — the `afterEach` dispose is resource cleanup, not state cleanup, so it matches *Test Isolation (302)* cleanly. The cost is that you pay SUT startup per test, which is the expense Dave suggests amortising ("share the costs of deployment and startup between multiple tests", 302). If the suite grows and feedback slows, the course's sanctioned alternative is a shared SUT plus *name aliasing* for isolation — which this suite doesn't currently implement because it doesn't need to. Worth keeping in your back pocket, not worth doing now.
- **No CI wiring present.** There's no `.github/workflows` (or equivalent) in the repo, so while the suite is honest (category G), nothing here actually gates releases on it. Per *306*, the value of a trustworthy suite is realised only when it's "a definitive statement of releasability" wired into the pipeline. Adding that wiring is the natural next step.

## 5. Suggested next steps

1. **Address the wall-clock performance assertions first** (priority 1) — it's the only change that affects trust in the suite's green/red signal.
2. **Wire the suite into CI** as a release gate, keeping `test:unit` and `test:acceptance` as distinct stages (they already are in `package.json`).
3. Leave the architecture alone. The four-layer model, DSL decomposition, PD contract and stub-as-translator are all exemplary and need no restructuring — the recipe here is "keep doing exactly this for each new feature" (*305*).

```json
{"acceptance_tests_found": true, "ratings": {"A": 4, "B": 4, "C": 4, "D": 4, "E": 4, "F": 3, "G": 4}, "disclosure": "full"}
```