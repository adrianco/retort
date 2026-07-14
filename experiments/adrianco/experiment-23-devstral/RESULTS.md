# Experiment 23 — a different bet, not a bigger one: Devstral-24B (agent-tuned)

After [exp-22](../experiment-22-qwennext80b/RESULTS.md) showed *bigger* doesn't
help, this tries the other axis: a **smaller (24B) but agent-tuned** model —
**Devstral Small** (Mistral, fine-tuned for coding-agent tool-loops, 68%
SWE-bench). Does the *right kind* of model beat raw size/generality on our
agentic task? Same Hermes-lcm stack, mainstream 4 languages, neutral, 3
replicates, default second chance on.

**Serving-layer note (the "allow for either layer" result):** oMLX *cannot* parse
Devstral's Mistral `[TOOL_CALLS]` format (it emits the call as text; the agent
runs nothing). So Devstral is served via **llama.cpp `--jinja`**, which parses it
correctly — the first non-oMLX model in the local set. oMLX for Qwen-format
models, llama.cpp for Mistral-format; Hermes points at whichever is on `:8080`.

> Credit: Birgitta Böckeler (direction) and kamihack (the local-serving pointers).

## Result: worst local result — and it barely terminates

| language | first-try pass | repaired | crashed (non-terminating) |
|---|---:|---:|---:|
| python | 2/3 | 0 | 1 |
| go | 0/3 | 0 | 2 |
| typescript | 0/3 | 0 | 2 |
| rust | 0/3 | 0 | 2 |
| **overall** | **2/12 = 0.17** | 0 | **7/12** |

- **0.17 — the lowest local pass-proportion measured**, below the general
  Qwen3.6-35B (0.38) and even the bigger Qwen3-Coder-Next-80B (0.33). Only Python
  worked (2/3, clean — test_coverage 0.98).
- **The failure mode is non-termination: 7 of 12 runs CRASHED** at the 30-minute
  wall (even with `max_turns=30`), one Go run burning 2.8M tokens without ever
  finishing. Devstral simply doesn't stop under this agent's loop.
- **Agent-tuning did NOT beat raw size here** — but with a large asterisk (below).

## The asterisk: wrong harness

Devstral is fine-tuned for its **native OpenHands scaffolding**, not for Hermes.
Its "agent-tuning" is tuned to a *different* agent's loop, stop conditions, and
tool protocol — so running it under Hermes is Devstral on the wrong harness, and
the runaway non-termination is consistent with that mismatch. This is a fair test
of *"can you drop Devstral into our stack"* (answer: no, it doesn't transfer), but
**not** a fair test of Devstral's ceiling with its intended agent. A proper
Devstral evaluation would pair it with OpenHands — a different experiment.

## Where the model search lands

Three genuinely different bets, none beat the general model:

| model | serving | pass-prop (mainstream) | bet |
|---|---|---:|---|
| **Qwen3.6-35B-A3B** | oMLX | **0.38** | general — **the winner** |
| Qwen3-Coder-Next-80B | oMLX | 0.33 | bigger — no headroom |
| Devstral-24B | llama.cpp | 0.17 | agent-tuned — wrong harness |

**Qwen3.6-35B-A3B remains the best local stack.** The useful, durable outcome of
this leg isn't Devstral's score — it's that the stack now serves **either layer**
(oMLX for Qwen tool-format, llama.cpp for Mistral), so the *next* Mistral-family
coder (Codestral, a future Devstral) can be dropped in and measured the same way.

*Data in `master.db`. Setup: `unsloth/Devstral-Small-2507-GGUF:Q4_K_M` via
llama.cpp `--jinja` on :8080; Hermes-lcm.*
