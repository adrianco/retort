# Future experiments & model candidates

A running scratchpad of ideas to try next, so they aren't lost. Nothing here is
committed to; it's a queue. Current stack context: the local-model work runs on a
**MacBook Pro M5, 64 GB** (GPU wired limit raised to ~56 GB), serving MLX models
via **oMLX** and driving them with the **Hermes** agent (+ `hermes-lcm` lossless
SQLite context). Best result so far: exp-18, Qwen3.6-35B-A3B, **0.38** pass-
proportion on bookshop (cracked TypeScript; Rust still fails/non-terminates).

Credits for the local-model direction: **Birgitta Böckeler** (the
[local-models writeup](https://martinfowler.com/articles/exploring-gen-ai/local-models-for-coding-experiences.html))
and **kamihack** (@kamihack@mastodon.cr) for the oMLX / model / tool-template
pointers.

---

## Candidate models to test next (claim better than what we've run, and fit 64 GB)

Fit budget: ~56 GB wired GPU → **~45 GB weight ceiling** (leaving room for KV +
compute buffers). We've already run Qwen3-Coder-30B-A3B and Qwen3.6-35B-A3B (both
MoE, ~3B active, ~18–20 GB Q4).

| Model | Size (total/active) | Fit on 64 GB (MLX) | Claim vs ours | Tool format |
|---|---|---|---|---|
| **[Agents-A1](https://huggingface.co/InternScience/Agents-A1) (35B MoE)** ⭐ **QUEUED — next new model** | 35B MoE (active n/s) | 4-bit ≈ **~20 GB** — fits easily | InternScience; **agent-tuned** (native function calling, 262K ctx, long-horizon/engineering/science). SciCode 44.3 | **`qwen3_coder` tool parser → Qwen-style, so oMLX should parse it natively.** MLX quants exist. Zero serving risk (unlike Devstral) |
| **Qwen3-Coder-Next (80B-A3B)** | 80B / 3B MoE | 4-bit ≈ **44.8 GB** (tight; reduce ctx) or 3-bit ≈ **34 GB** (comfortable) | "~96% of the 480B flagship"; "comparable to 10–20× more active params" | **Same Qwen `<tool_call>` format oMLX already parses** — zero new integration risk |
| ~~**Devstral Small 2 (24B)**~~ **BLOCKED** | 24B dense | ~14 GB Q4 — fits fine | 68% SWE-bench; agent-tuned | **oMLX does NOT parse Devstral's Mistral `[TOOL_CALLS]` format** (it emits the call as text; Hermes executes nothing — gate-probe on `mlx-community/Devstral-Small-2507-4bit` confirmed). Same wall as exp-12. Would need a different serving layer (vLLM with the mistral tool parser, or llama.cpp with the right template). |
| gpt-oss-120b | 117B / 5.1B MoE | **~64–65 GB — likely won't fit** at 56 GB wired | best raw coder (83% Multi-LCB; Codeforces 2622) | Harmony format; only if we push memory limits (OOM risk) |
| GLM-4.5-Air / 4.7-Flash | ~100B+ MoE | borderline → probably too tight | SWE-bench ~57.6% (Air) | MLX-tested; confirm exact size before trying |

**Excluded — too big (multi-GPU tier):** MiniMax M3 (428B/23B; 4-bit ≈ 228 GB —
tops open SWE-Bench Pro but no chance), GLM-4.6 (355B), DeepSeek-V4-Pro,
Kimi K2.6, Qwen3-Coder-480B.

**Recommendation:** add **Qwen3-Coder-Next (80B-A3B)** first — the bigger sibling
of what we've run, same architecture/tool-format, strongest fitting quality
claim. Direct "80B vs 35B, same stack" comparison: does doubling the model crack
Rust / raise the 0.38 ceiling? Optionally add **Devstral Small 2** as a cheap
second arm (different bet: agent-tuned, not just bigger).

### Agents-A1 — queued (next NEW model to add)

Flagged via LinkedIn; verified on the [HF card](https://huggingface.co/InternScience/Agents-A1).
The most promising new candidate we've queued, because it's a **like-for-like size
match for our champion** (35B MoE, same class as Qwen3.6-35B-A3B) that makes the
**agent-tuned** bet — and, critically, it uses the **`qwen3_coder` tool parser**, so it
should drop into the existing oMLX + Hermes stack with **no serving work**. That is the
exact wall Devstral hit (Mistral `[TOOL_CALLS]` → forced llama.cpp), so this is a much
cleaner test of the same hypothesis.

- **Why it's interesting:** "agent-tuned beats general-purpose" is a hypothesis we
  *thought* we'd killed with Devstral (exp-23, 0.17) — but that verdict is now in
  serious doubt: Devstral ran at temp 1.0 (its rec is **0.15**) *and* through the
  write-refusal bug. Agents-A1 re-tests the agent-tuned axis on a fair stack.
- **Recommended sampling (from the card):** temp **0.85**, top_p 0.95, top_k 20,
  min_p 0.0, **presence_penalty 1.1**, repetition_penalty 1.0. Two flags: (a) oMLX
  **strips `min_p`** and may not honour `presence_penalty` either (it silently dropped
  min_p) — verify before trusting the config, else the model runs off-spec exactly like
  everything pre-exp-28; (b) exp-27 found *repetition* penalty 1.1 caused unproductive
  loops on a reasoning model — a presence penalty is a different mechanism, but watch
  for the same stall signature.
- **Honest caveat:** it is **science-leaning, not a dedicated coder** (targets
  FrontierScience/Olympiad; SciCode 44.3). Our tasks are CRUD + an MCP server, so a
  strong general/science agent may still lose to a coding-specialised model. Treat the
  LinkedIn buzz as a prompt to measure, not a claim to trust.
- **Plan:** once exp-28 (the sampling/write-fix re-baseline) lands, add Agents-A1 as a
  new `stack` preset (its own recommended sampling) on the **fixed** stack, bookshop
  mainstream 4 languages, 3 reps — a direct head-to-head with the re-baselined
  Qwen3.6-35B. If it holds up, promote it to brazil-bench.

> **Status — the fitting + tool-calling search is largely exhausted; Qwen3.6-35B
> remains the best local stack.**
> - **exp-22 (Qwen3-Coder-Next-80B):** bigger is NOT better — first-try 0.33 vs
>   the 35B's 0.50, slower, more non-terminating (Rust to the wall at 3.9M
>   tokens). The 35B has no headroom to improve on (local mirror of "at the top,
>   extra spend buys nothing"). Did not expand to 9 languages.
> - **Devstral (different bet, exp-23):** unblocked by switching the serving layer
>   to **llama.cpp `--jinja`** (parses the Mistral tool format oMLX can't) — the
>   "allow for either layer" result. But it scored the WORST (0.17, 7/12 never
>   terminating), and it's tuned for OpenHands not Hermes (wrong harness). Neither
>   bigger nor agent-tuned-different beat the general 35B.
> - **What's left, all with a catch:** gpt-oss-120b (best raw coder but ~64 GB —
>   over the 56 GB wired limit; would need to push memory limits) or gpt-oss-20b
>   (fits, Harmony format — oMLX has a `harmony` reasoning parser, tool-parse
>   unverified — but 20B is unlikely to beat the 35B); GLM/MiniMax/DeepSeek are
>   all too big. To try Devstral or a Mistral-family coder, switch the serving
>   layer to vLLM or llama.cpp (they parse the Mistral tool format).
>
> **Bottom line:** among models that both fit 64 GB and tool-call cleanly via
> oMLX, **Qwen3.6-35B-A3B is the winner.** Further gains need either more memory
> (bigger models) or a different serving layer (broader tool-format support).

MLX builds seen: `mlx-community/Qwen3-Next-80B-A3B-Instruct-4bit` (44.8 GB,
general instruct); `majentik/Qwen3-Coder-Next-MLX-3bit` (~34 GB, coding-tuned);
`unsloth/Qwen3-Coder-Next-GGUF` (llama.cpp fallback).

---

## exp-21 — self-repair with evaluation feedback

Give exp-20's **near-miss** failures a **second try, prompted with the evaluation
results**, across all 9 languages, and measure the lift over the exp-20 baseline.
This is the model's first sight of the *independent* evaluation (it never saw the
spec-gate's requirement checklist or the scorer's build/test errors first pass),
so it's a clean test of self-repair.

- **Scope:** every exp-20 failed cell that produced a code artifact (skip $0
  crashes with no code).
- **Feedback (both, per failure type):** spec-failed runs → `assessment.json`
  `top_findings` (unmet requirements); tests-didn't-run runs → scorer /
  `retort diagnose` build-test error.
- **Mechanism:** seed a fresh playpen with the failed code + TASK.md, inject a
  REPAIR prompt ("your previous attempt is here; the evaluation found <feedback>;
  fix it, don't start over"), run the same stack, rescore + spec-gate. New
  exp-21 DB; compare pass-proportion vs exp-20 per language.
- **Attempts:** one second try to start; extend to an iterative loop if it helps.
- **Scoring — half credit on pass-proportion ONLY; quality metrics reflect final
  quality.** A repaired pass is worth less as a *reliability* signal (it needed the
  evaluation handed to it), but the *code it ends up with* is as good as it is. So:
  - **Repair-adjusted pass-proportion** (headline): first-try pass = 1.0,
    second-try/repaired pass = **0.5**, still-failing = 0.
  - **All quality/coverage metrics stay at their true final values** — code_quality,
    test_coverage, defect_rate, maintainability, idiomatic, requirement_coverage,
    token_efficiency are recorded raw (the repaired code's actual quality). Do NOT
    halve them.
  - The 0.5 is a *pass-count* weight applied at the reporting layer, not a
    discount on the stored scores. Gate on raw req_cov; a repaired req_cov==1.0
    is a real pass that simply counts 0.5 toward the adjusted pass-proportion.
- **Build:** needs a seed-workspace + augment-prompt hook (a `retort repair`
  subcommand or a script reusing LocalRunner) plus a repair-adjusted scorer view.

---

## Resolved — KV prefix cache (exp-24)

- **SSD prefix cache does NOT rescue the 80B.** oMLX's on-disk prefix cache is off
  by default (`--paged-ssd-cache-dir` enables it), so exp-22 ran without it. exp-24
  turned it on and re-ran the identical 80B grid:
  [RESULTS](../experiments/adrianco/experiment-24-qwennext80b-cached/RESULTS.md). First-try pass-
  proportion **0.33 → 0.33**, crashes **2 → 3**, completed-run duration unchanged.
  The cache demonstrably *hits* (an 88K-token prefix restored in ~2.5 s vs ~150 s
  cold, hybrid DeltaNet layers snapshotted to disk correctly) — but our runs are
  **generation-bound, not prefill-bound**: the 80B does ~61 tok/s, `hermes-lcm`
  grows context to 75–88K tokens, each turn is ~75 s of generation, and many turns
  march into the 30-min wall regardless of prefill speed. The mrzk.io 137× is the
  mirror image of our workload (huge fixed prompt, little generation). **"Bigger
  isn't better" stands; the mechanism is throughput, not caching.** Leave the cache
  on (free prefill latency) but don't expect pass-proportion from it.

## Resolved — the hard task on the local stack (exp-25)

- **The best local stack (35B) copes with brazil-bench in Python, not Go.**
  [RESULTS](../experiments/adrianco/experiment-25-brazil-35b/RESULTS.md). Python 1/3 (one *clean* MCP
  server: req_cov 1.0, test_cov 0.90, 23 min), Go 0/3; overall 1/6 = 0.17. Half the
  runs (3/6) hit the 30-min wall — generation-bound again (54 tok/s × a 12-capability
  task = 2–3.2M tokens without finishing). The 256K context was necessary and used
  (108K-token prompts, no OOM), so context was NOT the limit — throughput + the wall
  were. Setup notes: prompt=`none` (the brazil-bench guide already prescribes BDD, so
  don't inject a contradicting neutral wrapper); Hermes `context_length: 262144` (default
  fallback is only 64K). Confirms the Python-first story and sharpens it: the harder
  the task, the wider the Python-Go gap.
- **Timeout follow-up — DONE (exp-26).** Doubled the brazil timeout to 60 min
  ([RESULTS](../experiments/adrianco/experiment-26-brazil-35b-60m/RESULTS.md)): first-try pass 0.17 → 0.33,
  crashes 3 → 1, and Go went from *all zeros* (non-terminating) to code_quality 1.0 +
  test_coverage 0.6–0.81 + req_cov up to **0.92**. The 30-min wall was masking real
  capability, Go especially — highest-leverage single knob so far. It also *unlocked*
  self-repair for Go (runs now complete-and-fail instead of crashing, so they qualify),
  though the hard-last-mile repairs didn't convert (one regressed). Residual failures
  are now *capability* (Go's last mile, one genuinely non-terminating run at the full
  hour), not budget. **Next lever is throughput (MTP), not more wall-clock.**
- **MTP/speculative-decoding** remains the top open speed lever — more finished turns
  per minute is exactly what the remaining wall-bound / near-miss runs need.

## Harness bugs that invalidated results — a running list

Three separate bugs have now each moved a result more than the model choice did. All
three were **unrecorded stack variables**. They are listed here because the pattern —
not the individual bugs — is the finding: *suspect the harness before the model.*

| Bug | What it did | Fixed |
|---|---|---|
| **Playpen under `/var`** | Hermes refuses to write to a "sensitive system path", so the agent could not create files **in its own workspace**. A resilient model routed around it via the shell (burning turns); a weaker one wrote nothing and scored a **false zero**. Hit 41/48 runs in exp-27, 6/6 in exp-26. | playpens → `~/.retort/work`; `retort diagnose` now returns a **HARNESS** verdict; a no-write streak aborts the run. |
| **Sampling at `temperature: 1.0`** | oMLX's default, never recorded. Cost roughly **half** the reliability of every local result. Also: any `repetition_penalty > 1.0` derails an agentic tool loop into stalls — *even at the value the model's own card recommends.* | exp-27 measured it; correct sampling is now the default and lives in [optimal-blog](../optimal-blog.md) forbidden settings. |
| **Context silently 128K, not 256K** | The stack-reload hook **rebuilt** Hermes' per-model config map on a model switch, destroying `context_length: 262144`. Hermes then probes its fallback tiers and lands on **128K**, and `hermes-lcm` compacts at ~85% of that (~109K) — while the top-level `context_length:` in the file still read 262144 and **provenance dutifully reported it**. | Never rebuild the map; `context_length` is part of the preset *and* the reload signature; **provenance now reports the EFFECTIVE (per-model) value** and flags disagreement. |

**The Rust "context thrash loop" is now in doubt.** With the 128K bug, Rust ran a
grow→compact→regrow cycle (three full cycles in 33 min on an *easy* task, peaking at
114K). At a true 256K the compaction threshold moves to ~217K — well above that peak.
**Rust may simply terminate.** If it does, "Rust is a capability wall" goes the same
way the "niche-language wall" did, and every Rust non-termination result since exp-18
needs re-reading. exp-28 is re-running at a true 256K to find out.

New instrumentation to catch this class of bug earlier:
- **peak context** (`_max_context_tokens`) recorded per run, for local *and* Claude
  (per-turn usage from `stream-json`) — so context can be compared across the
  cloud/local boundary. The monitor shows current **and** peak live, because a
  compacting agent makes the current value alone actively misleading.
- **provenance.json** per run: versions, model revision hashes, sampling, agent config,
  and the harness settings that each turned out to matter.

## exp-29 DONE — the 80B re-baseline (Qwen3-Coder-Next)

**Result (n=3/language, aggregated into master.db, run `retort report optimal`):**

| lang | 80B pass | 35B (exp-28) | verdict |
|---|---|---|---|
| python | **1.00 (3/3)** | 0.85 | 80B **beats** the 35B |
| go | 0.67 (2/3) | 0.85 | 80B **worse** — rep2 stalled to the wall (25m no-progress) |
| typescript | 0.33 (1/3) | 0.00 | both weak; 2× "tests did not run" |

`retort diagnose` classified all 3 non-completions as **GENUINE** (not harness/TOOLING):
the Go stall and the TS failures are real model behaviour, not a blocked tool. So doubling
the model to 80B **helps Python but not Go/TS**, and it is ~2× slower (809 s vs 440 s mean).

**Decision:** the 80B is a **candidate, featured in the per-language matrix but NOT
recommended** — one experiment, n=3, a Go stall, and a TS gap. It does not displace the
35B (Python/Go) or the cloud stacks. Next: more 80B reps on Python/Go to see if the Go
stall was a one-off, and whether Python 1.00 holds. Also note the 80B ran with the model
correctly recorded in `stack.json` (the `stack_metadata()` fix), so it ingested with a real
model id — no slug guessing.

## exp-33 DONE — TypeScript on the 80B

**Result (n=6; combined with exp-29 → n=9): TS = 0.33 (3/9).** rep5/rep6 passed (1.00), rep1
a near-miss (0.9167, re-confirmed genuine), rep2/rep4 genuine fails, **rep3 stalled to the
wall**. So the earlier n=3 0.33 holds at n=9: TS local on the 80B is **unreliable**, and
crucially the **intermittent stall is NOT Go-specific** — it also hangs on TypeScript. TS
stays → cloud.

**Cross-cutting finding:** the 80B's non-termination bug is a *general* failure mode (Go
0.67 with 2 stalls, TS 0.33 with 2 stalls, hard task with stalls), not a Go quirk. Python is
the only language where it never hangs (21/21). Worth its own controlled dig (is the stall
context/compaction-triggered? Python runs stay shorter/smaller — maybe the hang correlates
with context growth on the harder-for-it languages).

## exp-33 (superseded plan) — TypeScript on the 80B

**Intent:** TS local is a weak, thinly-sampled cell — 35B 0.00 (n=3), 80B 0.33 (n=3) — and
the guide routes TS→cloud on that thin evidence. Re-test TS on the 80B (the leading local
model) at 6 reps: is TS local genuinely hopeless, or just under-sampled? Fills/firms a guide
cell.

**Design:** typescript routine (bookshop) × m80 (80B) × neutral × 6 reps. Tuned m80 stack
(proven), 60-min timeout. **Hypothesis:** TS lands ~0.3–0.5 (the 80B's TS is genuinely
weaker than its Python) — confirming TS→cloud, now on firmer n. If it clears ~0.8, TS joins
Python as a local-viable language on the 80B.

## exp-32 DONE — prompt-factor re-test on the 80B

**Result (python routine, n=3/prompt):** the prompt is a **flat line on the 80B** — every
methodology passes **1.00** (neutral, BDD, TDD, **ATDD**). Contrast the 35B (exp-19):
neutral/BDD 0.67, TDD 0.33, **ATDD 0.00**.

**Finding:** the prompt/methodology lever bites in proportion to how *weak* the model is. On
the 35B, ATDD's front-loaded discipline tanks the run (0/3); on the stronger 80B it's a no-op
(3/3), the same flat line seen on strong cloud models. So the "never ATDD locally" advice was
35B-specific — the guide now states the general rule: reach for a disciplined methodology
only near a model's capability edge; on a model that clears the task comfortably, the prompt
is ritual — pick neutral (cheapest). optimal-blog's prompt-method table now shows 35B vs 80B
side by side.

## exp-32 (superseded plan) — prompt-factor re-test on the 80B

**Intent:** the prompt-blog's methodology findings (neutral/BDD best, ATDD worst 0/3, TDD
middling) were established on the **35B**. Re-test on the **80B** (now the leading local
model): does the pattern hold, or does the prompt flatten toward a no-op as it does on strong
cloud models? Directly serves the standing goal ("re-test relevant factors on current
leaders").

**Design:** python routine (bookshop) × {neutral, BDD, TDD, ATDD} × m80 (80B) × 3 reps = 12
runs. Tuned m80 stack (already proven), 60-min timeout. Dry-run confirmed the 4-prompt design.

**Hypothesis:** on the stronger 80B the prompt is closer to a flat line than on the 35B —
neutral ≈ BDD ≈ TDD all near 1.00 (80B python is 1.00 at neutral already), and ATDD is less
catastrophic than the 35B's 0/3 (but still the weakest). If ATDD still tanks, that's a robust
cross-model result worth stating firmly in the guide.

## exp-31 DONE — the 80B on the HARD task (brazil)

**Result (n=6, in master.db):** the 80B scored **0.00 pass (0/6)** on brazil — but with a
**mean requirement_coverage of 0.83** (python 0.75/0.83/0.92, go 0.83/0.92 + 1 stall). It
**consistently gets ~10/12 capabilities but never all 12**. Compare the 35B: **0.25 (3/12)**,
mean 0.79 — *lower* average but it occasionally nails all 12. `reevaluate --force` re-confirmed
every near-miss (genuine, not scorer artifacts).

**Conclusion for the guide:** local models don't reliably clear hard tasks (0–25%). The 80B
is *closer on average* than the 35B but *worse on pass-proportion* (the metric that matters
for unattended runs). Hard tasks stay a cloud-frontier niche (Fable 5 = 1.00). The leading
table now shows the measured local hard numbers instead of a blanket `n/q`. The **Go stall
recurred here too** (go rep3 stalled to the wall) — the 80B's Go non-termination is
task-independent.

## exp-31 (superseded plan) — the 80B on the HARD task (brazil)

**Intent:** fill the guide's clearest gap — local models are `n/q` on hard tasks. The 35B
scored ~0.25 on brazil (exp-25/26). Does the bigger 80B, now the best local Python stack on
routine work, do better on a hard task (a Brazilian-soccer MCP server, 12 capabilities)?

**Design:** 80B (Qwen3-Coder-Next) at the tuned m80 sampling, brazil-bench guide task
(prescribes BDD → prompt=none), `design.csv` pinned to {python, go} × hermes-local × m80 ×
3 reps = 6 runs, **60-min** timeout (hard task; local needs the wall). Dry-run confirmed the
github task + pinned checklist resolve. Stack already smoke-proven in exp-30, so no separate
smoke — the new element is only the task.

**Hypothesis:** the 80B lands ≤0.3 on brazil (hard tasks remain a cloud-frontier niche);
if it surprises upward, that's a real story for the guide. Either way, local-on-hard stops
being a blank cell.

## exp-30 DONE — more 80B reps on Python/Go

**Result (exp-29 + exp-30 combined, n=9/language, in master.db):**

| lang | 80B (n=9) | 35B | verdict |
|---|---|---|---|
| python | **9/9 = 1.00** | 0.85 | 80B is the **best local Python** stack |
| go | **6/9 = 0.67** | 0.85 | 80B **unreliable** — **2 runs stalled** to the 25-min wall + 1 near-miss |

**The Go stall was NOT a one-off** — it recurred (exp-29 rep2, exp-30 rep4), `retort
diagnose` classified both as GENUINE non-termination (unproductive loop, killed by the
25-min stall guard). So the 80B has a real, intermittent Go hang. Python, by contrast, is
perfect across 9 reps. **Recommendation split: 80B for local Python (reliability, ~1.3×
slower than 35B), 35B for local Go.** The blog now says exactly this.

**Two harness bugs found and fixed while running this (both on main):**
- `_discover_active_runs` didn't see an agent launched behind a `uv run` wrapper → the live
  monitor showed nothing. Now descends through launcher wrappers.
- The tool-refusal abort fired on Hermes's benign "N file(s) NOT modified this turn"
  advisory even when the agent wrote a complete app → discarded a healthy 80B Go run. Now
  gated on `wrote_nothing`.

One recovered scorer artifact: go rep5 was a spec-gate near-miss (0.9167); `retort diagnose`
flagged it TOOLING, but `reevaluate --force` re-confirmed 0.9167 twice — a **genuine**
near-miss, not a false failure, so it stays a fail.

**Next:** exp-31 (brazil hard task on the local stacks), or Devstral (exp-30-era plan), or
re-test a factor on the cloud leaders. The 80B Go stall could get its own controlled dig
(is it language-specific, or context/compaction-triggered?).

## exp-28 DONE (m35 arm) — the 35B re-baseline

**exp-28 m35 re-baseline is complete and is the headline local result.** At correct
sampling (temp 0.6, top_p 0.95, top_k 20, no rep penalty) and a TRUE 256K context, the
35B on bookshop mainstream: **python 3/3, go 3/3** (both were ~0.5–0.67 at the broken
temp=1.0 stack — the old numbers were badly understated); typescript 0/3 ("tests did
not run"); rust 0/2 (thrash / near-miss). exp-29 (the 80B, above) was the follow-up.

The 35B remains the **headline local result** and the production local stack for
Python/Go; the 80B (exp-29) is a candidate that beat it only on Python.

## exp-35 DONE — context_threshold 0.7 PARTLY fixes the 35B's Rust wall

**Result (35B Rust × 3 at `LCM_CONTEXT_THRESHOLD=0.7`): 1/3 — rep1 PASS (1.00), rep2 & rep3
stalled** (both GENUINE per `retort diagnose`). rep1 reached **113K context** (past the
0.35 compaction point at ~92K, under the 0.7 point at ~183K) and terminated cleanly — the
35B's **first-ever Rust pass**. At 0.35 every Rust run thrashed to the wall (0.00).

**Answer to the doc's central question:** Rust is **not a pure capability wall** — the 92K
compaction was a real cause (one clean pass proves the 35B can write correct Rust when its
working history survives). But the threshold is only a **partial** fix on the 35B (2/3 still
stall), unlike the 80B on Go/TS where 0.7 gave 0/6. So the compaction lever's strength is
model/language-dependent. Rust stays → cloud for now.

**Caveats & follow-ups:**
- **Provenance bug found:** the `sampling` block in provenance.json records a STALE
  pre-reload value (showed m80's 0.7/40 while oMLX's settings.json — the effective config —
  correctly had m35's 0.6/20). "Provenance is truth" is violated here; the smoke caught it
  by checking settings.json. Worth fixing so provenance records the post-reload sampling.
- Next levers for Rust (the 2/3 that still stall): **self-repair on the build errors** (the
  exp-28 smoke saw terminate-with-3-compile-errors, a near-miss), a **stronger model / more
  bits**, or an even higher threshold. Also: does 0.7 help the 80B on the hard task (which
  also stalled)? And the queued 80B 0.7 re-baseline (Go/TS with more reps).

exp-35 (0.7) is EXCLUDED from the featured 35B numbers (which stay at the 0.35 default,
Rust 0.00). optimal-blog's stall-fix callout now carries the partial-fix nuance.

## exp-35 (superseded plan) — does context_threshold 0.7 fix the 35B's Rust wall?

exp-34 proved the 80B's stall is a compaction artifact (0.35 compacts at ~92K -> thrash).
The 35B thrashes-to-wall on Rust at 0.35 (exp-28 rust 0/2, ~0.00) — the doc's central open
question. **Test:** 35B on Rust with `LCM_CONTEXT_THRESHOLD=0.7`. If Rust terminates/passes,
'Rust is a capability wall' is (partly) a context-management artifact. Smoke ONE isolated
Rust cell first (watched), then rust x3. Hypothesis: 0.7 lets Rust terminate; whether it
then PASSES is a separate capability question (exp-28 smoke saw a near-miss with 3 compile
errors — self-repair may be the next lever).

## exp-34 DONE — raising lcm context_threshold 0.35→0.7 KILLS the 80B stalls

**Result (80B, Go+TS × 3, `LCM_CONTEXT_THRESHOLD=0.7`): 0 stalls in 6 runs, and Go went
3/3 = 1.00** (vs the 0.35 baseline's ~4 stalls in 15 Go+TS runs, Go 0.67). Hypothesis
**confirmed**: the intermittent 25-min hang is a *compaction artifact* — at 0.35, lcm
compacts live context at ~92K and truncates the agent's working history mid-build, so it
loses the thread and thrashes to the wall. At 0.7 (compact ~183K) that doesn't happen. The
env var was verified to take effect end-to-end before the grid (`LCMConfig.from_env()` →
0.7; present in the live agent process env).

Two distinct findings:
- **Go was ALL stalls** — remove them and Go is clean (3/3). The 80B may be viable on Go
  after all, at the 0.7 config.
- **TS is still 0.33 but now via genuine near-misses (0.83–0.92), not hangs** — a real
  capability gap, so TS stays → cloud.

exp-34 is a *different stack* (0.7) than exp-29–33 (0.35), so it is EXCLUDED from the
featured 80B leaderboard numbers (which stay at the 0.35 default). optimal-blog now
recommends `lcm.context_threshold: 0.7` for the 80B and carries a stall-fix callout.

**Next (queued): re-baseline the 80B at 0.7** — Go (and maybe TS/hard) with more reps
(n≥6) to confirm the improvement and, if Go holds ≥~0.85, promote it in the featured
numbers. Also worth: does 0.7 help the 35B on Rust (the original compaction-threshold
question — the 80B result strongly suggests yes)?

## exp-34 (superseded plan) — does raising lcm context_threshold kill the 80B stalls?

**Motivation (from exp-30/33):** the 80B's intermittent 25-min stall is **not Go-specific** —
it hangs on Go (2/9), TypeScript (2/9), and the hard task, but **never on Python** (21/21).
Python runs stay small; the stall languages grow context. This is exactly the
compaction-threshold hypothesis below, now testable on the 80B.

**Design:** 80B on **Go + TypeScript** (the stall-prone languages) × 3 reps, tuned m80, with
**`LCM_CONTEXT_THRESHOLD=0.7`** exported on `retort run` (compact at ~183K instead of ~92K).
Compare the stall rate to the 0.35 baseline (exp-30 Go, exp-33 TS, which had ~2 stalls each).
The env var is verified to override config.yaml's 0.35 via `LCMConfig.from_env()` (0.35→0.7);
smoke a single Go cell first and confirm the live agent used 0.7 before the grid.

**Hypothesis:** at 0.7 the stalls largely disappear — the hang is a context-management
artifact (lcm truncating working history mid-build), not intrinsic to the 80B. If so, the
80B could become viable on Go/TS with this one config change, a big result for the guide. If
stalls persist, the non-termination is intrinsic and the lever is a stronger model / more bits.

## Rust non-termination — is it the compaction threshold? (investigating)

**Smoke test (2026-07-14): inconclusive on the threshold, but Rust is NOT a wall.** One
clean isolated run terminated on its own at **25K context** (no thrash) and produced 332
lines of structured Rust with **3 compile errors** — a near-miss, not non-termination.
The threshold change (0.35→0.7) was **never exercised** (no run reached 92K). Two more
samples were run concurrently and interrupted — muddied, not usable (a control-conditions
mistake: single, isolated runs only). So Rust has (at least) two failure modes:
**thrash-to-wall** (exp-28) and **terminate-with-compile-errors** (smoke). The latter is
fixed by **self-repair on the build error**, likely a more relevant lever than the
context threshold. Still to do PROPERLY: (a) an isolated context_threshold 0.35-vs-0.7
run that actually reaches the threshold; (b) rust on a stronger model / more bits.


The 35B's Rust failure is a context THRASH: grow context → lcm compacts → the agent
loses the thread → regrow, forever (walls out). We suspected a residual 128K cap;
there isn't one. Investigation of the config (2026-07-14):

- context is correctly **262144** (Hermes top-level + per-model; model
  `max_position_embeddings` 262144, no rope/YaRN needed).
- The real ceiling is **lcm's `context_threshold: 0.35`** — lcm compacts when live
  context reaches `context_threshold × context_length` (`engine.py:626`) =
  0.35 × 262144 ≈ **92K**. The live Rust trace compacts at 92–117K, confirming it.
  So Rust never uses more than ~92K before its working history is truncated. This is
  a TUNABLE default, not a bug. (Separately, `l2_budget_ratio: 0.50` is unrelated —
  it's the step-down for lcm's second-tier summariser, not the compaction trigger.)

**Hypothesis:** the early compaction *causes* the thrash — the agent builds toward a
Rust solution, lcm truncates at ~92K, it loses state and rebuilds. **Test:** raise
`lcm.context_threshold` to **0.7** (compact at ~183K) and re-run the Rust bookshop
cell. If it converges/terminates, "Rust is a capability wall" is (partly) a
context-management artifact and comes off the board; if it still thrashes, the
non-termination is intrinsic and the next lever is a stronger model / more bits
(80B, a 6-bit 35B, or [[Agents-A1]]). Smoke-tested outside the experiment first
(single Rust run, watched live) before committing a grid.

## Inference-lever sweep (issue #40) — in progress

Prompted by [issue #40](https://github.com/adrianco/retort/issues/40) (jschoch): a
long list of local-inference levers (K/V quant, context quant, sampling params,
speculative decoding, MTP, quant scheme/level, SWA, MoE-vs-dense…) and the question
of whether they "resolve into reliability." Our harness is uniquely able to answer
that — pass-proportion **is** a reliability metric, unlike perplexity/KLD. Filtered
by our findings (generation-bound + wall-limited):

- **Tier 1 — sampling (exp-27, DONE).** Fractional factorial (Res IV 2^(4-1), 8
  presets) over temperature/top_p/top_k/repetition_penalty, 35B, bookshop, python+go.
  [RESULTS](../experiments/adrianco/experiment-27-sampling-ff/RESULTS.md). Overall **0.83** pass-proportion
  vs ~0.45 at the old temp=1.0 default. Main effects: **repetition_penalty 1.1 is
  harmful (−0.25 pass, owns all 4 stall-crashes)**; top_p 0.95 > 0.85 (+0.17); top_k
  20 slightly > off; **temperature 0.2 vs 0.7 = zero effect** (the win is getting OFF
  1.0, not the precise value). Best config ≈ **Qwen's own rec** (temp ~0.6, top_p
  0.95, top_k 20, NO rep penalty) — s7 went 6/6. **Re-baseline TODO:** every prior
  local experiment (exp-16→26) ran at temp=1.0, so their 0.38–0.50 numbers are
  *understated*; the recommended sampling is now the oMLX default for future local
  runs. `min_p` dropped (oMLX strips it from settings). The stall guard fired
  correctly (4 loops killed at ~16m, not the 45m wall).
- **Tier 1 — speculative decoding / MTP.** The throughput lever exp-24/26 point to
  (generation-bound → faster tok/s converts wall-crashes into passes). oMLX ships a
  Qwen3.5/3.6 MTP patch but the unsloth 4-bit build has no MTP weights → needs a
  small draft model for speculative decode. Highest payoff, more setup.
- **Tier 2 — quant level (4-bit → 6/8-bit) and scheme (unsloth/bartowski/stock).**
  Tests the brazil *capability* ceiling (Go reaches 0.92 req_cov but not 1.0): is the
  last mile lost to 4-bit quant error? 6-bit 35B (~26 GB) fits 64 GB.
- **Tier 2 — MoE vs dense** (issue #40 ask). Half-done (Devstral dense, wrong harness);
  a fair matched-size dense-vs-MoE on Hermes would isolate the architecture effect.
- **Deprioritised, with reasons.** K/V quant + context quant = *memory* levers, but
  context isn't our bottleneck and lossy KV risks reliability. convRot/turboquant, SWA
  = research-y, weak serving support. jinja/template = already solved for our Qwen path.
- **The meta-prize.** Log each config's pass-proportion alongside its published
  perplexity across the sweeps → *which inference levers move real coding reliability,
  and how badly perplexity mispredicts it.* No public benchmark answers this.

Harness support built for this (committed): a **stall-guard timeout** (high wall +
kill unproductive loops) and a **stack-reload hook** (`playpen.stack_presets` — a
`stack` factor whose presets reload the oMLX model + sampling at the model-selection
point, within one experiment). Run order groups by `stack` so each preset loads once.

## exp-28 — re-baseline the LOCAL LEADERBOARD (RUNNING; restarted after a harness bug)

exp-27 showed the 35B was crippled by oMLX's default sampling (temp=1.0). But **every
model has different author-recommended settings**, and we ran them all at the same
oMLX default (temp 1.0, top_p 0.95, top_k 0, rep 1.0). So the whole local leaderboard
may be invalid — and could reorder.

### The rerun: a second, worse confound found mid-flight (the write-refusal bug)

The first exp-28 launch had to be **killed and wiped**. Its Qwen3-Coder-30B arm went
**0/8** — fast no-op failures (10–25 s) and stall-kills — which looked like a terrible
model but was a **harness bug**:

> `[write_file] Refusing to write to sensitive system path: app.py`

retort put each playpen in the macOS temp dir (`mkdtemp` → `/var/folders/...`), and
**Hermes' safety guard classifies anything under `/var` as a sensitive system path**, so
it refused *every* `write_file` into the agent's own workspace. Fixed by moving playpens
to `~/.retort/work` (`_playpen_root`, commit `55dd192`); verified Hermes now writes with
zero refusals, and the 30B immediately started producing files.

**Why it hid for so long — and why that matters.** A *resilient* model routes around the
refusal via the shell and still produces code (so the run "works", just burning turns and
tokens); a *less resilient* one writes nothing and scores a **false zero**. The 35B —
our champion, and the model most of our conclusions rest on — was resilient, which
masked the bug. Measured incidence:

| experiment | runs hitting the write-refusal |
|---|---|
| exp-25 (brazil) | **3 / 3** |
| exp-26 (brazil, 60 min) | **6 / 6** |
| exp-27 (sampling FF) | **41 / 48** |

i.e. **essentially every local Hermes run since exp-17 has been fighting the harness.**

### Consequence: prior local results are floors, not measurements

Local numbers are now understated for **two independent reasons** — (1) sampling at
temp=1.0 (exp-27) and (2) the write-refusal. Everything Hermes-based (**exp-17 → exp-27**)
needs re-baselining on the fixed stack. `omp`-based runs (exp-16) are unaffected — the
guard is Hermes'.

**Conclusions now genuinely at risk** (ranked by how load-bearing they are):

1. **"Niche languages are a hard capability wall"** (exp-20: Clojure/Java/C#/Elixir/Erlang
   0/15, `requirement_coverage` flat zero, "never produced buildable code"). *Never
   produced buildable code* is exactly the write-refusal signature. This is the most
   suspect conclusion we have and the highest-value re-run.
2. **"Devstral is hopeless / agent-tuned doesn't transfer"** (exp-23: 0.17, 7/12
   non-terminating). Devstral ran at temp **1.0** vs its recommended **0.15** *and*
   through the write bug. Both the score and the "wrong harness" story are unsafe.
3. **"Bigger isn't better"** (exp-22/24, 80B ≤ 35B). Partially protected — the 80B was
   already near its recommended sampling — but it still ran through the write bug, and if
   the 35B gains more from the fix than the 80B, the gap *widens* rather than closes.
4. **Brazil hard-task numbers** (exp-25/26: 0.17 → 0.33, the Python-only story, Go's
   0.92 near-miss). All six runs hit the refusal; these are floors.
5. **Self-repair's value** (exp-21, 0.11 → 0.22). Some "failures" it repaired may have
   been write-refusals, not model errors.

**Probably safe:** exp-27's *main effects* (rep-penalty 1.1 harmful, top_p 0.95 > 0.85,
temp 0.2 ≈ 0.7). The write bug was **common-mode** across all 8 presets, so the
*differential* effects survive even though the absolute 0.83 is a floor. Worth a
confirmation pass, not a redo.

### Re-baseline queue (in priority order)

- **exp-28 (running):** the 3 Qwen models × own recommended sampling, bookshop mainstream
  4 languages — the leaderboard, on the fixed stack.
- **exp-29:** all 9 languages on the fixed stack — does the *niche-language wall* survive?
- **exp-30:** Devstral at temp 0.15 (needs llama.cpp; oMLX can't parse Mistral tool calls).
- **exp-31:** brazil-bench re-baseline (hard task, fixed stack + right sampling).
- **Then:** [Agents-A1](#agents-a1--queued-next-new-model-to-add) head-to-head vs the
  re-baselined 35B.

**Method note earned the hard way:** when a model produces *no code at all*, suspect the
harness before the model. A "capability wall" and a blocked file-write tool look
identical in the scores.

| model | recommended (source) | what we actually ran | mismatch |
|---|---|---|---|
| Qwen3.6-35B-A3B | temp 0.6, top_p 0.95, top_k 20, rep 1.0 (exp-27 empirical; = Qwen3 rec) | temp 1.0, top_k 0 | **wrong** — cost ~half its reliability |
| Qwen3-Coder-30B-A3B | temp 0.7, top_p **0.8**, top_k 20, rep **1.05** (`generation_config.json`) | all four off | **wrong on every knob** |
| Qwen3-Coder-Next-80B | temp **1.0**, top_p 0.95, top_k 40 (`generation_config.json`) | temp/top_p already right | **~already correct** |
| Devstral-Small-2507 | temp **0.15** (Mistral docs) | temp 1.0 | **catastrophically wrong** |

Note the Coder line *recommends* a repetition penalty (1.05) even though exp-27 found
1.1 harmful on the general 35B — so "rep penalty is bad" may be model-family-specific.

**Predictions (falsifiable):** the 35B and 30B jump; the **80B barely moves** (it was
already near its rec — which would *strengthen* "bigger isn't better", since the 35B
improves and the 80B can't); **Devstral could be transformed** (its 0.17 + 7/12
non-termination may be almost entirely a temp=1.0 artifact, not the "wrong harness"
story exp-23 told).

**Design:** bookshop (easy), mainstream 4 languages (python/go/typescript/rust),
prompt=neutral, 3 reps — matching the ORIGINAL leaderboard config so *sampling is the
only change*. Each model = a `stack` preset (served model + its own recommended
sampling); the reload hook swaps model+sampling at the model-selection point, run order
grouped so each model loads once.
- **exp-28 (oMLX):** the 3 Qwen models — 3 × 4 langs × 3 reps = **36 runs**.
- **exp-29 (llama.cpp):** Devstral at temp 0.15 — needs the llama.cpp serving path
  (oMLX can't parse its Mistral tool format; the exp-23 blocker), so it's a separate
  arm until the stack manager grows a backend field.

## Cheap opportunistic checks

- **oMLX 0.5.0 MTP (multi-token prediction) — now the top speed lever.** exp-24
  showed the binding constraint is **generation throughput**, so lossless
  speculative decoding is the right thing to try next: does faster generation let
  slow-but-terminating runs (esp. the 80B, and Rust/Go on the 35B) finish before
  the 30-min wall (crash → completed)? It won't raise *quality*, but converting
  crashes to real data points is exactly what our wall-bound failures need. Matters
  far more for the slow 80B than the 35B.
- **Timeout / turn-cap tuning.** Several failures were non-termination at the
  wall. A higher timeout or lower `max_turns` converts crashes to real data
  points more cleanly than MTP does.

---

## Standing method notes

- Incremental design: add ONE new model/factor at a time; run only the new cells;
  compare against `master.db`. Never re-run existing baselines.
- Spec-gate always ON. Clean archive bloat (truncate `_agent_stdout.log`, strip
  node_modules/target) before committing.
- After each experiment: update `model-blog.md` + push to GitHub.
- **Self-repair second-chance is the universal default** (every task, every run) —
  don't opt out with `--no-second-chance` unless explicitly asked. It repairs
  *completed-but-failed* runs; *crashes* (wall-timeouts) don't get it, so raise the
  timeout to convert them into repairable/passing runs.
- **Timeout is per-experiment and LOCAL runs need more time** (local models are slow).
  Set `playpen.timeout_minutes` generously in the workspace.yaml for any local stack
  (e.g. 60 min, vs ~30 for cloud). It's a property of the stack, not the task — don't
  bake it into the task definition.
