# Metaharness: the orchestration layer, and how Retort feeds it

**Three different things in this repo are called "metaharness."** They are related but separate, and
conflating them is the main way to get lost. This document names each one, says exactly what is
implemented versus planned, and specifies the interface between Retort and the metaharness project.

| # | Name | Lives in | Status |
|---|---|---|---|
| 1 | **The `metaharness` playpen runner** | `src/retort/playpen/metaharness_runner.py` | Implemented; **shells out to an external solver that is not in this repo** |
| 2 | **The `retort_metaharness` package** | `retort_metaharness/` (console script `retort-metaharness`) | Implemented as a separate DoE layer; 3 backends, one of which runs on our own local stack |
| 3 | **The routing feed** | `src/retort/reporting/optimal.py` + `retort report optimal --routing-json` | **Producer implemented and tested; nothing in this repo consumes it yet** |

---

## What metaharness actually is (the concept)

Metaharness is an **optimization and memory layer that chooses which harness/model to run for a given
problem**, rather than a fixed model you point at everything. Its levers are things like difficulty
routing (draft on something cheap, escalate when it looks hard), self-consistency (run N attempts, keep
the best), persistent memory across attempts, and an evolved "genome" of orchestration settings.

In Retort's vocabulary that makes it a **`tooling` factor level**, alongside `beads` and `graphify` —
not a model and not an agent. The distinction matters because the whole point of a DoE is to ask
whether the *orchestration* explains variance independently of the raw model.

Its heuristics today are language/task-based. **The interesting move is to feed it Retort's measured
results** so the choice is grounded in what actually passed, per language and per task size, rather
than in a prior — and then contribute that upstream.

---

## 1. The `metaharness` playpen runner

A `PlaypenRunner` registered under the name `metaharness`
(`src/retort/playpen/runner.py:200`), selectable from a workspace with:

```yaml
playpen:
  runner: metaharness
```

It provisions a workspace exactly like `LocalRunner` (TASK.md, `stack.json`, `git init`, support
files), then shells out to a **Node solver located via the `$METAHARNESS_SOLVER` environment
variable**, passing `--lang --model --max-steps --out metaharness-result.json`, plus `--escalate`,
`--route-difficulty` and `--memory` when the corresponding factors are set. Telemetry is read back
from `metaharness-result.json`, falling back to the last JSON line on stdout.

**The solver itself is not in this repo.** With `METAHARNESS_SOLVER` unset, every cell returns
`exit_code=1` with an explanatory stderr rather than pretending to run — so a misconfigured experiment
fails loudly instead of silently producing zeros (this repo's most expensive bug class).

Factors this runner reads beyond the usual ones:

| Factor | Levels | Effect |
|---|---|---|
| `routing` | `off`/`none`/`false` ⇒ disabled; `opus`→`opus-4.8`; `glm`→`glm-5.2`; `on`→`opus-4.8` | Difficulty-based escalation |
| `escalate` | an OpenRouter model alias | Explicit escalation target; presence also enables the difficulty router |
| `memory` | anything not in `none`/`off`/`false` | Adds `--memory` |

Model aliases are OpenRouter ids: `deepseek-v4-pro`, `glm-5.2`, `opus-4.8`, `gpt-5.2`.

Tested offline in `tests/unit/test_metaharness_runner.py` (protocol conformance, provisioning, routing
resolution, telemetry parsing) — no network and no Node required.

## 2. The `retort_metaharness` package

A **separate DoE/ANOVA methodology layer** with its own CLI (`retort-metaharness`), whose purpose is to
make the orchestration harness a first-class factor. Its factor catalog (`retort_metaharness/factors.py`):

| Factor | Levels |
|---|---|
| `model` | 4 OpenRouter (`deepseek-v4-pro`, `glm-5.2`, `opus-4.8`, `gpt-5.2`) + **2 local oMLX-served** (`qwen-80b-local`, `qwen-35b-local`) |
| `harness_config` | `base-ReAct`, `self-consistency-N`, `routed`, `+agenticow-memory`, `+darwin-evolved-genome` |
| `scaffold` | `none`, `plan-and-solve`, `reflexion` |
| `language` | python, typescript, go, rust |
| `task` | `rest-api-crud`, `cli-data-pipeline`, `brazil-bench` |

Subcommands: `factors`, `design`, `run`, `diagnose`, `analyze`, `report`, `smoke`.

### Three backends (`retort-metaharness run --runner ...`)

- **`local-stub`** — a **$0 deterministic fixture, no LLM at all**. It exists so the design/analysis
  plumbing can be exercised end to end, and it deliberately fabricates two failure modes so `diagnose`
  has something to classify. It is explicitly **not** a model benchmark; never quote its numbers.
- **`metaharness`** — shells out to `$METAHARNESS_RUNNER_CMD` as `<cmd> --cell-json cell.json --out
  result.json`. Raises at construction if the command is unset. **External solver, not in this repo.**
- **`local`** — **runs on our own stack, no OpenRouter key needed.** Requires `--stacks`. It composes
  Retort's pipeline in-process: `LocalRunner` (Hermes + oMLX) → `ScoreCollector` (`code_quality`,
  `test_coverage`) → the spec gate, with cost fixed at $0.

The `local` backend implements the harness configs it can:

| harness_config | Local behaviour |
|---|---|
| `base-ReAct` | one attempt |
| `self-consistency-N` | N attempts, keeps the best `test_coverage` |
| `routed` | drafts on the 35B, escalates to the 80B |
| `+agenticow-memory` | **N/A locally — degrades to base-ReAct, and says so** |
| `+darwin-evolved-genome` | **N/A locally — degrades to base-ReAct, and says so** |

Degrading loudly rather than silently is deliberate: a harness level that quietly behaves like another
level would show up in the ANOVA as "orchestration doesn't matter," which is a false null.

Tests: `tests/test_metaharness_local.py` (5, mocked attempts) and `tests/test_metaharness.py`
(factors/design/runner-glue/analysis/diagnose/report). No network in either.

## 3. The routing feed — the actual Retort → metaharness interface

This is the piece that makes metaharness's choices **mechanistic rather than heuristic**.

### Producing it

```bash
retort report optimal --routing-json routing.json    # or `-` for stdout
```

Backed by two functions in `src/retort/reporting/optimal.py`:

- **`per_language_routing(conn, task)`** — for each language, the **cheapest featured stack whose
  measured pass-proportion clears its own pass-bar**, or `null` if nothing qualifies.
- **`routing_config(conn)`** — wraps that for both tasks into the payload below.

### The contract

```json
{
  "source": "retort report optimal (master.db)",
  "objective": "cheapest featured stack per language/task that clears its pass-bar",
  "routes": {
    "rest-api-crud":     { "<language>": { "stack": "Claude Opus 4.8",
                                           "models": ["claude-opus-4-8", "opus-4.8"],
                                           "cost": 1.2778, "pass": 1.0, "n": 1 } },
    "brazil-soccer-mcp": { "<language>": null }
  }
}
```

Field semantics — these are the part a consumer must not guess at:

| Field | Meaning |
|---|---|
| `routes.<task>.<language>` | `null` means **nothing measured clears the bar** for that cell. It does *not* mean "unmeasured" and must not be treated as "use the default." |
| `stack` | Human-readable featured-stack name |
| `models` | **All model id spellings** that map to this stack. Match against any of them — the same model appears under multiple ids across experiments (e.g. `claude-opus-4-8` and `opus-4.8`). |
| `cost` | Mean USD per run for that cell. **`0.0` for local stacks** by explicit override — local marginal cost is zero, so cost alone will always prefer local where it qualifies. |
| `pass` | Measured pass-proportion (`requirement_coverage == 1.0` fraction) |
| `n` | Replicate count behind `pass`. **Read this.** Several cells are `n=1`; a 1.00 at n=1 is much weaker evidence than a 1.00 at n=9, and exp-47 is a worked example of an n=3 result that did not survive n=5. |

Two tasks only — `rest-api-crud` (routine) and `brazil-soccer-mcp` (hard) — because those are the two
task sizes with enough coverage to route on.

### Where the candidates come from

Candidate stacks are the **hand-curated `FEATURED_STACKS` list**, not a plain `GROUP BY`. The module
docstring explains why: `master.db` has no sampling or context columns and ~250 rows have a blank
model, so "the qualified config" cannot be reconstructed from the data alone. Each entry declares a SQL
predicate selecting the rows that represent it, plus a `pass_bar` (1.00 for cloud, 0.50 for local,
which buys $0 at a reviewed lower bar).

> ⚠️ **Enumerate a stack by matching its model, never by excluding the others.** The 35B's predicate
> was once "any local model except the 80B," which silently adopted every newly added local model —
> exp-47's 15 gpt-oss-20b runs were counted as 35B results and moved published per-language figures,
> including masking the fact that the 35B fails TypeScript outright. Two regression tests now pin this
> (`tests/unit/test_routing_feed.py`, `tests/unit/test_optimal.py`).

### Status and what is left

**Implemented and tested on the Retort side.** `tests/unit/test_routing_feed.py` asserts the JSON shape.

**Not yet built:**

1. **A `tooling: metaharness` factor level.** There is no such level in the code today — `tooling`
   handles `beads` and `graphify` only. The level would need to install metaharness into the playpen,
   hand it `routing.json`, and let it pick the model per cell.
2. **Agreement with the metaharness maintainer (ruvnet) on the schema**, so the contract above is a
   shared one rather than something Retort emits into the void.
3. **The first factor sweep** — `tooling{none, metaharness}` — to test the actual hypothesis: *does
   result-driven routing lower cost at equal pass-proportion?* That is the question the whole
   integration exists to answer, and it is unanswered.

Until (1)–(3) land, the routing feed is a **producer with no consumer**: correct, tested, and unused.

---

## Which one should I use?

- Measuring **models/languages/stacks** — plain `retort run`. Not this.
- Measuring whether **orchestration** matters, on our own hardware for $0 — `retort-metaharness run
  --runner local --stacks stacks.yaml`.
- Measuring orchestration against **OpenRouter models** — `--runner metaharness` plus the external
  solver and `$OPENROUTER_API_KEY`.
- **Feeding measured results into metaharness's routing** — `retort report optimal --routing-json`,
  then see "what is left" above.

Related: [`future-experiments.md`](future-experiments.md) for the staged plan,
[`../harness-blog.md`](../harness-blog.md) for what the harness layers are and why there are so many.
