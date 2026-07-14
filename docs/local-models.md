# Running local models (the `omp` harness) — findings & gotchas

An engineering record of getting a **local** coding model to run as a retort
agent on a 24 GB Mac, via the `omp` ([oh-my-pi](https://github.com/can1357/oh-my-pi))
harness. **Bottom line: the harness path works end-to-end and costs $0, but no
small local model that fits a 24 GB Mac cleared both bars (tool-call format *and*
agentic capability). It is doable with a capable ~30B model on enough VRAM —
which is how the harness's author originally validated it.**

See [experiment-12](../experiments/adrianco/experiment-12/README.md) for the recorded runs.

## What the omp PR/issue told us (PR #6, issues #1–2)

The `omp` harness was contributed by @jschoch, who ran it successfully against
**local** models — but with a setup that differs from a vanilla 24 GB Mac in the
two ways that turned out to matter:

- **Server: llama.cpp**, OpenAI-compatible endpoint (he added `omp_base_url` and
  made `LLAMA_CPP_API_KEY` optional), **not Ollama**.
- **Models: ~26–32B** — Gemma-4 26B MoE, a ~31B dense model, and *"the brand new
  Qwen 3.6 works great … csv and api tasks to completion."* On an AMD R9700 (32 GB).

His result tables show local runs **completing** go/python/elixir REST-API at
`code_quality` 1.0, `test_coverage` up to 0.96, ~$0.002–0.01/run (hardware +
electricity cost model — see `playpen.local_inference_cost` in
[configuration.md](configuration.md)). He also flagged the real tax up front:
*"yak-shaving env setup is … tedious and difficult"* for agentic harnesses.

## Setup that works (verified here)

1. **Install omp:** `brew install can1357/tap/omp` (or `curl -fsSL https://omp.sh/install | sh`).
2. **Serve a model.** Two options, both OpenAI-compatible:
   - **Ollama** — *use the cask, not the formula.* `brew install ollama` (formula)
     ships **without** its `llama-server` runner, so every call 500s with
     "llama-server binary not found". `brew install --cask ollama` bundles it.
   - **llama.cpp** — `brew install llama.cpp`; `llama-server -m <model.gguf> --jinja
     -ngl <N> -c <ctx> --port 8080`. `--jinja` applies the model's real chat
     template (needed for tool-call formatting). You can point it at the GGUF
     Ollama already downloaded (`ollama show <model> --modelfile` → the `FROM`
     blob path).
3. **Declare it to omp** as a custom `openai-completions` provider in
   `~/.omp/agent/models.yml` (provider name **without** "ollama" in it, or omp
   reroutes to its built-in Ollama launcher):
   ```yaml
   providers:
     lmlocal:
       baseUrl: http://localhost:11434/v1   # Ollama; or http://127.0.0.1:8080/v1 for llama.cpp
       apiKey: ollama                        # any literal; local servers ignore it
       api: openai-completions
       auth: apiKey
       models:
         - { id: <model-id>, name: <label>, input: [text], contextWindow: 32768, maxTokens: 8192,
             cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } }
   ```
4. **Verify before a run:** `omp -p --no-session --mode json --model lmlocal/<id> "reply ok"`.
5. **retort profile:** `local_agents: { my-local: { harness: omp, model: lmlocal/<id> } }`,
   then put `my-local` in the `agent` factor.

Verified end-to-end that omp **executes** local tool calls: with `llama3.2:3b`,
`omp -p "create hello.txt …"` calls the `write` tool and the file appears, $0.

## The two things that break small local models

Getting a local model to *complete the task* needs **both**, and the small models
that fit a 24 GB Mac each miss one:

| model | size | tool-call format | agentic capability | result |
|---|---:|---|---|---|
| qwen2.5-coder:7b | 4.7 GB | ✗ emits non-standard call (`{…}` on Ollama, `<json>{…}` on llama.cpp) — **neither** parser structures it into `tool_calls` | — never engages | fail |
| llama3.2:3b | 2.0 GB | ✓ structured `tool_calls` | ✗ 3B too weak to drive the task | fail |
| devstral (24B) | 14 GB | refuses without its OpenHands scaffolding | (n/a) | fail + **Metal OOM** on GPU |

1. **Tool-call serialization.** A client (omp, or any OpenAI-style agent) only
   executes **structured** `tool_calls`. Whether a model's call gets lifted into
   that field depends on the model's output format matching the server's
   chat-template tool parser. `qwen2.5-coder:7b` emits a format neither Ollama nor
   llama.cpp `--jinja` auto-parses; `llama3.2:3b` and (per the research below) the
   bigger Qwen3/Gemma-4 models emit the right format. **This is per-model**, not a
   single-server bug — though llama.cpp gives more control (chat-template override,
   grammars) when a model needs coaxing.
2. **Capability.** Even with tool calls working, a 3B general model won't drive a
   multi-step build. The models that *complete* these tasks are ~24–32B.

3. **GPU memory (24 GB Mac).** Capable models (devstral 14 GB, qwen3-coder ~18 GB)
   **OOM on Metal** at full GPU offload — the default `iogpu.wired_limit_mb` caps
   GPU memory at ~16 GB. Fixes: `sudo sysctl -w iogpu.wired_limit_mb=22000`, reduce
   `-ngl` (partial CPU offload, slower), or run CPU-only (slowest). jschoch's
   32 GB card sidestepped this.

## Local coding models to try (mid-2026 research)

Ranked for a 24 GB Mac (~18 GB weight budget) + reliable tool-calls + agentic coding:

| model | why | fit (Q4) |
|---|---|---|
| **Devstral Small (24B)** | purpose-built for coding agents (Mistral × All-Hands/OpenHands), tuned for tool-use loops | ~14 GB (needs Metal limit raised; expects agent scaffolding) |
| **Qwen3-Coder-30B-A3B** | MoE (3B active → fast), 50.3% SWE-bench Verified on a single 24 GB GPU, "extremely stable tool calling" — jschoch's "Qwen 3.6" lineage | ~18 GB (edge) |
| **Gemma-4 (27B)** | Apr-2026; "fewer dropped tool calls, fewer malformed JSON, native function calling" | ~17 GB (jschoch saw reasoning loops on his llama.cpp build) |
| **Qwen2.5-Coder-32B** | matches GPT-4o on HumanEval; very stable tools | ~20 GB (over budget on 24 GB) |
| GLM-5.1 / DeepSeek-R1-32B / Kimi K2.6 | top-tier agentic, but want >24 GB VRAM | — |

Sources: kilo.ai open-source-models, Unsloth Qwen3-Coder guide, Morph "best Ollama
models June 2026", Ollama tool-calling docs.

## Recommended next attempt

On a 24 GB Mac: raise the Metal limit, serve **Qwen3-Coder-30B-A3B** (or Devstral
with its agent system prompt) via `llama-server --jinja` on GPU, point an omp
`openai-completions` provider at `127.0.0.1:8080/v1`, verify structured
`tool_calls` with a one-shot probe, then run the cell. The harness, scoring, and
$0 cost accounting all already work — the missing piece is purely a model+VRAM
combination that clears both bars.
