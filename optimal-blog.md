# The Optimal Stack

*Living document — last reviewed July 2026. This records **what to run today**: the
leading stacks, and the exact configuration each one needs. It is not a history.
Superseded stacks and rejected configurations are not discussed here; they are
retired, and retirement is the point.*

---

## What this document is

A **stack** is the whole thing you actually deploy, not just a model:

> **language × model × quantization × serving layer × agent × context engine × sampling × prompt**

Retort scores stacks on **pass-proportion** — run a stack N times on a real task and
count the fraction whose output *fully implements the spec*: every requirement on a
fixed checklist, tests that actually execute, verified by an independent evaluator. A
run that misses one requirement is a failure, not a 0.9. Read it as *the probability
that a single unattended run comes out completely correct.*

That harsh bar is deliberate, because it is the number that decides whether you can
let a stack work unattended.

## Lifecycle: how a stack gets here, and how it leaves

This document is the human-readable view of a lifecycle the tool already runs. Each
stage is a retort command, so entries here are *derived*, not curated by taste:

```
CANDIDATE ──► SCREENING ──► TRIAL ──► PRODUCTION ──► RETIRED
```

| Stage | What it means | How it's decided |
|---|---|---|
| **Candidate** | a new model, agent or configuration appears | `retort intake --factor model --level <new>` augments the existing design rather than restarting it |
| **Screening** | Resolution III — do its main effects matter at all? | `retort run --phase screening` → `retort analyze` |
| **Trial** | Resolution IV/V — interactions estimated | `retort promote --from screening --to trial` (gate: p-value) |
| **Production** | **listed in this document** — the recommended stack for its niche | `retort promote --to production` (gate: posterior confidence); `retort maturity` scores readiness |
| **Retired** | dominated on *every* metric by a newer stack — removed, not demoted | `retort report pareto` identifies who is still non-dominated |

The gates are configuration, not opinion — they live in each `workspace.yaml`:

```yaml
promotion:
  screening_to_trial:   { p_value: 0.10 }
  trial_to_production:  { posterior_confidence: 0.80 }
```

**A stack earns a place here only by leading on an axis a developer actually chooses
along** — a language, a task size, a cost or latency budget. Being new is not a
qualification. When it leads on none, `retort report pareto` shows it dominated and it
comes out. The list stays short on purpose.

Configurations that reliably degrade a stack are eliminated outright and recorded as
**forbidden settings** (below). New model releases — frontier and local — trigger a
re-qualification pass, so this document is expected to churn.

---

## The leading stacks

Reliability, cost and time are all reported **per task size** — routine and hard are
different jobs, and a stack that is cheap-and-certain on routine work can be neither on a
hard one. The **routine reliability here is a cross-language blend and is the least useful
number in this document** — it hides a stack's weak languages inside its strong ones (local
Qwen passes Python/Go but not Rust; Opus 4.8 dips on Java). Use it only as a rough sort;
the [per-language success-rate matrix](#what-to-run-by-language-and-task-size) below is the
number to actually decide on. (Hard reliability is single-task, measured on Python/Go.)

<!-- GEN:leading-stacks START -->
| Stack | Reliability (routine · hard) | Cost (routine · hard) | Time (routine · hard) |
|---|---:|---:|---:|
| **Claude Fable 5** | 1.00 · 1.00 | $1.05 · $8.98 | 143 s · 1039 s |
| **Claude Sonnet 5** | 1.00 · 0.93 | $1.10 · $7.64 | 237 s · 1252 s |
| **Claude Opus 4.8** | 0.98 · 0.59 | $0.96 · $3.27 | 294 s · 608 s |
| **Claude Opus 4.7** | 1.00 · 0.40 | $0.97 · $2.95 | 190 s · 500 s |
| **Qwen3.6-35B-A3B (local, $0)** | 0.78 · n/q | $0.00 · — | 440 s · — |
| **Qwen3-Coder-Next 80B (local, $0)** | 0.76 · n/q | $0.00 · — | 582 s · — |
<!-- GEN:leading-stacks END -->

*(Table generated from `master.db` by `retort report optimal`
— do not hand-edit between the markers.)* Local is measured on the routine task in its
qualified languages (Python / Go, below); it is not qualified for hard tasks or for Rust.

**Pick by task size — the two columns tell different stories:**

* **Fable 5** is the *only* stack that clears the hard task **every time (1.00)**. When a
  hard, multi-capability job has to be right unattended, this is the one — you pay for it
  (~$9 and ~17 min a run), and the certainty is what you're buying.
* **Sonnet 5** lands **0.93 on hard** at ~15% less than Fable and comparable time — the
  cost-aware hard-task pick when roughly 1-in-14 misses is acceptable.
* **Opus 4.8** is the cheapest *hard-capable* cloud stack, but hard reliability is only
  **~0.59 — a coin flip**, so budget for review-and-retry. On **routine** work it is ~1.00
  and cheap; that's its real niche.
* **Opus 4.7** is a fine, cheap **routine** stack (1.00, ~$0.97) but **weak on hard (0.40)**
  — don't send hard work to it.
* **Qwen 35B local** does **routine** Python / Go for **$0** at **0.85 each** — its real
  niche. Its leading number (0.78) is *lower* than either language because the blend now
  includes its Rust and TypeScript runs, which score **0.00** — the clearest example in this
  doc of why you must read the per-language matrix, not the average. Not qualified for hard
  tasks, Rust, or TypeScript.
* **Qwen 80B local (`Qwen3-Coder-Next`) — the new best local *Python* stack; avoid it for
  Go.** Over **9 reps** (exp-29 + exp-30) it is **perfect on Python (9/9 = 1.00)** — better
  than the 35B's 0.85 — so for local Python where reliability matters more than speed, this
  is now the pick (it is ~1.3× slower than the 35B). On **Go it is only 0.67 (6/9)**: not a
  one-off — **two separate runs stalled to the 25-min wall** (a real, intermittent
  non-termination bug), plus one near-miss. So Go stays with the 35B (0.85, no stalls). Still
  weak on TypeScript (0.33) and unqualified for Rust/hard tasks.

> **On the Opus 4.8 hard number.** 0.59 is an honest blend: a small clean run scored 1.00
> (n=6) while a larger one scored 0.50 (n=36). The optimistic single-run figure is not
> representative — treat hard-task Opus 4.8 as a coin flip, not a sure thing.

---

## What to run, by language and task size

**Task size** is the axis that matters most, more than language:

* **Routine** — CRUD, glue, well-trodden patterns, a few interacting requirements.
* **Hard** — a novel domain, many interacting capabilities, real data, a protocol to
  implement correctly (our reference: an MCP server over six datasets, twelve required
  capabilities).

**Start from the per-language success rate, not a single headline number.** This is the
matrix that matters — routine pass-proportion for each language × stack, `pass (n)`,
generated from `master.db`. A blank cell means we have no qualified runs there. Read *down*
a column to see where a model is weak (Opus 4.8 on Java; the 35B local passes Python/Go but
scores 0.00 on Rust/TypeScript; the 80B local is strong on Python but drops on Go/TS), and
*across* a row to pick the cheapest stack that actually passes *that* language:

<!-- GEN:per-language-matrix START -->
| Language | Fable 5 | Sonnet 5 | Opus 4.8 | Opus 4.7 | Qwen 35B local | Qwen 80B local |
|---|---:|---:|---:|---:|---:|---:|
| **clojure** | 1.00 (3) | — | 1.00 (6) | 1.00 (6) | — | — |
| **csharp** | — | 1.00 (3) | 1.00 (1) | — | — | — |
| **elixir** | — | — | 1.00 (3) | 1.00 (3) | — | — |
| **erlang** | — | — | 1.00 (3) | 1.00 (3) | — | — |
| **go** | 1.00 (3) | 1.00 (3) | 1.00 (7) | 1.00 (6) | 0.85 (27) | 0.67 (9) |
| **java** | — | — | 0.83 (6) | 1.00 (6) | — | — |
| **python** | 1.00 (3) | 1.00 (3) | 1.00 (7) | 1.00 (6) | 0.85 (27) | 1.00 (9) |
| **rust** | 1.00 (3) | 1.00 (3) | 1.00 (6) | 1.00 (6) | 0.00 (2) | — |
| **typescript** | — | 1.00 (3) | 1.00 (7) | 1.00 (6) | 0.00 (3) | 0.33 (3) |
<!-- GEN:per-language-matrix END -->

**The language split is simple: Python and Go run locally for free; every other language
means Claude.** Local is qualified (at the tuned config) only on those two — TypeScript
has no tuned-config local runs yet, so it goes to cloud like the rest. Rust and TypeScript
score **0.00** on the 35B even at the tuned config, so a cross-language "local" average
(0.78) understates the Python/Go reality (**0.85 each**) — which is exactly why this
document leads with the matrix, not an average. The 80B (`Qwen3-Coder-Next`) splits the two
local languages apart: it is the **best local Python** stack (1.00 over 9 reps) but is
**unreliable on Go** (0.67 — two runs stalled to the wall), so "local" is no longer one
recommendation but two — 80B for Python, 35B for Go.

The recommendation table distills the matrix into, per language, the **cheapest model that
clears routine work**, the **hard-task** pick, and the **prompt / testing method** (the
last is qualitative, from the prompt experiments):

| Language | Routine → cheapest qualifying | Hard task | Prompt / testing method |
|---|---|---|---|
| **Python** | **Qwen 80B local ($0)** 1.00 (n=9) for reliability, or **35B** 0.85 for ~1.3× speed | **Fable 5** (1.00); Opus 4.8 cheaper but ~0.59 | **Local:** *neutral* (cheapest) or BDD — **never ATDD**. Cloud: *neutral* |
| **Go** | **Qwen 35B local ($0)**, 0.85 (the 80B stalls — 0.67) | **Fable 5**; Opus 4.8 cheaper / riskier | **Local:** *neutral* or BDD, **not ATDD**. Cloud: *neutral* |
| **TypeScript** | **Opus 4.8 (~$0.65)** — local n/q | **Fable 5** | Cloud: *neutral* — methodology optional |
| **Rust** | **Opus 4.8 (~$0.71)** — local n/q | **Fable 5** | Cloud: *neutral* |
| **Clojure** | **Opus 4.7 (~$1.06)** | **Fable 5** | Cloud: *neutral* |
| **Java** | **Opus 4.7 (~$0.92)**† | **Fable 5** | Cloud: *neutral* |
| **C#** | **Opus 4.8 (~$0.65)**‡ | **Fable 5** | Cloud: *neutral* |
| **Elixir** | **Opus 4.8 (~$0.85)** | **Fable 5** | Cloud: *neutral* |
| **Erlang** | **Opus 4.8 (~$1.35)** | **Fable 5** | Cloud: *neutral* |

† On our routine Java runs Opus 4.8 dipped to 0.83 while 4.7 held 1.00 — small n; review
Java output whichever you use. ‡ C# Opus 4.8 is n=1; Sonnet 5 (~$1.57, n=3) is the
better-sampled fallback.

**Prompt / testing method — why it's mostly one word.** On the strong cloud models the
prompt is a *flat line*: they pass routine work whatever you ask, so pick **neutral** and
spend nothing on methodology ceremony. It matters on the **local** model, where it is a
real lever: **neutral and BDD tie for best**, and neutral gets there at ~2.5× fewer
tokens, so it's the cheap winner. **Avoid ATDD** — it came last in every local experiment
(0/3 in the Python sweep); a weak model can't carry its front-loaded discipline and just
burns tokens. TDD is middling — no reason to prefer it.

**The decision procedure:**

1. **Hard task, must be right the first time, unattended?** → **Fable 5** (1.00). Costliest
   and slowest; certainty is what the premium buys.
2. **Hard task, but cost matters and ~1-in-14 misses is tolerable?** → **Sonnet 5** (0.93),
   ~15% under Fable. Opus 4.8 is cheaper again but only ~0.59 — budget a review-and-retry
   loop if you use it.
3. **Routine, local & free?** → **Python: Qwen 80B (1.00 over 9 reps)** for reliability, or
   the 35B (0.85) if you want ~1.3× the speed. **Go: Qwen 35B (0.85)** — the 80B stalls on Go
   (0.67). Review the output either way; you'll still see a miss every few runs. (TypeScript,
   Rust, everything else → cloud.)
4. **Routine, any other language?** → cheapest current cloud (Opus 4.7 / 4.8, ~$1); they all
   reach ~1.00, so paying more buys nothing. Use the **neutral** prompt.

---

## Configuration

Reliability is a property of the *stack*, not the model. A leading model on a bad
configuration is not a leading stack. These are the settings each one requires.

### Local: Qwen3.6-35B-A3B

| | |
|---|---|
| **Model** | `unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit` (4-bit MLX, ~20 GB) |
| **Serving** | oMLX 0.5.0 · served from `~/models/<name>` |
| **Agent** | Hermes v0.18 with the `hermes-lcm` plugin (`context.engine: lcm`) |
| **Context** | `context_length: 262144` — set it explicitly; the default fallback is far lower |
| **Hardware** | Apple Silicon, 64 GB. Raise the GPU wired limit: `sudo sysctl iogpu.wired_limit_mb=57344` |

**Sampling — this is not optional:**

```yaml
temperature:        0.6     # anything in 0.2–0.7; the requirement is: NOT 1.0
top_p:              0.95
top_k:              20
repetition_penalty: 1.0     # OFF. See forbidden settings.
```

**Harness settings that decide whether the model can work at all:**

```yaml
playpen_root:  ~/.retort/work   # NOT the system temp dir — see forbidden settings
timeout_minutes: 60             # a high wall: local models are slow, let good work finish
stall_minutes:   25             # kill unproductive loops, not slow-but-productive runs
```

### Cloud: Claude Fable 5, Sonnet 5, Opus 4.8 / 4.7

There is no single cloud winner — the pick is set by task size (see the tables above):
**Fable 5** for hard work that must be right, **Sonnet 5** for hard work on a budget,
**Opus 4.8 / 4.7** for cheap routine work.

Run the model as shipped. The stack that matters is the agent around it; **no sampling
tuning is required or recommended, and on cloud the prompt is a flat line** — use the
plain *neutral* prompt and don't pay for methodology ceremony.

---

## Forbidden settings

Configurations that measurably degrade a stack. These are eliminated, not tuned.

| Setting | Why it is forbidden |
|---|---|
| **`repetition_penalty` > 1.0** | Any repetition penalty derails an agentic tool-calling loop — the model stops converging, stalls, and produces nothing. This holds even at 1.05, and even when the model's own card recommends it: model-card sampling is tuned for single-turn generation, not multi-turn agent loops. **Set it to 1.0.** |
| **`temperature: 1.0`** (server default) | Costs roughly half the reliability of a local coding stack. Any value in 0.2–0.7 is fine; the precise value does not matter. |
| **Playpen under the system temp dir** (`/var/folders/...` on macOS) | Agents refuse to write to paths they consider system-owned, so the agent cannot create files *in its own workspace* — and a run that writes nothing scores a false zero indistinguishable from an incapable model. Keep playpens under `$HOME`. |
| **An unrecorded stack** | A pass-proportion without the stack it was measured on is not a result. Capture versions, model revision hashes, sampling, agent config, and harness settings — every run writes a `provenance.json`. |

---

## Measured data (auto-generated)

These tables are regenerated from `master.db` by
`retort report optimal` — run
`retort report optimal --write optimal-blog.md` to refresh everything between the `GEN` markers. The leading
stacks table above is generated the same way.

**Per language — cheapest stack that clears its reliability bar (routine task):**

<!-- GEN:per-language START -->
| Language | Routine → cheapest qualifying stack | Reliability | n |
|---|---|---:|---:|
| **clojure** | Claude Opus 4.7 ($1.06) | 1.00 | 6 |
| **csharp** | Claude Opus 4.8 ($0.65) | 1.00 | 1 |
| **elixir** | Claude Opus 4.8 ($0.85) | 1.00 | 3 |
| **erlang** | Claude Opus 4.8 ($1.35) | 1.00 | 3 |
| **go** | Qwen3.6-35B-A3B (local, $0) ($0) | 0.85 | 27 |
| **java** | Claude Opus 4.7 ($0.92) | 1.00 | 6 |
| **python** | Qwen3.6-35B-A3B (local, $0) ($0) | 0.85 | 27 |
| **rust** | Claude Opus 4.8 ($0.71) | 1.00 | 6 |
| **typescript** | Claude Opus 4.8 ($0.65) | 1.00 | 7 |
<!-- GEN:per-language END -->

**Prompt / testing method — the local sweep (on cloud the prompt is a flat line):**

<!-- GEN:prompt-method START -->
| Prompt | Reliability | avg test-cov | avg tokens | n |
|---|---:|---:|---:|---:|
| **neutral** | 0.67 | 0.64 | 0.40 M | 3 |
| **BDD** | 0.67 | 0.65 | 1.03 M | 3 |
| **TDD** | 0.33 | 0.33 | 0.54 M | 3 |
| **ATDD** | 0.00 | 0.27 | 0.73 M | 3 |
<!-- GEN:prompt-method END -->

---

## Keeping this current

Each new frontier or local model release triggers a qualification pass on the standard
tasks. A stack is added only when it leads on an axis someone chooses along, and is
removed when it no longer leads on any. The tables are regenerated from `master.db` by
`retort report optimal`; run
`retort report optimal --health` to check the data before trusting a
refresh.

**Known data-pipeline gaps** the generator has to work around (it curates the qualified
config in `FEATURED_STACKS` because master.db can't express it):

* **Historical local runs carry a blank `model`** — older runs recorded `agent:
  hermes-local` but no model, so ~250 rows are attributed to a stack only via their
  experiment slug. *Fixed going forward*: the harness now always records the resolved
  model (`stack_metadata()`), so exp-29 and later land with a real model id.
* **No sampling / context columns** — temperature, top_p, top_k, repetition_penalty are
  absent and `max_context_tokens` is populated only on the newest runs, so "the qualified
  config" can't be filtered from the data; the tuned experiments are named in the script
  instead.
* **experiment-11 isn't ingested** — it has no `retort.db` (an empty/aborted experiment).

Backfilling the historical blank-model rows and re-ingesting would let the generator drop
its slug curation and become a plain group-by.

*Next review: on the next frontier release, or the next local model that fits 64 GB and
tool-calls cleanly.*
