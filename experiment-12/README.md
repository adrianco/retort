# experiment-12 — a LOCAL model (Qwen2.5-Coder 7B via Ollama) on REST-API / Go

The first **local-model** run: the bookshop (REST-API CRUD) task in Go, driven by
the `omp` ([oh-my-pi](https://github.com/can1357/oh-my-pi)) harness pointed at a
local **Qwen2.5-Coder 7B** served by Ollama. `agent` is the explicit-override
path (a local model's name doesn't imply its harness), against the `claude-code`
baseline for Go on this task (experiments 1 / 6 / 7).

## Result: the integration works; the failure is a tool-call serialization gap

| agent | model | cost | result |
|---|---|---:|---|
| omp (oh-my-pi) | qwen2.5-coder:7b (local, Ollama) | **$0.00** | **fail** — tests never ran |

The harness path is fully functional — omp → Ollama → Qwen ran cleanly, at **$0**
(local inference), and retort captured token usage (~4.2 k). The model never wrote
any code, so the tests-gate failed in ~24 s. But the cause is **not** "the model
can't act as an agent."

Probing Ollama's OpenAI endpoint directly with a tool definition shows the model
**does produce the correct tool call** — given "write hello.txt", `qwen2.5-coder:7b`
returns exactly `{"name":"write_file","arguments":{"path":"hello.txt","content":"hi"}}`.
The problem: Ollama's OpenAI-compatible `/v1/chat/completions` endpoint returns
that call as **plain text in `content`**, not in the structured `tool_calls`
field. omp (like any OpenAI-style client) only executes structured `tool_calls`,
so it sees text, renders it as chat, and runs nothing — no file is written.

**Takeaway:** the limiter here is a **tool-call serialization mismatch in the
local OpenAI-compat layer**, not the model's capability or agency. `qwen2.5-coder:7b`
emits the right call; Ollama's `/v1` doesn't parse it into `tool_calls` for this
model's template. Fixes to try next: a model whose Ollama template emits proper
tool calls over `/v1`, a newer Ollama, or driving Ollama's native `/api/chat`
(which parses tool calls) instead of the OpenAI `/v1` shim.

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
