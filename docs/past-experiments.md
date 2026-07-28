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

**✅ Consultation caveat RESOLVED (2026-07-24).** Initially the local null was ambiguous — Hermes
writes only a minimal ~11-line stdout with no tool-call log, so grepping the transcript found nothing
and we couldn't tell "consulted-but-didn't-need-it" from "ignored-it." But Hermes DOES persist the
full transcript in its SQLite session store, keyed by the `session_id` in `.hermes_usage.json`. A new
`_export_hermes_session` (writes `_hermes_session.jsonl` after each Hermes run) + a cross-agent
`agent_consulted()` detector make it verifiable — and, exported retroactively for exp-45, **all three
graphify cells DID consult the graph** (95–115 tool_call refs, `GRAPH_REPORT.md` reads each). So the
80B null is genuinely **"used the graph, didn't help,"** exactly like Opus — not a logging artifact.
This unblocks the funkygibbon large-repo arm, where "did the agent actually use the graph?" is the
whole question.

**Combined §1 conclusion (exp-44 + exp-45):** on a *small* modify-existing task, tooling
(none/beads/graphify) is a no-op on correctness for **both** the frontier and the local 80B — a
~200-line seed is navigable without a map, and beads only adds wall-time. The real test of Graphify's
value stays the **large-repo** arm (funkygibbon-port / the-goodies ~30K lines), where navigation is
the actual bottleneck.

### exp-50 — the local hard-task wall is real for unattended runs, and breachable with feedback

Re-ran exp-39 unchanged except for the turn cap: `Qwen3-Coder-Next 80B × brazil-bench ×
{python, go} × n=3`, ctx 0.9, 120-min wall. 6/6 completed.

| language | rep1 | rep2 | rep3 |
|---|---|---|---|
| python | **1.00** (51 turns) | **1.00** (34) | 0.9167 (27) |
| go | **1.00** (56 turns) | 0.8333 (57) | 0.8333 (28) |

**3 of 6 runs fully implemented the hard task** — against exp-31/39's **0 of 12**. The 80B *can* do
brazil-bench, which the published "config-invariant capability wall" said it never does.

**But every single pass came on the self-repair SECOND attempt.** All six runs carry
`_second_try=1.0`: each failed its first unattended pass and was re-seeded with its own code plus the
evaluation feedback. **First-attempt, unattended: 0/6 — exactly exp-39's result.** Since retort counts a
second-try pass at half credit, the pass-proportion is **0.25**, not 0.50.

So the correct reading is narrow and more interesting than either extreme: **the 80B reliably reaches
~11 of 12 capabilities and cannot close the last one on its own, but given its own output and a
specific critique it closes it about half the time.** That is a claim about feedback loops, not raw
capability, and it connects directly to exp-41's self-repair work. "Hard tasks → cloud" stands for
unattended use; a local stack with a repair loop is a genuinely different proposition.

**⚠️ THE PREMISE OF THIS EXPERIMENT WAS WRONG, and the write-up is kept honest about it.** It was
launched on the theory that a 30-turn Hermes cap had been truncating exp-39. That theory came from
reading archived `api_calls` as **3 per turn**, making "90 api_calls" look like 3 × the cap. exp-50
records `api_calls` **and** `_turns` for the same runs and they are **1:1** (python 51 = 51, go 56 =
56). So exp-39's runs took 32–90 turns — *above* the supposed cap — and none hit the 60-minute wall
(longest 3016 s). **Nothing truncated exp-39; it fell short on merit.** The remaining explanation for
exp-50's passes is the serving stack having moved (oMLX 0.5.0rc1) or ordinary variance around a
threshold the model already sat on. The `max_turns` plumbing fix stands on its own — retort should not
silently disagree with its own declared config — it just isn't what this experiment measured.

*Method note:* this is the fourth time in this project that a single early run pointed one way and the
replicates pointed another. The first two cells here were both 1.00 and read as a clean overturn; at
n=6 the honest number is 0.25.

### exp-49 — thinking level: a 4× cost lever that buys nothing on routine work

The first experiment to treat **thinking level** (`claude --effort`) as a factor. Every result this
project had published ran at whatever the CLI chose by default, unrecorded — a confound sitting on
[versions-blog](../versions-blog.md)'s central claim that newer models take more turns. Design:
`{Opus 4.7, 4.8, Fable 5, Opus 5} × {default, low, medium, high, max}` + a `4.8-fast` serving control,
all on `python × bookshop × neutral`, **n=3 → 63 runs. 63/63 completed, 0 failures.**

**Headline 1 — effort is a large cost lever and a zero reliability lever.**

| effort | turns | tokens | cost | seconds | **pass** | n |
|---|---:|---:|---:|---:|---:|---:|
| **low** | **10.3** | **277 K** | **\$0.71** | **75** | **1.00** | 12 |
| medium | 12.4 | 340 K | \$0.84 | 95 | **1.00** | 12 |
| *default (CLI's own choice)* | 15.3 | 430 K | \$0.94 | 135 | **1.00** | 15 |
| high | 17.4 | 571 K | \$1.08 | 180 | **1.00** | 12 |
| max | 21.7 | 995 K | \$2.90 | 462 | **1.00** | 12 |

low → max costs **2.1× the turns, 3.6× the tokens, 4.1× the money and 6.2× the wall-clock** — for an
**identical 1.00**. Every one of the 62 telemetry-bearing runs passed, at every level, on every model.
**On routine work the thinking knob is pure expense.** Even against the CLI default, `low` is ~25%
cheaper and ~45% faster with no measured reliability cost — and the default is *not* the cheapest
setting, it sits between `medium` and `high`.

**Headline 2 — the version "progression" was mostly an artifact of one old experiment.**
versions-blog described a smooth climb: Fable 5 10.7 → Opus 4.8 17.3 → Opus 5 36.0 turns. Measured
**in-batch at default effort**, three generations are indistinguishable and only Opus 5 moves:

| model | in-batch turns (n=3) | published | ratio | source of the published figure |
|---|---:|---:|---:|---|
| Opus 4.8-fast | 11.5 | 11.3 | **1.02×** | exp-7 |
| Fable 5 | 13.0 | 10.7 | 1.21× | exp-10 |
| Opus 5 | 31.0 | 36.0 | **0.86×** | exp-46 |
| **Opus 4.7** | **10.3** | 17.2 | **0.60×** | **exp-6** |
| **Opus 4.8** | **9.3** | 17.3 | **0.54×** | **exp-6** |

Three of five replicate within ~15%. **The two that do not are both from exp-6**, the oldest source —
so this is not general noise but something specific to that experiment's harness era. Corrected, the
finding is sharper than the original: **Opus 4.7, 4.8 and Fable 5 all sit around 9–13 turns; Opus 5
alone takes ~2.7×.** The "gradual climb across versions" was exp-6's inflated middle.

**Headline 3 — effort and version interact; Opus 5 amplifies the knob.** low → max multiplies turns by
1.9× (4.7), 1.5× (4.8) and 1.7× (Fable 5) — but **2.8× for Opus 5** (15.7 → 43.7), and its cost goes
**\$0.75 → \$6.75, a 9× swing**, with wall-clock 114 s → 1110 s. The most expensive model is also the
one most sensitive to the most expensive setting.

**A retraction this experiment forced on itself.** The preliminary smoke cell that motivated the whole
run measured Opus 4.8 × max at **33 turns / 1.62 M tokens**, which was published as "thinking level
alone reproduces most of the cross-version turn gap." In-batch the same cell came in at **14, 18 and 14
turns (mean 15.3)**. The claim was wrong and is retracted in all four documents that carried it. Note
the smoke cell was run *concurrently with exp-48* — a violation of the one-experiment-at-a-time rule —
and its 33 sits far outside the in-batch range, which is suggestive but not proof of contamination.

**A harness bug this experiment exposed.** `retort aggregate` promoted a **hardcoded** list of factors
into `master.db`, so all 63 runs aggregated with `effort` **silently dropped** — recorded in the
experiment's own `retort.db`, absent from `master.db`, no error raised. Every cross-experiment analysis
of the new factor would have been impossible, and nothing would have said so. Fixed: `FACTORS` now
includes `effort`/`agent`/`stack`, and `unknown_factors()` reports any factor key present in the data
with no column, which `aggregate` prints as a warning. Three regression tests.

**The local half (6 runs) — and the local stacks finally get onto the turn axis.** Historical Hermes
runs recorded no turn count at all, so [versions-blog](../versions-blog.md) could only compare local to
cloud by *profile shape* (tokens and seconds). Measured directly:

| stack | n | turns | tokens | seconds | coverage |
|---|---:|---:|---:|---:|---:|
| Qwen3.6-35B (local) | 3 | **12.0** (10, 8, 18) | 288 K | 183 | 0.98 |
| Qwen3-Coder-Next 80B (local) | 3 | **24.7** (44, 17, 13) | 595 K | 205 | 0.95 |

Against the cloud arms at default effort the whole board orders as: **Opus 4.8 9.3 < Opus 4.7 10.3 <
35B 12.0 < Fable 5 13.0 < 80B 24.7 < Opus 5 31.0.** Two readings:

- **A 35B open-weights model on a laptop takes the same ~12 turns as the cloud frontier.** The
  "three generations flat at ~10 turns" cluster is not a Claude phenomenon; it spans vendors and a 20×
  size difference.
- **versions-blog's inference holds.** It claimed the 80B "mirrors Opus 5's profile" from tokens and
  seconds alone, before turns were recorded. On the turn axis: 24.7 vs 31.0 — close, and both far above
  everything else. The inference was sound.

Note the 80B's **variance is large** (44, 17, 13 — a 3.4× spread), much larger than the 35B's or any
cloud arm's. n=3 is thin for a stack that noisy, and a single 80B run is close to meaningless.

**Two harness faults surfaced in the local half, both caught by guards rather than published:**

1. **The 30-turn cap** (fixed before this half ran — see the commit). One of the three 80B runs took
   **44 turns**, so the old cap would have truncated it *on the routine task*. This is direct evidence
   that the cap was binding on real work, not merely arithmetically possible.
2. **oMLX 0.5.0rc1's memory enforcer refused to load the 80B.** Its `balanced` tier ceiling (~42.7 GB)
   is *below the model's own size* (43.85 GB), and the projection including a 262144-token KV cache is
   ~51.6 GB. All three m80 cells wrote nothing and failed in 8–10 s; the **no-write guard aborted the
   run** rather than recording false zeros, and the instant-failure-for-$0 signature matched the
   documented tell exactly. Fixed with an explicit `--memory-guard-gb 54` (under the kernel's ~56 GB
   Metal wired cap). **exp-38/39 ran this same model under plain `balanced`, which cannot have passed
   this enforcer — so it arrived or tightened in 0.5.0rc1, making the serving-layer *version* an
   uncontrolled stack variable in a project premised on the stack mattering.**

*Caveats:* one run (fast-mode rep3) persisted partial telemetry, so the **fast-mode control is n=2**.
All results are one language (Python) on the routine task — thinking level may well earn its cost on
harder work, which this experiment does not test. That is the obvious follow-up. The local arms carry
no `effort` factor (it is a Claude CLI flag with no Hermes equivalent), so they sit at their own
defaults and are comparable to the cloud arms' `default` column only.

### exp-48 — Fable 5 fills its gaps, and Opus 5's headline does not survive it

exp-46 crowned Opus 5 "the only model that clears the hard task in every language." That comparison was
**not like-for-like**: Fable 5 had only ever run 4 of the 13 languages (clojure/go/python/rust) on each
task, so its silence on the other 9 was mistaken for absence of capability. This experiment filled the
gap — `Fable 5 × the 9 missing languages × {bookshop, brazil-bench}` = 18 cells, n=1, prompt=neutral,
spec-gate ON, with the **120-minute wall** exp-46 learned it needed.

**Result: 18/18. Fable 5 cleared every gap language on BOTH tasks.** On the hard task it now stands at
**13/13 — exactly matching Opus 5's coverage.**

| brazil-bench, all 13 languages | n | pass | mean cost | mean time |
|---|---:|---:|---:|---:|
| **Claude Fable 5** | 21 | **1.00** | **\$10.47** | **18.2 min** |
| Claude Opus 5 | 13 | 1.00 | \$21.67 | 43.8 min |
| Claude Sonnet 5 | 15 | 0.93 | \$7.64 | 20.9 min |
| Claude Opus 4.8 | 42 | 0.57 | \$3.16 | 9.9 min |

Restricted to the **same 9 gap languages**, so the mixes are identical: Fable 5 \$12.47 / 19.3 min /
61.9 turns against Opus 5 \$25.70 / 52 min — **2.1× cheaper and 2.7× faster for an identical 1.00.**

**Languages only Opus 5 clears: NONE.**

**What this overturns.** exp-46's recommendation was "Opus 5 where nothing cheaper is proven," resting
on breadth no other model had. That justification is gone: Fable 5 is proven everywhere Opus 5 is, at
half the price and less than half the wall-clock. Opus 5's remaining distinction on this evidence is
that it is the most expensive way to obtain a result Fable 5 also obtains. **The hard-task routing
table, which selected Opus 5 for c/clojure/cpp/elixir/erlang, now selects Fable 5.**

**Method note — the failure mode this experiment was designed against.** The original comparison was not
wrong because a number was miscomputed; it was wrong because **an unrun cell reads exactly like a cell
that can't be run.** Fable 5's 4-language footprint made Opus 5 look uniquely broad, when the truth was
that nobody had asked Fable 5 the question. That is a systematic hazard for a project that adds models
incrementally, and the mitigation is the one applied here: when a headline claims uniqueness, fill the
comparison set before publishing it rather than after. The per-language matrix in optimal-blog exists
for this reason — an all-language average silently compares different language mixes.

*(Caveats kept honest: n=1 per cell, so these are coverage results, not reliability estimates — a 1.00
at n=1 is much weaker than Opus 4.8's 0.57 at n=42, and exp-47 is this repo's worked example of an n=3
result that did not survive n=5. What exp-48 establishes is that **Fable 5 can do these languages**, not
that it does them every time.)*

### exp-47 — gpt-oss-20b (OpenAI open weights): fast, uneven, not a replacement

First run of the **gpt-oss-20b** candidate (MXFP4 4-bit, ~12 GB) after its gate-probe passed —
**oMLX parses its Harmony tool calls into proper OpenAI `tool_calls`**, so unlike Laguna (arch wall)
and Devstral (unparseable Mistral format) it is fully servable AND drivable by Hermes. A lineage
probe: is a non-Qwen local model competitive? `language{python, go, typescript} × n=3` on bookshop,
ctx 131072 @ threshold 0.9, sampling matched to the 35B/80B baselines.

**Result (post-`recover`, extended to n=5) — compared with the local incumbents at their featured
config (80B = exp-38, ctx 0.9):**

| language | gpt-oss-20b (12 GB), n=5 | Qwen 80B (42 GB, n=3) | Qwen 35B (n=3) |
|---|---|---|---|
| **go** | **0.80** (4/5) — mean **102 s** | 1.00 — 345 s | 1.00 — 259 s |
| **typescript** | 0.60 (3/5) — 147 s | 1.00 — 1026 s | **0.00** (fails) |
| **python** | **0.40** (2/5) — 245 s | 1.00 — 440 s | 1.00 — 126 s |

**Headline: genuinely fast, but not reliable anywhere — it does not displace the 80B.** It is **3–7×
quicker** than the flagship from a quarter the memory, and it **beats the 35B on TypeScript** (0.60 vs
0.00), a language the 35B cannot do at all. But it is **perfect at nothing**, and Python at 0.40 is
disqualifying for a default. The right description is *fast and uneven*, not *fast and Go-solid*.

**Method note — replicates killed the headline twice.** This experiment is the clearest case yet for
n≥5:

| language | after n=1 | after n=3 | **final, n=5** |
|---|---|---|---|
| go | 1.00 | 1.00 | **0.80** |
| typescript | 1.00 | 0.67 | **0.60** |
| python | 1.00 | 0.33 | **0.40** |

The first replicate swept **3/3 at req-coverage 1.0** — "a 20B matches the 80B." n=3 demolished that
for python and typescript. And **n=5 then demolished the surviving claim**: Go held 1.00 through three
replicates and was about to be published as "matches the flagship at 3.6× the speed," which is exactly
the sentence the fourth and fifth replicates falsified. A single extra replicate was the difference
between a headline capability claim and a 0.80.

**The three all-zero failures are GENUINE — verified by reproduction, not assumed.** All-zeros on local
runs is this project's signature false-failure (four published conclusions have been harness artifacts),
so `rescore` was run first — it recovered 2 of 5 failures, and the remaining 3 were then reproduced by
hand rather than trusted:
- **typescript rep3** — `tsc` errors: duplicate identifier `db`, and `db` never exported from `./db`.
- **typescript rep5** — the model appended a *second copy* of the app into `index.ts`: two
  `export default app`, plus a call to an undefined `initDb`. Its agent log ends
  `⚠️ No reply: the model returned empty content after retries`.
- **python rep2** — the model wrote a local `httpx/` package to shim `AsyncClient(app=...)`. The shim
  imports *itself* (its `sys.path` juggling cannot work — it is already in `sys.modules`), so
  collection dies with `module 'httpx' has no attribute 'AsyncClient'`. A self-inflicted import cycle.

All three left real source trees and `"succeeded": true` metadata, which is precisely why they needed
checking; the zeros are the model's, not the harness's.

**Verdict:** keep the 80B as the featured local stack. gpt-oss-20b's value is **speed and lineage
evidence** (the OpenAI open-weights family is servable and drivable locally via Harmony tool-call
parsing) rather than any language it can be trusted with. The n≥5 follow-up that was queued here has now
run — this *is* it — and it removed the Go claim rather than confirming it.

### exp-46 — Claude Opus 5: 26/26 across every language and both tasks — at 3–7x the price

Added the new frontier model across **every supported language on both tasks** (n=1):
`language{python, go, typescript, rust, clojure, java, csharp, elixir, erlang, c, cpp, objc, swift}
× {bookshop, brazil-bench}` = 26 cells, prompt=neutral, spec-gate ON. **Model id verified three ways
before spending** — a bogus id 404s (so the CLI validates), `claude-opus-5` self-reports its id and
bills, and the live agent argv carried `--model claude-opus-5` while `provenance.json` recorded it.

**bookshop (routine): 13/13 — a clean sweep**, including java, where Opus 4.8 manages only 0.83.

**brazil-bench (hard). 13/13 at req-coverage 1.0** — and after the harness fixes below, no regressions:

> ### ⚠️ CORRECTION 3 — the "first/only model to clear the hard task everywhere" headline is WITHDRAWN.
>
> This entry originally read *"Opus 5 is the first model to clear the hard task in every language
> tried"*, and the recommendation "Opus 5 only where nothing cheaper is proven" was built on it.
> **[exp-48](#exp-48--fable-5-fills-its-gaps-and-opus-5s-headline-does-not-survive-it) falsified it.**
> Fable 5 had simply never been *run* on 9 of the 13 languages; when it was, it cleared **all 9**,
> reaching **13/13 on brazil at \$10.47 / 18.2 min against Opus 5's \$21.67 / 43.8 min.** Languages
> only Opus 5 clears: **none**.
>
> The error was not arithmetic — it was treating an **unrun cell as an unpassable one**. Opus 5's
> uniqueness was an artifact of who had been asked. Everything below about Opus 5's *own* results
> stands (26/26 is real); what does not stand is the claim that the coverage was exclusive, or the
> price premium that claim justified.

| brazil language | Opus 4.8 | **Opus 5** | |
|---|---|---|---|
| **rust** | 0.33 | **1.0** | ← beats 4.8 |
| **java** | 0.33 | **1.0** | ← beats 4.8 |
| **clojure** | 0.45 | **1.0** | ← beats 4.8 |
| go, typescript | 1.00 | 1.0 | matches |
| csharp, elixir, erlang, c, cpp, objc | *never run* | **1.0** | new ground |
| **python** | 1.00 | **1.0** *(was a harness false-failure — see Correction 2)* | matches |

**⚠️ CORRECTION 2 — brazil/python was a HARNESS false-failure, not a regression.** Digging into the
one apparent Opus 5 loss found the opposite of a model problem: the agent produced a complete MCP
server and **all 239 of its tests pass**. The scorer reported `test_coverage=0` because the project's
`pyproject.toml` sets `addopts = "-q"`, which combines with the scorer's own `-q` to make pytest
**doubly quiet** — it prints progress dots and *no* `N passed` summary line, so the pass-rate parser
found nothing and the mechanical gate failed a green suite. (`retort diagnose` compounded this by
labelling it GENUINE: it re-runs against the *archived* tree, where the same parse fails.) **Fix:** the
plain-test fallback now uses the **exit code** as the universal signal — the same principle already
applied to the C/C++/ObjC and Swift paths — since pytest exits 5 on "no tests collected", so rc==0
genuinely means tests ran and passed. Rescored: **python → test_coverage 1.00, brazil is 12/12**.
This bug would silently zero ANY Python project that configures quiet pytest output.

**⚠️ CORRECTION (added after comparing against Fable 5).** The first version of this entry called
Opus 5 "the first model to clear the hard task broadly." That over-claimed. **On the 4 brazil languages
all three models have actually run (clojure/go/python/rust), Fable 5 beats Opus 5 on every axis:**

| brazil, like-for-like (4 langs) | n | pass | \$/run | min/run | **\$/solved** |
|---|---|---|---|---|---|
| **Fable 5** | 12 | **1.00** | 8.98 | 17.3 | **8.98** |
| Opus 4.8 | 31 | 0.61 | **3.21** | **10.0** | 5.24 |
| Opus 5 | 4 | 0.75 | 13.59 | 25.5 | 18.12 |

Fable 5 is 4/4 where Opus 5 is 3/4, at **half the cost per solved task and 1.5× faster** — and it passes
brazil/python, which Opus 5 genuinely fails. On the ROUTINE task the gap is wider still: Fable 5 1.00 at
**\$1.05 / 2.4 min** vs Opus 5's **\$3.15 / 10.1 min**. **Opus 5's real claim is BREADTH, not
superiority:** it is the only model with brazil data for csharp, elixir, erlang, c, cpp and objc (six
languages, all 1.00) — but those are *untested* for Fable 5 and 4.8, not beaten. **Recommendation:
Fable 5 for routine and hard work in the languages it covers; 4.8 when cost dominates; Opus 5 only where
nothing else has been proven.** Obvious follow-up: **run Fable 5 on the other 9 brazil languages** to
make the comparison fair.

**Interpretation — a trade, not domination.** The hard task has been the standing ceiling: best local
0/6, and 4.8 reliable in only 3 of the 6 languages it had run. Opus 5 clears **eleven**, including all
three 4.8-blockers and six languages no model had ever attempted on brazil. But it **genuinely fails
brazil/python**, which 4.8 passes — diagnosed GENUINE ("tests do not run / do not pass on the archived
code"), not a tooling artifact. A single averaged score would have hidden both halves of that.

**The cost/time bill is real, and it is the other half of the result.** On the routine task Opus 5 is
**2.5–6× more expensive and 3–5× slower than 4.8 for the identical 1.00 outcome** (cpp \$6.72 vs \$1.08;
c \$5.43 vs \$1.28; python \$1.84 vs \$0.50). bookshop cost ~\$40 / 2.2 h wall; brazil ~\$234 / 8.8 h wall
(mean 47 min/cell). **So: keep 4.8 (or cheaper) for routine work — Opus 5 buys nothing there but a
bigger bill. Reach for Opus 5 when the task is hard**, which is exactly where it converts failures into
passes.

**Two config artifacts caught before they became false findings** (the recurring lesson):
1. **erlang and c "crashed"** — both were `Timeout after 3603s`, i.e. the **60-min hard wall**, not
   failure. Opus 5 is 3–5× slower, and brazil cells average 47 min. Raised the wall to **120 min** and
   both then **passed at 1.0** (erlang needed 53 min, c 53 min). Publishing the raw run would have
   claimed two capability failures that don't exist. (The exp-26 lesson — *the wall was masking
   capability* — recurring one tier up.)
2. **A "usage limit until 3pm" that wasn't.** The run exhausted quota at ~02:00 and the driver parked
   until the 15:00 daily reset — but a probe at 02:50 showed the quota already back (it was a short
   rolling window). Retry cadence changed to every 20 min, recovering **~12 idle hours**.

Also fixed here: `stall_minutes` was missing from the brazil workspace (a wedged cell would have burned
the full wall ×12), and bookshop's clojure "failure" was a scorer TOOLING false-zero that rescored to
1.00/0.97 — which is why bookshop is 13/13, not 12/13.

**FINAL (all 26 cells, post-recover/reevaluate): bookshop 13/13, brazil 13/13 — a perfect sweep.**
Cost/speed per solved cell: bookshop \$2.91 / 10.1 min, brazil \$20.00 / 43.8 min.

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
