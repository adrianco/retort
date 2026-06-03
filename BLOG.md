# The Best AI Coding Stack Isn't the Newest Model — It Depends on Your Language and Task

*June 2026 — Adrian Cockcroft*

---

Every few weeks a new frontier model lands at the top of the leaderboards, and the implicit advice is "upgrade." Sites like **[llm-stats.com](https://llm-stats.com/)** do a great job ranking models across many benchmarks — but they answer a question most engineering teams aren't actually asking. They hold the *stack* constant: one prompt, one harness, a fixed benchmark. They don't tell you whether the newest model is worth 5× the cost **in Rust**, whether last year's model is the better value **for a Go MCP server**, or how long any of it takes.

Those are the variables that decide a real project. So I built **[retort](https://github.com/adrianco/retort)** to measure them directly — and ran six experiments, ~200 scored runs, across two tasks, six languages, and four Claude models. The headline: **the best stack is task- and language-dependent, and it is frequently *not* the newest model.**

## What retort does

Retort applies statistical Design of Experiments (DoE) to AI coding agents. You give it factors — `language × model × tooling` — and a task, and it:

1. **Generates the design** (full factorial, or a fractional design if the grid is big), so every cell is a controlled comparison.
2. **Runs each cell in an isolated playpen** — the agent (`claude -p`) implements the task in a fresh workspace, then the code is built and tested in place.
3. **Scores it** — not just on quality and test coverage, but on whether it **provably implements the spec**. A run only passes if its tests actually run *and* a fixed requirement checklist is met. (More on why that gate took three tries to get right, below.)
4. **Aggregates everything** into one `master.db` so you can ask cross-experiment questions and pick the leading stack for your problem.

The whole thing is driven in plain language — you describe the experiment to Claude Code and it designs the matrix, checks prerequisites, estimates the cost, and runs it. Install and usage are at the end.

## The leading stack, by language and task

For each language I ranked the `(model, tooling)` cells by a deliberately practical priority: **does it implement the spec → do its tests pass → is it fast → is it cheap → is it clean.** Here's what won.

**On a hard task** (a Brazilian-soccer MCP server: CSV ingest, a knowledge graph, six query capabilities, BDD tests):

| Language | Leading stack | ReqCov | Speed | Cost |
|---|---|---:|---:|---:|
| clojure | sonnet / beads | 1.00 | 410 s | $1.03 |
| go | sonnet / none | 0.92 | 426 s | $1.18 |
| java | opus-4.6 / none | 1.00 | 474 s | $1.73 |
| python | sonnet / beads | 1.00 | 483 s | $1.25 |
| rust | sonnet / none | 1.00 | 471 s | $1.14 |
| typescript | sonnet / beads | 1.00 | 362 s | $0.93 |

**Sonnet and Opus-4.6 win almost everywhere** — and the newest models are nowhere in the table. Not because they're worse coders, but because they reach full requirement coverage at **~$1 and ~7 minutes**, while Opus 4.7 and 4.8 charge **~$5 and 12–17 minutes** for the *same or lower* coverage.

**On an easy task** (a REST CRUD API), almost every model nails the spec, so the ranking comes down to speed and cost — and there **Opus-4.7 wins as often as 4.8**, with 4.6 and Sonnet competitive on price. Full tables are in the [README](README.md).

## What we learned

**1. Newer is slower, much more expensive, and not reliably more accurate.** This is the controlled, apples-to-apples comparison — the same cells, two models:

| Same cells, two models | ReqCov | Speed | Cost/run |
|---|---:|---:|---:|
| REST-API: Opus-4.7 vs 4.8 | **1.00** vs 1.00 | **165 s** vs 243 s | **$0.85** vs $0.96 |
| Brazil: Opus-4.7 vs 4.8 | 0.67 vs **0.85** | **706 s** vs 1039 s | **$4.57** vs $5.60 |
| Brazil: Opus-4.6 vs 4.7 | 0.98 vs **1.00** | **443 s** vs 1385 s | **$1.46** vs $8.13 |

On the easy task, 4.7 and 4.8 are tied on accuracy — so paying for 4.8 buys *nothing* but a slower, pricier run. On the hard task, 4.8 genuinely beats 4.7 on spec coverage (0.85 vs 0.67) — but both cost ~$5 a run, while **Opus-4.6 hit 0.98 coverage for $1.46.** The cost-per-generation curve is brutal, and it is not buying proportional accuracy.

**2. Passing tests is not the same as meeting the spec — and that gap is invisible to most metrics.** On the hard task, Opus-4.7 runs had **93% test coverage but only 67% requirement coverage**: green test suites for a half-built feature. Lint scores and test coverage both looked fine. The only thing that caught it was a gate that reads the actual requirement checklist and checks the code against it.

Getting that gate to be trustworthy was its own saga. A single cheap LLM grader (haiku) was uselessly noisy — it scored the *identical* code 0.33 one run and 1.0 the next. The fix was three-part: **pin the requirement list per task** (so the denominator is constant), **judge with a stronger model** (Opus-4.6), and take a **"second opinion"** — only fail a run if two independent evals both find a gap. That turned a coin-flip into a reproducible number.

**3. Sonnet is the value play on hard problems.** Full requirement coverage at ~$1 where the newest Opus models cost ~$5. If your task is genuinely hard and you're running many variants, that 5× matters.

**4. Language dominates code quality; the model mostly moves cost and speed.** Across all experiments, ANOVA finds `code_quality` driven almost entirely by *language* — Java, Go, and Rust score high regardless of which model wrote the code. Switching models barely moves quality; it moves the bill and the clock.

**5. Extra tooling didn't help these tasks.** Adding the `beads` issue-tracker tooling cost ~30% more wall-clock and 10–20% more money with no quality gain on these single-shot tasks, so it was dropped from the later experiments. It's built for multi-step coordination these tasks don't exercise — a reminder that "more scaffolding" isn't free.

## The six experiments

1. **REST-API, Opus-4.6 vs Sonnet** (56 runs) — near-tied coverage; Java/Go/Rust sweep quality; Python is tooling-sensitive.
2. **Brazil, Opus-4.6 vs Sonnet** (22 runs) — the hard task; Opus-4.6 higher requirement coverage, Sonnet cleaner and cheaper.
3. **Brazil, Opus-4.6 vs 4.7** (7 runs) — 4.7 marginally more complete but 3× slower and 5.5× pricier.
4. **Brazil, Opus-4.8** (6 runs) — first 4.8 data; full coverage but the slowest, priciest runs of the whole program.
5. **Brazil, Opus-4.7 vs 4.8, full factorial** (36 runs) — 4.8 beats 4.7 on coverage (0.85 vs 0.67) but +47% time and cost; both expensive.
6. **REST-API, Opus-4.7 vs 4.8, full factorial** (71 runs) — accuracy tied at ~1.0; 4.7 is the better value.

Every run's source, tests, scores, and spec-eval output are committed in the repo under `experiment-N/runs/`, and the combined data is in `master.db` / `master.csv`. (A note on honesty: cross-experiment model averages mix different language/tooling sets, so the model-version claims above all come from the *controlled within-experiment* comparisons.)

## Try it on your own stack

The real value isn't my numbers — it's that you can get *your* numbers, on *your* task or codebase, in an afternoon. Install is a one-liner if you let Claude Code handle the C++ build dependency:

```text
$ claude
> clone and install https://github.com/adrianco/retort here
```

Then describe the experiment you want — "compare Opus 4.6/4.7/4.8 across Go, Rust and Python on this task" — and Claude designs the matrix, installs the toolchains, runs the cells (resuming across API usage-limit windows), and reports. Watch it live with `retort monitor`, and roll it all up with `retort aggregate`.

Leaderboards tell you which model is "best" in the abstract. Retort tells you which **stack** is best for the code you're actually shipping — and, often enough, it's not the one at the top of the leaderboard.

*Code, data, and full per-run results: [github.com/adrianco/retort](https://github.com/adrianco/retort)*
