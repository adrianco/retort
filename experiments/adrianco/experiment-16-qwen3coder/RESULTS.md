# Experiment 16 — a capable LOCAL model on the bookshop task (Qwen3-Coder-30B-A3B)

**Question.** [experiment-12](../experiment-12/README.md) showed the `omp` local-model
harness works end-to-end but that no *small* model (7B/3B) cleared both bars a
coding agent needs — a tool-call format the server can structure, **and** enough
agentic capability to drive the loop. It ended with: *"worth trying next: a
capable ~30B model (Qwen3-Coder-30B-A3B) on enough VRAM."* This is that run, on a
**MacBook Pro M5 Pro, 64 GB** — the exact machine
[Birgitta Böckeler used](https://martinfowler.com/articles/exploring-gen-ai/local-models-for-coding-experiences.html),
whose experience motivated the model choice.

**Model.** Qwen3-Coder-30B-A3B (MoE, 3B active), **Q4_K_M** GGUF from
`unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF` — Böckeler's daily-driver pick and
our [`docs/local-models.md`](../../../docs/local-models.md) top recommendation.

**Serving.** llama.cpp `llama-server --jinja -fa on -ngl 99 -c 65536` on
`127.0.0.1:8080` (jschoch's llama.cpp path, the setup that *completed* tasks in
exp-12). `omp` routes to it via an `openai-completions` provider. Local
inference → **$0 API cost**; spec-gated by an independent **opus-4.8** judge.

**Grid.** `language[python, go, typescript, rust] × agent[qwen3-coder-local]`,
**3 replicates**. Only the local cells ran; every `claude-code` baseline comes
from `master.db` (the incremental design).

---

## Headline: a capable local model, but far below the frontier on an "easy" task

Pass-proportion (`requirement_coverage == 1.0`, tests actually run) — the
probability a single run comes out **completely** correct:

| language | Qwen3-Coder-30B (local) | Claude baseline¹ | completed² | best req_cov | avg time | avg tokens |
|---|---:|---:|---:|---:|---:|---:|
| python | **0.33** (1/3) | 0.94 | 2/3 | **1.00** | 12 min | 1.2 M |
| go | **0.00** (0/3) | 1.00 | 2/3 | 0.92 | 14 min | 1.9 M |
| typescript | **0.00** (0/3) | 1.00 | 0/3 | — | 21 min | 2.4 M |
| rust | **0.00** (0/3) | 0.97 | 0/3 | — | 28 min³ | 1.6 M |
| **overall** | **0.08** (1/12) | **~0.98** | 4/12 | | | |

¹ `claude-code` on `rest-api-crud`, all models/tooling, from `master.db`.
² "completed" = tests ran and it was scored (mechanical gate passed), even if
`req_cov < 1.0`. ³ **Every** Rust replicate hit the 28-min graceful cap — it
*never* terminated on its own.

- **It cleared exp-12's two bars.** Qwen3-Coder-30B emits **structured
  `tool_calls`** llama.cpp lifts correctly, and it **drives the multi-step loop**
  — it plans, writes files, runs tests, iterates. The first capable local agent
  in this project. It just isn't *reliable*.
- **0.08 overall vs the frontier's ~1.00** on a task Claude models find trivial.
  The single pass was **python** (one replicate at `req_cov 1.0`, 64% coverage).
- **Language governs outcome, exactly as Böckeler reports.** Python is best
  (the only passes, fastest, least verbose); Rust is worst (0 passes, always
  spun to the cap); TypeScript is the most token-hungry (up to **3.2 M tokens**
  in one run). Even the local model's *code quality* on completed runs follows
  the usual per-language pattern (Go 0.96, Python 0.83) — quality is the
  language's, reliability is the model's.
- **Go was agonizingly close:** two of three runs scored `req_cov 0.92` (11 of 12
  requirements) with working, tested code — but never the full spec. That "almost
  right" is precisely the trap: plausible output that a human must review.

---

## Context window is a first-order reliability lever (64K → 128K)

The single biggest improvement came not from the model but from **giving it room
to think**. The initial grid ran at a 64K server context; but `llama-server`
defaults to **4 parallel slots**, so `-c 65536` actually splits into 4×16K-ish
and, more importantly, `omp`'s ~23K-token preamble means the agent was
**compacting its context mid-task** on the longer (Rust/TS) sessions — losing the
thread and over-iterating. Setting **`--parallel 1 -c 131072`** gives one session
a full **128K** window (and *lowers* memory — 29 GB RSS vs the 4-slot ~42 GB,
which also removed the crash pressure). Re-running the identical grid:

| language | 64K pass-prop | **128K pass-prop** | 64K completed | 128K completed |
|---|---:|---:|---:|---:|
| python | 0.33 (1/3) | **1.00 (3/3)** | 2/3 | 3/3 |
| go | 0.00 (0/3) | **0.33 (1/3)** | 2/3 | 1/3 |
| typescript | 0.00 (0/3) | 0.00 (0/3) | 0/3 | 0/3 |
| rust | 0.00 (0/3) | 0.00 (0/3) | 0/3 | 1/3 (req 0.83) |
| **overall** | **0.08 (1/12)** | **0.33 (4/12)** | 4/12 | 5/12 |

- **4× the pass-proportion (0.08 → 0.33) from context alone**, same model, same
  quant, same prompt. Python went from coin-flip to **perfect (3/3)**; Go scored
  its first pass; even Rust went from total failure to one completed run.
- So a large share of the 64K failures were **harness-induced (compaction), not
  capability**. For a slow, verbose local model on a multi-turn agentic task,
  **context headroom is one of the highest-leverage knobs** — and the default
  multi-slot server config actively works against you.
- **TypeScript remains 0/3** at both sizes — its failures look genuinely
  capability/verbosity-bound (2–3 M tokens/run, still never converging).
- The model's training context is **256K**; 128K used ~29 GB, so 256K (~43 GB,
  needs a raised Metal `iogpu.wired_limit_mb`) is the next lever to test whether
  the remaining TS/Rust failures also yield to more room.

*(Numbers above: 64K = `bookshop/`, 128K = `bookshop-128k/`; both in `master.db`.)*

---

## 256K context + prompt methodology (neutral vs ATDD) — two negative results

Raised context to the model's training max (256K, `--parallel 1 -c 262144`,
~41 GB RSS under a raised `iogpu.wired_limit_mb=57344`) and added a **prompt**
factor. Hypothesis for ATDD: since the model's dominant failure is runaway
verbosity, ATDD — which used the *fewest* tokens with strong models in exp-13 —
might make it converge. Both hypotheses came back negative.

| prompt | language | pass @256K | completed | avg tokens |
|---|---|---:|---:|---:|
| neutral | python | 3/3 | 3/3 | 1.0 M |
| neutral | go | 1/3 | 2/3 | 1.3 M |
| neutral | typescript | 0/3 | 0/3 | 1.4 M |
| neutral | rust | 0/3 | **3/3** | 2.0 M |
| ATDD | python | **1/3** | 2/3 | 1.6 M |
| ATDD | go | 0/3 | 0/3 | 1.7 M |
| ATDD | typescript | **1/3** | 2/3 | 1.6 M |
| ATDD | rust | 0/3 | 0/3 | 2.7 M |
| **neutral** | **(all)** | **0.33** | | 1.4 M |
| **ATDD** | **(all)** | **0.17** | | 1.9 M |

- **256K buys nothing over 128K on pass-proportion** — neutral is 0.33 at both.
  The one gain: Rust now *completes* 3/3 at 256K (up from 0/3) at `req_cov 0.92`
  — more room lets it stop spinning and produce runnable code, but still never
  the full spec. **128K was the sweet spot; past it, diminishing returns.**
- **ATDD made it *worse*, and *more* expensive** — 0.17 vs neutral's 0.33, at
  **~34% more tokens** (1.9 M vs 1.4 M). The token expectation inverted: ATDD is
  lean for *strong* models (exp-13) but a *weak* local model flails on ATDD's
  front-loaded "write executable acceptance tests through the public interface
  first" demand — python collapsed 3/3 → 1/3. This matches exp-13's one ATDD
  failure landing on its weakest stack: **the heavier methodology hurts the
  weaker model.** (Lone bright spot: ATDD got TypeScript its first-ever pass,
  1/3 — acceptance-first may impose useful structure there.)

**Bottom line across all context sizes (neutral prompt):**

| context | pass-proportion |
|---|---:|
| 64K | 0.08 |
| 128K | **0.33** |
| 256K | 0.33 |

Context headroom is the model's biggest lever up to 128K; beyond that, and with a
heavier prompt methodology, there's no more reliability to buy on this task.

---

## How the failures broke down (`retort diagnose`)

Of 11 non-passing runs: **3 TOOLING** (scorer false-failures, recovered by
`rescore`) and **8 GENUINE** model failures — the honest tooling-vs-model split.

**Genuine failure modes observed (the real signal):**

- **Broken tests that don't run** — python wrote a `tests.py` from which pytest
  collects **0 tests**; the code "looks" tested but isn't.
- **Tests for functions it never wrote** — go's `main_test.go` called
  `createBookHandler` / `updateBookHandler` / `deleteBookHandler` that don't
  exist in `main.go`, so the package **doesn't compile**.
- **Never terminating** — all three Rust runs (and one TypeScript run) ran until
  the graceful time cap without ever deciding they were done, emitting hundreds
  of MB of repetitive output (rust rep1: an **866 MB** cargo tree + a stdout
  stream truncated from ~700 MB). Böckeler's "text wall of doom," measured.

This is exactly her conclusion made quantitative: a capable local model produces
*plausible-but-wrong* code, so **code review is not optional**.

---

## Harness work required to measure it fairly (three fixes)

Getting a *valid* measurement — where a failure is the model's, not ours —
took three fixes, each a genuine gap surfaced by being the first capable local
run through the full pipeline:

1. **Context window.** `omp`'s ~23 K-token system-prompt/tool preamble triggered
   an auto-compaction loop against a 32 K server context. Raised `llama-server`
   to **64 K** (`-c 65536`) and matched `omp`'s `contextWindow` — loop gone.
2. **Output-discarding hard timeout** *(fix in [`local_runner.py`](../../../src/retort/playpen/local_runner.py))*.
   The `omp` command had **no effort bound** (the `claude-code` path caps at
   `--max-turns 50`). A slow, over-iterating local model therefore ran into
   retort's hard `subprocess` timeout, which **kills omp and discards its
   stdout** — so a *finished* workspace was recorded as "Timeout, all-zero." Added
   a graceful **`--max-time`** (hard-wall minus 2 min) so omp self-terminates and
   its work is captured and scored. *First smoke run hit exactly this: the model
   wrote a correct API with 8/8 passing tests in 5 min, then the run was marked
   FAIL because it was hard-killed at 30 min while over-iterating.*
3. **Server crashes under load** → a **self-healing supervisor** that restarts
   `llama-server`, plus **flash-attention** (`-fa on`). The first full grid died
   silently mid-run (Böckeler's "runtime crashed") and 10 cells failed in an
   identical 16 s against a dead server — the classic instant-$0 harness tell.
   With `-fa on` + the supervisor, the re-run completed all 12 cells with **one**
   server boot, zero crashes.

Cost accounting: **$0** on inference (local); the only spend is the opus-4.8
spec-gate judge.

---

## Verdict

Qwen3-Coder-30B-A3B is the **first genuinely agentic local model** in this
project — it clears the bars that stopped every exp-12 model, and on a good day
(python) it produces a completely-correct, spec-passing implementation for free.
But on the *easy* bookshop task it lands at **0.33 pass-proportion at 128K
context (0.08 at 64K) vs the Claude frontier's ~1.00**, fails TypeScript
outright, and its failures are the dangerous kind — plausible code with tests
that don't run or don't compile. Context headroom is its biggest lever
(64K→128K quadrupled the pass rate). On
this hardware it is a **plan-with-a-big-model, execute-small, review-everything**
tool, not a drop-in agent — precisely Böckeler's conclusion, now measured against
the same baselines as every other model in the dataset.

*Reproduce: see [`bookshop/workspace.yaml`](bookshop/workspace.yaml). Serve the
model with the supervisor, then `retort run --config bookshop/workspace.yaml
--design bookshop/design.csv --replicates 3`.*
