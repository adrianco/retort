# Experiment 17 — the Hermes agent vs omp, same local model (Qwen3-Coder-30B)

**Question.** [experiment-16](../experiment-16-qwen3coder/RESULTS.md) showed a local
Qwen3-Coder-30B reaches only ~0.33 pass-proportion on the easy bookshop task, and
that its dominant failure mode at small context was **omp compacting its history
mid-task**. So: does a *different agent* — **NousResearch Hermes**, whose pitch is
persistent SQLite-backed context management — do better on the identical model,
server, task, languages, and prompts? This is a controlled **agent** swap
(`agent: hermes-local` vs the exp-16 `omp` runs), everything else held constant.

**Stack.** Hermes (headless: `hermes --usage-file <ws> --yolo -m qwen3-coder-30b
-z <prompt>`) → **llama.cpp** `--jinja` serving **Qwen3-Coder-30B-A3B Q4_K_M**,
128K context, on the M5/64 GB. Same model + server as exp-16's omp runs.
`language[python, go, typescript, rust] × prompt[neutral, ATDD]`, 3 replicates,
spec-gated by opus-4.8. $0 inference.

> Credit: model choice follows **Birgitta Böckeler**'s
> [local-models writeup](https://martinfowler.com/articles/exploring-gen-ai/local-models-for-coding-experiences.html);
> the Hermes + local-serving path was unblocked by hints from **kamihack**
> (@kamihack@mastodon.cr).

---

## Result: Hermes did NOT beat omp — it was leaner but less reliable

Pass-proportion (`requirement_coverage == 1.0`), Hermes vs the omp baseline on the
same model:

| prompt | language | Hermes pass | omp pass¹ | Hermes best req | Hermes avg tokens |
|---|---|---:|---:|---:|---:|
| neutral | python | 1/3 | **3/3** | 1.00 | 0.82 M |
| neutral | go | 0/3 | 1/3 | 0.00 | 1.11 M |
| neutral | typescript | 0/3 | 0/3 | 0.00 | 1.13 M |
| neutral | rust | 0/3 | 0/3 | 0.00 | 0.55 M |
| ATDD | python | 1/3 | 1/3 | 1.00 | 0.62 M |
| ATDD | go | **1/3** | 0/3 | 1.00 | 0.74 M |
| ATDD | typescript | 0/3 | 0/3 | 0.08 | 1.19 M |
| ATDD | rust | 0/3 | 0/3 | 0.83 | 1.70 M |
| **overall** | | **0.12 (3/24)** | **~0.33** | | **0.98 M avg** |

¹ omp from exp-16 (128K neutral / 256K ATDD), same model.

- **Overall 0.12 vs omp's ~0.33** — Hermes was *worse*, driven by **Python
  regressing from omp's 3/3 to 1/3**. The one place Hermes helped: **Go under
  ATDD** (1/3 vs omp's 0/3).
- **Hermes is more token-efficient** — 0.98 M avg vs omp's ~1.4 M — so it fails
  *cheaper*, not *better*. TypeScript and Rust stay at 0, as with every local
  configuration so far.
- **`retort diagnose`: 19 GENUINE / 2 TOOLING** — the failures are real (broken
  or incomplete code), not scorer artefacts. Same plausible-but-wrong failure
  modes as exp-16.

## The caveat that matters: this is *default* Hermes, not `hermes-lcm`

This run used Hermes' **standard context compression** (summarise middle turns,
keep the first 3 and last 20) — its everyday loop. The **`hermes-lcm` plugin**
(the DAG-based SQLite "never lose a message" context engine that was the actual
reason to try Hermes) was **NOT enabled** (`plugins.enabled: []`, and it isn't on
PyPI — it needs a git install). So this measures Hermes' *baseline agent*, and the
honest read is: **swapping the agent alone, with default context handling, does
not beat omp on this model — the context-management upgrade is still untested.**

That upgrade, plus a stronger model, is the next run: **Qwen3.6-35B-A3B (MLX) via
oMLX, with `hermes-lcm` enabled** — the "best option" the original advice pointed
at. Only there can the SQLite-context hypothesis actually be judged.

*Data in `master.db`. Reproduce: `bookshop/workspace.yaml` + `design.csv`; needs
llama.cpp on :8080 and `~/.hermes/config.yaml` with an openai-compatible provider
(`api: <url>`, `api_mode: openai`) set as `default_provider`.*
