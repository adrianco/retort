# Brazil Bench: Qwen 3.5 vs Codex Instant

This is a two-cell, one-replicate comparison on Brazil Bench's Python
Brazilian-soccer MCP-server task. The workspace declares Go as a second
registry level, but `design.csv` selects Python only.

- `qwen35-strix`: OMP using the Qwen 3.5 27B Dense MTP model served at
  `http://192.168.1.185:8080` (the VM cannot resolve `strix.local`).
- `codex-instant`: Codex running `gpt-5.6-luna`.

## OMP prerequisite

The provider below has been added to `~/.omp/agent/models.yml` on this VM. On
another runner, add or merge it without removing existing providers.

```yaml
providers:
  strix:
    baseUrl: http://192.168.1.185:8080
    api: openai-responses
    auth: none
    discovery:
      type: llama.cpp
```

Verify OMP can make a request before spending a Brazil Bench run:

```bash
omp -p --no-session --mode json --model 'strix//home/schoch/.cache/huggingface/hub/models--unsloth--Qwen3.5-27B-MTP-GGUF/snapshots/88fb5663d646bc78e1140648e8d8cb7d3e849908/Qwen3.5-27B-UD-Q8_K_XL.gguf' 'Reply with ok.'
```

The workspace has no `stack_presets` entry because the Strix model is already
served remotely. Retort will not stop, restart, or otherwise manage it.

## Run

```bash
retort run --phase screening \
  --config experiments/schoch/experiment-52-brazil-qwen35-codex-instant/workspace.yaml \
  --design experiments/schoch/experiment-52-brazil-qwen35-codex-instant/design.csv \
  --resume
```

`evaluation.enabled` runs the Codex judge automatically after each completed
cell. Judge stdout, stderr, and invocation metadata are saved beneath each
run's `_judge/` directory.
