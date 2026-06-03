# Retort

**Evaluate the whole stack, not just the model.** Retort applies statistical Design of Experiments (DoE) to measure how AI coding agents actually perform across the variables that decide a real project — **programming language × model version × tooling** — on the tasks you care about. Every run is scored for whether it *provably implements the spec*, plus how fast, how expensive, and how clean.

> **Why not just read a leaderboard?** Sites like **[llm-stats.com](https://llm-stats.com/)** compare many models across many benchmarks — but they hold the *stack* constant and ignore programming language, the surrounding tooling, and time taken. They can't tell you whether Opus 4.8 is worth 4× the cost of 4.6 *in Rust*, how reliably each model gets a Go MCP server completely right, or how long any of it takes. Retort answers exactly that: point it at your languages, models, and tasks (or your own codebase) and it finds the leading stack variant for **your** problem.

---

## Features

- **Factorial / fractional-factorial designs** over `language × model × tooling` (and any factors you add), generated automatically — run the full grid or a quarter-fraction.
- **Isolated playpens** — each run gets a fresh workspace; the agent (`claude -p`) implements the task, then the code is built and tested in place.
- **Scoring that checks the spec, not just the vibes.** Eight built-in scorers (code quality, test coverage, defect rate, maintainability, idiomaticity, token efficiency, …) **plus a conformance gate**:
  - *Mechanical gate* — if the tests don't run, the run **fails** (no proof = no pass).
  - *Spec gate* — an **opus-4.6 second-opinion eval** checks the code against a **pinned requirement checklist** and records `requirement_coverage`; a run passes only if it implements the *whole* spec. (Single-pass LLM grading proved too noisy — haiku swung 0.33↔1.0 on identical code — so the gate uses a fixed checklist + a stronger judge + a two-attempt "second opinion" to kill false failures.)
- **Cross-experiment master database** — `retort aggregate` rolls every experiment into one tidy `master.db` / `master.csv`.
- **ANOVA + effects**, **live `retort monitor`**, resumable sharded runs, `cost_limit_usd`.

This repo is the result of running it: **six experiments, 198 scored runs, two tasks, four Claude models (Sonnet, Opus 4.6 / 4.7 / 4.8), six languages.**

---

## Install

### The easy way: ask Claude Code

Retort has a couple of environment gotchas (Python ≥ 3.11; `OApackage` is a C++ extension built with `cmake`). The fastest install is to let Claude Code handle them — point it at a directory and ask:

```text
$ cd Documents/GitHub
$ claude
> clone and install https://github.com/adrianco/retort here

⏺ Done. Retort is cloned and installed, and all tests pass.
  - Installed cmake (Homebrew) — needed to build OApackage (C++ extension, no wheel here).
  - Created a virtualenv with Python 3.12 at retort/.venv.
  - Ran pip install -e ".[dev,test]" — built retort + oapackage from source.
```

### By hand

```bash
git clone https://github.com/adrianco/retort.git
cd retort
pip install -e ".[dev,test]"     # Python deps + builds OApackage (needs cmake)
retort --help                    # CLI loads → deps OK
```

| Also needed | Why |
|---|---|
| **Python 3.11+**, **C/C++ toolchain + cmake** | runtime + building `OApackage` |
| **`claude` CLI, authenticated** | the agent runner shells out to `claude -p …` |
| **Per-language toolchains** | the scorer builds & tests the generated code (`go`, `rustup`, `node`≥20, JDK+maven, clojure, python) |
| **`bd` (beads) CLI** | only if a factor uses `tooling: beads` |

`.devcontainer/` provisions all of this for Codespaces / Dev Containers (authenticate `claude` once).

### Run an experiment — describe it in plain language

You don't hand-write `workspace.yaml` or do the factorial math. Open `claude` in the repo and **describe the experiment**; it designs the matrix, checks prerequisites, estimates cost, confirms the decisions that matter, and runs it — every experiment here was built this way:

```text
> compare opus 4.6, 4.7 and 4.8 across six languages on the brazil-bench task

⏺ That's a 3 model × 6 language × 2 tooling = 36-cell factorial, 3 replicates.
  Estimated real API spend + hours of wall-clock. Confirm a few choices:
  · full factorial or a quarter-fraction?   · keep beads tooling or drop it?   · run now, or set up and stop?
```

Claude then writes the workspace + design, installs toolchains, runs the cells (resuming across usage-limit windows, retrying failures, flagging cost), and reports — watch live with `retort monitor <experiment>`. You can also drive the CLI directly (`retort init/run/monitor/report/aggregate`).

---

## What the data says

The headline metric is **pass-proportion**: with N replicates of a stack, the fraction whose runs *fully implement the spec* (`requirement_coverage == 1.0`, a gate pass). Read it as **the probability that a single run of that stack comes out completely correct** — 3/3 → 1.00, 2/3 → 0.66, 1/3 → 0.33. A single sub-1.0 run is a fail.

### Model reliability vs. cost (the main result)

Aggregated per model per task (larger samples → robust):

| Model | Brazil MCP (hard) | REST-API (easy) | Speed¹ | Cost/run¹ |
|---|---:|---:|---:|---:|
| opus-4.6 | 0.47 | 0.59 | 309 s | $1.30 |
| sonnet | 0.50 | 0.63 | 440 s | $1.10 |
| opus-4.7 | 0.85 | **1.00** | 774 s | $4.92 |
| **opus-4.8** | **1.00** | **1.00** | 1035 s | $5.54 |

¹ Brazil task. **Pass-proportion = fraction of that model's runs that fully implement the spec.**

- **Newer *is* more reliable — markedly so on hard tasks.** Opus-4.8 produces a completely-correct result **100% of the time on both tasks**; 4.7 is 85% / 100%. The cheaper models (4.6, Sonnet) get the *hard* task completely right only **~half the time** — they're a coin-flip.
- **You pay steeply for that reliability.** On the hard task Opus-4.8 is **~3× slower and ~4× pricier** than 4.6 / Sonnet.
- **Opus-4.7 is the value-reliability sweet spot** — near-4.8 reliability for less, and **tied with 4.8 on the easy task**, where paying for 4.8 buys nothing.
- **On easy tasks, almost anything works**, so the cheapest reliable model wins (often 4.7 or even 4.6).
- **It's a reliability-vs-cost decision, and it's task-dependent** — precisely what a leaderboard can't tell you.

### Recommended leading stack per language

Best `(model, tooling)` per language, ranked **pass-proportion → test coverage → speed → cost → code quality**. Pass shown as `passes/replicates`.

**REST-API CRUD** (n = 3 per cell — robust): most models reach full coverage, so the cheapest reliable stack wins.

| Language | Leading stack | Pass | Speed | Cost |
|---|---|---:|---:|---:|
| clojure | opus-4.7 / none | 3/3 | 188 s | $0.92 |
| go | opus-4.8 / beads | 3/3 | 161 s | $0.72 |
| java | opus-4.7 / none | 3/3 | 168 s | $0.83 |
| python | opus-4.7 / none | 3/3 | 84 s | $0.50 |
| rust | opus-4.6 / beads | 3/3 | 143 s | $0.48 |
| typescript | opus-4.8 / none | 3/3 | 119 s | $0.47 |

**Brazil MCP** (hard task; per-cell replication is thinner, so treat the model-level result above as the firmer guide): the only model that is reliable across *every* language here is **opus-4.8** (1.00) — at the cost/speed premium shown. The cheaper models succeed on some languages and fail on others, which is the whole point of measuring per-language rather than trusting one rank.

---

## The experiments

Each row links to its **full per-cell results table** (every language × model × tooling, with pass-proportion, speed, cost, and quality, generated from `master.db`).

| # | Task | Models | Covered | Results table | Headline (clean data) |
|---|---|---|---:|---|---|
| 1 | REST-API | Opus-4.6, Sonnet | 56 | **[results →](experiment-1/results.md)** | Both ~0.6 reliable; Java/Go/Rust strongest; cheap but not certain |
| 2 | Brazil | Opus-4.6, Sonnet | 22 | **[results →](experiment-2/results.md)** | Hard task exposes them — only ~half of runs fully correct |
| 3 | Brazil | Opus-4.6, 4.7 | 7 | **[results →](experiment-3/results.md)** | 4.7 more reliable but **3× slower, 5.5× pricier** |
| 4 | Brazil | Opus-4.8 | 6 | **[results →](experiment-4/results.md)** | First 4.8 data: fully correct, but slowest/priciest |
| 5 | Brazil | Opus-4.7, 4.8 | 36 | **[results →](experiment-5/results.md)** | **4.8 = 1.00 pass vs 4.7 = 0.85**, +47% time/cost |
| 6 | REST-API | Opus-4.7, 4.8 | 71 | **[results →](experiment-6/results.md)** | Both 1.00 — 4.7 the better value, 4.8 is overkill |

The combined dataset across all six is in [`master.csv`](master.csv) (and `master.db`), rebuildable with `retort aggregate`.

All run data — per-run source, tests, scores, and the spec-eval output — is committed under `experiment-N/runs/`, combined in `master.db` / `master.csv` (`retort aggregate`).

**Methodology notes.** Of ~260 archived runs, **198** are completed runs with a reproducible `requirement_coverage` (the rest failed the tests-gate or are shard duplicates). The spec gate reads a pinned `REQUIREMENTS.json` per task (constant denominator) and judges with **opus-4.6** + a second opinion. Cross-experiment model means mix language/tooling sets, so per-model conclusions lean on the larger within-task samples.

---

## Status: 1.0 beta

Feature-complete for single-agent `claude-code` experiments with the `LocalRunner`. **Implemented:** `LocalRunner`, all scorers + the conformance spec gate, factorial/fractional design generation, ANOVA + effects, SQLite storage + cross-experiment `aggregate`/`reevaluate`, resumable sharded runs, `retort monitor`, `cost_limit_usd`, OMP local-agent profiles. **Not yet:** `DockerRunner` (skeleton), agents other than `claude-code`, the `intake`/`scheduler` paths.
