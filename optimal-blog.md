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

1. **Qualify.** A new model or configuration is measured on the standard tasks, at its
   own recommended settings, on a stack whose every variable is recorded.
2. **Promote.** It enters this document only if it wins on some axis a developer
   actually chooses along — a language, a task size, a cost or latency budget. Being
   new is not a qualification.
3. **Retire.** When a stack is beaten on *every* axis it used to lead, it is removed —
   not demoted, removed. The list stays short on purpose.
4. **Eliminate.** Configurations that reliably degrade a stack are recorded as
   **forbidden settings** (below) and never used again.

New model releases — frontier and local — trigger a re-qualification pass. The
document is expected to churn.

---

## The leading stacks

| Stack | Use it for | Reliability | Time / run | Cost / run |
|---|---|---:|---:|---:|
| **Claude Opus 4.8** (cloud) | anything you need *right*, especially hard tasks | **1.00** easy · **1.00** hard | ~150 s | ~$0.61 |
| **Claude Opus 4.7** (cloud) | the value pick — near-4.8 reliability, less money | 1.00 easy · 0.85 hard | ~150 s | ~$0.77 |
| **Claude Sonnet 5** (cloud) | when you want the Sonnet line current-gen | 1.00 easy · 0.93 hard | ~220 s | ~$0.98 |
| **Qwen3.6-35B-A3B** (local, $0) | routine work in Python / Go / TypeScript, on a laptop, privately | 0.83 easy* | ~180 s | **$0** |

\* Local reliability is measured on the easy task in its qualified languages (below).
It is not yet qualified for hard tasks or for Rust.

**The local stack is the newsworthy row.** At correct settings it gets an easy task
completely right ~4 times in 5, at zero marginal cost, in wall-clock comparable to a
cloud model. It is a real option for routine work now, not a toy.

---

## What to run, by language and task size

**Task size** is the axis that matters most, more than language:

* **Routine** — CRUD, glue, well-trodden patterns, a few interacting requirements.
* **Hard** — a novel domain, many interacting capabilities, real data, a protocol to
  implement correctly (our reference: an MCP server over six datasets, twelve required
  capabilities).

| Language | Routine task | Hard task |
|---|---|---|
| **Python** | **Qwen3.6-35B (local, $0)** — the strongest local language | **Opus 4.8**. Local is possible but only ~1-in-3 reliable |
| **Go** | **Qwen3.6-35B (local, $0)** | **Opus 4.8** |
| **TypeScript** | **Qwen3.6-35B (local, $0)** | **Opus 4.8** |
| **Rust** | **Opus 4.8 / 4.7** — local not qualified | **Opus 4.8** |
| Clojure, Java, C#, Elixir, Erlang | **Opus 4.8 / 4.7** — local not qualified | **Opus 4.8** |

**The decision procedure:**

1. **Is the task hard?** → cloud frontier. Reliability is the whole product; the
   premium is the cost of trust.
2. **Is it routine, in Python / Go / TypeScript?** → run it locally. Free, private,
   no slower, and right ~4 times in 5. Review the output — at 0.83 you will see a
   failure in every handful of runs.
3. **Routine, but any other language?** → cloud. Take the cheapest current model; on
   routine work they all reach 1.00, so paying for the newest buys nothing.
4. **Need it unattended and correct first time?** → Opus 4.8, regardless.

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

### Cloud: Claude Opus 4.8 / 4.7, Sonnet 5

Run the model as shipped. The stack that matters is the agent around it; no sampling
tuning is required or recommended.

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

## Keeping this current

Each new frontier or local model release triggers a qualification pass on the standard
tasks. A stack is added only when it leads on an axis someone chooses along, and is
removed when it no longer leads on any. The measured data behind every entry lives in
the experiment records; this document holds only the conclusion.

*Next review: on the next frontier release, or the next local model that fits 64 GB and
tool-calls cleanly.*
