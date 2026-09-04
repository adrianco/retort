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

### exp-55 — Terra vs Opus 5 at matched thinking levels: 4× to 40× for the same result

The first **cross-vendor, matched-effort** comparison. GPT-5.6's tiers price onto the Claude ladder
(Luna↔Sonnet, **Terra↔Opus**, Sol↔Fable), and Opus is the optimal Claude pick in most cells, so Terra
is its price-peer. `{gpt-5.6-terra, claude-opus-5} × {low, medium, high, xhigh, max} × {python, go} ×
n=2` on bookshop = 40 runs, judged by opus-4.8. **40/40 completed, every cell 1.00.**

| effort | Terra | Opus 5 | ratio | Terra time | Opus 5 time |
|---|---:|---:|---:|---:|---:|
| low | \$0.19 | \$0.81 | 4.3× | 112 s | 136 s |
| medium | \$0.15 | \$1.15 | 7.5× | 105 s | 222 s |
| high | \$0.18 | \$1.84 | 10.4× | 132 s | 401 s |
| xhigh | \$0.22 | \$4.63 | 20.7× | 169 s | 909 s |
| **max** | **\$0.35** | **\$14.21** | **40.1×** | 254 s | 1669 s |

**Terra's most expensive setting is still half the price of Opus 5's cheapest** (\$0.35 vs \$0.81),
and 40× cheaper at matched `max` — for an identical, independently-verified 1.00. Total experiment
cost: \$80.67, of which Opus 5 at `max` alone is a third.

**The mechanism is in the step counts, and it is the real finding.** Terra's agent steps stay
**flat across the entire dial — 10 to 19** regardless of setting. Opus 5's **explode: 15 → 23 → 22 →
43 → 140 turns.**

So the dial does structurally different things in the two systems. On Opus 5 it buys **more agentic
iteration**, which triggers the n²-ish cache-read growth documented in
[versions-blog](../versions-blog.md) — hence \$14.21 and 28 minutes for a CRUD API. On Terra it
appears to buy **deeper reasoning inside a roughly constant number of steps**, so cost rises ~2×
rather than ~18×. That is why the ratio *widens* with effort instead of holding at the ~2.4× the
per-token rates alone imply: roughly half the gap is pricing, half is token volume driven by turns.

**Why effort had to be set explicitly.** `default` is not a shared operating point — Claude's sits
near `high`, Terra's is `medium`, Sol's is `low`. Comparing defaults would have compared two vendors'
product decisions rather than two models, and would have shown a muddled ~9× instead of the clean
4×→40× interaction.

**Two plumbing bugs were fixed first, either of which would have invalidated the sweep:** `xhigh` was
missing from retort's effort levels (so exp-49's "five-level" sweep had actually skipped a real
level), and **codex ignored the effort factor entirely** — it has no `--effort` flag, the level is a
config key, so every codex cell would have run at the model's default while the design claimed to
sweep it. Now `-c model_reasoning_effort=<level>`, verified live because the API *rejects* an invalid
value.

*Caveats:* n=2 per cell (n=4 pooled across languages), bookshop only. Go's Opus 5 `max` came in
*below* its `xhigh` — non-monotonic, and a reminder that single cells are soft. Terra's cost rests on
a **92% cache-hit rate**; without the cached-input discount it would be ~3.3× higher, and that hit
rate is partly an artifact of retort running many cells behind an identical prompt prefix. Codex
reports no per-request context, so peak-context is blank for those cells — see the notes in
`_parse_codex_usage`.

### exp-56 — Terra clears every remaining language, both tasks, for \$7.44

The gap-fill for exp-55: `gpt-5.6-terra` via codex at **default effort** (its own default, medium),
1 replicate, across the nine languages Terra had never been run on, on **both** tasks. Judge held at
opus-4.8.

**18/18 at `requirement_coverage` 1.00 as originally run. Total spend: \$7.44.**

**Corrected 2026-08-17 (M1 review).** That 18/18 was accurate for the design as run, which
DELIBERATELY excluded swift and objc — `xcode-select` pointed at CommandLineTools, so either would
have scored a harness false zero. After the Xcode fix those four arms were added via `--resume`, and
the experiment now stands at **21 of 22**:

| | result |
|---|---|
| bookshop | 11/11 |
| brazil | 10/11 — **objc fails the MECHANICAL gate** (`tests did not run, test_coverage=0`) |

The headline "clears every remaining language, both tasks" is therefore true of bookshop and of ten
of eleven brazil languages, not of all of them. **The objc failure is not a Terra capability wall
and should not be read as one:** exp-46 scored objc 1.00 on this same task with Opus 5, so the
language and its scorer both work here. It is an unexplained mechanical-gate failure in this cell
and wants `retort diagnose`, not a conclusion.

| language | bookshop | brazil |
|---|---:|---:|
| typescript | 1.00 · \$0.22 | 1.00 · \$0.15 * |
| rust | 1.00 · \$0.14 | 1.00 · \$0.37 |
| java | 1.00 · \$0.38 | 1.00 · \$0.49 |
| clojure | 1.00 · \$0.33 | 1.00 · \$0.57 |
| erlang | 1.00 · \$0.34 | 1.00 · \$0.49 |
| elixir | 1.00 · \$0.42 | 1.00 · \$0.67 |
| csharp | 1.00 · \$0.26 | 1.00 · \$1.36 |
| c | 1.00 · \$0.26 | 1.00 · \$0.40 |
| cpp | 1.00 · \$0.26 | 1.00 · \$0.33 |

\* typescript/brazil passed on the **self-repair second chance** — the first attempt scored 0.9167
(11 of 12 requirements) and the repair closed it. Every other cell passed first time.

Put beside exp-46, where Opus 5 also went 13/13 on both tasks: Opus 5 spent **\$2.55–\$39.05 per
brazil cell**; Terra's dearest here is **\$1.36**. Clojure, C#, Elixir and Erlang — the languages
that wall the local 80B at 0.00 — are cleared for well under a dollar apiece.

**Effort was deliberately not swept.** exp-55 measured the dial as near-inert on Terra (\$0.12–\$0.29
across all five levels, every cell 1.00), so a 9 × 5 sweep would have re-measured a known flat
factor. `default` is what a user actually gets.

**Two scorer bugs surfaced, and both were false zeros on green code** — the pattern this project
keeps paying for. Neither was a model failure:

1. **typescript/bookshop scored 0.00 on every response.** The agent used Node's *built-in* runner
   with zero dependencies. The `node --test` branch matched and the tests ran; only the summary went
   unread, because the pattern accepted TAP's `# pass 7` while Node 26 emits its default spec
   reporter's `ℹ pass 3`. Verified by hand: 3/3 pass, exit 0. Pattern now takes both markers.
2. **csharp/brazil scored 0.00.** The agent shipped `App.csproj` + `App.Tests.csproj` at the root
   with no `.sln`, so a bare `dotnet test` exits on **MSB1011** ("more than one project or solution
   file") *before running anything*. The scorer already had an explicit-test-project path but only
   used it when the root held **no** project — an ambiguous root fails exactly like an empty one.
   Verified by hand: 5/5 pass. Both cells rescored and re-judged (ReqCov 1.0), with regression tests.

**swift and objc were excluded, and that was a harness call, not a result.** Full Xcode is installed
but `xcode-select` points at CommandLineTools, so `xcodebuild` errors and a minimal SwiftPM package
fails with "no such module 'XCTest'" (reproduced before launch). Either would have scored a false
zero indistinguishable from a capability wall. They need
`sudo xcode-select -s /Applications/Xcode.app/Contents/Developer` and then 4 runs via `--resume`.

*Caveats:* n=1 per cell. The two recovered cells were re-judged with `--eval-model opus-4.8`
explicitly — `retort reevaluate` otherwise falls back to the CLI's default judge, which would have
graded them under a different model than the other 16.

### exp-57 — the first correctness gate, and 3 perfect checklists that are wrong

**gpt-5.6-luna × brazil × {python, go} × n=3**, judge opus-4.8, **\$1.01 / 17 min**. The first
experiment to run the new `factual_accuracy` gate, which starts the finished server and checks two
externally-verifiable facts about the 2019 Série A (Flamengo 28W-6D-4L, all 20 clubs) — both stated
in the task's own worked example.

**2 of 6 pass. Five of six scored `requirement_coverage` 1.00, and three of those ship a
demonstrably wrong 2019 table** — clean passes under the old gates.

| lang | rep | req_cov | factual | defect |
|---|---|---|---|---|
| python | 2 | 1.00 | 1.00 | — |
| go | 2 | 1.00 | 1.00 | — |
| go | 1 | 1.00 | 0.50 | **76 played, 180 points** — exactly double 38/90: the five overlapping match files concatenated without dedup |
| python | 1,3 | 1.00 | 0.50 | `Athletico Paranaense` 27 + `Atletico Paranaense` 11 = 38 — one club split across two spellings, giving a 21-club division |
| go | 3 | 0.92 | 0.00 | 223-row "standings"; Athletico Paranaense split FOUR ways (`Atletico Paranaense` 46, `Atletico-PR` 38, `Athletico Paranaense - PR` 8, `Athletico` 8); no competition filter, so it cannot produce the spec's own worked example |

Every one of these implements the checklist, returns a table, and satisfies the accounting identity
`matches == wins+draws+losses` — within each fragment. That is exactly why the pinned checklist
cannot see it: it asks whether a capability exists, never whether its numbers are right.

**The dominant defect is name normalisation, not deduplication.** §0 predicted double-counting from
one run's log; only one cell shows it. Three show a club's season split across spellings the loader
never canonicalised — the hazard the task text explicitly warns about (`São Paulo-SP` vs
`Sao Paulo`). One run wrote a perfectly good normaliser and then keyed its standings map on the raw
string.

**Harness cost of getting here: 6 bugs, every one of which failed CORRECT work.** Four in the
scorer's own parsing (literal "38" lookup reading the points column; counting table-shaped lines and
catching a relegation-summary line as a 21st club; one name token per club; single-line JSON output
collapsing to one row), and two outside it — `go build -o X .` emitting a package ARCHIVE at mode
0644 for the idiomatic `cmd/<name>/main.go` layout while exiting 0, and a tool schema declaring
`required: ["season"]` with no `properties` block, so the probe never asked for 2019 and was
answered with all-time standings. The uncorrected run recorded 0/6; the truth is 2/6.

**Two gate-plumbing bugs found the same day, both of which silently un-did the gate:**
`factual_failed` drove `run_ok` — the console verdict and the `rep<N>-failed` archive name — but was
omitted from the argument that sets the stored DB status, so a failing run was recorded `completed`
and every downstream consumer saw a pass. And `retort rescore` reclassified on `test_coverage`
alone, flipping all six runs back to `completed RECOVERED`. A recovery path that resurrects runs a
gate rejected is worse than no recovery path.

**Standing caveat:** pass/fail now answers a different question than it did for the 284 pre-gate
brazil runs. `REQUIREMENTS.json` is untouched, so `requirement_coverage` still pools; any write-up
that pools *pass-proportions* across that boundary must say so.


### exp-58 — GPT-5.6 Sol, and the gap the checklist hides

**`gpt-5.6-sol` × brazil × {python, go, rust, typescript} × n=3**, its own default effort,
judge opus-4.8, **\$27.97 / ~75 min**. Sol is the new frontier Codex model
(`models_cache.json`, 2026-08-12: *"Latest frontier agentic coding model"*); master.db had only
terra and luna.

**10 of 12 pass with facts checked. 11 of 12 pass the checklist alone.** Head-to-head on the hard
task, same gate, same judge:

| model | n | checklist only | with facts |
|---|---:|---:|---:|
| gpt-5.6-luna | 6 | 0.83 | **0.33** |
| gpt-5.6-sol | 12 | 0.92 | **0.83** |

**The checklist barely separates these models; correctness separates them 2.5x.** That is the
clearest evidence yet for §0's premise — `requirement_coverage` measures whether a capability exists,
and on a task where the data is messy, existence and correctness diverge sharply for the weaker
model.

**Sol's two genuine failures are both worth naming:**
- **python rep3** declares `mcp>=1.28,<3` and uses `@server.list_tools()`, which exists in mcp 1.x
  and was **removed in 2.0**. Its own manifest specifies a version its own code cannot run against:
  install it as shipped and it crashes on start-up. Verified directly — `Server.list_tools` is
  present in 1.29.0, absent in 2.0.0.
- **typescript rep1** reports Flamengo at 55 played / 37 wins and splits Athletico across four rows.
  It also missed the checklist (0.92), so it was the one cell the old gate would have caught anyway.

**Cost and speed, versus terra:** sol runs **\$2.33/cell and 7.7 min median** against terra's
\$0.77 and 457 s on the same task — roughly 3x the price for +0.05 checklist reliability. Seven of
twelve cells needed the self-repair second chance (`ok*`, half credit).

**Two settings recorded because they are NOT comparable across models:** sol's own default reasoning
level is **`low`**, terra's is `medium` — "default effort" is not one setting. And a **new effort
level `ultra`** exists above `max` on sol/terra/luna, which exp-55's sweep never saw. Both queued.

**Harness cost: 2 more parser fixes, both failing CORRECT work** — a structured row whose JSON keys
are alphabetical (so the consecutive-`[28,6,4]` check missed a perfect answer), and a response that
puts a text preamble before pretty-printed JSON (parsing neither as JSON nor line-wise). The
uncorrected run recorded 8/12; the truth is 10/12. That makes **eight distinct output shapes** this
scorer has had to learn across two experiments — the format diversity across implementations of one
specification is itself a finding.


### exp-59 — `ultra`: 9.7x the cost, 8x the time, and nothing to show for it

**`gpt-5.6-terra` @ `ultra` × brazil × {python, go} × n=3**, judge opus-4.8, **\$22.80 / ~3.1 h**.
A sixth reasoning level exists on Sol/Terra/Luna above `max`. exp-49 and exp-55 both swept low..max
and stopped — not by choice: the codex launch path accepted `ultra` through an ad-hoc exception while
the only named list ended at `max`. **A gap nothing names is a gap nobody sees.**

**6 of 6 pass, on both the checklist and the factual gate.** So does every level below it. The
completed sweep, terra on brazil, python and go:

| effort | n | checklist | avg cost | avg minutes |
|---|---:|---:|---:|---:|
| low | 2 | 1.00 | \$0.39 | 3.9 |
| medium | 2 | 1.00 | \$0.39 | 4.0 |
| high | 2 | 1.00 | \$0.50 | 5.8 |
| xhigh | 2 | 1.00 | \$1.25 | 13.2 |
| max | 2 | 1.00 | \$2.77 | 25.0 |
| **ultra** | 6 | **1.00** | **\$3.80** | **31.1** |

**Reliability is flat across the entire dial while cost rises 9.7x and wall-clock 8x.** One `ultra`
cell took **50.6 minutes** and \$7.52 to reach the same 1.00 that `low` reached in 3.9 minutes for
\$0.39. This is exp-49's "4x cost lever that buys nothing on routine work" extended to the hard task
and to a tier the vendor added after that conclusion was drawn.

**Two of six `ultra` cells still needed the self-repair second chance** (half credit), which `low`
and `medium` did not — so the extra reasoning did not even buy first-attempt reliability.

**`ultra` is the only level in this table whose answers were checked.** exp-55's cells predate the
factual gate, so their `factual_accuracy` is NULL and they pass it by construction. The honest
comparison is on `requirement_coverage`, which pools cleanly and is what the table reports;
`ultra`'s own factual score is 1.00 on all 6. What is NOT established is whether the lower levels
would also answer correctly — that is a re-run, not an inference, and the flat checklist result makes
it a low-priority one.

**Caveat on n.** The low..max rows are n=2 each (exp-55, python+go, one replicate per language);
`ultra` is n=6. A flat line across six levels is still the cleanest reading, but the lower rows are
thin and a single failure would move them a lot.

**Harness fix that came with it:** `ultra` is now a named level —
`CODEX_ONLY_EFFORT_LEVELS = ("ultra",)`, with `CODEX_EFFORT_LEVELS` composing it — instead of an
`and effort != "ultra"` exception buried in the launch path. `CROSS_VENDOR_EFFORT_LEVELS` still
excludes it: Claude has no counterpart, so it is not a like-for-like operating point.


### exp-55b — the same sweep on the HARD task: 28× the cost, and the gap the pass metric hides

The brazil half of exp-55: `{gpt-5.6-terra, claude-opus-5} × {low, medium, high, xhigh, max} ×
{python, go} × n=1` = 20 runs, judge held at opus-4.8. **20/20 completed, every cell 1.00** — so on
the 12-capability MCP task, at every thinking level, in both languages, both models fully implement
the spec.

| | Terra | Opus 5 | ratio |
|---|---:|---:|---:|
| total cost, 10 cells | **\$10.58** | **\$296.08** | **28×** |
| total wall clock | 1.7 h | 7.6 h | 4.5× |
| cheapest passing cell | \$0.31 (python, high) | \$7.03 (go, low) | 23× |
| dearest passing cell | \$3.36 (go, max) | **\$85.45** (go, max) | 25× |

That \$85.45 / 98-minute run is **the most expensive single run this project has recorded**, and the
`low` cell of the same stack passed the identical checklist in 16 minutes for \$7.03.

**The finding that matters is what `requirement_coverage` cannot see.** All 20 cells are 1.00, but
the mechanical scorers are not equal:

| | `test_coverage` | range |
|---|---:|---|
| Opus 5, python | **0.98** | 0.95–1.00 |
| Terra, python | 0.82 | 0.69–0.88 |
| Opus 5, go | **0.88** | 0.86–0.90 |
| Terra, go | 0.56 | **0.27**–0.66 |

Opus ships materially better-tested code on the hard task — on Go it is 0.88 against Terra's 0.56,
with one Terra cell at **0.27**. So "Terra matches Opus at 1/28th the cost" is true *of spec
conformance* and false of test depth. The pinned checklist asks whether each capability exists, and
a thinly-tested implementation answers yes. Anyone reading the cost ratio as "same result" is reading
one column of four. (`code_quality` and `maintainability` are near-identical between them, so the
gap is specifically in testing, not in the code.)

**Effort still buys nothing on the pass metric here** — 1.00 at `low` and 1.00 at `max`, for 8× the
money. Behavioural detail of what Opus does with the extra time is in
[levels-blog](../levels-blog.md); briefly, the hard task is revision-heavy at *every* level
(Edit:Write > 0.9 even at `low`), unlike the routine task where writing dominates until `max`.

*Caveats:* n=1 per cell — these are single observations, and this project has reversed n=1 results
before. **One cell has no cost at all:** Opus 5 / go / `medium` completed and scored 1.00, but its
agent log was never written, so `_cost_usd` is NULL and tokens read 0 — the \$296.08 is a **lower
bound**, and the missing telemetry is filed as a harness bug (a completed run with no usage data
should fail loudly, because a missing cost and a free run are indistinguishable downstream). The
first resume attempt also crashed 3 cells in <1 s on `Not logged in` after the credential store was
blanked; those rows were re-run, not recorded.

### exp-53 — Codex joins the board, and is an order of magnitude cheaper

The first OpenAI-lineage agent in this corpus. Every cloud result before this was Claude (plus one
Gemini scaffold), so "which stack should I use" had never been answerable outside one vendor.
`codex exec` × `gpt-5.6-luna` × bookshop × {python, go, typescript} × n=3, prompt=neutral, judged by
**opus-4.8** — the same judge as every other experiment here, so the numbers pool.

| language | n | pass | cost | time | tokens |
|---|---:|---:|---:|---:|---:|
| **python** | 3 | **1.00** | **\$0.062** | 145 s | 171 K |
| **go** | 3 | **1.00** | **\$0.084** | 127 s | 245 K |
| typescript | 3 | 0.00 | \$0.116 | 186 s | 408 K |

**On the same python cell: Opus 4.8 \$0.67, Fable 5 \$1.24, Opus 5 \$2.27 — all also 1.00.** Codex
reaches the same verified result for roughly **11× less than Opus 4.8 and 37× less than Opus 5**.
That is the largest cost gap in the corpus, and it is n=3 on one routine task — a starting point, not
a verdict.

**That price only exists because of a fix made the same day.** A ChatGPT subscription reports no
per-run cost, so before `retort.pricing` landed Codex would have recorded **\$0** — and
`per_language_routing` picks the cheapest qualifying stack, so it would have won every recommendation
it qualified for on a number nobody measured. Cost here is list-price-per-token, the same basis
Claude's CLI reports (and does not bill on a Max plan).

**TypeScript 0.00 is a GENUINE failure, and the reasoning matters.** All three runs chose
`better-sqlite3`, which will not build under this machine's Node 26; `npm install` is all-or-nothing,
so `tsx` never installed either and the suite never ran. The tempting reading is "environment
incompatibility, not the model's fault" — **and the transcript refutes it.** The agent ran:

```
npm test                       -> sh: tsx: command not found
npm install                    -> (failed, node-gyp)
npm run build                  -> sh: tsc: command not found
npm install --ignore-scripts …
```

It watched its own suite fail, attempted the same workaround the scorer now uses, and finished
anyway — on a **repair** attempt where it had already been told it failed. An agent executing in the
playpen can inspect the target machine. Choosing a dependency that does not build there and shipping
untested code is a model failure, and the same model passed python and go on the same machine.

*(The scorer now retries `npm install --ignore-scripts` when a full install fails. That is a
diagnostic aid — it turns an opaque zero into "Could not locate the bindings file" — not an excuse
for the run.)*

**Three integration bugs were found first, each only visible by running the real CLI** (see PR #45's
review thread): the telemetry parser was written to an event shape `codex exec --json` does not emit
(returned 0 tokens / 0 turns on real output); `output_tokens` and `input_tokens` were double-counted
against their own subsets (~490 % cost inflation); and Codex's `turn.completed` fires **once per exec
invocation**, not per agent step, so recording it as `num_turns` would have put Codex at the bottom
of the turn axis and made it look radically more efficient than every measured stack. `num_turns` is
deliberately absent for Codex; `codex_items` / `codex_exec_turns` carry the data under honest names.

*Caveats:* n=3, one task, one tier at its default reasoning level. GPT-5.6 ships three tiers
(Sol/Terra/Luna) each with its own effort dial, so this measures one point in a 3 × 5 grid. Also
`gpt-5.x-codex` model ids are **API-key-only** — on a ChatGPT plan they 400; the usable set is in
`~/.codex/models_cache.json`.

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

## exp-60 — does "Terra clears every language" survive the correctness gate?  — DONE 2026-08-17

**Answer: no, but the gate found more harness bugs than model defects.** 11 cells, brazil ×
`gpt-5.6-terra` @ default × every language exp-56 covered, n=1, judge opus-4.8. Final:
**4/11 pass** (c, java, rust, typescript) — against exp-56's headline of "Terra clears every
remaining language". `requirement_coverage` is 1.00 on **five** of the seven failures, which is the
result the experiment existed to produce: the checklist credits a capability that exists in the code
and cannot be reached.

| language | factual | reqcov | verdict |
|---|---:|---:|---|
| c, java, rust, typescript | 1.00 | 1.00 | pass |
| clojure, cpp, objc | 0.50 | 0.83–1.00 | **data defect** — Athletico Paranaense split across two rows |
| erlang, elixir, swift | 0.00 | 0.92–1.00 | **interface defect** — every tool declares an empty `inputSchema` |
| csharp | 0.00 | — | **harness**: transient NuGet outage, needs a re-run |

**Finding 1 — one club decides three of the failures.** clojure, cpp and objc each return 21 rows
with Athletico Paranaense split in two: 27 played / 48 pts under the accented spelling and 11 played
/ 16 pts under the unaccented one. Total matches is exactly 760 (20 clubs × 38) in every case, so
fixture deduplication is *correct* — only club-name reconciliation fails, and only for this one pair.
The same 27/11 split appeared in luna/python back in exp-57, so it is now **four implementations
across two models and four languages**. It is the hardest normalisation case in the corpus and it is
what separates a pass from a fail.

**Finding 2 — three servers are unaskable.** erlang, elixir and swift each declare
`inputSchema: {"type": "object"}` with no properties, from a single shared one-line
`tool(name, description)` helper. The logic underneath is right — erlang scores
`requirement_coverage` 1.00 and answers `head_to_head` in 8.9 ms — but no client is ever told that
`season` is a parameter, so no client can ask for 2019. This is the cleanest instance the project has
produced of *capability present, capability unreachable*. It is also what motivated the two new
response columns (`mcp_conformance`, `mcp_client_facts`).

**Finding 3 — the harness produced three false failures out of eleven cells.** All three were
separable from real defects in minutes rather than re-runs, because `_factual.json` now stores the
server's own answer beside the verdict:

- **rust** scored 0.00 mid-run on a *correct* table: nested `record` object unread, plus the probe's
  competition list lacked the accented `Brasileirão` so it fell back to season-only and got Série A
  and Série B merged. Fixed, rescored to 1.00 (`eff9f0c3`). The run was stopped and restarted for it.
- **c** scored 0.50 on a *correct* table returned as one line of prose; `splitlines()` gave one row,
  so no per-row check could count more than one Atlético. Fixed, rescored to 1.00.
- **swift** scored 0.00 on everything with "swift build failed". Its code compiles clean in 2.91 s —
  the second-chance playpen had been seeded with attempt 1's `.build`, whose ModuleCache hard-codes
  attempt 1's path. `_seed_repair_workspace` was `copytree`-ing every directory from the prior
  attempt with no filter, so **every** self-repair inherited stale build output. Fixed; swift now
  scores `test_coverage` 1.00 and fails only on facts (the same empty-schema defect as erlang).

**Comparability.** Runtime figures are post-hoc, measured serially on a quiet machine during the
final rescore, not inline — `retort rescore` had been re-measuring timing with 4 workers, which swung
one rust cold start from 264 ms to 152 ms; it is now forced to 1 worker whenever runtime is in scope.
csharp and swift should be re-run before their cells are read as capability results.

## exp-61 — does Hermes 0.20.5 change anything?  — DONE 2026-08-22, null result

**No.** Same requirement coverage, same maintainability, duration distributions that overlap almost
exactly. The 0.18.2 numbers keep their shelf life and nothing in the blogs needs an asterisk.

Every local number in the corpus (360 runs, exp-17..exp-50) was produced by Hermes v0.18.2. Upstream
moved to v0.20.5 — 24,167 commits, 161 files and +64,258 lines in the agent core alone, a **new**
`agent/verify/` subsystem, and a rewritten turn loop (`run_agent.py` +3,663, `turn_context.py` +990,
`turn_summary.py` new). The hypothesis was that a rewrite that large moves turn count and duration
before it moves coverage. It moves neither.

Only the 0.20.5 arm ran; the 0.18.2 rows are exp-49's, as designed. Agent level `hermes-0205`.

| stack | version | n | mean | **range** | turns | tokens |
| --- | --- | --- | --- | --- | --- | --- |
| m35 | 0.18.2 | 3 | 183 s | **99–343 s** | 12.0 | 288 K |
| m35 | 0.20.5 | 3 | 203 s | **101–356 s** | 15.7 | 553 K |
| m80 | 0.18.2 | 3 | 205 s | **137–284 s** | 24.7 | 595 K |
| m80 | 0.20.5 | 3 | 224 s | **137–300 s** | 16.7 | 491 K |

`requirement_coverage` is **1.00 on all six runs**, matching baseline exactly. Maintainability 1.00
(m35) and 0.98 (m80), also matching.

**Why this is a null and not a slowdown.** The ranges overlap nearly completely — both m80 minima are
*identically* 137 s — and turns and tokens move in **opposite directions** across the two stacks
(m35 up, m80 down). A real effect does not reverse sign between two stacks running the same task.
The within-cell spread is the story: m35 ran 101 s / 179 K, then 356 s / 1,158 K, on identical
configuration. At n=3 against that dispersion, a ~10 % mean difference is unreadable.

**Read the single replicates as a cautionary tale.** The first m80 replicate came in at 13 turns
against a 24.7 baseline and 388 K tokens against 595 K — a spectacular-looking result that was
called out as such, and that regressed to the mean the moment replicates 2 and 3 landed. Same for
m35's first replicate at "17 % faster". Neither survived.

### What the experiment was actually worth: three harness bugs

**1. Hermes ≥ 0.20 ignores the spawn cwd** and operates in `$HOME`. The first smoke run scored 0.00
on everything with no files written; the agent explained it itself — *"The current working directory
is /Users/… (your home directory), and there is no TASK.md file here."* Measured, same dir + prompt +
model, only the binary differing: 0.18.2 → `/private/tmp/cwdtest`, 0.20.5 → `$HOME`. Neither
`--in DIR` nor `--no-restore-cwd` fixes it on the `-z` oneshot path; both were tested. `TERMINAL_CWD`
does, and `_build_env` now pins it to the playpen. `_assert_inside_playpen_root` could never have
caught this: the spawn cwd is correct and the agent relocates itself afterwards.

**2. Provenance measured the wrong binary.** `_tool_versions` ran a bare `hermes --version` off PATH
while every local experiment pins an absolute `serving.hermes_bin` precisely because hermes is
usually *not* on PATH (exp-43). With two versions installed, the recorded version could describe an
install that never ran — it would have mislabelled this very experiment. Now resolves the configured
binary and records `hermes_bin` beside the version. `LocalAgentConfig.bin` was also added so an
agent *version* can be a level of the agent factor at all; `serving.hermes_bin` is one value per
stacks file and cannot distinguish two profiles sharing a harness.

**3. The provisioned `venv` was being scored as agent-authored source — the serious one.**
`SKIP_PARTS` listed `.venv` but not `venv`, which is the name retort itself uses when it provisions
a venv into each python workspace (added 2026-07-30). Run-time scoring walked
`venv/lib/python3.x/site-packages`. Recorded vs a rescore of the *same* artifacts:

```
maintainability   0.27  ->  1.00
token_efficiency  1.00  ->  0.02
code_quality      0.83  ->  0.79
```

Wrong in both directions, and **the token_efficiency 1.00 is the dangerous one** — a perfect score on
every run reads as a flawless result, not a bug. It hid because `retort rescore` was always right:
the archived run dir has no venv, only the live playpen does, so recovery silently produced different
numbers than the run itself. exp-49/50 predate the venv change and are unaffected — their recorded
maintainability reproduces exactly on rescore. Post-07-30 experiments in master.db do not show the
signature (token_efficiency 0.01–0.1, not 1.00) but have not been rescored to confirm.

A fourth, smaller one: `--dry-run` rendered a naive replicate-major order while the runner actually
groups by stack, so the preview claimed six 42 GB stack reloads for a design that performs two. The
reload key is now computed once and shared by preview and runner.

### Comparability

exp-61 uses exp-49's settings verbatim — same stacks.yaml, `context_threshold` 0.9, per-model
featured sampling, `max_turns` 200 — with one variable, the Hermes binary. `agent.verify_on_stop`
stayed **off** in both arms: 0.20.5 ships a real self-verification subsystem, but enabling it is a
capability change rather than version drift, and mixing the two produces a delta nobody can
attribute. That is exp-62.

All six exp-61 rows in master.db carry the **rescored** metrics, not the run-time ones.

## exp-62 — does Hermes 0.20.5's verify-on-stop change local pass rates?  — NULL (unanswerable), 2026-09-01

**The factor works; the experiment could not measure it.** Three cell configurations were burned, and
the two arms that completed both sat at ceiling.

**What was delivered, and is solid:** `agent.verify_on_stop` demonstrably takes effect. Verified
inside the grid itself, not only in a smoke: the ON arm's transcripts carry
`finish_reason: verification_required` (2 and 1 occurrences) and all three OFF transcripts carry
zero. Retort also gained the ability to vary an AGENT setting as a factor at all — presets now take a
`hermes:` override block that deep-merges into the config and participates in the reload signature.

**Final grid (typescript x m35, n=3/arm):**

| arm | rep 1 | rep 2 | rep 3 |
|---|---|---|---|
| verify OFF | **1.00** (365 s) | failed — dependency | failed — dependency |
| verify ON | **1.00** (437 s) | **1.00** (1303 s) | killed by the stall guard at 3376 s |

One usable OFF point against two usable ON points, **all three at `requirement_coverage` 1.00**. The
hypothesis is that verify-on-stop converts NEAR-MISSES; with no near-miss in the completed cells there
is nothing for it to convert, so the null is structural rather than informative. This was
pre-registered before the cells landed, not rationalised after.

**Three cells burned, three distinct environmental causes** — the real finding:

1. **rust x m80** — the 42 GB model at full context sits on this machine's memory ceiling. The server
   aborted (`process memory limit exceeded, 51.9 GB against a 54.0 GB ceiling`) and died.
2. **rust x m35** — no memory crash, but sustained `adaptive_prefill_throttle` ground generation to
   ~1.2 KB/min; one cell burned the whole 90-minute wall. 60 min was a hard kill and 90 min was a hard
   kill, so raising the clock was not the fix.
3. **typescript x m35** — two OFF replicates lost because the model pinned `better-sqlite3@^9.4.3`,
   which ships no native binding for Node 26 / ABI 147, so its own tests cannot run. The cell that
   passed pinned ^11.6.0. Attributable to the deliverable, not the harness — and invisible to
   `requirement_coverage`, which sees the capability as implemented.

**Harness defects found and fixed along the way** (each has a regression test):

- `ensure()` trusted `_loaded_sig` without probing the port, so a server that died mid-experiment was
  never noticed and every later cell scored 0.00 against a dead port. This was also the
  previously-unexplained cause of exp-60's arm B failure.
- `_seed_repair_workspace` copied the prior attempt's build tree, so a second chance inherited a
  path-pinned `.build` and could never compile.
- `_store_run_result` labelled every conformance failure "tests did not run", including spec and
  factual ones.
- A `hermes:` override written flat lands a top-level key Hermes never reads — a silent no-op that
  would have run both arms verify-OFF.

**The stall guard works.** Cell 6 was killed with `stalled (no progress)` after the model pinned ~50%
CPU for 25+ minutes without emitting a token. Earlier in this experiment the guard was suspected of
being broken; it was not, and this is the positive confirmation.

**Where this factor should go next.** It needs a cell with genuine headroom AND an environment that
does not fail first. Every local option has now failed environmentally, in three different ways. The
next attempt should be a CLOUD arm, where none of memory pressure, prefill throttling, or local
native-build variance applies.

## exp-63 — does Graphify pay off on a LARGE repo?  — NULL, 2026-09-01

**The last open arm of the Graphify question, and it closes it.** The small-repo arms (exp-44/45)
found no benefit, which could always be waved away as "the repo was too small to need a knowledge
graph". This ran the same factor against a large real codebase — porting `the-goodies` (pinned at
tag v0.2.2) to Go as a `repo-pr` task — which is the case where a code knowledge graph is *most*
expected to pay off. It does not.

**Design:** `tooling{none, graphify} x go x funkygibbon-port x n=3`, cloud `claude-opus-4-8`,
judge held at opus-4.8. 6 cells, **$39.998**, ~15 min/cell.

| arm | test_cov | maintainability | idiomatic | tokens | cost | wall |
|---|---|---|---|---|---|---|
| none | 0.62 / 0.60 / 0.60 → **0.607** | 0.67 / 0.57 / 0.69 → **0.643** | **0.780** | **6.19 M** | **$6.27** | **834 s** |
| graphify | 0.68 / 0.60 / 0.65 → **0.643** | 0.70 / 0.72 / 0.73 → **0.717** | **0.797** | **7.49 M** | **$7.07** | **901 s** |

**Pass-proportion is 3/3 = 1.00 in BOTH arms.** The primary response is saturated, so it cannot
discriminate at all; everything below is secondary metrics.

### The real finding is about the design, not about Graphify

**n=3 vs n=3 cannot produce a significant result at α=0.05, whatever the effect size.** There are
only C(6,3) = 20 ways to split six runs into two arms of three, so the smallest two-sided
permutation p-value obtainable is 2/20 = **0.10**. The α=0.05 threshold is unreachable *by
construction*.

This is not hypothetical here. `maintainability` achieved **perfect separation** — every `none` run
(0.57, 0.67, 0.69) scored below every `graphify` run (0.70, 0.72, 0.73), with no overlap — and still
returned p = 0.100, because that is the floor. The strongest possible evidence this design can
generate is indistinguishable from its own noise ceiling.

| metric | none | graphify | Δ | ranges overlap? | perm p |
|---|---|---|---|---|---|
| test_coverage | 0.607 | 0.643 | +6.0% | yes | 0.400 |
| **maintainability** | 0.643 | 0.717 | **+11.4%** | **NO** | **0.100** (floor) |
| idiomatic | 0.780 | 0.797 | +2.1% | yes | 0.900 |
| tokens | 6.19 M | 7.49 M | +21.1% | yes | 0.200 |
| cost | $6.27 | $7.07 | +12.8% | yes | 0.200 |
| wall | 834 s | 901 s | +8.0% | yes | 0.400 |

**Consequence for this project: n=3 per arm is for screening, not for claims.** Any future two-arm
comparison that intends to *assert* a difference needs n≥5 per arm — C(10,5) = 252 gives a floor of
2/252 = 0.008, which clears even a 6-metric Bonferroni threshold of 0.0083. Re-read past two-arm
n=3 results in that light: they can rule effects *in* as worth pursuing, never *out*, and never
establish one.

### What can be said about Graphify

Graphify costs **+21% tokens and +12.8% dollars** and buys no pass-proportion benefit, on the task
type most favourable to it. That direction matches exp-44/45 exactly, where graphify also cost more
tokens than none. The `maintainability` separation is the one signal worth remembering — it is the
only metric whose arms do not overlap — but at the p-floor it is a hypothesis for a properly powered
run, not a result. **§2 of the queue is closed on this basis:** no further Graphify arms are planned.

### Two harness defects this experiment exposed

1. **`test_coverage` scored a real 21-file Go port as 0.0** — and the first cell died that way before
   the bug was caught, costing $1.47. `go test ./...` ran at the *repo root*, which for a `repo-pr`
   task is the base repo (`the-goodies`, a Python/TypeScript codebase with no `go.mod` anywhere),
   not the agent's new `wombat-go/` subdirectory. A greenfield task puts `go.mod` at the workspace
   root so this had never bitten; a repo-pr task structurally cannot. In the results a perfect port
   and an empty one were **identical**, which is the exact confusion this harness exists to prevent.
   Fixed by `_go_module_root()`: root `go.mod` wins; else the single subdirectory module; if several,
   stay at the root rather than guess which is the deliverable; hidden dirs ignored so a `.git`
   worktree cannot be mistaken for the port. The remaining 5 cells would all have failed identically.
2. **`graph_usage_score` overloads 1.0** — it means both "not applicable" (the `none` arm) and "graph
   built and consulted" (the `graphify` arm). Both arms report 1.00 here, meaning different things.
   Never average this column across arms; it inflates the consultation rate toward 1.0. Not fixed
   mid-experiment on purpose, since changing a scorer while cells are running makes completed and
   remaining cells incomparable. The fix is to return `None` for not-applicable.

**Cost estimation note.** This run was projected at ~$1.47/cell from the first *failed* cell, which
died before doing any work — an invalid basis. Real cost was ~$6.50/cell, 4.4x the estimate. Price a
cloud experiment from a cell that ran to completion, never from one that aborted early.

## exp-65 — Fable 5.1: does the point release move TIME and COST?  — YES for effort, 2026-09-01

**The first properly powered two-arm comparison in this project, and it found something.** Fable 5.1
released 2026-09-01. Model id `claude-fable-5-1`, established from the CLI's own model catalog (which
lists `claude-fable-5`, `claude-fable-5-1`, `claude-fable-5-mythos-5`) and confirmed with a live call,
not guessed. Required Claude Code 2.1.250 -> 2.1.257: the older CLI rejects the id as "not described
by this version's model catalog".

**Why the response is time and cost, not pass-proportion.** Fable 5 scores **1.00 on every cell it has
ever run** — 13 languages x 2 tasks, 52 runs, no exceptions — *and* 1.00 at low effort. A reliability
comparison was therefore guaranteed to return 1.00 vs 1.00 and measure nothing, the same structural
null that made exp-62 unanswerable. Efficiency was wide open, so efficiency is what was measured.

**Design:** `effort{low, default} x language{python, go, rust, typescript} x prompt{neutral, none}`,
`rest-api-crud`, n=3 per cell. 8 cells, 24 runs, **$38.20**.

### Result: low effort is strictly cheaper at identical quality

| metric | low (n=12) | default (n=12) | ratio | exact paired p |
|---|---|---|---|---|
| wall | 109.6 s | 184.4 s | **1.68x** | **0.0015** |
| cost | $1.33 | $1.91 | **1.45x** | **0.0010** |
| tokens | 368 K | 615 K | **1.67x** | **0.0010** |
| test_coverage | 0.930 | 0.927 | 1.00 | 0.75 (null) |

11 of 12 matched pairs favour `low` on time, cost and tokens; coverage is flat. All three clear a
4-metric Bonferroni threshold of 0.0125 with room to spare. **Default effort buys nothing measurable
here and costs 68% more wall-clock and 45% more money.**

The test is an **exact paired permutation** over the 12 (language, replicate) pairs — 2^12 = 4096
sign-flips, enumerated, not sampled. Pairing is legitimate because the design crosses effort against
language, so every language contributes a matched low/default pair in each replicate. `prompt`
alternates by language (python/rust pair low-with-neutral, go/typescript pair low-with-none), so its
effect cancels when pooled across all four rather than riding on the effort contrast.

### The design decision that made this readable — and it was a deliberate deviation

A **quarter** factorial was requested. The generator's quarter fraction of the 16-cell design came out
fully aliased on the one contrast the experiment exists to measure:

    low      python      neutral
    low      go          none
    default  rust        neutral
    default  typescript  none

`low` runs only python/go and `default` only rust/typescript. rust and typescript are the slower,
costlier languages here, so **"default is slower and dearer" would have come out guaranteed** — as an
artifact of which languages landed in which arm. A quarter of 16 cannot cross a 2-level factor against
a 4-level one; 8 cells is the minimum that can. The design was therefore written by hand as a **half**
fraction crossing effort x language completely and balancing effort x prompt 2/2. `design.csv` must
not be regenerated — `retort design generate` would restore the confound.

**This is the counter-example to exp-63.** exp-63 ran n=3 per arm and could not reach significance even
with perfect separation, because its permutation floor was 0.10. Here the effort main effect pools to
n=12 per arm, the floor drops to ~2^-12, and a real effect came out at p=0.001. Same project, same
week: the difference is entirely in how the design was sized.

### Fable 5.1 vs Fable 5 — flagged, NOT claimed

On the one cell both models have run (`rest-api-crud` / python / neutral):

| | wall | cost | tokens |
|---|---|---|---|
| Fable 5 low (exp-49, n=3) | 49.0 s | $0.909 | 131 K |
| Fable 5.1 low (n=3) | 85.3 s | $1.144 | 286 K |
| Fable 5 default (n=3) | 107.0 s | $1.207 | 352 K |
| Fable 5.1 default (n=3) | 127.1 s | $1.447 | 500 K |

5.1 looks **more expensive than 5.0** — 1.74x the wall-clock and 2.19x the tokens at low effort. Three
reasons this is a flag and not a finding: it is n=3 vs n=3, below the threshold exp-63 established;
5.1's own spread on that cell is wide ([59.9, 108.5, 87.5] s); and the CLI moved 2.1.250 -> 2.1.257
between the two, so **agent version is confounded with model version**. That confound was accepted
deliberately for the effort question (where both arms share one CLI and it cancels); it does NOT
cancel in a cross-model comparison. Re-running 5.0 on the current CLI at n>=5 would settle it.

**Smoke test, recorded before launch:** `--effort` demonstrably reaches 5.1 — thinking tokens 1089 at
low vs 1310 at default, 21.0 s vs 25.1 s on a fixed reasoning prompt. Without that check, an effort
flag silently dropped by a new model would have made both arms identical and produced a confident null.

## exp-64 — does quantization bit-width move coding reliability?  — YES, 2026-09-03

**The first positive result in the inference-lever sweep beyond sampling, and the mechanism is not
the one the question assumed.** §3 asked whether "the last mile" is lost to 4-bit quant error — i.e.
whether quantization degrades output *quality*. On the 30B it does something more basic than that: it
determines whether the agentic loop **terminates at all**.

**Design:** `quant{4-bit, 8-bit} x language{python, go} x rest-api-crud x n=5` = 20 local runs, $0.
`mlx-community/Qwen3-Coder-30B-A3B-Instruct` at both bit-widths — same base model, same conversion
pipeline, same publisher, identical `group_size: 64`, so **bit-width is the only thing that varies**.

| | 4-bit | 8-bit | Fisher exact (two-sided) |
|---|---|---|---|
| **pass-proportion** | **1/10 = 0.10** | **7/10 = 0.70** | **p = 0.0198** |
| **unproductive-loop stalls** | **8/10** | **1/10** | **p = 0.0055** |

Both clear a 2-metric Bonferroni threshold of 0.025, and **both languages agree independently**:
python 1/5 -> 3/5, go 0/5 -> 4/5.

### The finding: 4-bit doesn't produce worse code, it fails to stop

The failure MODE separates more sharply than the pass rate. The 4-bit arm was killed by the stall
guard — "no progress for 25m, unproductive loop" — in **eight of ten runs**. The 8-bit arm stalled
once. A pass/fail column alone would have shown "4-bit is worse" and hidden the interesting part:
quantization error at 4 bits appears to destabilise the multi-turn tool loop, so the model circles
instead of converging. **Qualified 2026-09-04: that is true of THIS build, not of 4-bit generally —
the 80B's 4-bit build stalls at 0.04 across 131 runs on the same cells. See the analysis note at the
end of this file.** That is a different claim from "quantized models write worse code", and it
predicts something useful — the damage should show up on *agentic* tasks long before it shows up on
single-turn benchmarks, which is exactly where published perplexity/quant comparisons look.

Corroborating detail from the same runs: 4-bit cells produced a complete `main.py` and confidently
declared the task finished. **Refined by exp-66** — across its 20 further 4-bit runs the model wrote
25 implementation files AND 17 test files while scoring `test_coverage = 0.00` every time, so the
failure is not "writes no tests" (an over-generalisation from a single cell here). It writes code,
writes tests, declares itself done, and never converges on a state where the tests run. The model is
not incapable of the code; it is unreliable about *finishing the job*.

### What this does NOT establish

- **The 30B is a proxy.** The last-mile gap that motivated §3 is on the 35B and 80B, and neither can
  be tested cleanly on this hardware: the 35B is an unsloth UD *dynamic* quant with no matching
  6/8-bit from the same pipeline (bit-width would confound with quant *scheme*), and an 8-bit 80B is
  ~85 GB, past both RAM and disk. This answers the question for the 30B only.
- **Passing is not doing it well.** Test coverage among the 8-bit passes ranges 0.06 to 0.94 (mean
  0.54). The defensible claim is that 8-bit *clears the gate* where 4-bit cannot, not that it does
  the task well. The mechanical gate only requires coverage > 0.
- **Sampling was the 35B's tuned config** — TESTED AND CLEARED by exp-66. The 30B has never been
  tuned on this stack, so exp-64 borrowed the 35B's numbers; both arms shared them, so the contrast
  was safe, but the 4-bit's absolute level was not. exp-66 re-ran the 4-bit under the Qwen card's
  own sampling (top_p 0.8 vs 0.95) for 20 further runs and got **0/10 in both arms** — tightening the
  nucleus moved failures toward stalls rather than passes. The gap is not an artifact of borrowed
  sampling. A full empirical sweep (the exp-27 treatment) is still open but now low priority.
- **The 8-bit runs under more memory pressure.** 30.41 GB resident against the 4-bit's 16 GB, with 16
  `adaptive_prefill_throttle` events observed and generation at ~30 tok/s vs ~50. It won anyway.

### Verification that the arms were genuinely different

This factor's specific false-null is oMLX silently serving the cached 4-bit for both arms, which
would have produced a confident null meaning nothing. Four independent checks:
`config.json` reports `bits: 4` vs `bits: 8` (identical `group_size: 64`); on-disk sizes 16 GB vs 30
GB; retort's own provenance line records `quant=4 size=16G` and `quant=8 size=30G` with different
revision hashes; and the server log states `Loaded model: ...-8bit (actual: 30.41GB)` with process
RSS moving 16.6 GB -> 30.8 GB at the arm switch.

### Process notes

- **A viability smoke test was missing and nearly cost the experiment.** The full grid was launched
  having verified the *quant parameter* but never that the 30B could complete this task at all. The
  first two cells failed, and the runner batches by stack (all ten 4-bit cells before loading the
  8-bit), so the run would have spent ~4 hours before revealing anything about the contrast. It was
  stopped and a 2-cell 8-bit smoke run instead — which passed both, established the test bed, and
  justified the full grid. Verify the *test bed*, not just the parameter.
- **Disk, not compute, was the binding constraint.** The volume hit 15 GB free of 926 GB and deleting
  ~110 GB of stale caches reclaimed almost nothing, because an APFS TimeMachine local snapshot pins
  freed blocks. `tmutil thinlocalsnapshots` plus pruning 57 GB of non-featured model weights restored
  205 GB. See the standing method notes.

## exp-66 — does 30B-tuned sampling rescue 4-bit?  — NO, exp-64 hardens, 2026-09-03

**Purpose: attack exp-64's own result rather than build on it.** exp-64 found 8-bit beating 4-bit
0.70 vs 0.10, with the 4-bit arm killed by the stall guard in 8 of 10 runs. But exp-64 ran both arms
at the **35B's** tuned sampling, because the 30B has never been tuned on this stack. That could not
have confounded the quant *contrast* (both arms shared it) but it could absolutely have set the
4-bit's absolute level — and the threat was specific, not hypothetical: the 4-bit failure is a *loop*
pathology, and this project has already measured sampling causing exactly that (`repetition_penalty`
derailing the tool loop even at the model card's recommended value). exp-64 ran 4-bit at a permissive
`top_p: 0.95`.

**Design:** `sampling{s35, qwen-card} x language{python, go} x rest-api-crud x n=5` = 20 runs, $0,
**4-bit only**. Presets verified BY PARSING to differ in nothing but the sampling block.

| arm | temperature | top_p | passes | stalls | fails |
|---|---|---|---|---|---|
| `s35` (exp-64's config) | 0.6 | 0.95 | **0/10** | 6 | 4 |
| `qwen-card` | 0.7 | **0.8** | **0/10** | 9 | 1 |

**Result: no rescue.** Twenty further runs, zero passes. Tightening the nucleus moved failures
*toward* stalls (6 -> 9), which is the opposite of a rescue. exp-64's conclusion therefore hardens:
the 4-bit's inability to finish this task is a property of the quantization, not an artifact of
borrowing the 35B's sampling.

`repetition_penalty` was held at **1.0 in both arms**, deliberately not adopting the Qwen card's
1.05. That value is already known here to derail the tool loop; importing it would have confounded
the nucleus change with a known-harmful penalty, and stalls are the very thing being explained.

### Bonus: an independent replication of exp-64's 4-bit baseline

The `s35` arm is exp-64's 4-bit cell re-run in a **separately launched experiment**: 0/10 with 6
stalls here against 1/10 with 8 stalls there. The stall pathology reproduces across runs, which is
worth more than either experiment alone — it rules out the possibility that exp-64's 4-bit arm was
one unlucky session.

### What the failure actually is — correcting a loose claim

exp-64's write-up says a 4-bit cell "never wrote tests". That was true of that cell but is the wrong
generalisation. Across exp-66's 20 runs the 4-bit wrote **25 implementation files and 17 test files**
— roughly one test file per run in the `qwen-card` arm — and still scored `test_coverage = 0.00` in
**every single run**. The model is not failing to author tests. It is failing to reach a state where
they run: 15 of 20 runs were killed mid-flight by the stall guard, and the 5 that completed produced
tests that did not pass. The task's own requirement R12 is explicit — ">= 3 tests exist **and run**
(test_coverage > 0)" — and the self-repair second chance fired with that feedback and still failed.

So the accurate statement of the 4-bit's failure mode is **"cannot converge on a working, tested
deliverable"**, not "writes no tests" and not "writes bad code". It writes plausible code, writes
tests, declares itself finished, and cannot close the loop.

### Caveat this does NOT remove

`qwen-card` is the **model card's** recommended sampling, not an empirically tuned 30B config. A real
sampling sweep on the 30B (the exp-27 treatment) could still find a config that rescues 4-bit. What
exp-66 rules out is the cheap and most plausible version of that objection — that exp-64's result was
an artifact of using another model's numbers. A full sweep remains open, but is now much lower
priority: two independent configs, twenty runs, zero passes.

## exp-67 — 6-bit: where is the knee?  — TWO CURVES, not one, 2026-09-03

**The question assumed a single curve. There are two, and they have different shapes.** exp-64 gave
4-bit 0.10 vs 8-bit 0.70 and exp-66 ruled out sampling as the cause. exp-67 adds the middle rung and
finds that the *termination* failure and the *quality* failure are separate phenomena.

**Design:** the new level ONLY — `6-bit x language{python, go} x rest-api-crud x n=5` = 10 runs, $0,
compared against exp-64's existing 4-bit and 8-bit rows. Legitimate because the q6 preset was
verified BY PARSING to differ from exp-64's q8 in nothing but the model id (identical sampling,
context, threshold), and nothing in the scoring path changed between the two.

| bits | size | pass-proportion | stalls |
|---|---|---|---|
| 4 | 16 GB | 0.10 (1/10) | **8/10** |
| **6** | **23 GB** | **0.40 (4/10)** | **1/10** |
| 8 | 30 GB | 0.70 (7/10) | 1/10 |

### Curve 1 — the stall pathology is a THRESHOLD, and it sits below 6 bits

| comparison | stalls | Fisher exact |
|---|---|---|
| 4 vs 6 bit | 8/10 vs 1/10 | **p = 0.0055** |
| 6 vs 8 bit | 1/10 vs 1/10 | p = 1.00 |

The "cannot terminate" failure that dominated exp-64 — the agent circling in an unproductive tool
loop until the stall guard kills it — is **entirely cured by going from 4 to 6 bits**, and six bits
is as good as eight. This is the well-supported half of the result.

### Curve 2 — output quality keeps improving, linearly, past the threshold

Pass-proportion is 0.10 -> 0.40 -> 0.70: **exactly linear at +0.15 per bit**, with no knee. But the
statistics do not support reading the intermediate steps:

| comparison | pass | Fisher exact |
|---|---|---|
| 4 vs 6 bit | 1/10 vs 4/10 | p = 0.3034 |
| 6 vs 8 bit | 4/10 vs 7/10 | p = 0.3698 |
| 4 vs 8 bit | 1/10 vs 7/10 | **p = 0.0198** |

Only the extremes separate. At n=10 per level a 0.30 step is not resolvable — the linear trend is
**suggestive, not established**, and saying otherwise would repeat exp-63's mistake of reading a
tidy-looking pattern as a result. Establishing the 6->8 step needs n>=20 per level.

### What this means in practice

**Two different things break at 4 bits, and they are fixed at different prices.** 6-bit costs 7 GB
more than 4-bit and buys the *entire* termination fix — the model stops circling. 8-bit costs a
further 7 GB and buys more finished-and-correct deliverables, but that step is not statistically
established here. On a 64 GB machine where the 8-bit's 30 GB is tight alongside a 262144-token KV
cache (exp-64 logged 16 `adaptive_prefill_throttle` events on the 8-bit and none of that pressure on
smaller builds), **6-bit is the defensible recommendation** and 8-bit is the option if the memory is
spare.

### Why this matters beyond this model

The two curves have different implications for how quantization is normally evaluated. Published
quant comparisons measure perplexity or single-turn benchmark scores — which would capture Curve 2
(gradual quality loss) and would be **blind to Curve 1 entirely**, because a single-turn generation
cannot exhibit a failure-to-terminate pathology. The lever that mattered most here is invisible to
the standard measurement. That is the meta-prize §3 was set up to chase, and this is the first
concrete instance of it.

### Verification

Same false-null guard as exp-64, four independent checks: `config.json` reports `bits: 6` with
`group_size: 64` matching both other arms; on-disk size 23 GB sits between 16 GB and 30 GB; retort's
provenance records `quant=6 size=23G` with its own revision hash; and oMLX RSS measured 25.5 GB
during the run, between the 4-bit's 16.6 GB and the 8-bit's 30.8 GB.

## exp-68 — is the stall threshold about BITS or about ERROR?  — ERROR, decisively, 2026-09-03

**This reframes exp-64 and exp-67, and produces the most useful practical result of the quant
sequence.** exp-67 described the agentic stall pathology as "a threshold below 6 bits". But bits and
quantization *error* are confounded in a bit-width ladder — every rung both adds bits and reduces
error — so that phrasing assumed the answer. `-DWQ` (distilled quantization) breaks the confound: it
is **4 bits with materially lower error**, distilled against the full-precision model rather than
round-tripped. It holds bit-width at the level that stalls and moves only the error.

**Design:** the new level ONLY — `4bit-DWQ x language{python, go} x rest-api-crud x n=5` = 10 runs,
$0, against exp-64's and exp-67's existing rows. Preset verified by parsing to differ from exp-64's
plain 4-bit in nothing but the model id; `config.json` confirms `bits: 4, group_size: 64` (identical
to plain 4-bit) and oMLX RSS measured 16.7 GB against plain 4-bit's 16.6 GB — same bits, same size.

### The full matrix

| build | bits | size | pass | stalls |
|---|---|---|---|---|
| `4bit` | 4 | 16 GB | 0.10 (1/10) | **8/10** |
| **`4bit-DWQ`** | **4** | **16 GB** | **0.80 (8/10)** | **0/10** |
| `6bit` | 6 | 23 GB | 0.40 (4/10) | 1/10 |
| `8bit` | 8 | 30 GB | 0.70 (7/10) | 1/10 |

### The answer: error, not bits

Holding bit-width and footprint fixed and changing only quantization quality:

| | DWQ-4bit | plain 4-bit | Fisher exact (two-sided) |
|---|---|---|---|
| stalls | **0/10** | 8/10 | **p = 0.00071** |
| pass | **0.80** | 0.10 | **p = 0.0055** |

The termination pathology is **a function of quantization error, not of bit-count**. exp-67's "6-bit
threshold" was not about six bits: 6-bit was simply the first rung in that ladder whose error fell
below whatever level destabilises the multi-turn tool loop. DWQ reaches that level at four bits.

### The practical result: 8-bit reliability at 4-bit memory cost

| | DWQ-4bit (16 GB) | 8-bit (30 GB) | Fisher |
|---|---|---|---|
| pass | 8/10 | 7/10 | p = 1.00 |
| stalls | 0/10 | 1/10 | p = 1.00 |

**Statistically indistinguishable at 47% of the memory.** This matters concretely on a 64 GB machine:
exp-64 logged 16 `adaptive_prefill_throttle` events on the 8-bit, which sits at 30.41 GB against a
54 GB guard with a 262144-token KV cache on top. The DWQ build has none of that pressure. **The
recommendation for the 30B is now `4bit-DWQ`, not 6-bit** — which supersedes exp-67's advice, written
before this arm existed.

DWQ vs 6-bit is 8/10 vs 4/10 (p = 0.17) — directionally better and cheaper, but not established.

### What this says about how quantization is normally evaluated

exp-67 noted that published perplexity and single-turn benchmarks would be blind to the stall
pathology, because a single-turn generation cannot fail to terminate. exp-68 sharpens it: the
variable those benchmarks *do* track — quantization error — turns out to be the right one, but the
*failure it causes* in agentic use is one they structurally cannot observe. A quant scheme could look
marginally better on perplexity and be the difference between an agent that finishes and one that
circles for 25 minutes.

### Caveats

- **Pass counts include self-repair.** 5 of the 8 DWQ passes were first-try; 2 passed on the second
  chance after evaluation feedback, and 1 more was recovered by re-scoring. Reported together here
  because exp-64's and exp-67's numbers are counted the same way (from `status='completed'`), so the
  comparison is like-for-like — but a first-try pass is stronger evidence than a repaired one.
- **One model, one task, two languages.** Whether DWQ closes the gap on the 35B/80B, or on harder
  tasks, is untested.
- **`-dwq-v2` and the 6/8-bit DWQ builds exist** and were not tested. If DWQ-4bit already matches
  8-bit, higher-bit DWQ is unlikely to be the interesting direction; a DWQ 30B against the 80B is.

## exp-69 — does DWQ's stall-elimination generalize to harder languages?  — YES, 2026-09-04

**exp-68's effect holds where the model is genuinely out of its depth.** exp-68 measured DWQ's
stall-elimination on python and go, the two languages this 30B handles best. The obvious objection is
that it was an easy-cell artifact. exp-69 re-runs the same comparison on rust and typescript, where a
30B is well past its range.

**Design:** `quant{4bit, 4bit-DWQ} x language{rust, typescript} x rest-api-crud x n=5` = 20 runs, $0.
Both arms fresh — there was no plain-4bit rust/typescript baseline on this stack. Presets verified by
parsing to differ in nothing but the model id; identical 4 bits, identical 16 GB, RSS 16.6 GB both.

| arm | bits | size | **stalls** | pass |
|---|---|---|---|---|
| plain 4-bit | 4 | 16 GB | **9/10** | 0/10 |
| **4bit-DWQ** | 4 | 16 GB | **0/10** | 2/10 |

**Stalls: 9/10 vs 0/10, Fisher exact two-sided p = 0.00012.**

Pooling with exp-68's python/go arms — same comparison, four languages, 40 runs:
**DWQ 0/20 stalls vs plain 17/20, p = 2.6e-8.** Across every language tested, at identical bit-width
and footprint, distilled quantization eliminates the agentic termination pathology completely.

### The design decision that made this measurable

**Pass-proportion floored, exactly as predicted: 0/10 vs 2/10 (p = 0.47).** Had passes been the
response variable this would have been another unanswerable null — the failure mode exp-62 recorded
and the reason the harder *task* (`brazil-soccer-mcp`) was rejected in the plan: the 80B scores only
0.17 there and the 35B 0.25, so a 30B would have floored in both arms and measured nothing.

Choosing **stalls** as the primary response is what let a floored-pass experiment still answer its
question. Recorded as a method note: when a comparison is expected to floor on the headline metric,
look for a response variable that stays measurable at the floor.

### What the effect IS and is not

DWQ does not make a 30B competent at rust. Both its passes came via **self-repair** (second chance,
after evaluation feedback), and they are marginal — coverage 0.14 and 0.85 with maintainability 0.59
and 0.26. What DWQ changes is the failure MODE: it converts *"circles in an unproductive tool loop
until the 25-minute guard kills it"* into *"terminates, usually with a wrong answer"*.

That distinction is worth more than the pass column suggests. A model that finishes and fails costs
one cell and returns a diagnosable artifact; a model that circles burns the entire wall clock and
returns nothing. For anyone running an agent loop unattended, that is the difference between a usable
and an unusable stack — and it is invisible to pass-proportion alone.

### Standing conclusion for the 30B

`4bit-DWQ` is the build to use: 16 GB, no stall pathology across four languages, and pass-proportion
on python/go (0.80) statistically indistinguishable from the 8-bit at 30 GB. This supersedes exp-67's
6-bit recommendation, which was written before the DWQ arm existed.

## Analysis note — the stall pathology is NOT a property of "4-bit"  — 2026-09-04

**No new runs; this is 1,227 archived runs re-read after exp-68/69.** It corroborates the
error-not-bits conclusion from data those experiments did not use, and it corrects a loose phrasing
in exp-64's write-up.

Stall (`crashed`) rate by local build, whole archive:

| build | n | stalls | rate |
|---|---|---|---|
| **30B-4bit (plain)** | 40 | 32 | **0.80** |
| devstral | 12 | 7 | 0.58 |
| 35B (unsloth UD-4bit) | 178 | 24 | 0.13 |
| 30B-6bit | 10 | 1 | 0.10 |
| 30B-8bit | 12 | 1 | 0.08 |
| **80B-4bit** | 131 | 5 | **0.04** |
| **30B-4bit-DWQ** | 20 | 0 | **0.00** |

Matched on task and language, so this is not a task-mix artifact:

| both 4-bit, both Qwen3-Coder | python/go | rust/typescript |
|---|---|---|
| 30B-4bit | 23/30 stalled | 9/10 stalled |
| **80B-4bit** | **2/57 stalled** | **1/22 stalled** |

**This is the strongest available evidence for error-over-bits, and it is free.** If *bit-width* were
the cause, the 80B at 4 bits would stall as badly as the 30B at 4 bits. It does not — 0.04 against
0.80 on identical cells. Larger models quantize more gracefully (more parameter redundancy per unit
of information destroyed), so "4-bit" corresponds to a **lower effective error** in the 80B, placing
it below the threshold that destabilises the agentic loop. exp-68 demonstrated the same thing by
lowering error at fixed bits; this shows it from the opposite direction, by holding bits fixed and
changing the model.

**Correction to exp-64's phrasing.** That write-up says "quantization error at 4 bits destabilises
the multi-turn tool loop". Read as a claim about 4-bit builds in general, that is wrong — the 80B's
4-bit build is one of the most stable in the archive. The accurate statement is that **the 30B's
4-bit build sits above the error threshold**, and neither the bit count nor the format alone predicts
which builds do.

**Practical consequence.** Do not generalise "avoid 4-bit" from exp-64/68/69. The rule is
per-model: measure the stall rate. The archive now gives it for free on any build with runs, and it
is a far cheaper screen than a pass-proportion grid — 20 runs of a new build will show a 0.80-vs-0.00
difference immediately, where distinguishing pass rates needs many more.

**Why this closed a candidate rather than opening one.** It was run to decide whether a
scheme-vs-scheme experiment on the 80B (`mxfp4` vs `4bit`, the nearest feasible substitute for a
DWQ-on-80B test) was worth ~42 GB and ~7 hours. It is not: at a 0.04 stall rate the 80B has no
pathology for a scheme change to fix, and the only response left would be pass-proportion on rust,
which needs far more than n=5 to move. One SQL query replaced a day of compute.
