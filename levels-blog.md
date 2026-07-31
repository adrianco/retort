# Thinking Level: What Opus Actually Does With the Extra Time

*Published 2026-07-31 · updated 2026-07-31 — Adrian Cockcroft*

`--effort low|medium|high|xhigh|max` is the newest and largest cost lever in retort, and the least understood. [versions-blog.md](versions-blog.md) established *that* it costs; this page is about *what the model does* with the time, read out of the archived agent logs rather than inferred from the totals.

The short version: below the top of the dial Opus 5 **writes more**. At the top it stops writing and starts **revising** — re-reading its own code, re-running its own tests, editing what it already wrote. That switch is where the cost curve leaves the time curve, and on the routine task it buys nothing the gate can see.

Data: `adrianco/experiment-55`, Claude Opus 5 and GPT-5.6 Terra, python and go, five effort levels, 2 replicates on the routine task (bookshop) and 1 on the hard task (brazil). Every figure below is recomputed from the per-run databases and the archived `_agent_stdout.log` files.

---

## The dial, end to end

Claude Opus 5 on the routine task, python, mean of 2 replicates per level:

| `effort` | wall | cost | turns | tool calls | tokens | src lines | tests | `test_coverage` | `requirement_coverage` |
|---|---|---|---|---|---|---|---|---|---|
| low | 2.0 min | $0.76 | 16 | 15 | 452,552 | 192 | 10 | 0.98 | **1.00** |
| medium | 3.1 min | $1.04 | 21 | 20 | 648,077 | 219 | 18 | 0.98 | **1.00** |
| high | 5.9 min | $1.68 | 29 | 28 | 1,083,234 | 458 | 60 | 0.98 | **1.00** |
| xhigh | 11.9 min | $2.55 | 42 | 40 | 1,714,098 | 574 | 51 | 0.99 | **1.00** |
| max | **35.1 min** | **$19.21** | **175** | **220** | **15,814,628** | 944 | 78 | 0.99 | **1.00** |

Everything scales monotonically — time, cost, turns, tokens, lines, tests. The one column that never moves is the one the project scores on: **`requirement_coverage` is 1.00 at every level**. The task is fully implemented in two minutes for 76 cents, and it is still exactly fully implemented 33 minutes and $19 later.

Note the curve shapes differ. Wall clock grows **17×** from low to max; cost grows **25×**; tokens grow **35×**. Cost outruns time because the work per turn intensifies, not just the number of turns.

---

## The behavioural switch: from writing to revising

The totals don't say what changed. The tool mix does. Same runs, mean tool calls per run:

| `effort` | Write | Edit | **Edit:Write** | Read | Bash |
|---|---|---|---|---|---|
| low | 5 | 2 | 0.30 | 1 | 8 |
| medium | 5 | 4 | 0.80 | 1 | 10 |
| high | 12 | 3 | 0.24 | 2 | 11 |
| xhigh | 18 | 6 | 0.33 | 2 | 14 |
| max | 26 | **64** | **2.43** | **36** | **86** |

Through `xhigh` the pattern is stable and unremarkable: Opus writes files, runs the tests a handful of times, and stops. Writes outnumber edits roughly 3:1. More effort simply means more of the same — `high` writes 12 files where `low` wrote 5.

At `max` the shape of the work changes. Edits outnumber writes **2.4:1**, Reads jump **18×** (2 → 36), and Bash calls jump **6×** (14 → 86). It is no longer producing a solution; it is auditing one it already has — re-reading its own modules, re-running the suite, adjusting. Tool calls per turn also rise from ~0.95 (one action per turn, all the way up the dial) to **2.02**, meaning it starts batching parallel actions.

This is where the self-imposed extras appear, and *only* here. Across the ten python runs, mutation testing, subagent delegation and a hand-written OpenAPI document occur exclusively in the two `max` runs — never at `low` through `xhigh`. That matches what the [slowest passing run](tasks-blog.md) turned out to contain: a seven-module package, unprompted `ruff` linting, and mutation testing, for a books CRUD API.

**On the hard task, it revises at every level.** The full brazil sweep (n=1 per cell):

| brazil, python | wall | cost | turns | Edit:Write | src lines | tests |
|---|---|---|---|---|---|---|
| low | 18.7 min | $8.14 | 75 | 0.93 | 2,485 | 74 |
| medium | 25.9 min | $13.94 | 126 | 1.91 | 3,397 | 165 |
| high | 59.9 min | $45.34 | 231 | 2.11 | 5,000 | 185 |
| xhigh | 53.0 min | $29.37 | 190 | 1.28 | 5,438 | 208 |
| max | 67.1 min | $58.42 | 211 | 1.79 | 5,267 | 172 |

Read this next to the routine task and the difference is the *baseline*, not a switch point. On bookshop, Edit:Write sits at 0.24–0.80 for four levels and only crosses 1.0 at `max`. On brazil it is **above 0.9 at every level, including `low`** — the hard task is revision-heavy from the start, because a 12-capability MCP server over six overlapping CSVs cannot be written correctly in one pass at any budget.

*An earlier version of this page claimed the switch point "moves two levels earlier" on the hard task. That was written when only `low`/`medium`/`high` had run, and the completed sweep does not support it — Edit:Write goes 0.93 → 1.91 → 2.11 → 1.28 → 1.79, which is noise around a high baseline at n=1, not a progression. The honest statement is the one above: hard tasks revise throughout.*

The brazil `go` arm is the same story and contains the most expensive run this project has recorded: **98.2 minutes and $85.45** at `max`, producing 8,573 lines and 142 tests — for a cell that `low` also passed, in 16 minutes for $7.03.

---

## Does any of it show up in a measured response?

Only where there was headroom. Compare the same dial in go, where the test-coverage scorer is not already pinned at the ceiling:

| `effort` | python `test_coverage` | go `test_coverage` |
|---|---|---|
| low | 0.98 | 0.73 |
| medium | 0.98 | 0.74 |
| high | 0.98 | 0.76 |
| xhigh | 0.99 | **0.87** |
| max | 0.99 | **0.88** |

Python starts at 0.98 and has nowhere to go — the extra 33 minutes move it 0.01. Go starts at 0.73 and gains **15 points**, a real and monotonic improvement. So the honest answer is not "effort buys nothing", it is: **effort buys coverage exactly where coverage is missing, and nothing where it isn't.**

Everything else is flat or worse. `requirement_coverage` is 1.00 at all ten cells. Maintainability does not improve with effort — on python it reads 0.96 at `low` and 0.89 at `max`, because 944 lines are simply more to maintain than 192.

---

## The same five names mean different things per vendor

Run the identical sweep on GPT-5.6 Terra and the dial barely registers:

| `effort` | Terra cost | Terra tokens | Opus 5 cost | Opus 5 tokens | cost ratio |
|---|---|---|---|---|---|
| low | $0.16 | 182,387 | $0.76 | 452,552 | 5× |
| medium | $0.12 | 118,504 | $1.04 | 648,077 | 9× |
| high | $0.16 | 165,724 | $1.68 | 1,083,234 | 11× |
| xhigh | $0.17 | 157,287 | $2.55 | 1,714,098 | 15× |
| max | $0.29 | 278,882 | **$19.21** | **15,814,628** | **67×** |

Terra's whole range is $0.12–$0.29 — its `max` costs 2.4× its `medium`. Opus 5's `max` costs 25× its `low`. Both score 1.00 in all ten cells.

The two CLIs accept the same five words, which makes the factor look comparable. It isn't: `max` is a mild nudge on one vendor and a regime change on the other. Any cross-vendor comparison has to pin the *level* explicitly and still report cost, because matching the name does not match the behaviour.

---

## What to actually do with the dial

- **On routine work, leave it at `low`.** Ten of ten cells scored 1.00; `low` did it in 2 minutes for 76 cents. Everything above it is paying for revision of an already-correct answer.
- **Raise it when a measured response has headroom** — the go coverage gain is real. That is a reason to go to `xhigh`, and the gain is already there at `xhigh` rather than `max`.
- **Treat `max` as a different mode, not one more notch.** It is where the model starts auditing itself, where cost goes super-linear, and where it does work nobody asked for.

---

## Caveats

**n is small.** Two replicates per bookshop cell, one per brazil cell. The bookshop go `max` row is n=1 (13.3 min, $4.21) and lands *below* its own `xhigh` (18.4 min, $6.70) — almost certainly the missing replicate rather than a real inversion, so it backs no claim above. At n=1 the brazil Edit:Write ratios wander (see the correction above); treat the *level* of that ratio as the signal and its ordering as noise.

**One brazil cell has no cost.** Opus 5 / go / `medium` completed and scored 1.00, but its agent log was never written, so `_cost_usd` is NULL and tokens read 0. Every Opus total on this page is therefore a **lower bound** with one cell missing. Filed as a harness bug — a run that completes without usage telemetry should say so loudly, because a missing cost and a free run look identical in every downstream table.

**One measurement trap, recorded because it bit this analysis.** A Claude Code JSONL log can contain **more than one `result` record** — 2 of the 24 Opus runs here do. Reading `num_turns` from the last record alone undercounts: the 45.6-minute `max` run reports 94 that way when the true total is 116 + 94 = **210**. An earlier version of [tasks-blog.md](tasks-blog.md) and [experiments-blog.md](experiments-blog.md) published the 94; both are corrected. Directly counted `tool_use` blocks (256 for that run) are the more reliable measure and are what the tool-mix table above uses.
