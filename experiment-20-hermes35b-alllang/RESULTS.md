# Experiment 20 — the best local stack across every language

Best prompt (`neutral`, from [exp-19](../experiment-19-hermes35b-prompts/RESULTS.md))
× **all 9 languages** retort has data for, on the best local stack (**Hermes +
`hermes-lcm` → oMLX → Qwen3.6-35B-A3B MLX**), 3 replicates, spec-gated by
opus-4.8. This is the widest local-model reach test: does the stack that cracked
TypeScript extend to Clojure, Java, C#, Elixir, and Erlang? (`max_turns` was 30 to
keep runs terminating.)

> Credit: Birgitta Böckeler (direction) and kamihack (the oMLX/model/tool-template
> pointers behind this stack).

## Result: a hard mainstream/niche split

| language | pass | completed | best req_cov | note |
|---|---:|---:|---:|---|
| python | 1/3 | 2/3 | 1.00 | |
| go | 1/3 | 2/3 | 1.00 | |
| typescript | 0/3 | 0/3 | **0.92** | near-miss |
| **rust** | **1/3** | 1/3 | 1.00 | **first-ever local Rust pass** |
| clojure | 0/3 | 0/3 | **0.00** | wall |
| java | 0/3 | 0/3 | **0.00** | wall |
| csharp | 0/3 | 0/3 | **0.00** | wall |
| elixir | 0/3 | 0/3 | **0.00** | wall |
| erlang | 0/3 | 0/3 | **0.00** | wall |
| **overall** | **3/27 = 0.11** | | | |

- **The mainstream four still carry, and Rust passed for the first time** — with
  the tighter `max_turns=30`, one Rust run finally terminated *and* passed
  (`req_cov 1.00`), where every prior local config either failed or crashed on
  Rust. Python/Go each landed 1/3, TypeScript missed but at 0.92.
- **The five new languages are a hard wall: 0/15, and `retort diagnose` confirms
  all GENUINE** (0 tooling) — the toolchains are installed and working; the model
  simply produces broken or incomplete code in Clojure, Java, C#, Elixir, and
  Erlang, never reaching a scoreable build. `best req_cov 0.00` across the board
  means the spec-gate never even had runnable code to grade.
- **Overall 0.11** — dragged down entirely by those five zeros. The stack's
  competence is confined to the **mainstream languages** it saw most in training;
  it collapses on the less-common ones. That's the clean finding: a local model's
  *language reach* is far narrower than the cloud frontier's, independent of the
  agent/context machinery around it.

## Caveat: `max_turns=30` and variance

This grid ran at `max_turns=30` (set to stop Rust's non-termination). That helped
Rust (its first pass) but likely capped the mainstream cells shorter than exp-18's
looser budget — Python came in at 1/3 here vs 3/3 in exp-18, and TypeScript at
0/3 (0.92) vs 1/3. With single-digit replicates on a noisy local model, treat the
*mainstream* per-cell numbers as indicative; the firm, robust result is the
**mainstream-vs-niche wall**, which is unambiguous (15/15 niche failures, all
genuine).

The many near-misses here (TypeScript at 0.92; the completed-but-failed cells)
are exactly the input for **exp-21**: give each near-miss a second try seeded with
the evaluation feedback and measure the lift.

*Data in `master.db`. `bookshop/workspace.yaml` + `design.csv`; needs the 9-language
toolchains on PATH.*
