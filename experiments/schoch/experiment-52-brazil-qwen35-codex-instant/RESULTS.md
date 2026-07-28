# Results: Brazil Bench Qwen 3.5 vs Codex

Run date: 2026-07-26. This is a smoke comparison, not a statistical result:
one Python replicate per harness on the Brazilian-soccer MCP-server task.

| Implementation arm | Requirement coverage | Code quality | Test coverage | Maintainability | Defect rate |
|---|---:|---:|---:|---:|---:|
| OMP + Strix Qwen 3.5 27B Dense MTP | 1.00 | 0.62 | 0.81 | 0.82 | 0.44 |
| Codex `gpt-5.6-luna` | 1.00 | 0.67 | 0.70 | 0.56 | 0.01 |

Both cells completed and passed the requirement gate. Each was evaluated with
the independent Codex judge `gpt-5.6-terra`; its raw stdout, stderr, and
invocation metadata are retained in the private run archive under `_judge/`.
The `assessment.json` `model` field names the implementation model, not the
judge; use `_judge/attempt-*.json` to audit the actual judge model.

## Reproduction notes

- The VM cannot resolve `strix.local`; OMP reaches the server at
  `192.168.1.185:8080`.
- The llama.cpp server exposes the Qwen Q8 GGUF under its full filesystem model
  ID. The OMP profile records that exact ID, instead of a friendly alias.
- The `strix` OMP provider is user-local (`~/.omp/agent/models.yml`) and is not
  committed. [README.md](README.md) contains the required provider block.
- The generated database and run archives remain private and uncommitted. This
  file records the outcome needed for a PR review and for Adrian's handoff.
