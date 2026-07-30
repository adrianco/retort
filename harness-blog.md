# The Stack Under the Model: oMLX, llama.cpp, Hermes, and Why There Are So Many

Most benchmarks answer "which *model* is best?" Retort insists that's the wrong unit. A coding result is produced by a whole **stack** — and the model is only one layer of it:

> **language × model × weights-format × serving engine × agent/harness × context engine × sampling × prompt**

Change any layer and the numbers move. TypeScript went from failing to 1.00 on the local 80B by raising *one context-engine knob* — same model, same weights. So before the results make sense, you need a map of the layers. This post is that map: what each piece is, where it came from, what competes with what, how they stack, and why the zoo is so crowded. Then it explains the **metaharness** — the part of Retort that turns the harness *itself* into a variable you can measure.

If you've seen `oMLX`, `llama.cpp`, `Hermes`, `GGUF`, `omp`, `lcm`, or `OpenRouter` fly past in the other blogs and nodded along without quite knowing what they are, start here.

---

## The stack, top to bottom

Read this from the bottom up — each layer sits on the one below it:

```
┌─────────────────────────────────────────────────────────────┐
│  PROMPT / METHODOLOGY   "write tests first" · BDD · terse    │  ← how you ask
├─────────────────────────────────────────────────────────────┤
│  AGENT / HARNESS        claude-code · Hermes · gemini · omp   │  ← the ReAct loop:
│                         opencode                             │    read → edit → run → repeat
├─────────────────────────────────────────────────────────────┤
│  CONTEXT ENGINE         lcm (compaction) · sampling knobs     │  ← what the model "sees"
├─────────────────────────────────────────────────────────────┤
│  SERVING ENGINE         oMLX · llama.cpp · Ollama · cloud API │  ← turns weights into tokens
├─────────────────────────────────────────────────────────────┤
│  WEIGHTS + FORMAT       safetensors · GGUF · MLX  (a model    │  ← the numbers on disk
│                         at some quantization, e.g. 4-bit)     │
├─────────────────────────────────────────────────────────────┤
│  HARDWARE               Apple Silicon · NVIDIA · a cloud GPU  │  ← what runs the math
└─────────────────────────────────────────────────────────────┘
```

"Which model is best" only asks about one band in the middle. Retort measures the column. The rest of this post walks the layers where the confusing names live — **weights, serving, agent, context** — and then the metaharness, which makes the *agent* layer a factor you can sweep.

---

## Layer 1: weights and their formats — safetensors, GGUF, MLX

A model is a big pile of numbers (weights). How those numbers are *stored on disk* is a surprising source of fragmentation, because the file format is tied to the engine that reads it.

- **safetensors** — the neutral, framework-agnostic format models are usually published in (it replaced the old, unsafe pickle format). Both of the local formats below are usually *converted from* safetensors.
- **GGUF** — the format used by **llama.cpp**. A single self-contained file that bundles the weights, the tokenizer, and metadata, at a chosen **quantization** (e.g. `Q4_K_M` ≈ 4-bit). Designed to run well on CPUs and non-CUDA GPUs.
- **MLX** — Apple's format, produced for **Apple's MLX framework**. MLX is Apple's array/ML library for Apple Silicon; it exploits the Mac's *unified memory* (CPU and GPU share the same RAM), which is why a 64 GB Mac can hold a 42 GB model that would otherwise need a datacenter GPU.

**Quantization** is the other axis here: the same model shipped at 4-bit is a quarter the size of 16-bit and runs far faster, at some accuracy cost. When you see `Qwen3-Coder-Next-4bit` (≈42 GB) that's "the 80B model, MLX format, 4-bit."

Why two local formats (GGUF and MLX) for the same models? Because each is glued to a different engine, which is the next layer.

---

## Layer 2: the serving engine — oMLX vs llama.cpp vs Ollama vs the cloud

The serving engine is the program that loads the weights and turns your prompt into tokens, usually exposing an **OpenAI-compatible HTTP endpoint** (`POST /v1/chat/completions`) so anything that speaks that protocol can drive it. This is the layer with the most competitors, because it's where hardware, format, and performance all collide.

- **llama.cpp** — the foundational open-source local engine, written in C/C++ by Georgi Gerganov. It reads **GGUF**, runs on almost anything (CPU, CUDA, and Apple's **Metal** GPU API), and defined the format the rest of the ecosystem converged on. Most local tooling is either llama.cpp or a wrapper around it. Its server binary is `llama-server`; Retort's `llamacpp` backend drives it with `--jinja` so the model's own chat/tool template is applied.
- **Ollama** — a friendly daemon + model registry *built on top of* llama.cpp (`ollama run qwen`). It made local models one-command easy and is how most people first run one. Retort's earliest local attempt used it (see below) and moved on.
- **oMLX** — a local server for **MLX**-format models on Apple Silicon, OpenAI-compatible on `127.0.0.1:8080`. It's the MLX-world counterpart to llama.cpp: same job (weights → tokens over HTTP), different format and a Metal/MLX-native path tuned for Macs. Retort restarts it at each experiment boundary and records the *effective* settings in `provenance.json`.
- **cloud APIs** — for Opus, Gemini, GPT, etc. you don't run a serving engine at all; a provider runs it and you rent tokens. Same OpenAI-shaped protocol, so the layers above don't care whether the tokens came from your laptop or a datacenter.

**What competes with what:** llama.cpp (GGUF) and oMLX (MLX) are the two serious *local* engines, split mostly by format and hardware heritage — GGUF/llama.cpp is the cross-platform default, MLX/oMLX is the Apple-Silicon-native path. Ollama competes on *ease*, not capability (it *is* llama.cpp underneath). Retort now supports **both** local engines via a `serving.backend: omlx | llamacpp` switch, precisely because neither dominates: some models ship only as MLX, some only as GGUF, and some new architectures land in one engine months before the other. That "which engine has this architecture yet?" gap is a recurring reason a promising model can't be tested — it's a serving-layer problem, not a model one.

---

## Layer 3: the agent / harness — claude-code, Hermes, gemini, opencode, omp

A served model just answers messages. To *build software* it needs a loop that reads files, writes edits, runs the tests, reads the failures, and tries again — the **agentic loop** (often "ReAct": reason → act → observe, repeat). That loop is the **agent / harness**, and it's a real, swappable layer: the same model behaves differently under different harnesses because they differ in how they present tools, when they retry, and how they manage the conversation.

The harnesses Retort supports:

- **`claude-code`** — Anthropic's Claude CLI. Retort's default, and it doubles as the impartial **spec-gate judge** that grades every run (so an independent model scores all agents fairly, even non-Claude ones).
- **`gemini`** — Google's [Gemini CLI](https://github.com/google-gemini/gemini-cli), used for `gemini-*` models. The agent usually *follows from the model id*: list a Claude id and you get claude-code, a Gemini id and you get the Gemini CLI.
- **`Hermes`** — the harness Retort uses to drive **local** models (via oMLX). It's the featured local path: Hermes runs the ReAct loop and manages context (its context engine is `lcm`, below) while oMLX serves the tokens. *Note:* here "Hermes" is the **agent**, not a model — the model underneath is Qwen.
- **`opencode`** — another open agent harness Retort can drive.
- **`omp`** — [oh-my-pi](https://github.com/can1357/oh-my-pi), an early community-contributed local harness (it talked to **llama.cpp**, not Ollama). It's documented as a **legacy** path — the first, honest dead-end on a 24 GB Mac before the Hermes + oMLX stack became the featured one.

**Why the agent is its own layer (and its own zoo):** each vendor ships the harness tuned for its own model, and open harnesses exist to run *any* model. They genuinely differ — a weak model can pass under a forgiving harness and fail under a strict one — which is exactly why "which harness?" deserves measurement rather than assumption. That's what the metaharness (last section) is for.

---

## Layer 4: the context engine and sampling — the knobs that quietly decide everything

Two smaller layers sit between the agent and the model, and they've caused more wrong conclusions in this project than any model choice.

- **The context engine (`lcm`)** decides *what the model actually sees*. An agentic coding session quickly grows past the model's context window, so the engine **compacts** older turns to make room. Hermes's engine is `lcm`, and its key knob is `context_threshold` — the fraction of the window at which it compacts. At the default `0.35` it compacts at ~92K tokens and the 80B intermittently *stalls*; raised to `0.9` ("full context") the same model runs Python, Go, **and TypeScript at 1.00**. Same weights, same engine — a different threshold. This is the single clearest example of a non-model layer deciding the result.
- **Sampling** — `temperature`, `top_p`, `top_k`, `repetition_penalty`: how randomly the next token is picked. Retort learned the hard way that the oMLX *default* `temperature = 1.0` roughly halved local reliability, and that a `repetition_penalty ≠ 1.0` (even a value a model's own card recommends) can derail the multi-turn tool loop into stalls. These are recorded per run and held fixed on purpose.

- **Thinking level** — how much reasoning the model does *before* it acts. Claude Code exposes it as `--effort low|medium|high|max`, and Retort now carries it as an `effort` factor, the newest entry in this list. Raising Opus 4.8 from `default` to `max` on a fixed task costs about **1.4× the agentic turns and 2× the tokens** — a real lever, though a first single-run measurement suggested a far larger one (2× turns, 5× tokens) and **failed to replicate**: two runs of that identical cell came out 33 turns and 14. Treat single runs of an agentic cell as noisy. Notably, reliability did **not** move at all — every effort level scored 1.00 on the routine task, so on easy work the knob buys cost, not correctness.

  Every result published before this factor existed ran at whatever the CLI chose — which, measured, is **not** any of the named levels. That is why `default` is kept as an explicit level rather than folded into `medium`: it is the historical baseline, and mislabelling it would silently rewrite the back catalogue.

The lesson threaded through the whole project: **a set-but-unverified knob in one of these quiet layers produces confident, wrong results.** Retort's provenance records the *effective* value of each, because the config file's value and the value the model actually ran at have diverged more than once. The corollary is that a knob nobody *records* is worse still — thinking level was an uncontrolled variable across every experiment here until it was made a factor, and [versions-blog.md](versions-blog.md) now says so in place of the conclusion it had drawn without it.

---

## So why *are* there so many?

The zoo isn't accidental. Several independent forces each spawn alternatives:

| Force | What it splits | Example |
|---|---|---|
| **Hardware lineage** | serving engine + format | Apple-Silicon/unified-memory → MLX/oMLX; cross-platform/CUDA → GGUF/llama.cpp |
| **Format lock-in** | which engine can even load a model | a model published only as MLX can't run on llama.cpp, and vice-versa |
| **New architectures** | which engine supports them *first* | a brand-new model's arch may land in one engine months before the other — the usual reason a candidate is "blocked" |
| **Ease vs control** | wrapper vs raw engine | Ollama (easy) wraps llama.cpp (control); one command vs every flag |
| **Vendor vs open** | the agent/harness | claude-code/gemini ship per-vendor; Hermes/opencode/omp run *any* model |
| **Cost & privacy** | local vs cloud | a 64 GB Mac runs the 80B for \$0 and offline; the cloud rents frontier capability per token |
| **Quantization** | size vs accuracy | the same model at 4-bit / 6-bit / 8-bit trades RAM and speed against quality |

None of these layers *dominates*, so none of the others disappear. That's the whole reason Retort measures the stack instead of the model: the interesting question is usually "which *combination* is best for **my** language, task, and budget?" — and the answer moves as new engines, formats, and harnesses land.

**Where Retort's featured stacks sit today:** the free local path is **Qwen3-Coder-Next 80B, MLX 4-bit, served by oMLX, driven by Hermes with `lcm` at `context_threshold 0.9`** on a 64 GB Mac — Python/Go/TypeScript at 1.00 for \$0. The cloud path is **Claude Opus 4.8 via claude-code** for the languages and hard tasks the local stack can't yet clear. Same protocol, different columns.

---

## The metaharness: making the harness *itself* a variable

Everything above treats the harness as a fixed choice per run. But the harness is a bundle of *strategies* — and those strategies plausibly move results as much as the model does. The **[`retort_metaharness`](retort_metaharness/)** layer (a documented, experimental side-branch) makes the **agentic-orchestration harness a first-class factor** you can sweep, so a statistical analysis can say *how much of any lift is the harness versus the raw model.*

It doesn't reinvent Retort — it composes the same design generator, ANOVA, and Pareto engine — but it adds three new factors on top of the usual language/model:

### `harness_config` — the orchestration strategy (the headline factor)

| level | what it does |
|---|---|
| **base-ReAct** | plain single-agent reason→act→observe loop. The control: no tricks. |
| **self-consistency-N** | sample **N** independent solutions and majority/judge-select the best. An *accuracy* lever that costs N× the tokens (default N=5). |
| **routed** | a **cheap** model drafts; a **frontier** model takes over only on low-confidence steps. A *cost* lever — aims for comparable reliability at lower \$. |
| **+agenticow-memory** | ReAct plus a copy-on-write memory that persists agent state across steps/replicates — tests whether memory changes the outcome. |
| **+darwin-evolved-genome** | ReAct driven by a harness "genome" (prompt + tool policy) tuned by an evolutionary loop — tests whether evolution moves the needle. |

### `scaffold` — the reasoning structure wrapped around each attempt

`none` · `plan-and-solve` (plan first, then execute) · `reflexion` (attempt, self-critique, retry).

### `model` — the raw model, spanning cheap→frontier

`deepseek-v4-pro` · `glm-5.2` · `opus-4.8` · `gpt-5.2`, reached through **OpenRouter** (a unified API that routes one request format to many providers), chosen to spread from cheap to frontier so the analysis can *separate* a model effect from a harness effect.

### What it would actually test

Because a fractional-factorial design crosses **all** of these at once (rather than changing one thing at a time), the ANOVA can attribute the variance in a metric to **model vs harness vs scaffold vs language + their interactions**, and report which effects are cleanly estimated versus confounded. Concretely, it answers questions the model-only grid structurally can't:

- *Of the lift from `+agenticow-memory`, how much is the memory branching versus just the underlying model being good?*
- *Does `routed` actually hold reliability while cutting cost — i.e., does it sit on the accuracy-vs-\$ Pareto front?*
- *Is `self-consistency-5` worth 5× the tokens, or a rounding error on a task the model already nails?*
- *Is a reasoning `scaffold` a real lever or a ritual — and does that depend on model strength?* (Retort already found the sibling result that **the prompt is a lever only in proportion to how weak the model is**; the metaharness generalizes that from *prompt* to *full orchestration*.)

### It runs on your own hardware now

The original caveat was that this was **cloud-only** — OpenRouter, metered, with the `self-consistency × frontier × replicates` corner getting expensive fast. That has changed. A **`--runner local`** backend composes Retort's own Hermes + oMLX pipeline in-process, so the harness factor can be screened **on-device for \$0**:

```bash
retort-metaharness run --runner local --stacks stacks.yaml --task rest-api-crud
```

It implements the orchestration levels it *can* locally — `base-ReAct` (one attempt), `self-consistency-N` (N attempts, keep the best), and `routed` (draft on the 35B, escalate to the 80B) — and the two that genuinely have no local equivalent, `+agenticow-memory` and `+darwin-evolved-genome`, **degrade to base-ReAct and say so in the result**. That last detail matters more than it sounds: a harness level that quietly behaved like another level would show up in the ANOVA as "orchestration doesn't matter," which is a false null — the most expensive kind of wrong answer.

The OpenRouter path is still there for the frontier models; it just isn't the only way in.

### The interesting part: feeding it *measured* results

Metaharness picks a model per problem. Today it picks using **language/task heuristics**. Retort's whole output is a measurement of exactly that — which stack actually passes, per language, per task size, at what cost. So the natural move is to hand metaharness the results instead of the heuristic:

```bash
retort report optimal --routing-json routing.json
```

That emits, for each language and each of the two task sizes, **the cheapest stack whose measured pass-proportion clears its bar** — or an explicit `null` where nothing measured qualifies (which is *not* the same as "unmeasured," and a consumer must not treat it as "use the default"). The intent is that metaharness routes on evidence, and that the adapter goes back upstream to the metaharness project rather than living here.

**Status, stated plainly:** the producer is implemented and tested; **nothing consumes it yet.** There is no `tooling: metaharness` level in the code — `tooling` handles `beads` and `graphify` only — and the schema still needs agreeing with the metaharness maintainer. So the honest summary is *a correct, tested feed with no consumer.* The full interface spec, the JSON contract field-by-field, and the three things still unbuilt are in [`docs/metaharness.md`](docs/metaharness.md); the staged plan is in [`docs/future-experiments.md`](docs/future-experiments.md).

One more caveat worth keeping: the real orchestration logic for the *OpenRouter* path lives in an **external solver** the adapter shells out to. Without it that path runs a \$0 stub — which is deliberately labelled a fixture, not a benchmark, so nobody quotes its numbers as a model result.

---

## Takeaway

There are "so many" harnesses and engines because at least six independent forces — hardware, format, new architectures, ease-vs-control, vendor-vs-open, and cost-vs-privacy — each keep their own alternatives alive, and no layer has a winner that retires the others. The practical consequence is the thesis of this whole repo: **don't benchmark the model, benchmark the stack.** The model is one band in a tall column, and the quiet layers under and around it — the serving engine, the context threshold, the sampling defaults, and the orchestration strategy — routinely decide the result. The metaharness is Retort turning the last of those, the orchestration layer, from an assumption into a measurement.
