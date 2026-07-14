# ATDD conformance rubric (for evaluating `prompt=ATDD` runs)

Source: Dave Farley / Continuous Delivery — *Acceptance Test Driven Development*
(How-To Guide, 2020). This rubric is **methodology conformance** — it asks
*"did this run actually do ATDD?"* — and is **separate** from the functional
`requirement_coverage` spec gate (*"does it implement the spec?"*). Apply it only
to runs with `prompt=ATDD`; it lets us tell whether any reliability/quality
difference is attributable to the methodology actually being followed.

## How to score

An LLM judge (e.g. `retort reevaluate --eval-model claude-opus-4-6`, or a
dedicated conformance pass) inspects the run's archived source + tests and scores
each criterion **1 / 0.5 / 0**. `atdd_conformance = mean(criteria)`. Cite file +
evidence per criterion; if there are no acceptance tests at all, score every
criterion 0.

## Criteria (from the guide's "Properties of Effective Acceptance Tests")

1. **Acceptance tests exist and are executable.** There is an automated acceptance
   test suite (not just unit tests) that runs and exercises end-to-end behaviour.
2. **Test-first / executable specification.** The acceptance tests read as a
   specification derived from the requirements/acceptance criteria, one (or more)
   per criterion — evidence the work was organised around them, not bolted on.
3. **External-user perspective.** Tests are written as an external user of the
   system would see it, not as internal-unit assertions.
4. **Through the public interface only.** Tests drive the System Under Test
   through its public interface (here: the MCP tools/protocol) — no back-door
   access to internal functions, private state, or the DB directly.
5. **What, not how.** Assertions are about *what* the system does in
   problem-domain terms (e.g. "find matches between two teams", "get team
   statistics"), not implementation mechanics.
6. **Domain language.** Test/step names use the language of the problem domain,
   not UI/impl verbs ("fill field", "call function X").
7. **Atomic & independent.** Each scenario is self-contained — starts from a
   running but empty system and shares no data with other tests.
8. **(Bonus) Separation of concerns.** Some layering toward Test Case → DSL →
   Protocol Driver → SUT (a reusable domain vocabulary / driver, rather than test
   logic talking to the SUT directly). Scored, but weighted lightly.

## Plan

After the exp-13 ATDD cells run, score `atdd_conformance` per run with the rubric
above and record it alongside `requirement_coverage`. Then the analysis can
separate two questions: (a) *was ATDD applied?* (conformance) and (b) *did
prescribing ATDD move reliability/quality vs neutral/TDD/BDD?* — a methodology is
only fairly credited/blamed when it was actually followed. Analogous rubrics
could be authored for TDD and BDD if we want conformance scores across all
prompt levels; ATDD is specified here per the provided guide.
