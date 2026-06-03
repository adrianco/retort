# Retort

**Evaluate the whole stack, not just the model.** Retort applies statistical Design of Experiments (DoE) to measure how AI coding agents actually perform across the variables that decide a real project — **programming language × model version × tooling** — on the tasks you care about. Every run is scored for whether it *provably implements the spec*, plus how fast, how expensive, and how clean.

> **Why not just read a leaderboard?** Sites like **[llm-stats.com](https://llm-stats.com/)** compare many models across many benchmarks — but they hold the *stack* constant and ignore programming language, the surrounding tooling, and time taken. They can't tell you whether Opus 4.8 is worth 5× the cost of 4.6 *in Rust*, whether Sonnet is the better value *for a Go MCP server*, or how long any of it takes. Retort answers exactly that: point it at your languages, models, and tasks (or your own codebase) and it finds the leading stack variant for **your** problem.

---

## Features

- **Factorial / fractional-factorial designs** over `language × model × tooling` (and any factors you add), generated automatically — run the full grid or a quarter-fraction.
- **Isolated playpens** — each run gets a fresh workspace; the agent (`claude -p`) implements the task, then the code is built and tested in place.
- **Scoring that checks the spec, not just the vibes.** Eight built-in scorers (code quality, test coverage, defect rate, maintainability, idiomaticity, token efficiency, …) **plus a conformance gate**:
  - *Mechanical gate* — if the tests don't run, the run **fails** (no proof = no pass).
  - *Spec gate* — an **opus-4.6 second-opinion eval** checks the code against a **pinned requirement checklist** and records `requirement_coverage`; a run passes only if it actually implements the spec. (We found single-pass LLM grading too noisy — haiku swung 0.33↔1.0 on identical code — so the gate uses a fixed checklist + a stronger judge + a two-attempt "second opinion" to kill false failures.)
- **Cross-experiment master database** — `retort aggregate` rolls every experiment into one tidy `master.db` / `master.csv` for analysis as the program grows.
- **ANOVA + effects** — multiplicative ANOVA surfaces which factors actually move each metric.
- **Live monitoring, resumable sharded runs, cost limits** — `retort monitor`, deterministic `--shard N/M`, `--resume` across API usage-limit windows, `cost_limit_usd`.

This repo is the result of running it: **six experiments, ~200 scored runs, two tasks, four Claude models (Sonnet, Opus 4.6 / 4.7 / 4.8), six languages.**

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
  - retort --help loads; test suite passes.
```

It will also offer to install the per-language toolchains and the `claude` / `bd` CLIs when you set up your first experiment.

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

`.devcontainer/` provisions all of this for GitHub Codespaces / VS Code Dev Containers (authenticate `claude` once interactively).

### Run an experiment — describe it in plain language

You don't hand-write `workspace.yaml` or do the factorial math. Open `claude` in the repo and **describe the experiment**; it designs the matrix, checks prerequisites, estimates cost, confirms the decisions that matter, and runs it — every experiment here was built this way:

```text
> I want to compare opus 4.6, 4.7 and 4.8 across six languages on the brazil-bench task

⏺ That's a 3 model × 6 language × 2 tooling = 36-cell factorial, 3 replicates.
  Estimated real API spend + hours of wall-clock. Confirm a few choices:
  · full factorial or a quarter-fraction?   · keep beads tooling or drop it?
  · run now, or set up and stop?
```

Claude then writes the workspace + design, installs toolchains, runs the cells, and reports — watch live with `retort monitor <experiment>`. It handles the messy parts: resuming across usage-limit windows, retrying failures, and flagging cost before spending. You can also drive the CLI directly (`retort init`, `retort run`, `retort monitor`, `retort report effects`, `retort aggregate`).

---

## Recommended leading stack per language

For each language we pick the winning `(model, tooling)` cell by this **priority order**: **requirement coverage → test coverage & pass → speed → cost → code quality** (each a tiebreaker for the one before). Numbers are means across replicates of the fresh opus-4.6 spec-gate re-evaluation. *Speed* = wall-clock seconds, *cost* = USD per run.

### Task: REST API CRUD (a "normal" web-service task)

| Language | Leading stack | ReqCov | TestCov | Speed | Cost |
|---|---|---:|---:|---:|---:|
| clojure | **opus-4.7 / none** | 1.00 | 1.00 | 188 s | $0.92 |
| go | **opus-4.8 / beads** | 1.00 | 0.71 | 161 s | $0.72 |
| java | **opus-4.7 / none** | 1.00 | 1.00 | 168 s | $0.83 |
| python | **opus-4.7 / none** | 1.00 | 1.00 | 84 s | $0.50 |
| rust | **opus-4.6 / beads** | 1.00 | 1.00 | 143 s | $0.48 |
| typescript | **opus-4.8 / none** | 1.00 | 0.97 | 119 s | $0.47 |

On this task most models reach full spec coverage, so the ranking is decided by speed/cost — and **opus-4.7 wins as often as 4.8** (with 4.6 / Sonnet competitive on price).

### Task: Brazilian-Soccer MCP server (a hard, multi-requirement task)

| Language | Leading stack | ReqCov | TestCov | Speed | Cost |
|---|---|---:|---:|---:|---:|
| clojure | **sonnet / beads** | 1.00 | 1.00 | 410 s | $1.03 |
| go | **sonnet / none** | 0.92 | 0.77 | 426 s | $1.18 |
| java | **opus-4.6 / none** | 1.00 | 1.00 | 474 s | $1.73 |
| python | **sonnet / beads** | 1.00 | 0.97 | 483 s | $1.25 |
| rust | **sonnet / none** | 1.00 | 1.00 | 471 s | $1.14 |
| typescript | **sonnet / beads** | 1.00 | 1.00 | 362 s | $0.93 |

On the hard task **Sonnet and Opus-4.6 lead almost everywhere** — not because they're "smarter," but because they reach full requirement coverage at **~$1 and ~7 min**, while Opus 4.7/4.8 cost **~$5 and 12–17 min** for the *same or lower* coverage (see below).

> **The point:** the leading stack is **task- and language-dependent**. A single leaderboard rank can't produce these tables — you have to run the variants.

---

## Model comparison (controlled, within-experiment)

Each block is the same cells run with two models, so it's apples-to-apples.

| Experiment | Model | ReqCov | TestCov | Speed | Cost/run |
|---|---|---:|---:|---:|---:|
| **exp-6** REST-API | opus-4.7 | **1.00** | 0.93 | **165 s** | **$0.85** |
| | opus-4.8 | 1.00 | 0.94 | 243 s | $0.96 |
| **exp-5** Brazil | opus-4.7 | 0.67 | 0.93 | **706 s** | **$4.57** |
| | opus-4.8 | **0.85** | 0.90 | 1039 s | $5.60 |
| **exp-3** Brazil | opus-4.6 | 0.98 | 0.95 | **443 s** | **$1.46** |
| | opus-4.7 | 1.00 | 0.81 | 1385 s | $8.13 |
| **exp-1** REST-API | opus-4.6 | **0.82** | **0.87** | 136 s | $0.45 |
| | sonnet | 0.82 | 0.76 | 178 s | **$0.37** |

**What we learned:**

1. **Newer is slower and far more expensive — and not reliably more accurate.** Across generations the cost and wall-clock climb sharply (Brazil: 4.6 ≈ $1.5 → 4.7 ≈ $8 → 4.8 ≈ $5.6). On the easy task 4.7 and 4.8 are **tied at ~1.0 coverage**, so paying for 4.8 buys nothing. On the hard task 4.8 *does* beat 4.7 on coverage (0.85 vs 0.67) — but both are ~$5/run and 12–17 min, while **Opus-4.6 hits 0.98 coverage for $1.46**.
2. **Passing tests ≠ meeting the spec.** Brazil/opus-4.7 has **test coverage 0.93 but requirement coverage 0.67** — it writes green tests for a half-built feature. Mechanical scorers (and the old single-pass eval) missed this; the spec gate is what surfaces it.
3. **Sonnet is the value play on hard tasks** — full coverage at ~$1 where the newest Opus models cost ~$5.
4. **Tooling (`beads`) rarely helps** these single-shot tasks: across the program it added ~30% wall-clock and ~10–20% cost with no quality gain, so it was dropped from later experiments. (It targets multi-step coordination these tasks don't exercise.)
5. **Language dominates code quality.** ANOVA across experiments finds `code_quality` driven almost entirely by *language*, not model — Java/Go/Rust score high regardless of model; the model mostly moves cost, speed, and spec coverage.

---

## The experiments

| # | Task | Models | Design | Covered runs | Headline |
|---|---|---|---|---:|---|
| **1** | REST-API CRUD | Opus-4.6, Sonnet | 6 lang × 2 model × 2 tooling | 56 | Opus-4.6 ≈ Sonnet on coverage; Java/Go/Rust sweep quality; Python tooling-sensitive |
| **2** | Brazil MCP | Opus-4.6, Sonnet | 6 lang × 2 model | 22 | Hard task; Opus-4.6 higher requirement coverage, Sonnet cleaner/cheaper |
| **3** | Brazil MCP | Opus-4.6, 4.7 | quarter-fraction | 7 | 4.7 marginally higher coverage but **3× slower, 5.5× pricier** than 4.6 |
| **4** | Brazil MCP | Opus-4.8 | 3 lang | 6 | First 4.8 data; full coverage but slowest/priciest of all |
| **5** | Brazil MCP | Opus-4.7, 4.8 | 6 lang × 2 model, full factorial | 36 | **4.8 > 4.7 on coverage (0.85 vs 0.67), +47% time/cost**; both expensive |
| **6** | REST-API CRUD | Opus-4.7, 4.8 | 6 lang × 2 model, full factorial | 71 | Accuracy **tied at ~1.0**; 4.7 the better value (faster, cheaper) |

All run data — per-run source, tests, scores, and the spec-eval output — is committed under `experiment-N/runs/`, with the combined results in `master.db` / `master.csv` (`retort aggregate`).

### Methodology notes
- **Coverable runs only:** of ~260 archived runs, **198** are completed runs with a fresh `requirement_coverage`; the rest failed (tests didn't run) or are duplicate shard casualties.
- **The spec gate** reads a pinned `REQUIREMENTS.json` per task (a fixed checklist, so the denominator is constant across runs) and judges with **opus-4.6**, taking a second opinion before failing a run — making `requirement_coverage` reproducible where single-pass haiku grading was not.
- **Honest confounds:** the cross-experiment model means mix different language/tooling sets, so the *controlled within-experiment* table above is the defensible basis for model-version claims.

---

## Status: 1.0 beta

Feature-complete for single-agent `claude-code` experiments with the `LocalRunner`. **Implemented:** `LocalRunner`, all built-in scorers + the conformance spec gate, factorial/fractional design generation, ANOVA + effects, SQLite storage + cross-experiment `aggregate`, resumable sharded runs, parallel bulk re-evaluation, `retort monitor`, `cost_limit_usd`. **Not yet:** `DockerRunner` (skeleton), agents other than `claude-code`, the `intake`/`scheduler` paths.
