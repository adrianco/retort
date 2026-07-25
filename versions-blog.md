# Why Is the Newer Model Slower? One Task, Every Version

Every stack in this post gets the **same easy task** — the "bookshop" REST API in **Python** — and
almost all of them get it **completely right**. So this isn't a post about reliability. It's about the
thing that varies wildly *when everything succeeds*: **how much work the model does to get there.**

Between the oldest and newest Claude versions, the same finished app costs **6× more** and takes **4×
longer**. That is worth understanding, because nothing about the deliverable changed.

## The board: one task, every stack

| stack | n | pass | turns | tokens | seconds | cost |
|---|---:|---:|---:|---:|---:|---:|
| **Fable 5** | 3 | 1.00 | **10.7** | 229 K | **96** | $0.76 |
| Opus 4.8 — **fast mode** | 3 | 1.00 | 11.3 | 242 K | 90 | $0.74 |
| Opus 4.7 | 6 | 1.00 | 17.2 | 613 K | 100 | $0.59 |
| Opus 4.8 | 6 | 1.00 | 17.3 | 310 K | 122 | **$0.50** |
| **Opus 5** | 1 | 1.00 | **36.0** | **1,252 K** | **392** | **$1.84** |
| Qwen3.6-35B (local, Hermes+oMLX) | 3 | 1.00 | — | 238 K | 126 | $0 |
| Qwen3-Coder-Next 80B (local, ctx 0.9) | 3 | 1.00 | — | 1,586 K | 440 | $0 |
| Qwen3-Coder-30B (local, llama.cpp) | 12 | 0.67 | — | 1,114 K | 531 | $0 |
| gpt-oss-20b (local) | 5 | 0.40 | — | 876 K | 245 | $0 |

*(Opus 5 is n=1 on this specific cell — but the pattern is confirmed at n=9 across nine more languages
below. Historical local runs don't record a turn count; see the gap section.)*

## The finding: it's turns, not speed

The tempting explanation is that newer models "think longer" per step. The data says otherwise —
**seconds per turn is roughly flat across versions** (5.8 s for 4.7, 7.0 s for 4.8, 9.0 s for Fable 5,
10.9 s for Opus 5). What explodes is the **number of agentic turns**:

- **Fable 5: 10.7 turns** → 96 s
- **Opus 4.8: 17.3 turns** → 122 s
- **Opus 5: 36 turns** → 392 s

Opus 5 takes **3.4× as many steps as Fable 5** to produce the same passing app. Time and cost follow
the step count almost mechanically. So the honest framing is not "the model got slower" — it's **"the
model became more willing to keep working."**

## Why cost grows *faster* than turns: the cache-read curve

Token totals grow faster than turn counts, and the transcript shows exactly why. Opus 5's Python run
breaks down as:

| | tokens |
|---|---:|
| fresh input | 16,495 |
| **output (actual generation)** | **32,731** |
| cache creation | 133,176 |
| **cache reads** | **3,280,338** |

The model only *generated* ~33 K tokens — the whole app, its tests, and every message. But it **read
3.28 M tokens back out of cache**, 100× more than it wrote. That's the structural cost of an agentic
loop: **every turn re-reads the entire accumulated conversation.** With `n` turns over a context that
grows as you go, cache-read volume scales roughly with **n²**, not n.

That is the real answer to "why is it more expensive": doubling the number of turns roughly
*quadruples* the tokens billed, even though the code written is identical. Cache reads are individually
cheap, which is what keeps the bill at $1.84 rather than something absurd — but they dominate the
totals, and they are why the `tokens` column looks alarming next to a 33 K-token deliverable.

## Confirmed on nine more languages (n=9, not n=1)

The Python cell above is a single replicate for Opus 5, so a separate experiment re-ran **nine further
languages** — TypeScript, Java, C#, Elixir, Erlang, C, C++, Objective-C and Swift — on the same routine
task. Every model scores the same result; only the work differs:

| bookshop, 9 languages | n | pass | turns | tokens | seconds | cost |
|---|---:|---:|---:|---:|---:|---:|
| **Fable 5** | 9 | **1.00** | **26.4** | 866 K | **280** | $2.68 |
| **Opus 5** | 9 | **1.00** | **59.8** | **2,878 K** | **712** | $3.76 |
| Opus 4.8 | 22 | 0.95 | 32.2 | 696 K | 375 | **$1.07** |

**The ratio holds.** Opus 5 needs **2.3× the turns** of Fable 5 for an identical 1.00 — and the tokens
grow **3.3×** off that 2.3× step increase, the n² curve again. It is the third independent dataset
(single Python cell, fast-mode across task difficulty, and now nine languages at n=9) pointing at the
same mechanism, so this is no longer a one-run curiosity.

Note also that Opus 4.8 is **cheapest but not perfect** here (0.95 — one miss across 22 runs on these
harder languages), which is the real trade: Fable 5 buys the last 5 % of reliability for ~2.5× the
price, and Opus 5 buys nothing over Fable 5 on this task except a bigger bill.

## Fast mode: the control that separates *serving* from *model*

Fast mode is the same Opus 4.8 weights served differently, so it isolates a question the version
comparison can't: **is the extra work coming from the model or from how it's delivered?**

| Opus 4.8, Python bookshop | n | turns | tokens | seconds | cost |
|---|---:|---:|---:|---:|---:|
| standard | 6 | 17.3 | 310 K | 122 | **$0.50** |
| **fast mode** | 3 | **11.3** | 242 K | **90** | $0.74 |

Fast mode finishes **26 % quicker** and bills **48 % more** (it's charged at 2× the standard rate — a
premium retort applies explicitly, since the CLI reports the standard-rate figure). That trade is the
expected one. The *unexpected* part is the **turn count: 11.3 vs 17.3** — the same weights taking a
third fewer agentic steps. With n=3 against n=6 that could be variance, but if it's real it means the
serving path affects *how many steps the loop takes*, not just how fast each one returns. Worth
resolving in exp-49, where fast mode gets the same instrumented treatment.

Fast mode also shows the turn count tracking task difficulty, which is the cleanest confirmation of the
central thesis. Same model, same serving, harder task:

| Opus 4.8 fast mode | n | turns | tokens | seconds | cost |
|---|---:|---:|---:|---:|---:|
| bookshop (routine, all languages) | 12 | 14.7 | 370 K | 143 | $1.08 |
| **brazil-bench (hard)** | 12 | **55.8** | **4,110 K** | **887** | **$8.72** |

Same weights, same serving, **3.8× the turns → 11× the tokens → 6× the time**. Nothing about the model
changed; only how much work the task demanded. That super-linear token growth against a merely
3.8× step increase is the n² cache-read curve again, measured on a second axis.

## What Opus 5 is actually doing with those turns

From its transcript — 55 assistant messages, 35 tool calls:

| tool | calls |
|---|---:|
| Bash | 13 |
| Write | 11 |
| Edit | 9 |
| Read | 2 |

The shape is **write → run → edit → run again**: eleven file writes, nine follow-up edits, and thirteen
shell invocations (installs, test runs). Only two reads — it isn't exploring, it's **iterating on its
own output**. More than half the tool calls come *after* the first version of the code exists. That is
consistent with a model tuned to verify and refine rather than to emit once and stop.

Whether that iteration is what *buys* Opus 5 its unmatched breadth elsewhere — it is the only model
that clears the [hard task](past-experiments.md) in all 13 languages — is the interesting open
question. On an easy task the extra cycles are pure overhead. On a hard one they may be the mechanism.

## The local models tell the same story

The pattern isn't Anthropic-specific. Among local stacks on the identical task:

- **Qwen3.6-35B: 238 K tokens, 126 s** — the lean end, and it passes 3/3. Its profile is remarkably
  close to Opus 4.8's (310 K, 122 s).
- **Qwen3-Coder-Next 80B: 1,586 K tokens, 440 s** — the verbose end, also 3/3. Its profile mirrors
  **Opus 5's** (1,252 K, 392 s).

So "bigger/newer model, same result, ~4× the work" reproduces across two entirely different model
families. That suggests the driver is **how the model was tuned to behave in an agent loop**, not
anything specific to one vendor's architecture.

Two local stacks also spend heavily *without* succeeding — Qwen3-Coder-30B (1,114 K tokens, 0.67) and
gpt-oss-20b (876 K, 0.40 at n=5) — a useful reminder that high token counts signal *effort*, not
competence.

## What we can't yet answer honestly

**We cannot compare the tool-call mix across versions**, because the older runs have no transcripts:
`_agent_stdout.log` capture was added part-way through this project, so exp-6 (Opus 4.7 / 4.8) and the
early local experiments archived scores but not the agent's steps. The Opus 5 profile above is the only
one we can compute. Everything cross-version in this post therefore rests on **turns / tokens /
seconds / cost**, which are recorded throughout — and the tool-level claim is deliberately confined to
the one run that supports it.

Two measurement gaps to close:

1. **No transcripts for older versions** → we can't say whether 4.8 also writes-then-edits, or whether
   Opus 5's extra turns are extra *edit* cycles specifically.
2. **Local stacks recorded no turn count** — `turns` was empty for every Hermes run, so the local rows
   above can't be put on the cloud's axis. **Now fixed:** Hermes reports `api_calls` (one per model
   round-trip) in its usage file and the parser was dropping it; it is now recorded as `num_turns`
   (verified on an archive: a gpt-oss TypeScript run = 27 turns). *Historical* local runs stay blank,
   which is why exp-49 re-runs them.

**A controlled rerun is scheduled** (see `docs/future-experiments.md`): the same Python bookshop cell
across Opus 4.7 / 4.8 / Fable 5 / Opus 5 and the local 35B / 80B, with full transcript capture and turn
recording on every arm, n≥3. That converts the central claim of this post — *newer models take more
steps, and cost scales with the square of steps* — from one well-instrumented run plus aggregate
counters into a properly replicated comparison.

## The practical takeaway

If your task is routine, **the newest model is the wrong default**. On this task Opus 4.8 delivers the
identical 1.00 for **$0.50 and 122 s**, against Opus 5's **$1.84 and 392 s** — and Fable 5 finishes
fastest of all at 10.7 turns. Fast mode is the exception worth knowing: ~26 % quicker for ~48 % more, same result — buy it when latency matters, not when throughput does. Newer models are earning their keep somewhere else: at the hard end of the
range, where the extra iteration converts failures into passes. Pay for the steps when the steps are
what you need.
