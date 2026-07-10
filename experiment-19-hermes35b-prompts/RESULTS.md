# Experiment 19 — prompt sweep on the best local stack (Python only)

Holding the exp-18 "best option" stack fixed (**Hermes + `hermes-lcm` → oMLX →
Qwen3.6-35B-A3B MLX**) and `language = python`, vary the **prompt** across all four
methodologies to add TDD and BDD to the record and pick the best prompt for the
cross-language run (exp-20). 3 replicates each, spec-gated by opus-4.8.

> Credit: Birgitta Böckeler (direction) and kamihack (the oMLX/model/tool-template
> pointers behind this stack).

## Result: neutral and BDD tie on reliability; neutral is far cheaper

| prompt | pass | completed | avg test-cov | avg tokens |
|---|---:|---:|---:|---:|
| **neutral** | **2/3** | 2/3 | 0.96 | **0.40 M** |
| **BDD** | **2/3** | 2/3 | 0.97 | 1.03 M |
| TDD | 1/3 | 1/3 | 0.98 | 0.54 M |
| ATDD | 0/3 | 2/3 | 0.41 | 0.73 M |

- **neutral and BDD tie for best** — both 2/3 pass at ~0.96–0.97 coverage — but
  **neutral gets there at ~2.5× fewer tokens** (0.40 M vs 1.03 M). BDD's
  behaviour-scenario structure buys nothing over neutral on reliability here,
  only cost.
- **ATDD is worst again** (0/3, coverage 0.41) — the *fourth* experiment in a row
  where the front-loaded acceptance-test discipline hurts a local model. TDD sits
  in the middle (1/3).
- Note the variance: exp-18 saw python/neutral at 3/3, exp-19 at 2/3 — single-
  digit replicate counts on a local model are noisy (a known caveat throughout).

**Chosen for exp-20 (best prompt × every language): `neutral`** — tied for the
best pass-proportion, the most token-efficient, and the most consistent performer
across exp-16/17/18. (BDD is the co-winner; TDD/ATDD are not competitive here.)

*Data in `master.db`. `bookshop/workspace.yaml` + `design.csv`; prompts in
`bookshop/prompts/`.*
