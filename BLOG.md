# What Actually Makes AI-Generated Code Good? Six Experiments, 190 Runs, One Clear Answer

*May 2026 — Adrian Cockcroft*

---

We ran six structured experiments — **~190 coding runs, ~$210 in API costs** — to answer a question most teams settle with intuition: when an AI agent writes code, what actually determines whether it's good? The language? The model version? The tooling? We measured it with statistical Design of Experiments instead of guessing. **Here are the results first; the method and the tooling to reproduce them follow.**

---

## The Results

### 1. Language dominates everything else

Across every experiment, ANOVA on `code_quality` returns the same verdict: **language is the dominant factor** (p < 1e-18 on the first experiment), and it stays dominant on harder tasks and newer models. The ranking is remarkably stable:

| Language | Quality | Why |
|----------|---------|-----|
| **Java** | 1.000 | Spring Boot + JUnit + JaCoCo is a complete scaffold; the agent rarely missteps |
| **Go** | ~0.98–1.00 | `go mod` + `go test ./...` + a simple language make non-functional code hard to write |
| **Rust** | 0.833 | Consistent on every successful run; the compiler enforces correctness |
| **TypeScript** | 0.73 | Reliable *when* a test framework is wired up; fragile when it isn't |
| **Clojure** | 0.83 | Strong on harder tasks; bimodal on simple ones |
| **Python** | 0.54–0.78 | Highest variance — permissive structure means the agent improvises differently each run |

**Switching language buys you more quality than switching model.** Going from Python to Go moves the needle further than going from Sonnet to Opus (at 2× the price). Choose the ecosystem first.

### 2. Newer model ≠ better — and newer ≠ faster or cheaper

We compared **four models** — `sonnet-4.5` and three Opus generations (`4.6 → 4.7 → 4.8`) — on the same tasks. The headline isn't "newer is better." It's "newer is *different*, mostly in second-order ways, and it costs more."

The cleanest controlled comparison is Go with no tooling, the one cell measured on all three versions of the hard brazil-bench task:

| Version | code_quality | **test_coverage** |
|---------|--------------|-------------------|
| opus-4.6 | 1.000 | 0.42 |
| opus-4.7 | 1.000 | **0.81** |
| opus-4.8 | 1.000 | 0.44 |

`opus-4.7`'s coverage spike was a **peak, not a trend** — `opus-4.8` reverts to 4.6-level coverage (with less runtime, so it isn't a timeout artifact). Code quality is a flat 1.000 throughout. The much-touted "newer model writes more tests" effect was specific to 4.7.

On the simpler bookshop task (a full 24-cell factorial, 71 runs), **4.7 and 4.8 are a statistical dead heat**:

| | code_quality | test_coverage | cost/run |
|---|---|---|---|
| opus-4.7 | 0.861 | 0.929 | $0.84 |
| opus-4.8 | 0.860 | 0.941 | $0.96 |

Per-language, the two versions produce **identical** quality (go 1.00/1.00, java 1.00/1.00, rust 0.83/0.83, clojure 0.83/0.83, ts 0.73/0.73, python 0.77/0.78). 4.8 costs a little more. The language ladder is untouched by the model bump.

Putting all four models side by side on that same bookshop task tells the fuller story:

| Model | code_quality | duration (median) | cost/run |
|---|---|---|---|
| sonnet-4.5 | 0.752 | 2.9m | $0.37 |
| opus-4.6 | 0.833 | **2.3m** | $0.45 |
| opus-4.7 | **0.861** | 2.8m | $0.84 |
| opus-4.8 | 0.860 | 2.7m | $0.96 |

Quality climbs from Sonnet to Opus and rises 4.6 → 4.7, then **plateaus** at 4.8. But the resource curve goes the *other* way: **opus-4.6 is the fastest** model, and **cost roughly doubles** from Sonnet/4.6 (~$0.40) to 4.7/4.8 (~$0.90). So the newest model is the most expensive and among the slowest, for no quality gain over 4.7 — on this task `opus-4.7` is the value sweet spot, and on the harder brazil-bench task 4.8 runs *longer still* (Time taken, below). "Upgrade to the newest model" is not free, and not automatically better.

### 3. Task difficulty reshuffles the middle of the pack

The top (Java, Go) and the method are stable, but the middle moves with task difficulty — a real **model × task interaction**. On the simple CRUD task Opus and Sonnet performed similarly; on the harder MCP task, TypeScript/Opus produced broken builds that Sonnet didn't. A cross-task ANOVA (pooling tasks as a factor) confirms `model:task` is significant. **Single-task benchmarks miss this** — they generalize less than people assume.

### 4. Task-tracking tooling doesn't move code quality

Beads vs. no-beads was statistically insignificant for `code_quality` across both tasks and every model — **and it's not free.** Turning beads on added **~30% wall-clock and ~10–20% cost** (bookshop: 2.3 → 3.0 min median, $0.81 → $0.99; brazil-bench: 11 → 14 min, $4.82 → $5.33) with quality *identical or slightly worse*. That's not a knock on beads — it solves multi-step *coordination*, which these single-shot tasks don't exercise — but for this kind of benchmark it's pure overhead, so we **dropped it from the experiment program** going forward. The lesson generalizes: don't pay for tooling against a metric it was never aimed at.

### 5. Cost: the expensive task is 6× the cheap one

The same factorial costs ~$0.34–$0.96 per run on the CRUD task and ~$5 per run on the MCP-server task. Compiled languages (Go, Rust, Clojure) consume the most tokens because the agent spends the extra budget writing tests. Only `go/sonnet/beads` sat on the Pareto frontier across both tasks — nothing beat it on quality *and* cost simultaneously.

### 6. Time taken: task first, then language, then (weakly) model — and newer isn't faster

Wall-clock per run tracks tokens and cost closely, and the same ordering holds: **task dominates, language is next, model version is a distant, task-dependent third.**

- **Task is a 5–9× multiplier.** The identical languages run far longer on the hard MCP task than on the bookshop CRUD task — Go ≈ 2.6 min vs ≈ 23 min, Python ≈ 1.9 min vs ≈ 13 min. Budget by task before anything else.
- **Language sets the rest, and the tail matters.** Scripted languages (python ≈ 1.8 min median, typescript ≈ 2.4) are quickest; JVM/compiled are slower, and **java and clojure carry the heavy right tails** — single bookshop runs of 17 min (java) and 27 min (clojure) against a ~3-minute median.
- **A newer model is not a faster model.** On the easy task all four are close — **opus-4.6 quickest** (2.3 min median), Sonnet-4.5 ~2.9, the newer opus versions 2.7–2.8 (4.7 ≈ 4.8). On the *hard* task the model effect explodes into a steep ladder: **opus-4.6 ≈ 4 min → 4.7 ≈ 11 → 4.8 ≈ 16** (Sonnet-4.5 ~7, between 4.6 and 4.7) — each generation ~1.5–2× the last, for the same quality. The "newer = quicker" intuition is exactly backwards: newer Opus generations spend *more* time (and ~2× the cost), and the gap widens as tasks get harder. (The timeout doesn't cause this — it only fails a run that overruns; a completed run takes as long as it takes.)

This long-tail-on-hard-tasks behavior is exactly why retort's adaptive timeout is **extend-only** (it floors at your configured budget and only ever grants *more* time): an early, fast run must never set a ceiling that strangles a later, legitimately slow one.

---

## How These Results Are Produced

### Design of Experiments, applied to AI stacks

Statistical **Design of Experiments** (DoE) was built in the 1920s for agriculture: you can't find the best fertilizer by varying one thing at a time, because the factors interact. The same is true for AI coding stacks. "Is Go better than Python?" is the wrong question; "which combination of language + model + tooling + task wins, and why?" is the right one.

A full factorial (every combination × replicates) is too expensive, so Retort uses **fractional factorial designs** — statistically valid answers at a fraction of the cost — and falls back to full factorials when a comparison (like 4.7-vs-4.8) needs to be aliasing-free.

The workflow: **define factors → generate a design matrix → run each cell in an isolated playpen via the Claude Code CLI → score the output → ANOVA for significance → promote or retire stacks**.

### What gets measured

Every run produces a complete, buildable implementation of a task. Eight scorers grade it:

- **`code_quality`** — 1.0 minus a weighted penalty for code-review findings (critical 0.25, high 0.10).
- **`test_coverage`** — real line coverage (pytest-cov, `go test -cover`, cargo-llvm-cov, JaCoCo, vitest/jest). **A 0 here vetoes every other metric** — the "test gate" that stops impressive-but-nonfunctional code from scoring.
- **`test_quality`** — rewards BDD (Given/When/Then) patterns over plain unit tests.
- **`defect_rate`**, **`maintainability`**, **`idiomatic`**, **`token_efficiency`**, **`findings`** — build/test reliability, LLM maintainability assessment, idiom usage, cost-efficiency proxy, and severity-weighted finding counts.

### The six experiments

| # | Task | Design | Runs | Cost | Focus |
|---|------|--------|------|------|-------|
| 1 | CRUD books API | 6 lang × 2 model × 2 tooling | 73 | $25 | Baseline — language dominates |
| 2 | Brazil-bench MCP server | 24-cell screening | 24 | $30 | Cross-task; model × task interaction |
| 3 | Brazil-bench | Res-III ¼-fraction | 14 | $55 | opus-4.6 vs 4.7 |
| 4 | Brazil-bench | ¼-fraction augment | 6 | $32 | + opus-4.8 (three-way) |
| 5 | Brazil-bench | **full** 4.7×4.8 factorial | 72* | — | 4.7-vs-4.8 confirmation (de-aliased) |
| 6 | CRUD books API | **full** 4.7×4.8 factorial | 71 | $64 | Cross-task 4.7-vs-4.8 confirmation |

\*Experiment 5 is the brazil-bench confirmation; it is being completed in resume cycles (see "usage limits" below).

### The infrastructure that makes it repeatable

**Sharded parallelism.** `retort run --shard 2/4` runs only the cells a deterministic hash assigns to shard 2 of 4; all shards write one SQLite DB with per-run commits, so two workers never collide and a crash loses at most one run.

**Adaptive timeouts — that only ever extend.** `_estimate_run_timeout` sizes each run's budget from historical timing for the same cell/language. A subtle bug let it shorten a run *below* the configured budget — so an early, history-poor run could be killed under-budget and score a false all-zeros timeout. It's now floored at the configured `timeout_minutes` (extend-only): the adaptive logic can grant a slow language more time but never less than you asked for.

**Live monitoring.** `retort monitor --db <db> --watch` is a built-in dashboard: completed/remaining, per-cell coverage, running cost and tokens, parallelism-aware throughput and ETA, and a failures list. It doubles as a tripwire — a burst of 1–2s failures is the unmistakable signature of an API usage limit, which lets you stop in seconds instead of burning an overnight batch.

**Usage limits are cumulative.** A hard lesson from these runs: provider usage limits track *total* consumption, not just concurrency. Four parallel shards trip them fastest, but even a single sequential shard hits the cap on a big expensive experiment. The recovery pattern is `--resume`: completed cells are skipped, so you bank progress each window and continue after the limit resets. Experiment 6 absorbed a mid-run limit exactly this way and still finished 71/72.

**Auto-evaluation & cost caps.** After each run Retort invokes the `evaluate-run` skill to produce code-review findings (archived next to the source), and `cost_limit_usd` aborts a run cleanly before an experiment can surprise you with the bill.

**Scorer engineering.** Getting scoring right was harder than running experiments. Each language needs its own coverage toolchain, and we fixed four scorer bugs mid-program (Java's `-q` silencing Surefire; Clojure's `-X:test` vs `-M:test`; Rust's missing coverage path; TypeScript's `.bin/vitest` wrapper) and rescored every prior run.

---

## How to Run Retort

Retort is [open source](https://github.com/adrianco/retort) (Apache-2.0). The quick start is genuinely quick.

### Install — the easy way, ask Claude Code

Retort has a couple of environment gotchas (Python ≥3.11, and `OApackage` is a C++ extension that must be built with `cmake`). The fastest install is to let Claude Code handle them — point it at a directory and ask:

```text
$ cd Documents/GitHub
$ claude
> clone and install https://github.com/adrianco/retort here

⏺ Done. Retort is cloned and installed, and all tests pass.

  Setup steps I had to take (the system default python3 is 3.9.6, but retort needs ≥3.11):
  - Installed cmake via Homebrew — required to build OApackage (a C++ extension).
  - Created a virtualenv with Homebrew's Python 3.12 at retort/.venv.
  - Ran pip install -e ".[dev,test]" — built retort and oapackage from source.

  Verification: retort --help loads; test suite 573 passed.
```

It will also offer to install the per-language toolchains and the `claude`/`bd` CLIs when you set up your first experiment.

### Install — by hand

```bash
git clone https://github.com/adrianco/retort.git
cd retort
pip install -e ".[dev,test]"
```

You also need: **Python 3.11+**, a **C/C++ toolchain + cmake** (for the `OApackage` orthogonal-array extension), the authenticated **`claude` CLI**, the per-language **toolchains** you list as factors (go, node, rustup, a JDK + maven, clojure), and **`bd`** (beads) only if you use `tooling: beads`.

### Define an experiment — just describe it to Claude Code

You don't have to hand-write `workspace.yaml` or work out the fractional-factorial math. Open `claude` in the repo and describe the experiment in plain language; it designs the matrix, checks prerequisites, estimates cost, confirms the decisions that matter, and runs it. Every experiment in this post was built this way:

```text
> I want to run a quarter fraction experiment 4 that extends experiment 3,
  which compared opus 4.6 and 4.7, to compare opus 4.8 as well

⏺ Two findings that shape the design:
  - claude CLI is present (v2.1.156) — good.
  - bd (beads) is NOT installed. Experiment-3 used tooling: beads in several
    cells … so any beads cell in experiment-4 needs beads installed first.

  Experiment-3 is a 6-cell Resolution III quarter-fraction of a 24-cell
  factorial (6 language × 2 model × 2 tooling), 2 replicates. Adding
  claude-opus-4-8 makes model a 3-level factor → the full factorial becomes
  3 × 6 × 2 = 36 cells, and a quarter-fraction is 9 cells.

  Before I build and run this (real API spend — exp-3 cost ~$55 — and hours
  of wall-clock), confirm a few design decisions:

⏺ User answered Claude's questions:
  · How should experiment-4 be structured?  → Augment exp-3 (reuse + add 4.8)
  · bd (beads) isn't installed. Tooling?     → Install bd, keep beads cells
  · Execute the runs, or set up and stop?    → Set up, then run it
```

Claude writes `experiment-4/workspace.yaml` + `design.csv`, installs the toolchains it needs, runs the cells, and reports results — and resumes cleanly across API usage-limit windows along the way.

### Or write the config yourself

`retort init my-eval` scaffolds a `workspace.yaml` you can edit directly — factors, response metrics, task, replicates:

```yaml
factors:
  language: { levels: [python, go, rust, java, typescript, clojure] }
  model:    { levels: [claude-opus-4-7, claude-opus-4-8] }
  tooling:  { levels: [none, beads] }
responses: [code_quality, test_coverage, maintainability, idiomatic]
tasks:
  - source: bundled://rest-api-crud      # or github://owner/repo/task.md
playpen: { runner: local, replicates: 3, timeout_minutes: 45 }
design:  { screening_resolution: 3 }     # add `fraction: 0.25` for a quarter-fraction
```

### Run, watch, analyze

```bash
# Execute (add --shard 0/4 ... 3/4 across workers; --resume to continue after a stop)
retort run --phase screening --config workspace.yaml

# Live dashboard / usage-limit tripwire (separate shell)
retort monitor --db retort.db --config workspace.yaml --watch

# Main effects + interactions, and ANOVA with predictions for unrun cells
retort report effects --db retort.db --matrix-id 1 --metric code_quality
retort analyze --data results.csv -r code_quality -f language -f model -f tooling --predict

# Score-driven stack maturity, and a promotion gate
retort maturity --db retort.db
retort promote my-stack --from screening --to trial --evidence '{"p_value": 0.05}' --config workspace.yaml
```

Every run's generated source, evaluation findings, scores, and the full SQLite database are archived under `experiment-*/` in the repo — the rankings above are measurements you can re-derive, not opinions.

---

*The combinatorial mess of AI-assisted development is real. Measuring it systematically is the only way out.*
