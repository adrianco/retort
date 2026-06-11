# Does *How* You Ask Change How Reliable It Is? Testing the Prompt

In the [model blog](model-blog.md) I varied the language, the model, and the
tooling, and held one big lever deliberately constant: **the prompt**. Every run
got the same terse *"implement TASK.md, make the tests pass."* But how you ask
plausibly moves reliability as much as which model you pick — and unlike a model
upgrade, it's nearly free. This is the experiment that varies it.

The specific knob here is **test methodology**. When you tell a coding agent
*how* to test — write the tests first, drive from acceptance criteria, use
behaviour scenarios — does the resulting code come out more reliably correct? Or
is methodology a ritual the model can take or leave on a task it already knows
how to do?

## Setting it up so the prompt is the only thing that changes

The hard task (a Brazilian-soccer MCP server built from a multi-file spec) is the
same one the model blog used — except its template *already prescribed BDD* in a
"Testing Approach" section. That's a confound: every existing run was quietly a
BDD run. So I forked the template into a **methodology-neutral** version
([`brazil-bench-neutral`](https://github.com/adrianco/brazil-bench-neutral)) with
all testing-methodology guidance stripped out. Now the methodology comes *only*
from the prompt — a clean factor.

Four levels, compared head-to-head:

- **BDD** — the existing baseline. The original template's runs are re-labelled
  `prompt=BDD` (they *were* BDD), so they become the fourth arm for free.
- **neutral** — the control. No methodology prescribed; implement it however you
  like, with tests that show it works.
- **TDD** — classic red-green-refactor, *unit*-test-first: write a failing test,
  make it pass, refactor, repeat.
- **ATDD** — executable **Acceptance** Test-Driven Development. Translate each
  acceptance criterion into an automated, executable acceptance test *first* —
  written from the external user's perspective, through the system's public
  interface, asserting *what* not *how*, in the language of the problem domain —
  then implement until they pass, with finer-grained TDD underneath. (Grounded in
  Dave Farley's Continuous Delivery ATDD guide, which is also the basis for the
  conformance rubric below.)

The grid: `language[go, python] × model[sonnet, opus-4.8-fast] × prompt[neutral,
TDD, ATDD]` = 12 cells, against the relabelled BDD baseline. Sonnet is the cheap
model; Opus-4.8-fast is the expensive one — between them they bracket the
reliability-vs-cost frontier from the model blog.

## Did the methodology actually get *followed*?

A subtlety the model blog never had to worry about: prescribing a methodology and
the agent *following* it are two different things. So for the ATDD arm there's a
second, separate measurement — an **ATDD conformance** score (from
[`experiment-13/ATDD-eval-criteria.md`](experiment-13/ATDD-eval-criteria.md),
derived from Farley's guide): are there executable acceptance tests, written
test-first, from the external-user perspective, through the public interface,
asserting what-not-how, atomic and independent? This separates two questions a
single pass/fail can't: *was ATDD applied?* and *did applying it help?* A
methodology should only be credited — or blamed — when it was actually used.

## Results

*Pending — experiment-13 is running (1 replicate, so results are directional, not
definitive). This section will be filled in with the four-way comparison
(BDD / neutral / TDD / ATDD) per model and language — pass-proportion, test
coverage, code quality, speed, and cost — plus the ATDD-conformance findings,
once the run completes and is scored.*

## How it's measured

Same harsh gate as everything else: a run passes only if its tests actually run
*and* an independent model confirms it implements the whole pinned requirement
checklist (`requirement_coverage == 1.0`). The requirements are functional and
methodology-agnostic — they ask *what* the server does, not *how* it was tested —
so no methodology is favoured by the gate itself. The methodology's effect shows
up (if it shows up at all) in the pass-proportion and quality numbers, not in a
rigged denominator.

## Try it on your own task

`prompt` is just another factor in retort — named strategies in
`prompts/<level>.md`, injected into the implement instruction. Point it at your
codebase, write the methodologies you actually argue about, and let the data say
whether the argument is worth having. See the
[README](https://github.com/adrianco/retort).
