# How Reliable Is Your AI Coding Stack? I Measured It

*June 2026 — Adrian Cockcroft*

---

Every few weeks a new frontier model tops the leaderboards. Sites like **[llm-stats.com](https://llm-stats.com/)** rank them well across many benchmarks — but they answer a question most engineering teams aren't asking. They hold the *stack* constant: one prompt, one harness, a fixed benchmark. They don't tell you whether the newest model is worth 4× the cost **in Rust**, how *reliably* each model gets a Go MCP server completely right, or how long any of it takes.

Those are the variables that decide a real project. So I built **[retort](https://github.com/adrianco/retort)** to measure them — six experiments, 198 scored runs, across two tasks, six languages, and four Claude models. Here's what I found.

## The metric that matters: how often is it *completely* right?

Most scores grade on a curve — 80% test coverage, a clean linter run. But for shipping code, "mostly implemented" is a failure. So retort's headline metric is **pass-proportion**: run a stack N times, and count the fraction whose output *fully implements the spec* — every requirement on a fixed checklist, verified by an independent eval. Read it as **the probability that a single run comes out completely correct.** 3 of 3 → 1.00, 2 of 3 → 0.66. A run that misses even one requirement is a fail, not a 0.9.

## The result

| Model | Brazil MCP (hard) | REST API (easy) | Speed (hard) | Cost (hard) |
|---|---:|---:|---:|---:|
| opus-4.6 | 0.47 | 0.59 | 309 s | $1.30 |
| sonnet | 0.50 | 0.63 | 440 s | $1.10 |
| opus-4.7 | 0.85 | **1.00** | 774 s | $4.92 |
| **opus-4.8** | **1.00** | **1.00** | 1035 s | $5.54 |

Three things jump out:

1. **Newer genuinely is more reliable — and the gap is huge on hard tasks.** Opus-4.8 produced a completely-correct result **100% of the time, on both tasks.** The older, cheaper models (4.6 and Sonnet) got the hard task fully right only **about half the time.** On a difficult task, the cheap model is a coin-flip.
2. **You pay through the nose for that reliability.** Opus-4.8 was **~3× slower and ~4× more expensive** than 4.6/Sonnet on the hard task. Reliability isn't free; it's a line item.
3. **Opus-4.7 is the sweet spot, and on easy tasks the newest model is overkill.** On the REST API, 4.7 and 4.8 are *tied* at 100% — so paying for 4.8 buys nothing but a slower, costlier run. On the hard task 4.7 hits 85% for less money than 4.8's 100%.

So the real decision isn't "which model is best" — it's **how much reliability you need and what you'll pay for it**, and that depends on whether your task is a CRUD API or a knowledge-graph server. The leading stack is **task- and language-dependent**, which is exactly what a single leaderboard rank can't capture. (Per-language tables — where the cheap models win some languages and fail others — are in the [README](README.md).)

## What the variance actually comes from

Because this is a designed experiment, I can decompose *where each metric's variation comes from* — language vs. model vs. tooling — with an ANOVA. The separation is almost suspiciously clean:

- **Code quality and test coverage are ~95% explained by the *language*** (p < 10⁻⁴⁰) — and **~0% by the model.** Java, Go, and Rust score high no matter which model writes the code; the model barely moves it.
- **Cost and run time are dominated by the *task*** (~75–82% of the variance) — and within a fixed hard task, by the *model* (the newer one is the slower one).
- **Reliability is the *only* metric the model meaningfully drives.**

In plain terms: **language governs how clean the code is, the task governs how much it costs, and the model governs how reliably it's correct.** So reaching for a newer model to get "better code" is mostly wasted spend — it buys you *reliability* (and a bigger bill), not cleaner code. That's the kind of thing you only see when you vary the whole stack and do the statistics, instead of reading one model off a leaderboard. (Extra tooling — a `beads` issue tracker — showed up in exactly one place: more cost and time, with no quality or reliability payoff.)

## How it's measured

Each run gets its own isolated workspace; the agent implements the task, and the code is then built and tested in place. The spec check is the strict part: an independent eval verifies the code against a **fixed requirement checklist** for the task, and a run only counts as a pass if it implements *all* of it and its tests actually run. To keep that grading reproducible, the checklist is pinned (so the denominator is constant across runs), a strong model does the judging, and a borderline result gets a second opinion before it's recorded. Every number above is that gate applied across 198 runs — not a hand-picked sample.

## Try it on your own stack

The point of retort isn't my numbers — it's that you can get *yours*, on *your* task or codebase, in an afternoon:

```text
$ claude
> clone and install https://github.com/adrianco/retort here
> then compare opus 4.6/4.7/4.8 across Go, Rust and Python on this task
```

Claude designs the experiment, installs the toolchains, runs the cells (resuming across usage-limit windows), and scores each one for whether it actually implements the spec. Watch it live with `retort monitor`; roll it up with `retort aggregate`.

Leaderboards tell you which model wins in the abstract. Retort tells you which **stack** wins for the code you're shipping — how reliably, how fast, and for how much — and sometimes the answer is the newest model, sometimes it's the one that's four times cheaper. You won't know until you measure it.

*Code, data, and full per-run results: [github.com/adrianco/retort](https://github.com/adrianco/retort)*
