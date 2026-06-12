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

| model | language | BDD | neutral | TDD | ATDD |
|---|---|:--:|:--:|:--:|:--:|
| opus-4.8-fast | go | 1.00 | 1.00 | 1.00 | 1.00 |
| opus-4.8-fast | python | 1.00 | 1.00 | 1.00 | 1.00 |
| sonnet | go | 1.00 | 1.00 | 1.00 | **0.33** |
| sonnet | python | 1.00 | 1.00 | 1.00 | 1.00 |

**BDD** is folded in from the original brazil-bench runs (which prescribed
Given-When-Then scenarios in-repo) re-graded on the same judge: opus-4.8-fast
n=3, sonnet n=1. **Fifteen of sixteen cells pass regardless of what I told the
agent about testing.** The lone exception is **ATDD on the weakest stack —
Sonnet writing Go** — where two of three runs left a small spec gap. ATDD asks
for the most up-front discipline (turn every acceptance criterion into an
executable test through the public interface *before* implementing), and the
cheaper model on the less forgiving language occasionally didn't carry that all
the way home. Give it a stronger model or a more forgiving language and the gap
closes. BDD, TDD, and neutral are interchangeable on reliability — all 1.00.

### What kind of tests get written

Where methodology shows up cleanly is **coverage** — the unit-statement coverage
of the code the agent leaves behind. Mean test coverage per cell:

| model | language | BDD | neutral | TDD | ATDD |
|---|---|:--:|:--:|:--:|:--:|
| opus-4.8-fast | go | 0.71 | 0.57 | 0.67 | 0.50 |
| opus-4.8-fast | python | 0.92 | 0.97 | 0.95 | 0.79 |
| sonnet | go | 0.77 | 0.78 | 0.69 | 0.58 |
| sonnet | python | 0.96 | 1.00 | 1.00 | 1.00 |

**ATDD consistently lands lower — 0.50–0.79 on the harder cells vs 0.67–0.97 for
BDD/TDD/neutral.** That's the methodology working as designed, not failing: ATDD
spends its effort on acceptance tests that drive the system end-to-end through
its public interface, not on exhaustive unit tests, so the *statement* coverage
is lower even though the spec is fully met. BDD lands right alongside TDD and
neutral (0.71–0.96) — its Given-When-Then scenarios still leave unit-level
coverage behind. On the easy Python cells everything saturates near 1.00 and the
distinction washes out; it only separates where the task has enough surface area
to matter. ATDD is the clear outlier on coverage, not BDD.

### How the prompt moves time, tokens, and cost

This is where the prompt earns its keep — and where I had to eat an earlier
claim that "cost tracks the model, not the methodology." It does track the model
*between* tiers (Opus-4.8-fast runs ~$11, Sonnet ~$2). But *within* a model, the
methodology you prescribe swings the bill by ~20%. Averaged across all twelve
runs per arm:

| methodology | pass | test cov | time | tokens | cost |
|---|:--:|:--:|:--:|:--:|:--:|
| neutral | 1.00 | 0.83 | 989 s | **5.1M** | **$7.96** |
| TDD | 1.00 | 0.83 | 906 s | 4.6M | $6.97 |
| ATDD | 0.83 | 0.72 | 941 s | **3.4M** | **$6.49** |

- **Tokens and cost: the *unstructured* prompt is the most expensive.** "neutral"
  — implement it however you like — burns **5.1M tokens / $7.96 per run**, the
  most of any arm. Hand the agent a methodology and it spends *less*: ATDD is
  leanest at **3.4M tokens / $6.49** (a third fewer tokens than neutral), TDD
  sits between at 4.6M / $6.97. Structure constrains the exploration — telling
  the model *how* to test apparently saves it from wandering. The effect is
  consistent per model: on Opus-4.8-fast, neutral costs **$13.79** vs ATDD's
  **$11.09** (24% more); Sonnet shows the same ordering at ~$2.
- **Time barely moves** — all three arms land 900–990 s, neutral marginally
  slowest. Wall-clock is bounded by the model's reasoning, not by the testing
  discipline, so the token savings don't translate into a speed-up.

### The practical read

On a task the model already understands, **which discipline you prescribe is
mostly a wash for whether it ships** — but it's *not* a wash for the bill or the
tests you're left with:

- **BDD and TDD are the safe picks** — full reliability (1.00 everywhere) and
  solid unit coverage (0.71–0.96). TDD is also ~12% cheaper than letting the
  model freestyle; BDD leaves business-readable Given-When-Then scenarios behind.
- **ATDD is the cheapest** (fewest tokens) and leaves executable acceptance specs,
  but trades that for lower unit coverage and the one reliability wobble on the
  weak Sonnet/Go stack.
- **neutral (no methodology) is the worst of both** — same reliability as TDD/BDD
  but the highest token bill and no test scaffolding to show for it. Giving the
  agent *a* methodology, almost any methodology, beats giving it none.

*(BDD is folded in from the original brazil-bench runs — which prescribed BDD
in-repo rather than via this prompt factor — re-graded on the same judge as the
others. It ran on the original template, not the methodology-neutral fork, and
its sonnet arm is n=1, so treat the BDD reliability/coverage as a consistent
reference point rather than a perfectly-matched fourth arm. Its token/cost
figures come from a different experiment and aren't in the table above.)*

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
