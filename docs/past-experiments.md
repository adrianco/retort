# Past experiments — completed runs & rejected candidates

Append-only log of finished work, in **increasing experiment order**. Each entry is the
**result** (the pre-registration plan lived in [`future-experiments.md`](future-experiments.md)
before launch and is removed from the queue once the run lands). Rejected / parked model
candidates are recorded at the end. The live queue of what to do next is in
[`future-experiments.md`](future-experiments.md).

Local-model work runs on a **MacBook Pro M5, 64 GB** (GPU wired limit ~56 GB), serving MLX
models via **oMLX** and driving them with the **Hermes** agent (+ `hermes-lcm` context engine).
Credits: **Birgitta Böckeler** ([local-models writeup](https://martinfowler.com/articles/exploring-gen-ai/local-models-for-coding-experiences.html))
and **kamihack** (oMLX / model / tool-template pointers).

---

## Completed experiments

### exp-16–20, 22, 23 — the early local exploration
Full per-cell results are under each `experiments/**/RESULTS.md`. Key findings: **exp-16**
(Qwen3-Coder-30B via llama.cpp) — context is the first-order lever (0.08 @32K → 0.33 @128K).
**exp-17** — the Hermes agent vs `omp`. **exp-18** — Hermes-lcm + Qwen3.6-35B cracked TypeScript
(0.38, the best local result at the time). **exp-19** — prompt factor on the 35B (ATDD worst,
0/3). **exp-20** — 35B × 9 languages (niche-language wall). **exp-22** — 80B first-try 0.33 < 35B
0.50 ("bigger isn't better", later shown to be a compaction artifact — see exp-34/38). **exp-23**
— Devstral via llama.cpp, 0.17 (wrong harness). ⚠️ **All exp-17→27 Hermes runs are understated
floors**, not measurements — they ran through the temp=1.0 and write-refusal bugs (see *Harness
bugs* below); the exp-28+ re-baseline supersedes them.

### exp-21 — self-repair with evaluation feedback (35B)
Gave exp-20's near-miss failures a second try, seeded with their own code + the evaluation
feedback. **Repair roughly doubled pass-proportion 0.11 → 0.22, but only on mainstream
languages** — the niche-language wall held (a true capability ceiling, not something feedback
rescues). Scoring rule (still in force): a repaired pass counts **half credit** toward
pass-proportion (it needed the eval handed to it), while all quality metrics stay at their true
final values. This is the same mechanism as the default inline second-chance now baked into
every run; the self-repair *method* is reused by the queued exp-41 (iteration-2 on the 80B).

### exp-24 — KV prefix cache (resolved: no help)
Turned oMLX's on-disk prefix cache on and re-ran the identical 80B grid
([RESULTS](../experiments/adrianco/experiment-24-qwennext80b-cached/RESULTS.md)). Pass-proportion
**0.33 → 0.33**; the cache *hits* (88K prefix restored in ~2.5 s vs ~150 s cold) but our runs are
**generation-bound, not prefill-bound**, so faster prefill doesn't convert to reliability. Leave
the cache on for free prefill latency, but expect nothing from it. (Operationally: keep the
paged-SSD cache **small** — a 120 GB cap silently fills the disk; 5 GB is plenty.)

### exp-25/26 — the hard task on the local 35B (resolved)
**exp-25:** the 35B copes with brazil-bench in Python (1/3 clean MCP server, req_cov 1.0), not Go
(0/3); overall 0.17, half the runs hit the 30-min wall (generation-bound). **exp-26:** doubling
the timeout to 60 min lifted pass 0.17 → 0.33, crashes 3 → 1, and Go went from all-zeros to a
0.92-req-coverage near-miss. The wall was masking capability; the residual gap is now capability
(Go's last mile), not budget. **Next speed lever is throughput (MTP), not more wall-clock.**

### exp-27 — sampling fractional factorial (35B) — the sampling tier of issue #40
Res IV 2^(4-1), 8 presets over temperature/top_p/top_k/repetition_penalty
([RESULTS](../experiments/adrianco/experiment-27-sampling-ff/RESULTS.md)). Overall **0.83
pass-proportion vs ~0.45 at the old temp=1.0 default.** Main effects: **repetition_penalty 1.1 is
harmful** (−0.25 pass, owns all 4 stall-crashes); top_p 0.95 > 0.85 (+0.17); top_k 20 slightly >
off; **temperature 0.2 ≈ 0.7 (zero effect — the win is getting OFF 1.0, not the precise value).**
Best config ≈ Qwen's own rec (temp ~0.6, top_p 0.95, top_k 20, no rep penalty). `min_p` dropped
(oMLX strips it). This established the correct local sampling now baked into optimal-blog's
forbidden settings, and revealed that every prior local number was understated.

### exp-28 — the local re-baseline (35B arm)
At correct sampling (temp 0.6, top_p 0.95, top_k 20, no rep penalty) and a **true 256K context**,
the 35B on bookshop mainstream: **python 3/3, go 3/3** (both were ~0.5–0.67 at the broken temp=1.0
stack — the old numbers badly understated); typescript 0/3 ("tests did not run"); rust 0/2
(thrash/near-miss). The 35B is the production local stack for **Python/Go** (0.85 each across
later aggregation). See *Harness bugs & the re-baseline saga* below for why this re-baseline was
necessary and what it invalidated.

### exp-29 — the 80B re-baseline (Qwen3-Coder-Next)
n=3/language: **python 1.00 (beats 35B), go 0.67 (rep2 stalled to the wall), typescript 0.33.**
`retort diagnose` classified the non-completions GENUINE. Doubling the model helps Python but not
Go/TS, and it's ~2× slower. Recorded the model correctly via the `stack_metadata()` fix (no slug
guessing). Verdict at the time: a candidate, not yet recommended.

### exp-30 — more 80B reps on Python/Go
exp-29+30 combined, n=9/language: **python 9/9 = 1.00** (best local Python), **go 6/9 = 0.67** —
the Go stall recurred (2 runs stalled to the 25-min wall, both GENUINE non-termination). Split
recommendation at the time: 80B for Python, 35B for Go. Two harness bugs fixed here: the live
monitor now descends through launcher wrappers; the tool-refusal abort is gated on `wrote_nothing`
so Hermes's benign "N files NOT modified" advisory no longer discards good runs.

### exp-31 — the 80B on the HARD task (brazil)
n=6: **0.00 pass (0/6)** but **mean requirement_coverage 0.83** — the 80B consistently gets ~10/12
capabilities, never all 12. The 35B is 0.25 (3/12), mean 0.79 — lower average but occasionally
nails all 12. `reevaluate --force` re-confirmed every near-miss as genuine. **Local models don't
reliably clear hard tasks (0–25%); hard stays a cloud niche** (Fable 5 = 1.00). The Go stall
recurred here too (task-independent).

### exp-32 — prompt-factor re-test on the 80B
python routine, n=3/prompt: the prompt is a **flat line on the 80B** — neutral/BDD/TDD/**ATDD all
1.00.** Contrast the 35B (exp-19): neutral/BDD 0.67, TDD 0.33, ATDD 0.00. **The methodology lever
bites in proportion to model weakness** — "never ATDD locally" was 35B-specific. General rule now
in the guide: reach for a disciplined methodology only near a model's capability edge, else pick
neutral (cheapest).

### exp-33 — TypeScript on the 80B (at the 0.35 default)
n=6 (combined with exp-29 → n=9): **TS = 0.33 (3/9)** — 2 passes, 1 near-miss, 2 genuine fails,
**1 stall.** Confirmed TS-on-80B unreliable at the default threshold, and — the cross-cutting
finding — the **intermittent stall is NOT Go-specific** (it hangs on TS too). Python is the only
language it never hangs on (21/21). This motivated the compaction-threshold investigation
(exp-34), which later *unlocked* TS at full context (exp-38).

### exp-34 — raising lcm context_threshold 0.35 → 0.7 KILLS the 80B stalls
80B, Go+TS × 3 at `LCM_CONTEXT_THRESHOLD=0.7`: **0 stalls in 6 runs, Go 3/3 = 1.00** (vs ~4 stalls
in 15 runs, Go 0.67 at 0.35). **The intermittent 25-min hang is a compaction artifact** — at 0.35,
lcm compacts live context at ~92K and truncates the agent's working history mid-build, so it loses
the thread and thrashes to the wall; at 0.7 (compact ~183K) it doesn't. TS still 0.33 but now via
genuine near-misses (0.83–0.92), not hangs. Env var verified end-to-end before the grid.

### exp-35 — context_threshold 0.7 PARTLY fixes the 35B's Rust wall
35B Rust × 3 at 0.7: **1/3 — rep1 PASS (the 35B's first-ever Rust pass, reached 113K context),
rep2/rep3 still stalled** (GENUINE). At 0.35 every Rust run thrashed (0.00). So **Rust is not a
pure capability wall** — the 92K compaction was a real cause — but 0.7 is only a *partial* fix on
the 35B (unlike the 80B on Go/TS, 0/6 stalls). The compaction lever's strength is
model/language-dependent; Rust stays → cloud. (Also found: provenance.json recorded a stale
pre-reload sampling value — verify sampling via oMLX `settings.json`, not provenance.)

### exp-36 — 80B Go promoted at context_threshold 0.7
80B Go × 6 at 0.7: 5/6 (one genuine near-miss), 0 stalls. Combined with exp-34 → **Go 8/9 = 0.89
at 0.7, zero stalls** — up from 0.67-with-2-stalls at 0.35, on par with the 35B. The stall fix
holds at scale; the 80B is now local-viable on Go as well as Python at ctx 0.7.

### exp-37 — 80B Python at 0.7 = 1.00 (an anomaly that was serving degradation)
First pass showed Python 4/6 with 2 fast all-zeros fails — traced to **oMLX serving degradation
after ~12h continuous running**, not a 0.7 effect (Python is 21/21 at 0.35 and never reaches the
compaction point). After **restarting oMLX + disk cleanup**, the retried cells passed →
**Python-at-0.7 = 6/6 = 1.00.** Operational lessons shipped: restart oMLX before a run you'll
trust; `retort run` now does a disk preflight; `monitor --watch` follows the run process.

### exp-38 — full 9-language 80B at full context: TypeScript UNLOCKED
All 9 bookshop languages on the 80B at `LCM_CONTEXT_THRESHOLD=0.9` (compact ~236K), n=3 = 27 cells:

| Language | pass | mean req-cov | verdict |
|---|---|---|---|
| python / go / **typescript** | **3/3** | 1.00 | reliable local (**TS newly, was 0.33**) |
| rust | 1/3 | 0.94 | near-misses → cloud |
| java / erlang | 0/3 | 0.25 / 0.19 | near-miss → cloud |
| clojure / csharp / elixir | 0/3 | 0.00 | GENUINE (no working code) → cloud |

**Full context unlocks TypeScript** (0.33 → 3/3): at 0.9 the agent keeps its whole working history
through the longer TS build. Python/Go stay 3/3, so **0.9 is the recommended 80B config.** Rust's
rep2/rep3 were scorer TOOLING false-failures (code compiles, tests pass 100%; reevaluate gave true
0.92 near-misses) — not stalls. Generator gained a per-stack `routine_scope` so the leading-stacks
headline is scoped to a stack's recommended languages (else the niche 0.00s wrongly rank the 80B
below the 35B). **Process lesson: an all-zeros cell on a capable language ⇒ `retort recover` before
believing it** (4 of 17 fails were tooling false-failures).

### exp-39 — hard task is config-invariant (VERIFIED)
Re-ran brazil on the 80B at ctx 0.9, n=3 (python/go): **0/6, same as exp-31 at 0.7.** python mean
0.75 (rep1 0.917 = 11/12, the closest any local run has come; never all 12); go mean 0.22, and go
rep3 **STALLED** — Go *regressed* at 0.9 because full context makes a non-finishing run thrash
longer (the same downside as exp-38 rust). **Full context is strictly a lever for the easy
languages; it does not raise the hard-task ceiling.** The featured 80B hard column uses exp-39
(0.9) for config-purity. 4/6 fails were scorer TOOLING false-failures (recovered via `retort
recover`).

### exp-41 — self-repair ITERATION 2 does not close the 80B's near-misses

Tested whether a *second* dedicated repair pass (seeded with the iter-1 code + a fresh FEEDBACK.md via
`--repair-from exp-38`) closes the last 1–2 requirements on the 80B's near-misses. Design: rust/java/
erlang × `prompt=repair` × m80 × n=3 (rust rep1 skipped — already 1.0 in exp-38). Post-`recover` (3 of
6 fails were scorer TOOLING false-zeros; the diagnose caught them):

| lang | exp-38 baseline (post-iter-1) | iter-2 repaired req_cov | verdict |
|---|---|---|---|
| **rust** | 0.9167 (11/12) | 0.917, 0.833 | **no gain** — the headline near-miss did NOT close |
| **erlang** | 0.3333 | 0.333, 0.333 | **no change** |
| **java** | 0.75 | 0.917 (rep1) | **+1 req** — the only lift; still <1.0 |

**Headline: iteration-2 self-repair is not a reliable lever.** The most-likely-to-flip cell (Rust at
0.9167) stayed there — a second pass reproduces the same near-miss rather than closing the final
requirement, so **Rust does not become locally viable on the 80B** (stays cloud). Erlang flat. The one
positive is java 0.75→0.92 (repair closed ~1 req on a lower-starting-point cell), but nothing reached
1.0. **Interpretation:** the *default inline* second-chance (iteration-1, which already runs on every
failing cell) captures essentially all the repairable gain; a dedicated iteration-2 mostly re-derives
the same result. **Caveat:** 3 cells (erlang rep3, java rep2/rep3) were INTERRUPTED at ~23 s — a
mid-run hermes/oMLX hiccup, not scored — so java's iter-2 picture is one rep, not three; a
`--resume --retry-failed` re-run would complete it, but wouldn't change the Rust/Erlang verdict.

### exp-43 — C / C++ / Objective-C / Swift exploration (cloud vs local 80B)

First run on the **systems + Apple** tier: `language{c, cpp, objc, swift} × model{Opus 4.8 cloud,
Qwen3-Coder-Next 80B local @ ctx 0.9} × bookshop × n=1` = 8 cells. The point was a first
cloud-vs-local read on four languages new to the harness — and, as much, to *harden the harness* for
them.

**Result (after `retort recover` with all harness fixes applied — req-coverage / spec-gate):**

| lang | Opus 4.8 (cloud) | Qwen 80B (local) |
|---|---|---|
| **c**   | ReqCov **1.0** ✓ | ReqCov **1.0** ✓ — **full pass** (cq 1.00, cov 1.00) |
| **cpp** | ReqCov 1.0 ✓ | ReqCov **0.83** — near-miss (cq 0.93, ~5/6 requirements; a repair candidate like Rust) |
| **objc**| ReqCov 1.0 ✓ | fail — wrote 1134 loc ObjC but **no build system / tests** (genuine incomplete) |
| **swift**| ReqCov 1.0 ✓ | fail — real SwiftPM/Vapor project, build/test didn't pass (genuine) |

**Headline:** the **frontier sweeps 4/4**; the **80B fully implements the C bookshop (ReqCov 1.0)**
and near-misses C++ (0.83) — much stronger on the systems tier than the *raw* run suggested, and
better than it does on several "niche" languages. ObjC/Swift are genuine incompletes (no runnable
tests / a broken Vapor build). So the systems-tier gap is **C/C++ are locally viable-to-close; the
Apple frameworks are not yet**.

**⚠️ The number that moved most was a HARNESS bug, not the model.** The raw run scored local-C
**0.00**; `retort recover` (with the new server-reaping fix) flipped it to **1.00**. The 80B's C was
*always* correct — its integration test backgrounded a server that leaked and squatted port 8765, so
the retry and scorer hit "address already in use" and false-failed working code. Six harness bugs in
total surfaced and were fixed *before* any conclusion was drawn (below); the recovered numbers above
are the honest result. Textbook "suspect the harness before the model": publishing the raw run would
have claimed "the 80B can't write C," which is flatly false.

**The harness hardening — the real yield of the run** (all fixed + regression-tested):
1. **hermes not on PATH** → all 4 local cells crashed at 0.0s → `serving.hermes_bin` + a new
   **local-agent binary preflight** (`retort run` now warns up front instead of crashing every cell).
2. **C has no canonical test format** — three real bookshops used three formats (TAP, `N checks, M
   failures`, bare names) → make the **test-command exit code the universal pass signal** in
   `_native_coverage`, plus TAP + broadened summary patterns.
3. **Swift 6 uses Swift Testing** (`@Suite`/`@Test`), not XCTest → added its patterns + a `swift test`
   exit-code fallback + a 900s timeout (SwiftPM/Vapor builds are slow).
4. **DEVELOPER_DIR** auto-resolution so Swift/ObjC XCTest works when `xcode-select` points at the CLT.
5. **`.build` (SwiftPM vendored deps) wasn't skipped** → swift loc inflated ~1000× (834K vs ~200) →
   added to `SKIP_PARTS`.
6. **`retort monitor --watch`** exited immediately / hid the running cell for `cd <exp> && retort run`
   launches → detect the run process by **cwd**, not just argv.
7. **Leaked server processes** (the big one) — a model's integration test backgrounds a real server
   that outlives the test command, keeps LISTENing, and false-fails the retry + later cells with
   "address already in use" → `_run_reaped` runs every test command in its own process group and
   SIGKILLs the group afterward (temp-file output + `wait()`, since a backgrounded server holds the
   stdout pipe open and blocks `communicate()`). This is what flipped local-C 0.00 → 1.00 on recover.

Full scorer support (build/test/coverage/lint) for c/cpp/objc/swift landed here — see the README
toolchain table. Remaining follow-up: give ObjC/Swift-local a fair shot — the 80B produced ObjC
source with no build system and a Vapor Swift app that won't build in-env; a lighter task variant or
a build-scaffold nudge would separate "can't" from "didn't scaffold."

### exp-44 — Graphify tooling factor on a modify-existing Python task (frontier arm)

First run of the **tooling: graphify** factor (a pre-built code knowledge graph) on the new
**modify-existing** task `py-catalog-reservations` (add a reservations feature to a seeded
catalog/ library; scored on req-coverage of the new capability AND a no_regression gate that the
seed's existing suite still passes). Design: `tooling{none, beads, graphify} × Opus 4.8 × n=3` = 9
cells, cloud-first to isolate the tooling effect from local-capability noise.

**Result — tooling is a NO-OP on correctness here; it only costs time:**

| tooling | req_cov | no_regression | code_quality | mean duration |
|---|---|---|---|---|
| **none**     | **1.0** | 1.0 | 0.833 | **79 s** |
| **beads**    | **1.0** | 1.0 | 0.833 | 132 s (**+67%**) |
| **graphify** | **1.0** | 1.0 | 0.833 | 86 s (+9%) |

All three sweep 3/3 at perfect req-coverage and no-regression. **beads actively costs 67% more wall
time** (the issue-tracking loop) for zero correctness gain; **graphify's graph-build + consultation
adds ~9%** and also changes nothing. This is the same shape as the prompt blog's finding, now for
*tooling*: **on a strong model + an easy task, tooling is a lever only in proportion to model
weakness — here, zero.** The catalog seed is ~5 modules / ~200 lines, which a frontier model
navigates without a map.

**This is the control, not the headline.** Graphify's value proposition is comprehending a *large*
existing codebase, so a clean null on a *small* one is exactly what predicts where it *should* bite.
The plumbing itself is validated: the consultation smoke confirmed Opus genuinely used the graph (4×
GRAPH_REPORT.md reads + `graphify explain`/`query`/`path`), so this null is "tooling didn't help," not
"tooling was ignored." New reusable machinery landed here: the `tooling: graphify` capability, the
`no_regression` scorer, and a seed-based modify-existing task type (`seed/` → support_dir).

### exp-45 — Graphify tooling on the LOCAL 80B (the weaker-model arm)

Same design as exp-44 (`tooling{none,beads,graphify} × catalog × n=3`) but on the local
**Qwen3-Coder-Next 80B** — the "does a weaker model need the map?" half. **Result: identical null —
all three tooling levels 1.0 req_cov + 1.0 no_regression** (graphify 170 s ≈ none 181 s; beads +43 %).
The 80B solves this small modify-existing task cleanly unaided, just like Opus.

**⚠️ Important caveat — consultation is UNVERIFIABLE for the local agent.** Unlike claude-code (whose
stream-json logs every Read/Bash, so exp-44 *proved* Opus queried the graph), **Hermes writes only a
minimal stdout** (~11 lines: no tool-call log), so grepping the transcript for graph reads finds
nothing — which is a *logging gap, not proof the 80B ignored the graph*. The graph WAS built
(graphify-out/ present, 45 nodes, noted in the eval). So exp-45's null is honestly "tooling didn't
change the outcome," but we cannot distinguish "consulted-but-didn't-need-it" from "ignored-it" for
the 80B. **Harness follow-up:** parse Hermes' usage/session file (or enable verbose logging) so
tool-consultation is verifiable for local agents — this matters for the funkygibbon large-repo
graphify arm, where "did the agent actually use the graph?" is the whole question.

**Combined §1 conclusion (exp-44 + exp-45):** on a *small* modify-existing task, tooling
(none/beads/graphify) is a no-op on correctness for **both** the frontier and the local 80B — a
~200-line seed is navigable without a map, and beads only adds wall-time. The real test of Graphify's
value stays the **large-repo** arm (funkygibbon-port / the-goodies ~30K lines), where navigation is
the actual bottleneck.

---

## Historical: harness bugs & the local re-baseline saga

Three harness bugs each moved a result more than the model choice did — all **unrecorded stack
variables**. The pattern, not the individual bugs, is the finding: *suspect the harness before the
model* (now enshrined in CLAUDE.md and `retort diagnose`).

| Bug | What it did | Fixed |
|---|---|---|
| **Playpen under `/var`** | Hermes refuses to write to a "sensitive system path", so the agent couldn't create files in its own workspace. A resilient model routed around it (burning turns); a weaker one wrote nothing → **false zero**. Hit 41/48 runs in exp-27, 6/6 in exp-26. | playpens → `~/.retort/work`; `retort diagnose` returns a **HARNESS** verdict; a no-write streak aborts the run. |
| **Sampling at `temperature: 1.0`** | oMLX's default, never recorded — cost roughly **half** the reliability of every local result. `repetition_penalty > 1.0` also derails the agent loop, even at the model card's value. | exp-27 measured it; correct sampling is the default and lives in optimal-blog's forbidden settings. |
| **Context silently 128K, not 256K** | The stack-reload hook rebuilt Hermes' per-model config map on a model switch, destroying `context_length: 262144` → Hermes fell back to 128K, while the config *and* provenance still read 262144. | Never rebuild the map; `context_length` is part of the preset + the reload signature; provenance now reports the **effective** per-model value. |

**Consequence:** every Hermes-based local result **exp-17 → exp-27** is an understated *floor*, not
a measurement — the re-baseline (exp-28 onward, correct sampling + true 256K + fixed playpen)
supersedes them. The most load-bearing conclusion overturned was the **"niche-language wall"**:
"never produced buildable code" was partly the write-refusal signature — though exp-38 later
confirmed clojure/csharp/elixir *are* genuine 0.00 even on the fixed 80B stack. Instrumentation
added to catch this class of bug: per-run **peak context** (`_max_context_tokens`, local + cloud),
and a `provenance.json` recording the **effective** sampling / context / revision hash / harness
settings.

---

## Rejected / parked model candidates

Candidates examined and removed from the queue (fit budget: ~56 GB wired GPU → ~45 GB weight
ceiling).

- **Ornith-1.0-35B — SKIPPED (vision-optimized VLM, agent-hostile sampling).** Downloaded,
  inspected, deleted (2026-07-19). Three disqualifiers at pre-flight: (1) the MLX build is a
  **multimodal VLM** (`Qwen3_5MoeForConditionalGeneration` + `vision_config`, served via
  `mlx_vlm`) — vision + Terminal-Bench focus, not our text CRUD/MCP niche; (2) its recommended
  sampling collides with three forbidden settings (temp 1.0, repeat_penalty 1.05, min_p — stripped
  by oMLX); (3) the linked 5-bit build is deprecated (points to `-5bit-XL`). **Lesson: check
  `architectures`/`model_type` in the HF `config.json` at intake — a "tuned Qwen" can be a VLM.**
- **Agents-A1 — DEPRIORITIZED (also VLM).** Verified 2026-07-19: identical
  `Qwen3_5MoeForConditionalGeneration` + `vision_config` — **the whole Qwen3.5-35B-A3B fine-tune
  family is VLM-arch**, not text-native like our production Qwen3.6-35B. Would need the `mlx_vlm`
  text path + a tool-parse gate-probe. Revisit only if we deliberately want to test the VLM serving
  path. (Was queued as the "agent-tuned beats general" head-to-head; that hypothesis is better
  tested by exp-41 self-repair or a non-VLM candidate.)
- **Poolside Laguna XS 2.1 (33B/3B MoE) — BLOCKED (arch not in mainline serving).** Gate-probe
  2026-07-21. Text arch (`LagunaForCausalLM`, 262K ctx), MLX + GGUF builds exist (~17 GB Q4), but it
  can't be served by anything mainline: **oMLX** lacks the `laguna` arch (mlx-lm 0.31.3) *and* the
  `poolside_v1` XML tool parser; **llama.cpp** (brew build 9910 *and* master) lacks the `laguna`
  arch too — its support PRs are **unmerged** (#25165 open, #25595 closed-unmerged) with open Metal
  MoE-overflow issues. Downloaded the Q4 GGUF and confirmed `llama-server` errors `unknown model
  architecture: 'laguna'`. Testable only via an experimental llama.cpp PR-branch build or vLLM (which
  has the `poolside_v1` parser). Deprioritised: modest expected value (30B-class) vs. building from
  an unmerged PR. Revisit once laguna lands in a mainline llama.cpp release. **Revisit path found (2026-07-22):** Ollama *does* ship `laguna-xs-2.1` (its bundled llama.cpp has the arch), and Poolside's own **`pool`** agent (ACP, speaks `poolside_v1` natively) drives it via `ollama launch pool --model laguna-xs.2`. So Laguna is testable by adding `pool` as a retort agent harness (bounded work, like the gemini/omp/opencode harnesses) pointed at Ollama-served laguna — no oMLX/llama.cpp arch gap on that path.
- **Devstral Small 2 (24B) — NOW UNBLOCKABLE via the llama.cpp backend.** oMLX doesn't parse its
  Mistral `[TOOL_CALLS]` format (exp-12/23 wall). But retort now has a **`serving.backend: llamacpp`**
  path (2026-07-21), and Devstral's Mistral arch + tool template *are* in mainline llama.cpp — so it
  can now be gate-probed via `llama-server --jinja`. Requeue if the agent-tuned-coder question is
  worth re-testing on a fair stack (its exp-23 0.17 ran at temp 1.0 through the write-refusal bug).
- **Excluded — too big for 64 GB:** gpt-oss-120b (~64–65 GB, over the wired limit), GLM-4.5-Air /
  4.7-Flash (borderline), and the multi-GPU tier (MiniMax M3 428B, GLM-4.6 355B, DeepSeek-V4-Pro,
  Kimi K2.6, Qwen3-Coder-480B).
