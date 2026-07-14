# Experiment 21 — self-repair with evaluation feedback

Take every non-passing cell of [exp-20](../experiment-20-hermes35b-alllang/RESULTS.md)
and give it a **second attempt, seeded with its own prior code + a FEEDBACK.md**
(the requirement checklist + what the independent evaluation found wrong), on the
same stack (Hermes-lcm + Qwen3.6-35B via oMLX). Run as a normal retort experiment
via `retort run --repair-from experiment-20-.../bookshop` → its own `retort.db`.

**Scoring (user rule):** a run that only passes on the second try counts **0.5**
toward pass-proportion (a first-try pass = 1.0); quality/coverage metrics keep
their true final values. (This is now retort's **default** behavior for any model
— see the `--no-second-chance` opt-out; exp-21 is the demonstration.)

> Credit: Birgitta Böckeler (direction) and kamihack (the oMLX/model/tool-template
> pointers behind this stack).

## Result: feedback doubles effective reliability — but only where the model is competent

| language | exp-20 first-try (×1.0) | repaired by feedback (×0.5) | **repair-adjusted pass-prop /3** |
|---|---:|---:|---:|
| python | 1/3 | **+2** | **0.67** |
| go | 1/3 | **+2** | **0.67** |
| rust | 1/3 | 0 | 0.33 |
| typescript | 0/3 | +1 | 0.17 |
| java | 0/3 | +1 | 0.17 |
| clojure | 0/3 | **0** | **0.00** |
| csharp | 0/3 | **0** | **0.00** |
| elixir | 0/3 | **0** | **0.00** |
| erlang | 0/3 | **0** | **0.00** |
| **overall** | **3/27 = 0.11** | +6 repaired | **6.0/27 = 0.22** |

- **One round of feedback doubles the effective pass-proportion, 0.11 → 0.22.**
  That's a real, cheap lift: the model *can* fix a lot of its own first-shot
  mistakes once it's shown the independent evaluation it never saw.
- **But the lift is entirely in the mainstream languages.** Python and Go had
  **every** first-shot failure rescued (2/2 each) — jumping to 0.67 adjusted.
  TypeScript and Java each got one repair. These were **first-shot problems**:
  the model knew the language, just missed something the first time, and the
  feedback closed the gap.
- **The niche-language wall is a TRUE capability ceiling, not a first-shot
  problem.** Clojure, C#, Elixir and Erlang were handed the *exact* evaluation
  feedback — which requirements were unmet, what the build/test errors were — and
  **still could not fix them: 0 rescued across all of them.** The monitor made it
  vivid: the repair attempts burned real time (7–30 min each) and still produced
  code that didn't build. You can't repair what you fundamentally can't write.

## How to read it

Self-repair is a genuine, low-cost reliability multiplier — worth having on by
default — but it **amplifies existing competence rather than creating new
competence.** Feed a model the evaluation and it will patch the languages it
already knows (mainstream) most of the way to done; hand it the same feedback in
a language it can't write (the niche BEAM/Lisp/JVM/dotnet set) and nothing moves.
So the exp-20 lesson stands and sharpens: a local model's **language reach** is
the hard limit, and no amount of feedback, agent, or context machinery extends
it — it only helps *within* reach.

*Data in `master.db` (`second_try` column flags the half-credit runs). Base:
exp-20. Setup identical to exp-18/20.*
