# experiment-12 — a LOCAL model (Qwen2.5-Coder 7B via Ollama) on REST-API / Go

The first **local-model** run: the bookshop (REST-API CRUD) task in Go, driven by
the `omp` ([oh-my-pi](https://github.com/can1357/oh-my-pi)) harness pointed at a
local **Qwen2.5-Coder 7B** served by Ollama. `agent` is the explicit-override
path (a local model's name doesn't imply its harness), against the `claude-code`
baseline for Go on this task (experiments 1 / 6 / 7).

## Result: the integration works; the small local model doesn't

| agent | model | cost | result |
|---|---|---:|---|
| omp (oh-my-pi) | qwen2.5-coder:7b (local, Ollama) | **$0.00** | **fail** — tests never ran |

The harness path is fully functional — omp → Ollama → Qwen ran cleanly, at **$0**
(local inference), and retort captured token usage (~4.2 k). But the 7B model
**failed to act as an agent**: given the task, it made **zero tool calls** —
instead of `read`-ing `TASK.md` (which it had access to) and `write`-ing code, it
replied conversationally ("please provide the content of `TASK.md`"). No files
were written → nothing built → the tests-gate failed in ~24 s.

**Takeaway:** for small local models in an agentic coding harness, the limiter is
**tool-use behavior, not raw capability**. The cloud agents (Claude, Gemini) drive
the read/edit/run loop; this one wouldn't engage it at all. A larger or more
agent-tuned local model is the natural next thing to try.

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
