# Retort

**Evaluate the whole stack, not just the model.** Retort applies statistical Design of Experiments (DoE) to measure how AI coding agents actually perform across the variables that decide a real project — **programming language × model × context/serving/sampling × tooling** — on the tasks you care about. Every run is scored for whether it *provably implements the spec*, plus how fast, how expensive, and how clean.

> **Why not just read a leaderboard?** Sites like **[llm-stats.com](https://llm-stats.com/)** compare many models across many benchmarks — but they hold the *stack* constant and ignore programming language, the surrounding tooling, and time taken. They can't tell you whether Opus 4.8 is worth its cost *in Rust*, how reliably a local model gets a Go MCP server completely right, or how long any of it takes. Retort answers exactly that: point it at your languages, models, and tasks (or your own codebase) and it finds the leading stack variant for **your** problem.

---

## Contribute your experiment results

**Ran retort on a model, language, or task combination we haven't tried? Open a pull request with the results — they're welcome and credited.** Every contributor's runs land in their own namespace:

```
experiments/<your-github-id>/experiment-<name>/
```

Namespacing by GitHub id **avoids collisions** between contributors and makes every run **attributable** — the path itself is the provenance and the credit. Your `experiment-<name>/` carries its own `workspace.yaml`, `design.csv`, per-run archives, `retort.db`, and a `provenance.json` recording the exact stack each run used, so the result is reproducible and traceable to you. `retort aggregate` folds your runs into the shared `master.db` alongside everyone else's, and `retort report optimal` picks them up in the leading-stack tables.

See [`experiments/README.md`](experiments/README.md) for the layout and the step-by-step (describe the experiment to Claude Code, or drive the CLI directly), and [`docs/future-experiments.md`](docs/future-experiments.md) for the open queue if you want something worth running.

---

## Features

- **Factorial / fractional-factorial designs** over `language × model × tooling` (and any factors you add — context length, sampling, agent, prompt), generated automatically — run the full grid or a fraction.
- **Isolated playpens** — each run gets a fresh local workspace; the agent implements the task, then the code is built and tested in place. Agents supported: **`claude-code`**, **`hermes`** (local models via oMLX), **`gemini`**, **`opencode`**, and **`omp`**.
- **Scoring that checks the spec, not the vibes.** Nine built-in scorers (code quality, test coverage, test quality, defect rate, maintainability, idiomaticity, token efficiency, findings, bead usage) **plus a conformance gate**:
  - *Mechanical gate* — if the tests don't run, the run **fails** (no proof = no pass).
  - *Spec gate* — a **second-opinion LLM eval** (judge defaults to the **latest** Claude) checks the code against a **pinned requirement checklist** and records `requirement_coverage`; a run passes only if it implements the *whole* spec. A default inline **self-repair second chance** re-seeds a failing cell with its own code + the evaluation feedback before recording it (half credit).
- **`retort recover`** — the one-step post-run cleanup: `diagnose` (classify each failure **TOOLING** vs **GENUINE**) → `rescore --only-failed` (recover scorer false-failures) → `reevaluate` (refresh `requirement_coverage`). So you never hand-investigate a failure.
- **Cross-experiment master database** — `retort aggregate` rolls every experiment into one `master.db` / `master.csv`; **`retort report optimal`** generates the living per-language recommendation from it.
- **ANOVA + effects**, **live `retort monitor`**, resumable sharded runs, `cost_limit_usd`.

This repo *is* the result of running it: ~40 experiments across two tasks and nine languages (Go, Python, TypeScript, Rust, Clojure, Java, C#, Erlang, Elixir), the Claude frontier (Opus 4.6/4.7/4.8, Sonnet 5, Fable 5, fast mode), local MLX stacks (Qwen 30B/35B/80B via Hermes+oMLX), a Gemini cross-agent scaffold, and prompt / sampling / context / self-repair studies.

---

## What the data says

Full, always-current results live in three companion documents — each the **single home** for its topic. This README summarizes and links; it does not re-host tables that go stale.

- ⭐ **[optimal-blog.md](optimal-blog.md)** — *what to run today*: the leading stacks, the per-language / per-task-size recommendation, and the exact configuration each needs (generated from `master.db` by `retort report optimal`). No history — stacks appear when they lead and are removed when they don't.
- 📝 **[model-blog.md](model-blog.md)** — the narrative: reliability-vs-cost, fast mode, the local-model arc, and the measurement bugs found along the way.
- 🎯 **[prompt-blog.md](prompt-blog.md)** — whether the prescribed test methodology (BDD / TDD / ATDD vs none) moves reliability.

The headline metric is **pass-proportion**: over N replicates of a stack, the fraction whose runs *fully implement the spec* (`requirement_coverage == 1.0`). Read it as **the probability a single unattended run comes out completely correct**. A single sub-1.0 run is a fail.

**The current picture (latest experiments):**

- **Cloud reliability is a cost decision, and it's task-dependent.** On the *hard* task only **Fable 5** clears it every time (1.00); **Sonnet 5** is 0.93 at less cost; **Opus 4.8** is a ~0.59 coin-flip (but ~1.00 and cheap on routine work); **Opus 4.7** is a fine routine stack (1.00) but weak on hard (0.40). On easy work almost anything reaches ~1.00, so the cheapest reliable model wins.
- **A local laptop stack is free and now covers three languages.** **Qwen3-Coder-Next 80B** (MLX + Hermes + oMLX on a 64 GB Mac, at `context_threshold: 0.9`) runs **Python, Go and TypeScript at 1.00** for $0 — TypeScript unlocked by raising the compaction point (a config lever, not a capability wall). **Rust (0.33) and the niche languages** (Clojure/C#/Elixir/Java/Erlang, ~0.00) still go to cloud, and no local stack reliably clears the hard task (**0/6**, config-invariant — verified at both ctx 0.7 and 0.9). The **35B** is the faster Python/Go alternative (0.85 each).
- **The prompt/methodology is a lever only in proportion to model weakness** — it tanks ATDD on a weak stack (Sonnet/Go, the 35B) but is a flat no-op on strong ones (the 80B: neutral/BDD/TDD/ATDD all 1.00; and cloud). See the prompt blog.

### Factor analysis (ANOVA): what actually moves each metric

The point of a designed experiment is that you can *decompose* the variance — for each response, how much is explained by language vs. model vs. tooling. Type-II ANOVA on the balanced experiments (cost/duration log-transformed) gives a clean separation of concerns:

| Response | Dominant factor | What it means |
|---|---|---|
| **code_quality** | **language ≈ 94–96%** (p < 10⁻⁴⁰); model ~0% | Quality is the *language's*, not the model's. |
| **test_coverage** | **language ≈ 92–95%**; model ~0% | The language and its test ecosystem dominate. |
| **duration** | **task ≈ 75%**; then model on a fixed hard task | The task sets the clock; on hard tasks the newer model is the *slower* one. |
| **cost** | **task ≈ 82%**; `beads` tooling +10%; language ~4% | The task sets the bill; `beads` measurably *adds* cost. |
| **requirement_coverage** | **model** (borderline) | The one metric where model choice shows up — reliability is what a newer model buys. |

**Headline:** *language* governs code quality and tests, *task* governs cost and time, and the *model* mostly governs spec-reliability (and, on hard tasks, speed). Picking a newer model to "write better code" is largely wasted — it writes *more reliably*, not more cleanly. Reproduce with `retort report effects --db <experiment>/retort.db --metric <response>`.

### The experiments

Queued experiments are in **[docs/future-experiments.md](docs/future-experiments.md)** (a prioritized queue); finished runs and rejected candidates move to **[docs/past-experiments.md](docs/past-experiments.md)** (in experiment order). Every scored run is combined into **[`master.csv`](master.csv)** / `master.db` (rebuild with `retort aggregate --out master.db --csv master.csv`). Per-run source, tests, scores, and spec-eval output are committed under each `experiments/**/runs/`. Stack maturity (production / trial / screening / candidate per stack) is in [`maturity-report.txt`](maturity-report.txt) — regenerate with `retort maturity --db master.db --metric requirement_coverage`.

> **Experimental side-branch — [`retort_metaharness/`](retort_metaharness/)** (console script `retort-metaharness`): a methodology layer that makes the *agentic-orchestration harness* (routing / self-consistency / memory / evolved genome / scaffold) a first-class DoE factor, so the ANOVA can separate a harness effect from the raw model. It composes Retort's engine but is **cloud-only (OpenRouter) and needs an external harness solver**, so it stays a documented side-branch until a screening run shows the harness variance is real — see the staged plan in [future-experiments §6](docs/future-experiments.md#6-methodology-harness-orchestration-factor-retort-metaharness).

**Why some runs fail — and how the gate stays honest.** The strict "tests must run" gate is deliberate, but a *failure* has to be the model's, not the harness's. Every new language/stack surfaced measurement bugs (Elixir's deprecated `mix do deps.get, test`; Go acceptance tests scoring 0% without `-coverpkg`; fast-mode cost under-reported 2×; a rerun harness that overwrote good runs with instant $0 failures). All are fixed and regression-tested, and **`retort diagnose`** now makes the tooling-vs-genuine call automatically — the same class of scorer false-failure that `retort recover` cleans up after every run. The tell is always the same: a *genuine* failure burns model time; a *harness* failure fails instantly for $0.

---

## Install

### The easy way: ask Claude Code

Retort has a couple of environment gotchas (Python ≥ 3.11; `OApackage` is a C++ extension built with `cmake`). The fastest install is to let Claude Code handle them:

```text
$ cd Documents/GitHub
$ claude
> clone and install https://github.com/adrianco/retort here
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
| **`claude` CLI, authenticated** | the default agent runner, and the spec-gate judge |
| **Per-language toolchains** | the scorer **builds, tests, and lints** the generated code — see the table below |
| **Full Xcode, installed *and launched once*** | only for **Swift / Objective-C** (XCTest + Foundation) — see the Apple-language note below |
| **`bd` (beads) CLI** | only if a factor uses `tooling: beads` |
| **`gemini` / `omp` CLI, or Hermes + oMLX** | only to run non-Claude agents — see [Comparing coding agents](#comparing-coding-agents) and [docs/configuration.md](docs/configuration.md#local-serving-stack-hermes--omlx) |

`.devcontainer/` provisions this for Codespaces / Dev Containers (authenticate `claude` once).

### Per-language build & test toolchains

You only need the toolchains for the languages you list as `language` factor levels. The scorer **shells out to each language's real build/test/lint tools**, so they must be on `PATH` — a missing tool fails the run's mechanical gate (tests can't run = no pass).

| Language | Tools the scorer runs | macOS (Homebrew) | Debian/Ubuntu |
|---|---|---|---|
| **python** | `pytest`, `coverage`, `ruff` | (bundled via the pip extras) | (bundled via the pip extras) |
| **typescript** | `node` ≥20 + `npm` (`jest`/`vitest`, `tsc`, `eslint`) | `brew install node` | `apt install nodejs npm` |
| **go** | `go test -cover`, `go vet` | `brew install go` | `apt install golang-go` |
| **rust** | `cargo test`, `cargo clippy` | `brew install rustup-init && rustup-init -y` | rustup via [sh.rustup.rs](https://sh.rustup.rs) |
| | then add the linter: | `rustup component add clippy` | `rustup component add clippy` |
| **java** | `mvn test`, `jacoco`, `mvn compile` (JDK 17+) | `brew install openjdk maven` | `apt install default-jdk maven` |
| **clojure** | `clojure -M:test` **and** `lein test`, `cloverage`, `clj-kondo` | `brew install clojure/tools/clojure leiningen borkdude/brew/clj-kondo` | see [clojure.org](https://clojure.org/guides/install_clojure) / [leiningen.org](https://leiningen.org/#install) |
| **erlang** | `rebar3 eunit` **and** `rebar3 ct`, `rebar3 compile` | `brew install erlang rebar3` | `apt install erlang rebar3` |
| **elixir** | `mix test`, `mix compile --all-warnings` | `brew install elixir` | `apt install elixir` |
| **csharp** | `dotnet test`, `dotnet build` (.NET SDK) | `brew install dotnet` | `apt install dotnet-sdk-8.0` |
| **swift** | `swift test --enable-code-coverage`, `swift build`; `swiftlint` (optional) | `brew install swift swiftlint` (or Xcode) | `apt install swift` |
| **c** ᴱ | `clang` + `cmake`; CTest / Makefile test target (pass-rate = coverage proxy) | Xcode CLT + `brew install cmake lcov` | `apt install clang cmake lcov` |
| **cpp** ᴱ | `clang++` + `cmake`; CTest (Catch2 / GoogleTest / doctest) | Xcode CLT + `brew install cmake lcov` | `apt install clang cmake lcov` |
| **objc** ᴱ | `clang` + Foundation/XCTest via `xcodebuild` (**macOS only**) | full **Xcode** | — (macOS only) |

> ⚠️ **Clojure needs *both* the Clojure CLI and Leiningen** (agents pick either a `deps.edn` or a `project.clj` layout). **Erlang needs `rebar3`**; **Elixir needs `mix`**. A missing toolchain is the single most common "why did every run of language X fail?" — verify with `lein test`, `rebar3 --version`, `mix --version` before launching.
>
> ᴱ **Exploratory (exp-43).** C / C++ / Objective-C are scored by **test pass-rate as the coverage proxy** (no single canonical runner, so the scorer auto-detects CMake+CTest → Makefile → xcodebuild). Their **lint + defect signal is the compiler itself** — a `-Wall -Wextra` build (the same compiler-as-linter pattern Java/C#/Erlang use), counting distinct warning/error diagnostics. Objective-C requires a full Xcode (Foundation + XCTest) and can't run on Linux CI.
>
> 🍎 **Swift / Objective-C prerequisite — full Xcode, installed *and launched once* (macOS only).** XCTest and Foundation ship only with a full **Xcode.app**, not the Command Line Tools. Install Xcode from the App Store (or [developer.apple.com](https://developer.apple.com/xcode/)), then **open it once** so it accepts the license and installs its components — verify with `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild -checkFirstLaunchStatus` (exit 0 = ready). You do **not** need `sudo xcode-select -s`: when `xcode-select` still points at the CLT, the scorer auto-sets `DEVELOPER_DIR` to the installed Xcode so `swift test` / `xcodebuild` find XCTest. Without a launched Xcode, Swift/ObjC runs fail the mechanical gate with `no such module 'XCTest'`.

### Run an experiment — describe it in plain language

You don't hand-write `workspace.yaml` or do the factorial math. Open `claude` in the repo and **describe the experiment**; it designs the matrix, checks prerequisites, estimates cost, confirms the decisions that matter, and runs it:

```text
> compare opus 4.6, 4.7 and 4.8 across six languages on the brazil-bench task

⏺ That's a 3 model × 6 language × 2 tooling = 36-cell factorial, 3 replicates.
  Estimated real API spend + hours of wall-clock. Confirm a few choices:
  · full factorial or a quarter-fraction?   · keep beads tooling or drop it?   · run now, or set up and stop?
```

Watch live with `retort monitor <experiment>`, or drive the CLI directly. A **task** is what the agent builds; [`tasks/registry.yaml`](tasks/registry.yaml) indexes tasks by name → a canonical source (`bundled://` in-repo, or `github://` hosted). List them with `retort tasks list`.

---

## Command reference

Every command is `retort <command> [options]`; add `--help` for the authoritative, version-specific list.

### Set up & design
| Command | What it does |
|---|---|
| `init NAME` | Create a workspace dir (config template, visibility-aware `.gitignore`, initialized DB). |
| `tasks list` / `tasks show NAME` | List registered tasks and their source URIs, or show one. |
| `design generate` | Generate a fractional-factorial **design matrix** (CSV) for a phase; honors `design.fraction`. |
| `report aliasing` | Show the **confounding structure** of a fractional design. |
| `intake` | Ingest a **new factor level** (e.g. a new model) and D-optimally augment the existing design. |

### Run & watch
| Command | What it does |
|---|---|
| `run` | The core loop: design → provision playpens → run the agent per cell → build/test/score → store. Key flags: `--phase`, `--config`, `--design <csv>`, `--replicates`, `--resume`, `--retry-failed`, `--shard I/N`, `--repair-from <dir>`, `--no-second-chance`. |
| `monitor [TARGET]` | Live progress of a run DB (completed/remaining, coverage, cost, ETA). `--watch/--once`. |

### Score, evaluate, recover
| Command | What it does |
|---|---|
| `recover` | **One-step post-run cleanup**: diagnose → rescore --only-failed → reevaluate on the recovered languages. |
| `diagnose` | Classify every **failed** run **TOOLING** (scorer false-failure) vs **GENUINE**, with the cause. Read-only. |
| `rescore` | Re-score archives with the current scorers; a run whose tests now run flips to completed. `--only-failed`, `--metrics`. |
| `reevaluate` | Re-grade with the second-opinion spec eval, persisting `requirement_coverage`. Self-checks the judge; resumable. |
| `evaluate` | Run the evaluate-run skill over archives (manual/retroactive grading). |
| `promote STACK_ID` | Evaluate a promotion gate (screening → trial → production). |

### Analyze & report
| Command | What it does |
|---|---|
| `analyze` | **Type-II ANOVA** per response on a CSV; `--predict` estimates unrun cells + 95% CI. |
| `report optimal` | Generate the **optimal-blog** tables (leading stacks + per-language matrix) from `master.db`. `--health`, `--write <blog.md>`. |
| `report effects` | Main + interaction effects for a design matrix. |
| `report pareto` | **Pareto-optimal stacks** across objectives (quality vs cost vs speed). |
| `maturity` | Score each stack's maturity → production/trial/screening/candidate. |
| `report wardley` / `report dashboard` / `report compare` / `report web` | Evolution-map overlay · workspace overview · compare-runs skill · static HTML report. |

### Aggregate, export, safety
| Command | What it does |
|---|---|
| `aggregate` | Roll **every** `experiment-*/retort.db` into one wide `runs` table (`master.db` + `--csv`). |
| `export csv` / `export merge` | Flatten one DB to the wide CSV `analyze`/`pareto` consume · union per-experiment CSVs. |
| `visibility-check` | Audit which artifacts publish vs stay local per `experiment.visibility`. |
| `plugin list` / `plugin show NAME` | List / detail installed scorers and runners. |

---

## Comparing coding agents

**The agent usually follows from the model id** — a `gemini-*` model runs via Google's Gemini CLI, every Claude id via `claude-code` — so you just list models in the `model` factor and the right agent is selected per cell:

```yaml
factors:
  model:    { levels: [claude-opus-4-8, gemini-2.5-pro] }   # agent follows the model
  language: { levels: [go, python, rust, typescript] }
```

The `gemini` harness needs the [Gemini CLI](https://github.com/google-gemini/gemini-cli) on `PATH` and a Gemini auth method. The spec-gate judge stays on Claude so an independent model grades every agent fairly.

**Local / self-hosted models** are routed by an explicit `playpen.local_agents` profile that overrides the model rule. The **featured** local path is **Hermes + oMLX** running Qwen 35B/80B on Apple Silicon — see [docs/configuration.md → Local serving stack](docs/configuration.md#local-serving-stack-hermes--omlx) and [optimal-blog.md](optimal-blog.md) for the exact config. An earlier **`omp` / Ollama** path (experiment-12) is documented in [docs/local-models.md](docs/local-models.md) as the legacy alternative.

---

## Status: 1.0 beta

Feature-complete for single-agent experiments with the `LocalRunner`. **Implemented:** `LocalRunner`, all nine scorers + the conformance spec gate, factorial/fractional design generation (incl. `prompt`, `sampling`, `context` as factors), ANOVA + effects, SQLite storage + cross-experiment `aggregate` / `reevaluate` (with a judge-tooling health-check), `rescore` / `diagnose` / `recover` for failure recovery, self-repair second chance + `--repair-from`, resumable sharded runs, `retort monitor`, `cost_limit_usd`, `intake` for augmenting a design with a new factor level, a local **Hermes + oMLX** stack, and **Gemini** / **opencode** / **omp** harnesses. **Not yet:** `DockerRunner` (skeleton), the `scheduler` paths.

See [`docs/`](docs/) for the full configuration reference, concepts, extending guide, quickstart, and local-model setup.
