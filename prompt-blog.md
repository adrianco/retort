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

Three replicates, 36 runs, all graded by the spec judge. And the first answer is
almost an anticlimax: **on a task the model already knows how to build,
prescribing a methodology barely moves reliability.** Pass-proportion
(does it implement the whole pinned checklist?) by cell:

| model | language | neutral | TDD | ATDD |
|---|---|:--:|:--:|:--:|
| opus-4.8-fast | go | 1.00 | 1.00 | 1.00 |
| opus-4.8-fast | python | 1.00 | 1.00 | 1.00 |
| sonnet | go | 1.00 | 1.00 | **0.33** |
| sonnet | python | 1.00 | 1.00 | 1.00 |

Eleven of twelve cells pass regardless of what I told the agent about testing.
The lone exception is **ATDD on the weakest stack — Sonnet writing Go** — where
two of three runs left a small spec gap. ATDD asks for the most up-front
discipline (turn every acceptance criterion into an executable test through the
public interface *before* implementing), and the cheaper model on the less
forgiving language occasionally didn't carry that all the way home. Give it a
stronger model or a more forgiving language and the gap closes.

Where methodology *does* show up cleanly is **what kind of tests get written**.
ATDD consistently produces lower unit-statement coverage than TDD or neutral —
0.50–0.79 vs 0.67–0.97 on the harder cells — because it writes acceptance tests
that drive the system end-to-end rather than exhaustive unit tests. That's the
methodology working as intended, not failing: it still meets the functional spec
everywhere except Sonnet/Go, where the unit-test scaffolding TDD and neutral
leave behind seems to help the weaker model finish the job.

Cost tracks the model, not the methodology: Opus-4.8-fast runs ~$8–17, Sonnet
~$1–3, and no methodology is reliably cheaper than another.

So the practical read: on a task the model already understands, **which testing
discipline you prescribe is mostly a wash for whether it ships correctly** — pick
the methodology you want for the *tests it leaves behind* (ATDD for executable
acceptance specs, TDD for unit coverage), not for a reliability boost. The one
caveat is the weak-model/strict-language corner, where the lightest-weight
prompt is the safer bet.

*(BDD, the fourth arm, is held for a later comparison — those baseline runs need
re-scoring on the same footing first. The neutral/TDD/ATDD arms above are all
scored identically.)*

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
