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

## Newest first: the prompt bites in proportion to how *weak* the model is

The most recent prompt data comes from the other end of the capability range —
**local** models on a laptop (served with MLX/oMLX, driven by the Hermes agent, the
stack from the [model blog](model-blog.md)) — and it splits cleanly by model
strength.

On a *weak* local model — **Qwen3.6-35B-A3B** — the prompt is a real lever.
Sweeping all four methodologies on Python (experiment-19, pass-proportion over 3
replicates):

| prompt | pass | avg test-cov | avg tokens |
|---|:--:|:--:|:--:|
| **neutral** | **2/3** | 0.96 | **0.40 M** |
| **BDD** | **2/3** | 0.97 | 1.03 M |
| TDD | 1/3 | 0.98 | 0.54 M |
| **ATDD** | **0/3** | 0.41 | 0.73 M |

Two things land. First, **neutral and BDD tie for best, but neutral gets there at
~2.5× fewer tokens** — the plain prompt is the cheap winner. Second, and more
strongly: **ATDD is dead last — 0/3** — and it isn't a one-off. Across *four*
local experiments (exp-16/18/19/20) ATDD has come in worst every time: 0.17 vs
neutral's 0.33, 0.25 vs 0.50, and 0/3 here. A weak model can't carry ATDD's
front-loaded discipline (turn every acceptance criterion into an executable test
through the public interface *before* implementing); it flails and burns tokens.

But step *up* to the stronger **Qwen3-Coder-Next 80B** and the lever vanishes.
Re-running the identical Python sweep (experiment-32, n=3) — every methodology
passes **1.00**, ATDD included:

| prompt | 80B pass |
|---|:--:|
| **neutral** | **3/3** |
| **BDD** | **3/3** |
| **TDD** | **3/3** |
| **ATDD** | **3/3** |

Same task, same four prompts, opposite result. The 80B has enough headroom that the
methodology is ritual: ATDD's front-loaded discipline, which tanked the 35B, is a
no-op on a model that clears the task comfortably — the same flat line the strong
cloud models show below.

So the sharpened headline isn't "the prompt is (or isn't) a flat line" — it's that
**the prompt/methodology lever bites in proportion to how *weak* the model is.** Near
a model's capability edge (the 35B, and the weak-ish cloud stacks below) the wrong
methodology breaks the run; on a model with headroom (the 80B, and the strong cloud
models) it's flat. The practical rule for a local model **inverts the usual "more
discipline is better"**: reach for a disciplined methodology only when you're near
the edge. On the **35B**, keep the prompt plain and *never* reach for ATDD; on the
**80B** (and on cloud) pick **neutral** because it's the cheapest and loses nothing.
The cloud story below is where that flat line first showed up — with ATDD on the one
weak-ish cloud stack (Sonnet + Go) as the single place a prompt broke a run.

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
[`experiment-13/ATDD-eval-criteria.md`](experiments/adrianco/experiment-13/ATDD-eval-criteria.md),
derived from Farley's guide): are there executable acceptance tests, written
test-first, from the external-user perspective, through the public interface,
asserting what-not-how, atomic and independent? This separates two questions a
single pass/fail can't: *was ATDD applied?* and *did applying it help?* A
methodology should only be credited — or blamed — when it was actually used.

## Results

Three replicates, all graded by the spec judge. And right away one model drops
out of the conversation: **Opus-4.8-fast saturates — 1.00 on every cell with
every prompt.** Once a model is strong enough for the task, the prompt is a flat
line; there is nothing to see. So the interesting model is the *cheap* one,
where a prompt might actually earn its keep. Here is **Sonnet**, by prompt and
language (BDD folded in from the original brazil-bench runs, re-graded on the
same judge):

| prompt | Go pass | Go cov | Go $ | Python pass | Python cov | Python $ |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| BDD | 1.00 | 0.77 | 1.2 | 1.00 | 0.96 | 0.7 |
| neutral | 1.00 | 0.78 | 3.0 | 1.00 | 1.00 | 1.3 |
| TDD | 1.00 | 0.69 | 3.3 | 1.00 | 1.00 | 1.3 |
| ATDD | **0.33** | 0.58 | 1.9 | 1.00 | 1.00 | 1.8 |

Even on Sonnet, **three of the four prompts are interchangeable** — BDD, neutral,
and TDD all pass 1.00 on both languages. The only thing that moves reliability is
**ATDD on Go, and it moves it *down*** — 0.33, two of three runs short of the
spec. ATDD asks the most up front (turn every acceptance criterion into an
executable test through the public interface *before* implementing), and the
cheap model on the stricter language sometimes didn't carry it home. So the
prompt's real effect on Sonnet is **asymmetric**: a sensible methodology keeps it
reliable; the wrong one is the only way to break it.

Coverage tells the same story it told on both models — ATDD leaves the least unit
coverage (it spends its effort on acceptance tests, not unit tests), while
BDD/neutral/TDD sit higher. On Sonnet/Go that's 0.58 for ATDD against 0.69–0.78
for the rest; on Python everything saturates near 1.00 and the distinction washes
out.

### Does Sonnet with the best prompt match Opus with no prompt?

This is the question that decides the bill. **Yes — and it isn't close on cost.**

| | reliability | coverage (Go / Py) | cost/run (Go / Py) |
|---|:--:|:--:|:--:|
| **Sonnet + a sensible prompt** | 1.00 | 0.78 / 1.00 | **$3.0 / $1.3** |
| Opus-4.8-fast + no prompt | 1.00 | 0.57 / 0.97 | $17.3 / $10.3 |

Sonnet with neutral, TDD, or BDD hits Opus's 1.00 reliability **and writes more
tests** — 0.78 statement coverage on Go versus Opus's 0.57 — at **roughly
one-seventh the cost**. On this task the expensive model buys nothing a decent
prompt doesn't already give the cheap one. The only way to make Sonnet *worse*
than Opus is to hand it the wrong prompt: ATDD on Go is the single cell where it
falls behind.

So the cheap lever here isn't "upgrade the model." It's "give the cheap model a
sensible methodology — and don't prescribe ATDD on a strict language."

### What the prompt costs

Within Sonnet the bill stays low — $0.7–$3.3 a run whatever the prompt — because
the *model* dwarfs the methodology on cost (Opus is 5–10× pricier). The one
consistent effort signal across both models is that the **unstructured "neutral"
prompt burns the most tokens**: handing the agent *a* methodology constrains its
exploration and tends to cost less (clearest on Opus, where neutral runs $13.79
vs ATDD's $11.09). Time barely moves with the prompt — wall-clock is bounded by
the model thinking, not by the testing discipline.

*(BDD is folded in from the original brazil-bench runs — which prescribed BDD
in-repo rather than via this prompt factor — re-graded on the same judge as the
others. It ran on the original template, not the methodology-neutral fork, and
its Sonnet arm is n=1, so treat its numbers as a consistent reference point
rather than a perfectly matched fourth arm. The full per-model tables, including
Opus, are in [experiment-13/results.md](experiments/adrianco/experiment-13/results.md).)*

### Does it hold across more languages?

Go and Python are forgiving. To check the finding isn't a two-language fluke,
[experiment-14](experiments/adrianco/experiment-14/results.md) reran the same prompts on the other
six — **clojure, rust, java, typescript, erlang, elixir** — with both models (one
replicate each, so single-run signal rather than pass-proportions). The pattern
is the same, only wider:

- **Opus saturates on all six** — 1.00 on every language with every prompt, just
  like Go and Python. On the strong model the prompt remains a flat line across
  eight languages.
- **Sonnet clears the spec on five of the six with every prompt.** The only
  genuine misses are both **TypeScript** (neutral and ATDD each landed one
  requirement short at 0.92 — but TDD passed it), which reads as a
  TypeScript-Sonnet quirk, not a methodology effect. (One Clojure cell was lost
  to a usage limit, not a real failure.)

So across **eight languages and two models**, the conclusion holds and sharpens:
**the prompt is the smallest lever.** The dips that do happen track the
*language* — TypeScript here, Go-with-ATDD earlier — not the testing discipline
you prescribed. If you want to move reliability, change the model or pick the
language carefully; the methodology mostly decides *what tests you're left with*
and what you pay in tokens, not whether the thing ships.

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
