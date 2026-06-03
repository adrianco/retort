# How Reliable Is Your AI Coding Stack? I Measured It — and Nearly Published the Wrong Answer

*June 2026 — Adrian Cockcroft*

---

Every few weeks a new frontier model tops the leaderboards. Sites like **[llm-stats.com](https://llm-stats.com/)** rank them well across many benchmarks — but they answer a question most engineering teams aren't asking. They hold the *stack* constant: one prompt, one harness, a fixed benchmark. They don't tell you whether the newest model is worth 4× the cost **in Rust**, how *reliably* each model gets a Go MCP server completely right, or how long any of it takes.

Those are the variables that decide a real project. So I built **[retort](https://github.com/adrianco/retort)** to measure them — six experiments, 198 scored runs, across two tasks, six languages, and four Claude models. This post is about what I found, and about the bug that almost made me publish the exact opposite conclusion.

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

## The part where I was almost wrong

Here's the uncomfortable bit. The **first** version of this post said the opposite: "newer isn't better, Sonnet is the value play, you're overpaying for 4.8." I had the data, the tables, the charts. I nearly shipped it.

Then, checking a footnote, I noticed an evaluation flagging a run for missing a requirement that read *"simple lookups respond in < 2 seconds."* That was never in my requirement checklist — it was a performance SLA the grader had invented. Digging in, I found the evaluator had two compounding problems:

- It was **grading against requirements it extracted itself**, non-deterministically — the *same code* scored 0.33 on one pass and 1.0 on the next. (A cheap grader model was the culprit.)
- Worse, when a grading run hit a usage limit and silently failed, my pipeline **read the previous grade from disk and treated it as fresh** — so 124 of 198 results were stale, carried over from the noisy old evaluator.

The stale grades were biased *low* — that invented "< 2 second" requirement auto-failed runs that were actually complete — and they happened to drag down the newest models most. Fix the evaluator (pin the checklist so the denominator is constant, judge with a stronger model, take a second opinion, and never read a grade you didn't just write), re-run all 198, and the conclusion **flipped**: newer is more reliable, not less.

The lesson isn't "LLM evals are hard" (though they are). It's that **a measurement tool is only as trustworthy as its own plumbing** — and the failure was silent. That's the whole reason to build something like retort rather than eyeball a few runs: it makes the comparison reproducible, and it makes bugs like this *findable*.

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
