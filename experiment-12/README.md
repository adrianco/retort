# experiment-12 — a LOCAL model (Qwen2.5-Coder 7B via Ollama) on REST-API / Go

The first **local-model** run: the bookshop (REST-API CRUD) task in Go, driven by
the `omp` ([oh-my-pi](https://github.com/can1357/oh-my-pi)) harness pointed at a
local **Qwen2.5-Coder 7B** served by Ollama. `agent` is the explicit-override
path (a local model's name doesn't imply its harness), against the `claude-code`
baseline for Go on this task (experiments 1 / 6 / 7).

## Result: the integration works; two separate things break the local models

| agent | model | cost | result | why |
|---|---|---:|---|---|
| omp (oh-my-pi) | qwen2.5-coder:7b (local, Ollama) | **$0.00** | **fail** | tool-call **format** |
| omp (oh-my-pi) | llama3.2:3b (local, Ollama) | **$0.00** | **fail** | agentic **capability** |

The harness path is fully functional — omp → Ollama ran cleanly at **$0** (local
inference) and retort captured token usage. Verified end-to-end that omp *does*
execute local tool calls: with `llama3.2:3b`, `omp -p "create hello.txt …"`
calls the `write` tool and the file appears. So the failures below are about the
**models**, not the integration — and they are two distinct failures:

**1. qwen2.5-coder:7b — tool-call format.** Probed directly, the model produces
the intended call as text — `{"name":"write_file","arguments":{…}}` — but Ollama
returns it in the `content` field, not the structured `tool_calls` field, on
**both** the OpenAI `/v1/chat/completions` endpoint **and** native `/api/chat`,
*even though the model advertises a `tools` capability*. It emits bare JSON
instead of the `<tool_call>…</tool_call>`-delimited output its Ollama template
expects, so Ollama can't lift it into `tool_calls`. omp (per oh-my-pi
`docs/provider-streaming-internals.md`, which maps structured streaming
`tool_calls` only — no generic text-to-tool-call recovery) sees text and runs
nothing. The model never even attempts the build.

**2. llama3.2:3b — agentic capability.** This model's tool calls *do* serialize
correctly (Ollama returns proper `tool_calls`; the hello.txt probe works). But on
the real bookshop task the 3B general model doesn't drive the loop — it makes no
tool calls, reads no files, writes no code. Tool format fixed, capability
insufficient.

**Takeaway:** a usable local coding agent needs **both** (a) a model whose tool
calls Ollama can structure into `tool_calls`, **and** (b) enough capability /
agentic tuning to actually drive a multi-step task. `qwen2.5-coder:7b` clears (b)'s
intent but fails (a); `llama3.2:3b` clears (a) but fails (b). Neither small local
model clears both. Worth trying next: a capable ~30B model (Qwen3-Coder-30B-A3B,
Devstral) on enough VRAM.

For the full setup (Ollama cask vs llama.cpp `--jinja`), the per-model tool-call
findings, the 24 GB-Mac GPU-memory (Metal) constraint, and the researched model
shortlist, see [`docs/local-models.md`](../docs/local-models.md).

## Reproduce

See the [Local / self-hosted models](../README.md#local--self-hosted-models-via-the-omp-harness-oh-my-pi)
section for the verified Ollama (cask, not formula) + `omp` `openai-completions`
provider setup. Then:

```bash
export PATH="/opt/homebrew/bin:$HOME/go/bin:$PATH"
PYTHONPATH=src .venv/bin/python -c 'from retort.cli import main; main()' run \
  --phase screening --config experiment-12/bookshop/workspace.yaml \
  --design experiment-12/bookshop/design-qwen-go.csv --replicates 1 --resume
```
