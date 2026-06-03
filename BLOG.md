# How Reliable Is Your AI Coding Stack? I Measured It

*June 2026 — Adrian Cockcroft*

---

Every few weeks a new frontier model tops the leaderboards, and the implicit advice is "upgrade." Sites like **[llm-stats.com](https://llm-stats.com/)** rank models well across many benchmarks — but they answer a question most engineering teams aren't actually asking. They hold the *stack* constant: one prompt, one harness, a fixed benchmark. They don't tell you whether the newest model is worth 4× the cost **in Rust**, how *reliably* each model gets a Go MCP server completely right, or how long any of it takes.

Those are the variables that decide a real project. So I built **[retort](https://github.com/adrianco/retort)** to measure them properly — with statistical Design of Experiments, the same technique you'd use to tune a manufacturing process. Vary the factors you care about (here: programming **language** × **model version** × **tooling**), run a factorial grid on a real task, score every cell, and let the analysis tell you which factors actually matter. Six experiments, **198 scored runs**, two tasks, six languages, four Claude models. Here's what came out.

## The metric that matters: how often is it *completely* right?

Most code scores grade on a curve — 80% test coverage, a clean linter run, a plausible-looking diff. But for code you intend to ship, "mostly implemented" is a failure, not a B+. So retort's headline metric is **pass-proportion**: run a stack N times and count the fraction whose output *fully implements the spec* — every requirement on a fixed checklist, with tests that actually execute, verified by an independent evaluator.

Read it as **the probability that a single run comes out completely correct.** 3 of 3 → 1.00, 2 of 3 → 0.66, 1 of 3 → 0.33. A run that misses even one requirement counts as a fail, not a 0.9. That's a deliberately harsh bar, and it's the one that matters when you're deciding whether to trust an agent with a feature.

## The headline: newer is more reliable — and you pay for it

Aggregated per model per task:

| Model | Brazil MCP (hard) | REST API (easy) | Speed (hard) | Cost (hard) |
|---|---:|---:|---:|---:|
| opus-4.6 | 0.47 | 0.59 | 309 s | $1.30 |
| sonnet | 0.50 | 0.63 | 440 s | $1.10 |
| opus-4.7 | 0.85 | **1.00** | 774 s | $4.92 |
| **opus-4.8** | **1.00** | **1.00** | 1035 s | $5.54 |

Three things jump out:

1. **Newer genuinely is more reliable — and the gap is enormous on hard tasks.** Opus-4.8 produced a completely-correct result **100% of the time, on both tasks.** The older, cheaper models (4.6 and Sonnet) got the *hard* task fully right only **about half the time.** On a difficult task, the cheap model is a coin-flip — it'll look fine in a demo and bite you in review.
2. **You pay through the nose for that reliability.** Opus-4.8 was **~3× slower and ~4× more expensive** than 4.6/Sonnet on the hard task. Reliability isn't free; it's a line item, and it grows fast across model generations.
3. **Opus-4.7 is the value sweet spot, and on easy work the newest model is pure overhead.** On the REST API, 4.7 and 4.8 are *tied* at 100% — so paying for 4.8 there buys you nothing but a slower, costlier run. On the hard task, 4.7 reaches 85% for noticeably less money than 4.8's 100%.

## The controlled view: same cells, two models

Those aggregates mix experiments, so the firm conclusions come from the *within-experiment* comparisons — identical language/tooling cells, run with two models, three replicates each.

**Hard task (Brazil, 6 languages × {4.7, 4.8}):** opus-4.8 passed **18/18** cells; opus-4.7 passed **15/18** — it dropped to 2-of-3 on Go and **1-of-3 on Rust**. So the newer model didn't just win on average; it closed specific, repeatable failure modes. But it took **~1040 s vs ~710 s** per run and cost **~$5.6 vs ~$4.6**.

**Easy task (REST API, 6 languages × {4.7, 4.8}):** both models passed essentially everything (1.00). The *only* measurable difference was that 4.8 was **~50% slower** (243 s vs 165 s) and a bit pricier. Identical result, higher bill.

The pattern is consistent: **each model generation buys you reliability on hard problems, and charges you time and money for it everywhere.** If your work is routine, the premium is wasted; if it's genuinely hard, it may be the difference between "ship it" and "rewrite it."

## It's not just the model — it's the language *and* the task

Average a model over everything and you hide the most useful signal. Break reliability down by language **and** task and it swings wildly:

| Language | Task | n | Pass | CodeQual | TestCov | Speed (s) | Cost ($) |
|---|---|---:|---:|---:|---:|---:|---:|
| clojure | Brazil (hard) | 12 | 0.75 | 0.83 | 1.00 | 715 | 3.51 |
| clojure | REST-API (easy) | 21 | 0.62 | 0.75 | 0.90 | 302 | 1.10 |
| go | Brazil (hard) | 13 | 0.69 | 1.00 | 0.58 | 773 | 4.35 |
| go | REST-API (easy) | 20 | **1.00** | 1.00 | 0.67 | 142 | 0.61 |
| java | Brazil (hard) | 10 | 0.80 | 1.00 | 1.00 | 784 | 4.03 |
| java | REST-API (easy) | 23 | **0.52** | 1.00 | 1.00 | 208 | 0.78 |
| python | Brazil (hard) | 14 | 0.86 | 0.73 | 0.90 | 638 | 3.30 |
| python | REST-API (easy) | 20 | 0.90 | 0.65 | 0.80 | 97 | 0.43 |
| rust | Brazil (hard) | 10 | **0.50** | 0.83 | 0.93 | 717 | 3.97 |
| rust | REST-API (easy) | 23 | **0.96** | 0.83 | 1.00 | 169 | 0.60 |
| typescript | Brazil (hard) | 12 | 0.92 | 0.61 | 0.82 | 617 | 3.31 |
| typescript | REST-API (easy) | 20 | 1.00 | 0.73 | 0.89 | 168 | 0.56 |

Look at the spread:

- **Rust flips completely**: 0.96 on the easy task, **0.50 on the hard one.** The agents write clean, well-typed Rust for a CRUD API, but the harder knowledge-graph task trips them up half the time.
- **Java runs the other way**: 0.80 on the hard task but only **0.52 on the easy one** — counter-intuitive until you see *how* it fails (over-engineered scaffolding that misses a small requirement on the simple task).
- **TypeScript and Python are the all-rounders**: strong on both (0.92–1.00 and 0.86–0.90).
- And **code quality barely moves across tasks within a language** — Go and Java sit at 1.00 regardless of difficulty — even as their *reliability* swings. Clean code and complete code are not the same thing, and they're driven by different factors (see below).

There is **no single "best language."** "Use Rust, it's rigorous" is good advice for a service and bad advice for the hard task; the only way to know is to run your task.

## What the variance actually comes from (ANOVA)

Because this is a designed experiment, I can decompose *where each metric's variation comes from* — language vs. model vs. tooling — with a type-II ANOVA (cost and time log-transformed, since they scale multiplicatively). The separation of concerns is almost suspiciously clean:

| Response | Dominant factor (variance share) | Reading |
|---|---|---|
| **code_quality** | **language ≈ 94–96%** (p < 10⁻⁴⁰); model ≈ 0% | Quality is the *language's*, not the model's. |
| **test_coverage** | **language ≈ 92–95%** (p < 10⁻¹⁵); model ≈ 0% | Same — the language and its test ecosystem dominate. |
| **duration** | **task ≈ 75%**; model (on a fixed hard task) ≈ 37% | The task sets the clock; the newer model is the slower one. |
| **cost** | **task ≈ 82%**; tooling +10% (p < 0.001) | The task sets the bill; `beads` tooling measurably adds to it. |
| **requirement_coverage** | **model** (borderline, p ≈ 0.06) | The only metric the model meaningfully moves. |

Stated plainly: **language governs how clean the code is, the task governs how much it costs, and the model governs how reliably it's correct.** Three different factors, three different knobs. The practical consequence is sharp — reaching for a newer model to get "better code" is mostly wasted money. It doesn't write *cleaner* code (the language already decided that); it writes *more reliable* code, and charges you time and dollars for it. You can only see that by varying the whole stack and doing the statistics, instead of reading one number off a leaderboard.

(The `beads` issue-tracker tooling I tested showed up in exactly one place — extra cost and time, with no quality or reliability payoff — which is why it was dropped from the later experiments. Worth remembering the next time someone suggests bolting more scaffolding onto an agent "to be safe.")

## So how should you actually choose?

The data suggests a simple decision procedure:

1. **Classify the task.** Is it routine (CRUD, glue, well-trodden patterns) or genuinely hard (novel domain, many interacting requirements)?
2. **Easy task → optimize for cost/speed.** Almost every model fully implements it, so take the cheapest fast one — here that's Opus-4.7, with 4.6 and Sonnet close behind. Paying for the newest model is wasted.
3. **Hard task → pay for reliability if you need it right.** Opus-4.8 was the only model that got the hard task completely right every time. If a half-chance of a subtly-incomplete implementation is unacceptable, that premium is the cost of trust.
4. **Pick the language for quality, not the model.** If you have latitude, Go/Java/Rust score top marks for code quality on these tasks — but check *reliability* for your specific task, because that's where languages diverge.
5. **Don't add tooling for its own sake.** It cost time and money here and changed nothing else.

## How it's measured

Each run gets its own isolated workspace; the agent implements the task, and the code is then built and tested in place. The spec check is the strict part: an independent evaluator verifies the code against a **fixed requirement checklist** for the task, and a run only counts as a pass if it implements *all* of it and its tests actually run. To keep that grading reproducible, the checklist is pinned (so the denominator is constant across runs), a strong model does the judging, and a borderline result gets a second opinion before it's recorded. Every number above is that gate applied across all 198 runs — not a hand-picked sample. Per-experiment tables and the combined dataset are in the [README](https://github.com/adrianco/retort) and `master.csv`.

## Try it on your own stack

The point of retort isn't my numbers — it's that you can get *yours*, on *your* task or codebase, in an afternoon:

```text
$ claude
> clone and install https://github.com/adrianco/retort here
> then compare opus 4.6/4.7/4.8 across Go, Rust and Python on this task
```

Claude designs the experiment, installs the toolchains, runs the cells (resuming across usage-limit windows), and scores each one for whether it actually implements the spec. Watch it live with `retort monitor`; roll it all up with `retort aggregate` and run the ANOVA with `retort report effects`.

Leaderboards tell you which model wins in the abstract. Retort tells you which **stack** wins for the code you're shipping — how reliably, how fast, and for how much. Sometimes the answer is the newest model; sometimes it's the one that's four times cheaper. You won't know until you measure it.

*Code, data, and full per-run results: [github.com/adrianco/retort](https://github.com/adrianco/retort)*
