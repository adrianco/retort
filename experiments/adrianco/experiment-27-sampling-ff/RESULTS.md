# Experiment 27 — sampling parameters: the lever we'd never touched

Prompted by [issue #40](https://github.com/adrianco/retort/issues/40)'s question —
do inference levers "resolve into reliability"? — and an embarrassing discovery: every
local experiment so far (exp-16 → 26) ran at oMLX's **default temperature = 1.0**, well
above Qwen's own ~0.6–0.7 recommendation, with no repetition penalty. So the first
lever to screen is **sampling**.

A **fractional factorial** — Resolution IV 2^(4-1), 8 presets — over four request-time
levers: **temperature, top_p, top_k, repetition_penalty**. 35B stack (oMLX + Hermes),
bookshop (easy) task, python+go, 3 replicates = 48 runs. Each preset is a `stack`
factor level; the runner reloads oMLX with that preset's sampling at the model-selection
point (run order grouped by stack → each preset loaded once). `min_p` was dropped —
oMLX strips it from settings and Hermes won't send it per-request.

> Credit: Birgitta Böckeler (direction), kamihack (oMLX/serving), jschoch (issue #40).

## Headline: getting off temperature 1.0 nearly doubles reliability

**Overall pass-proportion 40/48 = 0.833** — versus **~0.45** at the old temp=1.0
default on the same stack/task. The sampling we'd been using was quietly costing us
half our reliability.

## Main effects (Resolution IV, 24 runs per level)

| lever | low → high | pass-proportion | effect |
|---|---|---|---:|
| **repetition_penalty** | 1.0 → 1.1 | 0.958 → 0.708 | **−0.25** |
| **top_p** | 0.85 → 0.95 | 0.750 → 0.917 | **+0.17** |
| top_k | 0 (off) → 20 | 0.792 → 0.875 | +0.08 |
| **temperature** | 0.2 → 0.7 | 0.833 → 0.833 | **0.00** |

Three findings, one of them counterintuitive:

- **Repetition penalty (1.1) is actively harmful — the biggest effect.** It drops
  pass-proportion by a quarter, makes runs ~2× slower, and **owns all 4 crashes**.
  I added it expecting it to *curb* the runaway, verbose generation behind our wall-
  crashes. The opposite happened: on a reasoning + tool-calling model, penalising
  repeated tokens derails the structured reasoning and tool-call scaffolding into
  unproductive loops. **Leave repetition_penalty at 1.0 (off).**
- **Temperature, within 0.2–0.7, does not matter** (0.833 either way). The entire win
  over the old baseline comes from being *off 1.0*, not from the precise value — so
  the earlier hunch that "lower temp is the headline" was wrong. Pick anything in the
  0.3–0.7 band.
- **top_p 0.95 beats 0.85** (+0.17) and **top_k 20 slightly beats off** (+0.08) —
  both point back to Qwen's own recommended values.

**Best config ≈ the model author's recommendation:** temperature ~0.6, top_p 0.95,
top_k 20, **no** repetition penalty. Preset s7 (temp 0.7 / top_p 0.95 / top_k 20 /
rep 1.0) went **6/6**. The model shipped with good advice; we'd been ignoring it.

## The stall guard earned its keep

All 4 crashes were **stall-kills**, not hard-wall timeouts: *"Killed after ~1000s —
stalled (no progress for 15m, unproductive loop)."* The new progress-aware guard
caught each derailed run at ~16 minutes instead of letting it burn the 45-minute wall
— ~2 hours of compute saved on this run alone — and correctly attributed them (all in
the repetition_penalty=1.1 presets). Exactly the "time out unproductive loops, not
good-but-slow work" behaviour it was built for; the 42 productive runs finished
untouched (152–460s).

## What this means for everything before it

Every local pass-proportion we've published — the 35B's 0.38–0.50 on mainstream, the
brazil-bench 0.17→0.33, the whole "a laptop model is a third of the way to the
frontier" story — was measured at **temperature 1.0**, a demonstrably poor setting.
Those numbers are **understated**. The recommended sampling (top_p 0.95, off temp 1.0,
no rep penalty) is now the oMLX default going forward, and the prior results deserve a
re-baseline at proper sampling — the local stack is likely meaningfully more capable
than the earlier arc concluded.

And to issue #40's meta-question — *do these levers resolve into reliability?* — yes,
sharply and measurably, in a way perplexity/KLD would never surface: a repetition
penalty that looks harmless on a perplexity chart quietly quarters end-to-end coding
reliability here.

## Next

Re-baseline the 35B on bookshop + brazil at the recommended sampling, then the Tier-2
levers — **speculative decoding / MTP** (throughput, for the brazil wall) and **quant
level 4→6-bit** (the brazil capability ceiling).

*Data in `experiment-27-sampling-ff/bookshop/retort.db`. Setup:
`unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit` via oMLX on :8080; Hermes + `hermes-lcm`;
sampling per preset (stacks.yaml); M5 MacBook Pro 64 GB. 45-min hard wall, 15-min
stall guard.*
