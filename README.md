# Retort

**Evaluate the whole stack, not just the model.** Retort applies statistical Design of Experiments (DoE) to measure how AI coding agents actually perform across the variables that decide a real project — **programming language × model version × tooling** — on the tasks you care about. Every run is scored for whether it *provably implements the spec*, plus how fast, how expensive, and how clean.

> **Why not just read a leaderboard?** Sites like **[llm-stats.com](https://llm-stats.com/)** compare many models across many benchmarks — but they hold the *stack* constant and ignore programming language, the surrounding tooling, and time taken. They can't tell you whether Opus 4.8 is worth 4× the cost of 4.6 *in Rust*, how reliably each model gets a Go MCP server completely right, or how long any of it takes. Retort answers exactly that: point it at your languages, models, and tasks (or your own codebase) and it finds the leading stack variant for **your** problem.

---

## Features

- **Factorial / fractional-factorial designs** over `language × model × tooling` (and any factors you add), generated automatically — run the full grid or a quarter-fraction.
- **Isolated playpens** — each run gets a fresh workspace; the agent (`claude -p`) implements the task, then the code is built and tested in place.
- **Scoring that checks the spec, not just the vibes.** Eight built-in scorers (code quality, test coverage, defect rate, maintainability, idiomaticity, token efficiency, …) **plus a conformance gate**:
  - *Mechanical gate* — if the tests don't run, the run **fails** (no proof = no pass).
  - *Spec gate* — a **second-opinion LLM eval** (the judge defaults to the **latest** Claude model, tracking new releases) checks the code against a **pinned requirement checklist** and records `requirement_coverage`; a run passes only if it implements the *whole* spec. (Single-pass LLM grading proved too noisy — haiku swung 0.33↔1.0 on identical code — so the gate uses a fixed checklist + a stronger judge + a two-attempt "second opinion" to kill false failures.) The eval **self-checks**: `reevaluate` preflights the judge and errors instead of silently grading nothing.
- **`retort diagnose`** — re-tests every *failed* run's archive and classifies it **TOOLING** (a scorer false-failure that `rescore` recovers) vs **GENUINE** (a real model/spec failure), with the cause. So you never have to hand-investigate a failure.
- **Cross-experiment master database** — `retort aggregate` rolls every experiment into one tidy `master.db` / `master.csv`.
- **ANOVA + effects**, **live `retort monitor`** (shows in-flight runs across parallel shards), resumable sharded runs, `cost_limit_usd`.

This repo is the result of running it: **ten experiments across two tasks and eight languages (Go, Python, Clojure, Rust, Java, TypeScript, Erlang, Elixir), four Claude models (Sonnet, Opus 4.6 / 4.7 / 4.8) plus Opus-4.8 fast mode, the next-tier Claude Fable 5, a Gemini cross-agent scaffold, and a prompt / test-methodology study (BDD / TDD / ATDD).**

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
| **Per-language toolchains** | the scorer **builds, tests, and lints** the generated code — see the table below |
| **`bd` (beads) CLI** | only if a factor uses `tooling: beads` |
| **`gemini` CLI** / **`omp` (oh-my-pi) CLI** | only to run non-Claude agents — Google Gemini, or local/other models via [oh-my-pi](https://github.com/can1357/oh-my-pi); see [Comparing coding agents](#comparing-coding-agents-eg-claude-vs-gemini) |

`.devcontainer/` provisions all of this for Codespaces / Dev Containers (authenticate `claude` once).

### Per-language build & test toolchains

You only need the toolchains for the languages you actually list as `language`
factor levels in `workspace.yaml`. The scorer **shells out to each language's
real build/test/lint tools**, so they must be on `PATH` — if a tool is missing
the run fails its mechanical gate (tests can't run = no pass). Install exactly
what you use:

| Language | Tools the scorer runs | macOS (Homebrew) | Debian/Ubuntu |
|---|---|---|---|
| **python** | `pytest`, `coverage`, `ruff` | (bundled via `pip install -e ".[dev,test]"`) | (bundled via the pip extras) |
| **typescript** | `node` ≥20 + `npm` (`npx` pulls `jest`/`vitest`, `tsc`, `eslint` per project) | `brew install node` | `apt install nodejs npm` (or NodeSource for ≥20) |
| **go** | `go test -cover`, `go vet` | `brew install go` | `apt install golang-go` |
| **rust** | `cargo test`, `cargo clippy` | `brew install rustup-init && rustup-init -y` | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| | then add the linter: | `rustup component add clippy` | `rustup component add clippy` |
| **java** | `mvn test`, `jacoco`, `mvn compile` (JDK 17+) | `brew install openjdk maven` | `apt install default-jdk maven` |
| **clojure** | `clojure -M:test` **and** `lein test`, `cloverage`, `clj-kondo` | `brew install clojure/tools/clojure leiningen borkdude/brew/clj-kondo` | clojure CLI + `lein` via the [official](https://clojure.org/guides/install_clojure) [scripts](https://leiningen.org/#install); `clj-kondo` from its [releases](https://github.com/clj-kondo/clj-kondo/releases) |
| **erlang** | `rebar3 eunit` **and** `rebar3 ct`, `rebar3 compile` | `brew install erlang rebar3` | `apt install erlang rebar3` |
| **elixir** | `mix test`, `mix compile --all-warnings` (pulls Erlang/OTP) | `brew install elixir` | `apt install elixir` |

> ⚠️ **Clojure needs *both* the Clojure CLI (`clojure`/`clj`) and Leiningen
> (`lein`)** — agents pick either a `deps.edn` or a `project.clj` layout, and the
> scorer runs whichever the generated project uses. **Erlang needs `rebar3`**
> (for both EUnit and Common Test suites); **Elixir needs `mix`** (ships with
> Elixir). Java/Clojure/Erlang/Elixir all need a **JDK/BEAM** on `PATH`. A
> missing one of these is the single most common "why did every run of language
> X fail?" — verify with `lein test`, `rebar3 --version`, `mix --version`, etc.
> before launching an experiment.

### Run an experiment — describe it in plain language

You don't hand-write `workspace.yaml` or do the factorial math. Open `claude` in the repo and **describe the experiment**; it designs the matrix, checks prerequisites, estimates cost, confirms the decisions that matter, and runs it — every experiment here was built this way:

```text
> compare opus 4.6, 4.7 and 4.8 across six languages on the brazil-bench task

⏺ That's a 3 model × 6 language × 2 tooling = 36-cell factorial, 3 replicates.
  Estimated real API spend + hours of wall-clock. Confirm a few choices:
  · full factorial or a quarter-fraction?   · keep beads tooling or drop it?   · run now, or set up and stop?
```

Claude then writes the workspace + design, installs toolchains, runs the cells (resuming across usage-limit windows, retrying failures, flagging cost), and reports — watch live with `retort monitor <experiment>`. You can also drive the CLI directly (`retort init/run/monitor/report/aggregate`).

**Task sources.** A task is what the agent builds (`task.yaml` + optional `validate.py`). [`tasks/registry.yaml`](tasks/registry.yaml) indexes tasks by name → a canonical **source**: bundled in this repo (`bundled://`) or hosted in a git/GitHub repo (`github://`). List them with `retort tasks list`, and reference one by bare name (`--task brazil-bench`) or explicit URI. See [`tasks/README.md`](tasks/README.md) to add your own.

---

## What the data says

> 📝 For the narrative walkthrough of these findings — the reliability-vs-cost story, fast mode, the BEAM languages, and the measurement bugs along the way — see the companion **[model blog](model-blog.md)** (updated as new models arrive). The **[prompt blog](prompt-blog.md)** covers the separate question of whether the *prompt* — specifically the prescribed test methodology (BDD / TDD / ATDD vs none) — moves reliability.

The headline metric is **pass-proportion**: with N replicates of a stack, the fraction whose runs *fully implement the spec* (`requirement_coverage == 1.0`, a gate pass). Read it as **the probability that a single run of that stack comes out completely correct** — 3/3 → 1.00, 2/3 → 0.66, 1/3 → 0.33. A single sub-1.0 run is a fail.

### Model reliability vs. cost (the main result)

The whole landscape, cloud frontier down to a local laptop stack (**pass-proportion = fraction of runs that fully implement the spec**), newest additions (local, $0) in bold at the bottom:

| Model | Serving | Brazil MCP (hard) | REST-API (easy) | Cost/run¹ |
|---|---|---:|---:|---:|
| **opus-4.8** | cloud | **1.00** | **1.00** | $5.54 |
| opus-4.7 | cloud | 0.85 | **1.00** | $4.92 |
| sonnet-5 ⁴ *(newest cloud)* | cloud | 0.93 | **1.00** | $7.64 |
| fable-5³ | cloud | **1.00** | **1.00** | $8.98 |
| opus-4.8-fast² | cloud | **1.00** | **1.00** | $8.72 |
| sonnet 4.6 | cloud | 0.50 | 0.63 | $1.10 |
| opus-4.6 | cloud | 0.47 | 0.59 | $1.30 |
| **Qwen3.6-35B-A3B** ⁵ *(best local)* | **local · $0** | — | **0.38** | **$0** |
| **Qwen3-Coder-Next-80B-A3B** ⁷ *(bigger ≠ better)* | **local · $0** | — | 0.33 | **$0** |
| **Qwen3-Coder-30B-A3B** ⁶ | **local · $0** | — | **0.33** | **$0** |
| **Devstral-24B** ⁸ *(agent-tuned, wrong harness)* | **local · $0** | — | 0.17 | **$0** |

¹ Cost on the Brazil (hard) task for cloud; local inference is $0. **Pass-proportion = fraction of that model's runs that fully implement the spec.**
² Fast mode (`/fast`), 4 languages (clojure/go/python/rust). Cost is at fast mode's **2× per-token rate** ([announcement](https://www.anthropic.com/news/claude-opus-4-8)) — see [Fast mode](#fast-mode-speed-for-a-2x-price-premium).
³ Claude Fable 5 (`claude-fable-5`), same 4 languages. A **distinct model a tier above Opus 4.8**, priced at the same **$10/$50 per Mtok** rate as fast mode; the CLI prices it natively. See [exp-10 results](experiment-10/results.md).
⁴ Claude Sonnet 5 (exp-15). Only Sonnet 5 was newly run; every other cloud row is read from the accumulated `master.db` — the incremental design.
⁵ **Qwen3.6-35B-A3B** on an **M5/64 GB laptop** (MLX via oMLX, Hermes agent), REST-API easy task, four mainstream languages. Across **all nine** languages it drops to **0.11** — the niche-language wall (Clojure/Java/C#/Elixir/Erlang all fail); a default self-repair second chance lifts that to **0.22**, mainstream only. First local stack to crack TypeScript. Exp 16–21.
⁶ **Qwen3-Coder-30B-A3B** via llama.cpp — **0.08** at a 32 K context, **0.33** at 128 K: context is the first-order lever for a local model.
⁷ **Qwen3-Coder-Next-80B-A3B** (exp-22, same stack as the 35B). Doubling the model *lowered* first-try reliability (0.33 vs the 35B's 0.50) — slower and more prone to never terminating. Bigger ≠ better on this task.
⁸ **Devstral-24B** (exp-23), smaller but agent-tuned, served via **llama.cpp** (oMLX can't parse its Mistral tool format). Lowest local result (0.17), 7/12 non-terminating — but tuned for OpenHands, not Hermes, so it's on the wrong harness. Neither bigger nor agent-tuned beat the general 35B.

- **Newer *is* more reliable — markedly so on hard tasks.** Opus-4.8 produces a completely-correct result **100% of the time on both tasks**; 4.7 is 85% / 100%. The cheaper models (4.6, Sonnet) get the *hard* task completely right only **~half the time** — they're a coin-flip.
- **You pay steeply for that reliability.** On the hard task Opus-4.8 is **~3× slower and ~4× pricier** than 4.6 / Sonnet.
- **Opus-4.7 is the value-reliability sweet spot** — near-4.8 reliability for less, and **tied with 4.8 on the easy task**, where paying for 4.8 buys nothing.
- **Fast mode is the same reliability at the highest price.** Opus-4.8 fast matches 4.8's 1.00/1.00 and shaves wall-clock, but its 2× per-token rate makes it one of the **costliest rows here** ($8.72/run on the hard task) — you're buying latency, not value.
- **A tier *above* 4.8 buys no extra reliability either.** Claude Fable 5 — a distinct model above Opus 4.8, at the same $10/$50 rate as fast mode — also lands at **1.00 / 1.00**, matching 4.8 exactly. But where 4.8 is already perfect there is no headroom to buy: Fable 5 is the **priciest *and* slowest** option on the hard task ($8.98, 1039 s), with no measurable reliability gain. Paying up a tier is pure overhead until a task is hard enough that 4.8 itself drops below 1.00 — neither task here reaches that.
- **On easy tasks, almost anything works**, so the cheapest reliable model wins (often 4.7 or even 4.6).
- **It's a reliability-vs-cost decision, and it's task-dependent** — precisely what a leaderboard can't tell you.
- **A local model on a laptop is about a third of the way to the frontier — for free, and only in the languages it knows.** The best local stack (Qwen3.6-35B, MLX + Hermes on an M5) reaches **0.38** on the easy task's mainstream languages ($0/run) but **0.11 across all nine** — Clojure/Java/C#/Elixir/Erlang are a hard capability wall no agent/context/serving upgrade moves. Context size was the biggest lever (0.08→0.33). A default self-repair second chance (any model, half credit) lifts local to 0.22, but only within the mainstream. See exp 16–21 and the [model blog](model-blog.md).

### Recommended leading stack per language

Best `(model, tooling)` per language, ranked **pass-proportion → test coverage → speed → cost → code quality**. Pass shown as `passes/replicates`.

**REST-API CRUD** (n = 3 per cell — robust): most stacks reach full coverage, so the ranking is decided by the speed tiebreaker (and cost only after that).

| Language | Leading stack | Pass | TestCov | Speed | Cost |
|---|---|---:|---:|---:|---:|
| clojure | opus-4.7 / none | 3/3 | 1.00 | 188 s | $0.92 |
| go | opus-4.8 / beads | 3/3 | 0.71 | 161 s | $0.72 |
| java | opus-4.7 / none | 3/3 | 1.00 | 168 s | $0.83 |
| python | opus-4.7 / none | 3/3 | 1.00 | 84 s | $0.50 |
| rust | **opus-4.8-fast** / none | 3/3 | 1.00 | 135 s | $1.06 |
| typescript | opus-4.8 / none | 3/3 | 0.97 | 119 s | $0.47 |
| erlang | opus-4.8 / none | 3/3 | 1.00 | 345 s | $1.35 |
| elixir | opus-4.8 / none | 3/3 | 1.00 | 207 s | $0.85 |

> ⚠️ **Fast mode and the speed-before-cost ordering.** Because the ranking weights *speed* above *cost*, **fast mode is the ranked winner for Rust** — but only by an 8-second margin (135 s vs 143 s for `opus-4.6/beads`, the runner-up) at **more than 2× the price** ($1.06 vs $0.48, at fast mode's 2× rate). Fast mode is also the close runner-up for Clojure and Go: always a touch faster, always pricier. **If you weight cost at all, prefer the non-fast pick** — fast mode's speed edge on routine work rarely justifies double the bill. (See [Fast mode](#fast-mode-speed-for-a-2x-price-premium).)

**Brazil MCP** (hard task; per-cell replication is thinner, so treat the model-level result above as the firmer guide): the only model that is reliable across *every* language here is **opus-4.8** (1.00) — at the cost/speed premium shown. The cheaper models succeed on some languages and fail on others, which is the whole point of measuring per-language rather than trusting one rank. **Fast mode is *not* a leading pick here**: on the hard task it matched 4.8's 1.00 reliability but, at the 2× rate, cost roughly double (~$8.70 vs ~$4.85/run on the shared languages) *without* being reliably faster — speeding up token output doesn't help a reasoning-bound task. Regular opus-4.8 dominates fast mode on Brazil.

### Results by language × task

Aggregated across all models and tooling for each language on each task (Pass = pass-proportion = probability of a completely-correct run):

| Language | Task | n | Pass | CodeQual | TestCov | Speed (s) | Cost ($) |
|---|---|---:|---:|---:|---:|---:|---:|
| clojure | Brazil MCP (hard) | 12 | 0.75 | 0.83 | 1.00 | 715 | 3.51 |
| clojure | REST-API (easy) | 21 | 0.62 | 0.75 | 0.90 | 302 | 1.10 |
| go | Brazil MCP (hard) | 13 | 0.69 | 1.00 | 0.58 | 773 | 4.35 |
| go | REST-API (easy) | 20 | 1.00 | 1.00 | 0.67 | 142 | 0.61 |
| java | Brazil MCP (hard) | 10 | 0.80 | 1.00 | 1.00 | 784 | 4.03 |
| java | REST-API (easy) | 23 | 0.52 | 1.00 | 1.00 | 208 | 0.78 |
| python | Brazil MCP (hard) | 14 | 0.86 | 0.73 | 0.90 | 638 | 3.30 |
| python | REST-API (easy) | 20 | 0.90 | 0.65 | 0.80 | 97 | 0.43 |
| rust | Brazil MCP (hard) | 10 | 0.50 | 0.83 | 0.93 | 717 | 3.97 |
| rust | REST-API (easy) | 23 | 0.96 | 0.83 | 1.00 | 169 | 0.60 |
| typescript | Brazil MCP (hard) | 12 | 0.92 | 0.61 | 0.82 | 617 | 3.31 |
| typescript | REST-API (easy) | 20 | 1.00 | 0.73 | 0.89 | 168 | 0.56 |
| **erlang** | REST-API (easy) | 6 | **1.00** | **1.00** | **1.00** | 349 | 1.49 |
| **elixir** | REST-API (easy) | 6 | **1.00** | **1.00** | **1.00** | 271 | 1.32 |

Reliability swings hard by **both** axes: **Rust** is near-perfect on the easy task (0.96) but a coin-flip on the hard one (0.50); **Java** runs the other way (0.80 hard / 0.52 easy); **TypeScript** and **Python** are strong on both. Code quality, by contrast, is steady within a language across tasks (consistent with the ANOVA below) — Go and Java stay at 1.00 regardless. *There is no single "best language"; it depends on the job.*

The two **BEAM languages** (Erlang, Elixir — exp-8, opus-4.7/4.8 on the REST API) are a clean addition: **1.00 on every measure** — pass-proportion, test coverage, *and* code quality — making them the most consistently solid stacks on the easy task. Elixir on opus-4.8 was the cheapest/fastest of the pair (207 s, $0.85/run).

### Fast mode: speed for a 2× price premium

Opus-4.8 has a **fast mode** (the `/fast` toggle — same model, faster token output). Crucially, it is billed at **2× the standard per-token rate** — $10/$50 vs $5/$25 per million input/output tokens, per the [Opus 4.8 announcement](https://www.anthropic.com/news/claude-opus-4-8). (The Claude CLI's reported `total_cost_usd` computes at the *standard* rate, so retort now scales fast-mode runs by 2× to record the cost you're actually billed — the figures below are corrected.) Experiment 7 ran it on the same languages as the regular-4.8 baseline (exp-5/6), both tasks:

| Task | Language | Fast 4.8 (speed / cost) | Regular 4.8 (speed / cost) | Pass (both) |
|---|---|---:|---:|:--:|
| REST-API (easy) | clojure | **208 s** / $1.37 | 508 s / $1.92 | 1.00 |
| REST-API (easy) | go | **140 s** / $1.17 | 147 s / $0.66 | 1.00 |
| REST-API (easy) | python | **90 s** / $0.74 | 122 s / $0.50 | 1.00 |
| REST-API (easy) | rust | **135 s** / $1.06 | 185 s / $0.71 | 1.00 |
| Brazil (hard) | clojure | 712 s / $6.18 | 941 s / $4.58 | 1.00 |
| Brazil (hard) | go | 959 s / $9.90 | 867 s / $4.59 | 1.00 |
| Brazil (hard) | python | 967 s / $9.91 | 899 s / $5.10 | 1.00 |
| Brazil (hard) | rust | 909 s / $8.90 | 1081 s / $6.09 | 1.00 |

- **Reliability is identical** — every fast cell holds pass-proportion 1.00, same as regular 4.8. Fast mode costs you nothing in correctness.
- **But it is *more* expensive, not cheaper.** At 2× per token it runs ~50–75% pricier than regular 4.8 on most easy-task languages (the lone exception, clojure, is an artifact of an outlier 508 s regular run), and roughly **2× the cost on the hard task**.
- **And the speedup only shows up on easy work.** On the REST API fast mode is ~20–40% faster in wall-clock; on the hard, reasoning-bound task it's **not reliably faster at all** (Go and Python fast runs were actually *slower* than regular) — because the bottleneck is the model thinking, not emitting tokens.
- **Takeaway:** fast mode buys **latency, not savings**. It's worth the 2× premium only when wall-clock turnaround on routine work matters more than the bill. On hard tasks you pay double for no speed gain — don't.

### Does the prompt matter? Test methodology (neutral / TDD / ATDD)

Every experiment above held the *prompt* constant. Experiment-13 varies it — the
prescribed **test methodology** — on a methodology-neutral fork of the hard task
(BDD stripped from the repo, so the discipline comes only from the prompt):
`language[go, python] × model[sonnet, opus-4.8-fast] × prompt[neutral, TDD, ATDD]`,
3 replicates. Pass-proportion (`requirement_coverage == 1.0`):

| model | language | BDD | neutral | TDD | ATDD |
|---|---|:--:|:--:|:--:|:--:|
| opus-4.8-fast | go | 1.00 | 1.00 | 1.00 | 1.00 |
| opus-4.8-fast | python | 1.00 | 1.00 | 1.00 | 1.00 |
| sonnet | go | 1.00 | 1.00 | 1.00 | **0.33** |
| sonnet | python | 1.00 | 1.00 | 1.00 | 1.00 |

(BDD folded in from the original brazil-bench runs — BDD prescribed in-repo —
re-graded on the same judge; opus-4.8-fast n=3, sonnet n=1.)

- **Prescribing a methodology barely moves reliability** on a task the model
  already understands — 15 of 16 cells pass regardless; BDD, TDD and neutral are
  interchangeable. The lone drop is **ATDD on the weakest stack (sonnet + go)**:
  ATDD front-loads the most work
  (executable acceptance tests through the public interface first), and the
  cheaper model on the stricter language occasionally didn't finish the spec.
- **The methodology shows up in *what tests get written*, not whether it ships.**
  ATDD yields lower unit-statement coverage (acceptance-test focused) than
  TDD/neutral, yet still meets the spec everywhere except sonnet/go. Pick a
  methodology for the tests it leaves behind, not for a reliability boost.
- Cost tracks the model, not the methodology. Full write-up:
  **[prompt blog](prompt-blog.md)** · [exp-13 results](experiment-13/results.md).
  (BDD, the fourth arm, needs its baselines re-scored on the same footing before
  a fair comparison — the recommended follow-up.)

---

## Factor analysis (ANOVA): what actually moves each metric

The point of a designed experiment is that you can *decompose* the variance — for each response, how much is explained by language vs. model vs. tooling, and is it significant. Type-II ANOVA on the balanced experiments (cost/duration log-transformed, since they scale multiplicatively) gives a strikingly clean separation of concerns:

| Response | Dominant factor (share of variance) | What it means |
|---|---|---|
| **code_quality** | **language ≈ 94–96%** (p < 10⁻⁴⁰) · model ~0% (n.s.) | Quality is the *language's*, not the model's. Java/Go/Rust score high whoever writes the code. |
| **test_coverage** | **language ≈ 92–95%** (p < 10⁻¹⁵) · model ~0% | Same story — the language (and its test ecosystem) dominates. |
| **duration** | **task ≈ 75%**; then *model* on a fixed hard task (37% in exp-5); language ~6% | The task sets the clock; on hard tasks the **newer model is the one that's slower**. |
| **cost** | **task ≈ 82%**; **tooling +10%** (p < 0.001); language ~4% | The task sets the bill; `beads` tooling measurably *adds* cost. |
| **requirement_coverage** | **model** (borderline, p ≈ 0.06); ceiling on easy task | The *only* metric where the model choice shows up — reliability is what you're buying with a newer model. |

**The headline ANOVA insight:** *language* governs code quality and tests, *task* governs cost and time, and the *model* mostly governs spec-reliability (and, on hard tasks, speed). Picking a newer model to "write better code" is largely wasted — it writes *more reliably*, not more cleanly, and it costs you time and money to do so. (`beads` tooling shows up in exactly one place — extra cost and time — with no quality or coverage payoff, which is why it was dropped from the later experiments.)

Reproduce with `retort report effects --db <experiment>/retort.db --metric <response>`.

**The prompt as a factor (explored — experiment-13).** The experiments above held the *instruction* constant; exp-13 varies the prescribed **test methodology** (`prompt` is a first-class factor — named strategies in `prompts/<level>.md`). The result: on a task the model already understands, the methodology **barely moves reliability** — it changes *what tests get written* (ATDD trades unit coverage for acceptance coverage) more than whether the run ships. See [Does the prompt matter?](#does-the-prompt-matter-test-methodology-neutral--tdd--atdd) above and the [prompt blog](prompt-blog.md). Prompt strategy beyond test methodology (terse vs. detailed, worked examples) remains a one-line addition to the grid for future study.

---

## The experiments

Each row links to its **full per-cell results table** (every language × model × tooling, with pass-proportion, speed, cost, and quality, generated from `master.db`).

Newest first — the recent work is the **local-model arc** (exp 16–21) plus **Sonnet 5** (exp-15):

| # | Task | Models | Covered | Results table | Headline (clean data) |
|---|---|---|---:|---|---|
| 24 | REST-API (**local**) | KV **prefix-cache** ON vs OFF on the 80B (ablation) | 12 | **[results →](experiment-24-qwennext80b-cached/RESULTS.md)** | Cache hits (88K prefix in ~2.5 s) but **0.33→0.33**: runs are generation-bound, not prefill-bound. Bigger≠better survives |
| 23 | REST-API (**local**) | **Devstral-24B** (agent-tuned) via llama.cpp | 12 | **[results →](experiment-23-devstral/RESULTS.md)** | Different bet, not bigger: 0.17, 7/12 non-terminating — but wrong harness (OpenHands-tuned). 35B still best |
| 22 | REST-API (**local**) | **Qwen3-Coder-Next-80B-A3B** vs the 35B | 12 | **[results →](experiment-22-qwennext80b/RESULTS.md)** | Bigger ≠ better: 80B first-try **0.33 < 35B's 0.50**; slower, more non-terminating |
| 21 | REST-API (**local**) | Self-repair: 2nd try + feedback on Qwen3.6-35B | 27 | **[results →](experiment-21-repair-lcm/RESULTS.md)** | Repair doubles pass **0.11→0.22**, but only mainstream; niche wall is a true capability ceiling |
| 20 | REST-API (**local**) | Qwen3.6-35B × **all 9 languages** | 27 | **[results →](experiment-20-hermes35b-alllang/RESULTS.md)** | Mainstream/niche split: 0.11; Clojure/Java/C#/Elixir/Erlang all fail (all genuine) |
| 19 | REST-API (**local**) | Qwen3.6-35B × **prompt**[neutral/TDD/ATDD/BDD], Python | 12 | **[results →](experiment-19-hermes35b-prompts/RESULTS.md)** | neutral & BDD tie best; **ATDD worst (0/3)**; neutral ~2.5× cheaper |
| 18 | REST-API (**local**) | **Hermes-lcm + Qwen3.6-35B** (MLX/oMLX) | 24 | **[results →](experiment-18-hermes-35b-lcm/RESULTS.md)** | Best local: **0.38**; **cracks TypeScript**; Rust non-terminating |
| 17 | REST-API (**local**) | **Hermes agent** vs `omp`, Qwen3-Coder-30B | 24 | **[results →](experiment-17-hermes/RESULTS.md)** | Agent swap: default Hermes 0.12 < omp 0.33 (LCM plugin not yet on) |
| 16 | REST-API (**local**) | **Qwen3-Coder-30B** (llama.cpp), 64K/128K/256K + prompt | 48 | **[results →](experiment-16-qwen3coder/RESULTS.md)** | First local model: **0.08→0.33** (context is the first-order lever); ATDD hurts |
| 15 | Brazil + REST-API | **Claude Sonnet 5** × prompt | 30 | **[results →](experiment-15-sonnet5/RESULTS.md)** | Sonnet 5 vaults to the frontier (0.93 / 1.00) — but priciest & slowest |
| 14 | Brazil-neutral | Sonnet, Opus-fast × prompt × **8 languages** | — | **[results →](experiment-14/results.md)** | Prompt is the smallest lever, across 8 languages |
| 1 | REST-API | Opus-4.6, Sonnet | 56 | **[results →](experiment-1/results.md)** | Both ~0.6 reliable; Java/Go/Rust strongest; cheap but not certain |
| 2 | Brazil | Opus-4.6, Sonnet | 22 | **[results →](experiment-2/results.md)** | Hard task exposes them — only ~half of runs fully correct |
| 3 | Brazil | Opus-4.6, 4.7 | 7 | **[results →](experiment-3/results.md)** | 4.7 more reliable but **3× slower, 5.5× pricier** |
| 4 | Brazil | Opus-4.8 | 6 | **[results →](experiment-4/results.md)** | First 4.8 data: fully correct, but slowest/priciest |
| 5 | Brazil | Opus-4.7, 4.8 | 36 | **[results →](experiment-5/results.md)** | **4.8 = 1.00 pass vs 4.7 = 0.85**, +47% time/cost |
| 6 | REST-API | Opus-4.7, 4.8 | 71 | **[results →](experiment-6/results.md)** | Both 1.00 — 4.7 the better value, 4.8 is overkill |
| 7 | Brazil + REST-API | Opus-4.8 **fast** | 24 | **[results →](experiment-7/results.md)** | Fast mode = 1.00 pass on both, but 2× per-token price — buys speed, not savings |
| 8 | REST-API | Opus-4.7, 4.8 (**Erlang+Elixir**) | 12 | **[results →](experiment-8/results.md)** | Both BEAM languages 1.00 on every measure |
| 10 | Brazil + REST-API | **Claude Fable 5** | 24 | **[results →](experiment-10/results.md)** | A tier above 4.8: 1.00 pass on both, but ~2× cost / slowest — no reliability to buy where 4.8 is already 1.00 |
| 11 | REST-API | **Gemini** (`gemini-2.5-pro`) vs `claude-code` | — | **[scaffold →](experiment-11/README.md)** | First cross-**agent** study. Harness validated end-to-end against the live Gemini CLI; runs pending free-tier capacity |
| 13 | Brazil (neutral fork) | Sonnet, Opus-4.8-fast × **prompt**[neutral/TDD/ATDD] | 36 | **[results →](experiment-13/results.md)** | Prompt / test-methodology study: methodology barely moves reliability (11/12 cells pass); ATDD trades unit coverage for acceptance coverage |

The combined dataset across all experiments with scored runs is in [`master.csv`](master.csv) (and `master.db`), rebuildable with `retort aggregate --out master.db --csv master.csv`; it includes the 24 Fable 5 runs (experiment-10) and the 36 prompt-methodology runs (experiment-13). (Experiment-11 is a ready-to-run cross-agent scaffold — no result rows yet; see [Comparing coding agents](#comparing-coding-agents-eg-claude-vs-gemini).)

All run data — per-run source, tests, scores, and the spec-eval output — is committed under `experiment-N/runs/`, combined in `master.db` / `master.csv` (`retort aggregate`).

**Methodology notes.** Of ~300 archived runs, **234** are completed runs with a reproducible `requirement_coverage` (the rest failed the tests-gate or are shard duplicates). The spec gate reads a pinned `REQUIREMENTS.json` per task (constant denominator) and judges with a strong second-opinion model — the judge now defaults to the **latest** Claude (earlier runs in this dataset used opus-4.6; exp-13 used opus-4.8). Cross-experiment model means mix language/tooling sets, so per-model conclusions lean on the larger within-task samples.

---

## Stack maturity: which stacks are production-ready

`retort maturity` scores every stack (a unique `language × model × tooling × task` combination) into a lifecycle phase — **production / trial / screening / candidate** — from a composite of replicate agreement, completion rate, reliability level, and replicate coverage. It's the "which stack should I actually use?" view. Across all 103 stacks in the combined data ([`maturity-report.txt`](maturity-report.txt), headline metric `requirement_coverage`):

| Phase | Stacks | What it means |
|---|---:|---|
| **production** (≥0.85) | **67** | Reliable + reproducible — ship it |
| trial (0.65–0.85) | 18 | Promising, needs more evidence |
| screening (0.40–0.65) | 12 | Inconsistent — only on easy tasks |
| candidate (<0.40) | 6 | Avoid |

Two things fall out of the ranking:

- **Every new stack reached production (12/12):** all four fast-mode language cells on *both* tasks, and all four Erlang/Elixir cells, scored 1.00 maturity.
- **The whole immature tail is the hard task** — and overwhelmingly the hard task **with `beads` tooling**. On Brazil, `tooling=none` stacks average **0.88** maturity (18 production); `tooling=beads` stacks average just **0.54** (only 2 production). Even Opus-4.8 drops to *candidate* on Brazil once `beads` is bolted on. The tooling doesn't just add cost (see ANOVA) — on a hard task it actively destabilizes the run. That's the quantified reason `beads` was dropped from the later experiments.

Regenerate with `retort maturity --db <db> --metric requirement_coverage`.

---

## Why some runs failed

Roughly 60 of the archived runs are not completed-with-coverage. The strict gate is deliberate — *if the tests don't run, the run fails* — but it's worth separating **harness measurement bugs** (our fault, now fixed) from **genuine model failures** (the real signal). Each new experiment surfaced measurement bugs precisely because it exercised code paths the earlier ones never did:

- **Elixir false-failures (harness).** Every Elixir run initially scored `test_coverage=0` and failed the gate — but the agents had written *valid* Elixir (a sample archive runs **17 tests, 0 failures**). The scorer used the deprecated `mix do deps.get, test` comma syntax, removed in recent Elixir. Fixed to `mix test`; all 6 Elixir runs then passed at 1.00. *A model that looked like it failed had actually succeeded.*
- **Missing cost on the newest runs (harness).** Experiments 7 & 8 recorded duration but `$0.00` cost. The OMP-harness change (PR #6) routed the cost parser by agent name but dropped the `unknown → claude-code` fallback the command builder has, so for cells that didn't pin an agent, Claude ran and billed but its cost JSON was discarded. Fixed + regression-tested; re-run with cost intact.
- **Re-eval found zero runs (harness).** The tooling-free designs (exp-7/8 vary only language × model) tripped a matcher that did `tooling = NULL` in SQL — never true — so `reevaluate` silently graded nothing. Fixed to `IS NULL`.
- **Fast-mode cost under-reported 2× (harness).** Fast mode bills at double the standard per-token rate ([announcement](https://www.anthropic.com/news/claude-opus-4-8)), but the CLI's `total_cost_usd` reports the *standard*-rate figure (confirmed by probe). retort now applies the 2× multiplier for fast-mode runs — without it, the fast-mode cost comparison was wrong in fast's favour (it's a premium, not a saving).
- **A rerun harness that recorded its own failure as the model's (harness).** An overnight pass tried to re-run the `beads`-tooling false-failures in experiments 1/2/5 under the fixed harness. The rerun harness never launched the model — every cell came back in ~1–4 s with **$0 cost and all-zero scores** — yet it *overwrote* the previously-good runs with those instant failures (experiment-5 dropped from 36 to 18 completed; experiment-1 lost 3). The DBs were **restored from `.pre-rerun.bak` snapshots**; no cell actually changed state. The tell was the same one as always: a *genuine* failure burns minutes of model time, a *harness* failure fails instantly for $0. (Full breakdown in [exp-10 results → Rerun outcomes](experiment-10/results.md#rerun-outcomes-experiments-1-2-5).)
- **ATDD cross-package + python-deps false-failures (harness).** The prompt-methodology study (exp-13) ran acceptance tests that drive the system through its public interface — and surfaced two more scorer blind spots. `go test -cover` *without* `-coverpkg` scores an acceptance test in one package that exercises its siblings at **0%** (the entire ATDD pattern), and python coverage ran the bare `pytest` script without the project's deps / without `python -m`, so collection failed. Seven runs the gate marked "tests did not run" had actually built and passed at **77–96%** coverage. Fixed (`-coverpkg` + a `-count=1` profile total for Go; a project-deps venv + `python -m pytest` for Python) and regression-tested; all 36 exp-13 runs then completed. This is exactly the class **`retort diagnose`** now catches automatically (re-test each failure → tooling-vs-genuine), and the `reevaluate` health-check refuses to report success when its judge silently graded nothing.
- **Genuine failures (signal).** The real failures cluster exactly where the data says they should: the **hard task with cheaper models or `beads` tooling**, and the one **ATDD × sonnet/go** corner above. A handful of Erlang runs also flaked the tests-gate on first attempt and passed on `--retry-failed` — ordinary non-determinism, not a model limitation.

The lesson cuts both ways: a strict "tests must run" gate is essential to avoid scoring vibes — but you have to be sure a *failure* is the model's and not the harness's. Every measurement bug is fixed and covered by tests, and `retort diagnose` + the reevaluate health-check now make the tooling-vs-genuine call for you.

---

## Command reference

Every command is `retort <command> [options]`; add `--help` to any of them for the authoritative, version-specific list. Global: `retort --version`, `retort --help`. Most analysis/reporting commands take `--db <experiment>/retort.db` and `--format text|json` (some also `csv`/`html`) with `-o/--output` to write a file instead of stdout.

### Set up a workspace & design the grid

| Command | What it does | Key options |
|---|---|---|
| `init NAME` | Create a workspace dir: config template, visibility-aware `.gitignore`, and an initialized SQLite DB. | `--visibility public\|private` (default **private** = fail-closed, artifacts local-only); `--force` to overwrite. |
| `tasks list` / `tasks show NAME` | List registered tasks and their canonical **source** URIs (`bundled://` for in-repo tasks, `github://` for hosted ones), or show one task's source + description. | `--format text\|json`. |
| `design generate` | Generate a fractional-factorial **design matrix** (CSV) for a phase. Reads factors from `--config` or a JSON `{factor: [levels]}` on stdin; honors `design.fraction`. | `--phase screening\|characterization` (req); `--config`; `-o` CSV out. |
| `report aliasing` | Show the **confounding structure** of a fractional design — which effects are aliased and thus not independently estimable. | `--phase` (screening = Res III, characterization = Res IV); `--max-order 1\|2\|3`; `--config` or factors on stdin. |
| `intake` | Ingest a **new factor level** (e.g. a newly shipped model) and D-optimally augment the existing design with the minimum new runs. | `--factor`, `--level` (req); `--phase`; `--nrestarts` (optimizer restarts); `-o`. |

### Run & watch

| Command | What it does | Key options |
|---|---|---|
| `run` | The core loop: generate design → provision isolated playpens → run `claude -p` per cell → build/test/score → store in the DB. | `--phase` (req); `--config`; `--task`; `--replicates`; `--design <csv>` (run an exact, hand-trimmed matrix); `--resume` (skip completed cells); `--retry-failed` (with `--resume`, re-attempt cells that only ever failed); `--shard INDEX/TOTAL` (deterministic slice for parallel runners on a shared DB); `--dry-run`. |
| `monitor [TARGET]` | Live progress of a run DB: completed/remaining, per-cell coverage, cost + token totals, throughput, ETA. Safe to point at a DB being actively written. | `TARGET` = experiment dir or `.db`; `--watch/--once`; `--interval`; `--total`; `--json`. |

### Score, evaluate & gate

| Command | What it does | Key options |
|---|---|---|
| `evaluate [RUN_DIRS…]` | Run the **evaluate-run** skill over run archives (manual/retroactive grading, or after updating the skill). | `--experiment-dir` (bulk-eval all runs); `--force`; `--workers` (default 4). |
| `reevaluate` | Re-grade archived runs with the **second-opinion spec eval**, persisting `requirement_coverage` into the DB. **Self-checks** (preflights the judge; errors instead of silently grading nothing; reports matched/orphaned). Non-destructive (status unchanged), resumable (skips already-graded unless `--force`). | `--experiment-dir` (req); `--eval-model` (default **unset → the CLI's latest model**, tracking new releases; pass an id to pin); `--workers`; `--force`. |
| `rescore` | Re-score archived runs with the **current** scorers (after fixing/upgrading one) and write corrected metrics back to the DB + `scores.json`. A run whose tests now run (`test_coverage > 0`) flips to **completed**. | `--experiment-dir` (req); `--only-failed`; `--metrics` (subset, no gate); `--workers`; `--dry-run`. |
| `diagnose` | Deep-analyse every **failed** run: re-test its archive and classify **TOOLING** (scorer false-failure — `rescore` recovers it) vs **GENUINE** (real model/spec failure), with the cause. Read-only. | `--experiment-dir` (req); `--as-json`. |
| `promote STACK_ID` | Evaluate a **promotion gate** and report whether a stack passes from one lifecycle phase to the next. | `--from`, `--to` (req); `--evidence '{"p_value":0.05}'`; `--config` (gate thresholds). |

### Analyze & report

| Command | What it does | Key options |
|---|---|---|
| `analyze` | **Type-II ANOVA** per response metric on a CSV: which factors have significant effects. Log-transform by default (multiplicative model for cost/time/tokens). | `--data` (req); `-r/--responses` (req, repeatable); `-f/--factors`; `--interactions`; `--transform log\|none`; `--significance`; `--residuals`; `--predict` (estimate unrun cells + 95% CI). |
| `report effects` | Main effects + interaction effects (mean response per factor level / level-pair) for a design matrix. | `--db`, `--matrix-id`, `--metric` (all req); `--format text\|json\|csv\|html`. |
| `report pareto` | **Pareto-optimal stacks** across multiple objectives (quality vs cost vs speed…). Prefix a metric with `-` to minimize. | `--data` (req); `--metric` (req, repeatable, `-` to minimize); `--group-by` (default `language,model,tooling`). |
| `maturity` | Score each **stack's maturity** (replicate agreement + completion rate + headline level + coverage → production/trial/screening/candidate). The "which stack to use" report. | `--db` (req); `--metric` (headline, default `code_quality` — use `requirement_coverage` for reliability); `--stack` (filter). |
| `report wardley` | Wardley-map overlay placing each stack on the evolution axis (Genesis → Custom → Product → Commodity) from its lifecycle phase. | `--db` (req); `--format`. |
| `report dashboard` | One-screen workspace overview: active experiments, lifecycle states, budget usage, recent promotions. | `--db` (req); `--format`. |
| `report compare` | Run the **compare-runs** skill to contrast evaluated runs across factor dimensions → `comparison.md`. | `--experiment-dir`; `--group-by`; `-o`. |
| `report web` | Static HTML report (sortable per-stack maturity table + run drill-down). Respects `experiment.visibility` (redacts in private mode). | `--db` (req); `--config`; `--out`; `--title`. |

### Aggregate & export

| Command | What it does | Key options |
|---|---|---|
| `aggregate` | Roll **every** `experiment-*/retort.db` into one tidy wide `runs` table (one row/run, a column per metric). Rebuilt from scratch — re-run after a reevaluation pass. | `--experiments-dir` (default `.`); `--out` (default `master.db`); `--csv`. |
| `export csv` | Flatten one DB's `experiment_runs + run_results` into the wide CSV that `analyze`/`pareto` consume. | `--db` (req); `-o`; `--include-failed`. |
| `export merge` | Union multiple per-experiment CSVs into one (each input `label=path.csv`), tagging rows by source — for cross-experiment ANOVA. | `INPUTS…` (req); `--tag-column` (default `experiment`); `-o`. |

### Plugins & safety

| Command | What it does | Key options |
|---|---|---|
| `visibility-check` | Audit which workspace artifacts would be **published vs kept local** per `experiment.visibility`; exits non-zero if a private workspace would leak a sensitive path. | `--config`. |
| `plugin list` | List installed scorers/runners and what they contribute. | `--format`. |
| `plugin show NAME` | Detail for one scorer or runner (e.g. `build_time`, `docker`). | — |

---

## Status: 1.0 beta

Feature-complete for single-agent `claude-code` experiments with the `LocalRunner`. **Implemented:** `LocalRunner`, all scorers + the conformance spec gate, factorial/fractional design generation (incl. `prompt` as a factor), ANOVA + effects, SQLite storage + cross-experiment `aggregate`/`reevaluate` (with a judge-tooling health-check), `rescore` + `diagnose` for failure recovery and tooling-vs-genuine classification, resumable sharded runs, `retort monitor` (live in-flight view across shards), `cost_limit_usd`, OMP local-agent profiles, and a **Gemini CLI** harness (`agent` becomes a factor — compare `claude-code` vs `gemini` head-to-head; see below). **Not yet:** `DockerRunner` (skeleton), the `intake`/`scheduler` paths.

### Comparing coding agents (e.g. Claude vs Gemini)

**The agent is the same variable as the model** — it isn't a separate factor. The harness follows from the model id: a `gemini-*` model runs via Google's Gemini CLI, every Claude id via `claude-code`. So you just list the models you want in the **`model`** factor and the right agent is selected per cell:

```yaml
factors:
  model:    { levels: [claude-opus-4-8, gemini-2.5-pro] }   # agent follows the model
  language: { levels: [go, python, rust, typescript] }
```

`retort analyze` then decomposes how much of quality/reliability/cost is the *model/agent* versus the language and task. The `gemini` harness needs Google's [Gemini CLI](https://github.com/google-gemini/gemini-cli) on `PATH` and a Gemini auth method (`GEMINI_API_KEY`, ADC, or a free OAuth login) in the environment. The CLI reports tokens but not a dollar cost, so retort derives cost from `GEMINI_PRICING` in `local_runner.py` (base-tier rates — verify against current Google pricing). The spec-gate judge stays on Claude (the latest model by default; pin one with `reevaluate --eval-model <id>`) so an independent model grades every agent fairly.

#### Local / self-hosted models via the `omp` harness (oh-my-pi)

A **local/self-hosted** model whose name doesn't imply its harness can't be inferred, so it's routed by an explicit profile that overrides the model rule. The `omp` harness drives **[oh-my-pi](https://github.com/can1357/oh-my-pi)** (`omp`) — a terminal coding agent that natively supports local backends (**Ollama**, LM Studio, llama.cpp, vLLM) as well as cloud providers. This is how you put a *local* model in the grid (`claude-code` runs Claude; `omp` runs whatever local/other model you point it at).

**Install `omp`** (one of):

```bash
brew install can1357/tap/omp          # macOS / Linux (Homebrew)
curl -fsSL https://omp.sh/install | sh  # macOS / Linux (script)
bun install -g @oh-my-pi/pi-coding-agent # any platform with Bun ≥ 1.3.14
```

**Serve a local model with Ollama, then declare it to `omp`.** This path is verified end-to-end (experiment-12: Qwen2.5-Coder-7B on bookshop/Go).

```bash
# ⚠️ Use the CASK, not the formula. `brew install ollama` (formula) ships
# WITHOUT its inference runner (llama-server) — every call then 500s with
# "llama-server binary not found". The cask bundles the runner:
brew install --cask ollama && open -a Ollama     # starts the server on :11434
ollama pull qwen2.5-coder:7b
```

`omp`'s *built-in* Ollama integration launches its own `llama-server` and is brittle against modern Ollama installs. The reliable wiring is a custom `openai-completions` provider in `~/.omp/agent/models.yml` pointed at Ollama's OpenAI-compatible endpoint (use a provider name **without** "ollama" in it so omp doesn't reroute to its launcher):

```yaml
# ~/.omp/agent/models.yml
providers:
  lmlocal:
    baseUrl: http://localhost:11434/v1
    apiKey: ollama          # ignored by Ollama; any literal works
    api: openai-completions
    auth: apiKey
    models:
      - id: qwen2.5-coder:7b          # the id Ollama serves; sent on the wire
        name: Qwen2.5 Coder 7B (local)
        input: [text]
        contextWindow: 32768
        maxTokens: 8192
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }   # local = free
```

Verify with a one-shot before launching a run, then point a retort profile at the `provider/id`:

```bash
omp -p --no-session --mode json --model lmlocal/qwen2.5-coder:7b "reply ok"   # should print usage + cost:0
```

```yaml
playpen:
  local_agents:
    qwen-local: { harness: omp, model: lmlocal/qwen2.5-coder:7b }
factors:
  agent: { levels: [qwen-local, claude-code] }   # explicit override for non-inferable local models
```

retort invokes `omp -p --no-session --mode json --model <model> …` and parses its JSON usage events; local runs record `$0` (or a hardware-cost estimate if `local_inference_cost` is configured). omp also supports LM Studio, llama.cpp, and vLLM the same way — see the [provider docs](https://omp.sh/docs/providers). **Note on local tool-calling:** experiment-12 (two local models, both fail, $0) shows a usable local coding agent needs **two** things, and small models miss one each. `qwen2.5-coder:7b` fails on **tool-call format** — it emits the intended call as bare JSON, which Ollama returns in `content` (not `tool_calls`) on *both* `/v1` and native `/api/chat`, despite a `tools` capability — so omp (which executes only structured `tool_calls`) runs nothing. `llama3.2:3b` fixes that (its tool calls serialize; the integration executes them end-to-end) but lacks the **agentic capability** to drive the real task. So you need a model whose tool calls Ollama can structure **and** that's capable enough to drive a multi-step loop (try `qwen2.5:7b-instruct`, `llama3.1:8b`, `mistral-nemo`). See [experiment-12](experiment-12/README.md).

Adding another cloud agent is the same three-part adapter: a command branch, a usage parser, and one `LocalHarness` literal (plus a model-prefix rule in `_harness_for_model` if the new agent's models should auto-route).
