# Experiment 26 — double the clock: brazil-bench on the 35B at a 60-min timeout

[exp-25](../experiment-25-brazil-35b/RESULTS.md) ran the hard task (brazil-bench, a
Brazilian-soccer MCP server) on the best local stack and lost **half its runs to the
30-minute wall** — non-termination, not failure. Those crashes never produced a
scored attempt, so they never got the default self-repair second chance either. The
[exp-24](../experiment-24-qwennext80b-cached/RESULTS.md) finding said why: local runs
are **generation-bound** (~54 tok/s), and brazil is far bigger than the CRUD task.

So this is a clean, single-variable ablation: **exactly exp-25, with the timeout
doubled to 60 minutes** (a per-experiment `playpen.timeout_minutes`, because *local
runs need more time* — a property of the slow stack, not the task). Same 35B, same
Python + Go, same 256K context, same default second-chance. Does the extra clock
convert wall-crashes into real data points — and passes?

> Credit: Birgitta Böckeler (direction) and kamihack (the oMLX/serving + 256K-context
> pointers).

## Result: more time roughly doubles everything that matters

| metric | exp-25 (30 min) | exp-26 (60 min) |
|---|---:|---:|
| first-try pass-proportion | 1/6 = **0.17** | 2/6 = **0.33** |
| crashed at the wall | **3/6** | **1/6** |
| Python first-try | 1/3 | **2/3** |
| Go first-try | 0/3 | 0/3 |
| Go: does it build tested code? | **no — all zeros** | **yes — cq 1.0, test_cov 0.6–0.81** |
| Go best requirement_coverage | 0.00 | **0.92** (near-miss) |

Three things changed, all pointing the same way:

- **Crashes collapsed 3 → 1.** The extra clock converted non-terminating runs into
  completed/failed ones — actual data points. Only one run (python rep1) still walled
  out, at the *full* 3600 s, so even 60 minutes isn't always enough.
- **First-try passes doubled, 0.17 → 0.33.** Python went 2/3 — two clean, tested MCP
  servers (requirement_coverage 1.0, test_coverage 0.96).
- **Go went from collapse to near-miss.** At 30 minutes Go was *all zeros* — no
  working code, tests never ran, non-terminating. At 60 minutes every Go run builds
  **high-quality code (code_quality 1.0) with running tests (test_coverage 0.6–0.81)**
  and reaches requirement_coverage **0.75 and 0.92**. Go's exp-25 "0/3, can't do it"
  was largely a **wall artifact**, not incapability — it just needed the clock.

## What more time did *not* fix

- **Go still didn't cross the line (0/3 passes).** It gets to 0.92 requirement
  coverage but not 1.0 — the last mile (all 12 capabilities + correct MCP wiring) is a
  genuine capability gap, not a time gap.
- **Second-chance now *engages* on Go but doesn't convert.** Because the runs now
  *complete-but-fail* instead of crashing, all three Go runs got the default repair
  (they couldn't before) — exactly the compounding effect the timeout was meant to
  unlock. But none reached 1.0, and one repair *regressed* (go rep3 → 0.0): handing
  back the evaluation helps a near-miss climb, but it can also send a model rewriting
  in the wrong direction on the hard last mile. Repaired passes: **0**.
- **The cost is real.** More clock means more generation — Go rep3 burned **5.3M
  tokens** in one run. Context again reached **113K tokens** (used, no OOM).

## The takeaway

Doubling the timeout is the **highest-leverage single knob** we've turned on the hard
task: it roughly doubled the pass rate, cut crashes to one, and revealed that the
local 35B is *far* more capable on brazil-bench than exp-25's 30-minute numbers
suggested — Go especially. It confirms the generation-bound diagnosis from the flip
side: give the slow model enough clock and the wall-crashes turn into near-passes.

But it also marks a ceiling. Even at 60 minutes with self-repair, reliability tops out
at **0.33 first-try**, and the residual failures are now *capability* (Go's last mile,
the occasional genuinely non-terminating run), not *budget*. Beyond here the lever is
**generation throughput** (MTP / speculative decoding — finish more turns per minute)
or a stronger model, not simply more wall-clock. Time bought most of the easy wins;
what's left is hard.

*Data in `experiment-26-brazil-35b-60m/brazil/retort.db` (own DB; a timeout ablation
of exp-25). Setup identical to exp-25 except `timeout_minutes: 60`.
`unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit` via oMLX on :8080 (256K, paged SSD cache);
Hermes + `hermes-lcm`, context_length 262144; M5 MacBook Pro 64 GB.*
