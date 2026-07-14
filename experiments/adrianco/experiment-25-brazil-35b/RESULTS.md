# Experiment 25 — the HARD task on the best local stack: can the 35B cope?

Every prior local run used the **easy** bookshop CRUD task. This asks the real
question: does the best local stack — **Hermes + `hermes-lcm` → oMLX →
Qwen3.6-35B-A3B**, the model that tops our local leaderboard — cope with a
genuinely **hard** build? The task is [brazil-bench](../../../tasks/brazil-bench/):
a **Brazilian-soccer MCP server** built from a multi-file guide over **6 kaggle
datasets** (~13 MB), with **12 required capabilities** (match/team/player/
competition queries, standings computed from results, head-to-head, aggregate
stats, and a test suite). It's the task cloud frontier models find non-trivial.

Scope: **Python and Go** (the two languages the local stack is most reliable on),
neutral stack, **3 replicates = 6 runs**. This is a *ceiling* probe (best stack,
best languages, hard task), not a reach probe.

**Two deliberate setup choices:**
- **Prompt = `none`, not neutral.** brazil-bench's guide already prescribes **BDD**
  tests. Injecting our "neutral" prompt factor ("no methodology prescribed") would
  *contradict* the task, so we inject nothing and let the guide's own BDD
  instructions govern — running brazil-bench exactly as defined.
- **Biggest context.** The 35B's native max is **262,144 (256K)**. We set Hermes
  `context_length: 262144` (default fallback is only 64K) so `hermes-lcm` manages a
  256K budget in SQLite; oMLX serves at model-max with the paged SSD cache so KV can
  page. This was **necessary and used**: prompts reached **108K tokens** (median
  54K) — well past the 64K default — with **no OOM** (memory guard never fired).

> Credit: Birgitta Böckeler (direction) and kamihack (the oMLX/serving + 256K-with-
> SQLite-context pointers).

## Result: it copes — in Python, sometimes; in Go, never

| language | first-try pass | crashed (30-min wall) | failed | best req_cov |
|---|---:|---:|---:|---:|
| **python** | **1/3** | 1 | 1 | **1.00** ✓ |
| **go** | 0/3 | 2 | 1 | 0.00 |
| **overall** | **1/6 = 0.17** | **3/6** | 2/6 | — |

- **Python cleared the hard task once, cleanly** (rep2): a real
  `brazilian_soccer_mcp/` package — `server.py`, `query_engine.py`,
  `data_loader.py` — with a passing test suite (**requirement_coverage 1.0,
  test_coverage 0.90**), in 22.7 minutes and 3.0M tokens. That's a complete,
  tested MCP server over the kaggle data, built by a local model on a laptop.
- **The other Python runs got close but ran out of clock**: rep1 crashed at the
  30-min wall with substantial-but-incomplete code (code_quality 0.83); rep3 was a
  **near-miss** — requirement_coverage **0.83**, tests never quite ran — even after
  the default second-chance repair, at 2.0M tokens.
- **Go went 0/3 and never produced working code**: two runs hit the wall, the
  third burned **3.2M tokens** and still `tests did not run` (test_coverage 0). The
  Go "tests don't compile / never execute" failure we saw on the *easy* task
  amplifies badly at this scale.

## Why: the wall, not the ceiling

The dominant failure mode is **non-termination at the 30-minute wall — 3 of 6
runs** — and it's the same mechanism [exp-24](../experiment-24-qwennext80b-cached/RESULTS.md)
isolated: these runs are **generation-bound**. The 35B generates at **~54 tok/s**,
brazil-bench is far larger than bookshop (12 capabilities + 6 datasets to wire up),
so runs spend **2–3.2M tokens** and still don't finish. The model isn't failing on
*capability* so much as on *throughput within the budget* — Python rep2 proves the
capability is there; the other five just couldn't close 12 requirements before the
clock (or, for Go, get tests to run at all).

The big context earned its keep — 108K-token prompts, no OOM — so context was **not**
the bottleneck. Throughput and the fixed 30-minute wall were.

## The easy-vs-hard contrast

| | bookshop (easy) | brazil-bench (hard) |
|---|---:|---:|
| Python first-try | ~0.67–1.00 | **0.33** |
| Go first-try | ~0.67–1.00 | **0.00** |
| dominant failure | occasional non-termination | **non-termination + Go tests never run** |

The hard task **widens the Python–Go gap to a chasm**: on bookshop both languages
worked; here Python still carries (a real MCP server, 1/3) while Go collapses to
zero. The takeaway from the local-model arc holds and sharpens — **a local model is
a Python-first tool, and the harder the task, the more that's true.** It *can* do
serious, multi-capability work on a laptop, but reliability drops to a third and
the 30-minute wall becomes the binding constraint.

**What would move it:** faster generation (MTP / speculative decoding, per exp-24)
to fit more turns before the wall, and a higher turn/timeout budget to convert
wall-crashes into real data points — both aimed at *throughput*, since capability
(Python rep2) is demonstrably present.

*Data in `experiment-25-brazil-35b/brazil/retort.db` (own DB; a new task on the
local stack). Setup: `unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit` via oMLX on :8080
(256K, paged SSD cache); Hermes + `hermes-lcm`, context_length 262144; M5 MacBook
Pro 64 GB. Throughput/context figures from the oMLX server log.*
