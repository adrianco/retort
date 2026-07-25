# Future experiments — prioritized queue

The live queue of what to run next, highest priority first. When an experiment finishes (or a
model candidate is rejected), its write-up moves to [`past-experiments.md`](past-experiments.md)
in increasing experiment order, and it comes off this queue.

**Workflow (CLAUDE.md):** before launching any experiment, write its plan / hypothesis here and
push; verify every tuning parameter takes effect with a smoke test first; after it lands, run
`retort recover` + `retort aggregate`, update the blogs, and move the entry to past-experiments.

**Current best local stack:** Qwen3-Coder-Next 80B via Hermes + oMLX at `context_threshold: 0.9`
("full context") — Python/Go/TypeScript all 1.00, Rust 0.33 (near-misses → cloud), niche languages
~0.00, hard task 0/6 (config-invariant). The 35B is the faster Python/Go alternative (0.85). See
[optimal-blog.md](../optimal-blog.md).

---

## 0. exp-46 — Opus 5: all languages × both tasks  — DONE, see past-experiments

Ran 2026-07-24/25 → [past-experiments.md](past-experiments.md). **Result: 26/26 — every one of the 13
languages on BOTH tasks at req-coverage 1.0.** The first model to clear the hard task in every language
tried (4.8 manages 0.59 there; nothing else exceeds six languages). **But it buys coverage, not
efficiency:** \$2.91/solved on routine (vs 4.8's \$0.99 for the same 1.00) and \$20.00/solved on the hard
task (vs Fable 5's \$8.98). Recommendation: cheapest model that clears your language; Opus 5 only where
nothing cheaper is proven. Added to FEATURED_STACKS; optimal-blog + model-blog refreshed; the hard-task
routing table now selects Opus 5 for c/clojure/cpp/elixir/erlang.

**Three harness artifacts were caught and fixed before they became false capability claims** (the 60-min
wall killing erlang+c, doubly-quiet pytest zeroing a green Python suite, and a "usage limit until 3pm"
that was really a rolling window). See the entry for details.

## 0b. exp-48 — fill Fable 5's per-language GAPS  — SCHEDULED (runs after exp-46)

exp-46 compared Opus 5 (13 languages) against Fable 5 — but **Fable 5 has only ever run 4 languages
(clojure/go/python/rust) on each task**, so the headline comparison wasn't like-for-like. Per-language
results with honest gaps are fine (user, 2026-07-25); the fix is to **fill the gaps**, not to hedge the
table.

**Design:** `Fable 5 × the 9 missing languages {typescript, java, csharp, elixir, erlang, c, cpp, objc,
swift} × {bookshop, brazil-bench}` = **18 cells**, n=1, prompt=neutral, spec-gate ON — matching exp-46's
shape so the per-language tables line up cell-for-cell. brazil gets the **120-min wall** (the exp-46
lesson: 60 min silently "crashed" erlang and c mid-work).

**Why it matters.** On the 4 languages both have run, Fable 5 already beats Opus 5 on success, cost AND
speed (4/4 vs 3/4; \$8.98 vs \$18.12 per solved hard-task cell; 17 vs 25 min) — and it's ~3× cheaper
and ~4× faster on the routine task. If that holds across the other 9, **Fable 5 is the default
recommendation for both task sizes** and Opus 5's niche shrinks to whatever Fable 5 can't do. If it
doesn't hold, Opus 5's breadth claim becomes real. Either way the per-language matrix (and the routing
table that feeds metaharness) gets its missing half.


## 0c. exp-49 — instrumented version comparison on ONE cell (Python bookshop)  — SCHEDULED (after exp-47/48)

[`versions-blog.md`](../versions-blog.md) asks why newer Claude versions cost 6× and take 4× longer for
an identical passing app. The aggregate answer is solid: **turns**, not per-turn speed (Fable 5 10.7 →
Opus 4.8 17.3 → Opus 5 36.0), and cost grows ~**n²** because every turn re-reads the whole conversation
from cache (Opus 5: 33 K tokens *generated* vs **3.28 M cache reads**).

**What we cannot answer, and why.** The tool-call *mix* can only be computed for Opus 5 — older runs
(exp-6 Opus 4.7/4.8, the early local experiments) have **no `_agent_stdout.log`**, because transcript
capture was added later. And **local stacks record no turn count**, so they can't be put on the cloud's
axis.

**Design.** The same cell — `python × bookshop × prompt=neutral` — across **Opus 4.7, Opus 4.8, Fable 5,
Opus 5** and the local **Qwen 35B** and **80B**, **n≥3**, with full transcript capture on every arm.
Metrics: turns, tool-call histogram (Write/Edit/Read/Bash), output vs cache-read tokens, wall time.
**Hypothesis:** the extra turns in newer models are disproportionately **Edit + Bash (verify/refine)
cycles** rather than initial Writes — i.e. newer models iterate on their own output more. If that holds,
it explains both the routine-task overhead AND (plausibly) the hard-task breadth Opus 5 uniquely has.

**Prerequisite fix:** record `turns` for Hermes runs (the local arms currently log none) — otherwise the
local half of the comparison stays unquantified. The `_hermes_session.jsonl` export added 2026-07-24
already captures the tool calls, so the turn count can be derived from it.


## 1. Graphify tooling factor + large-existing-codebase task  — PLANNED (top priority)

Add a third level to the `tooling` factor (currently `none` / `beads`): **`graphify`** — a
code knowledge-graph skill ([graphify.com](https://graphify.com/),
[GitHub](https://github.com/Graphify-Labs/graphify)). It uses Tree-sitter + LLM extraction to turn
a repo into a queryable graph (`graph.json` + `GRAPH_REPORT.md` + god-node/blast-radius analysis)
so the agent answers questions about *relationships* instead of grepping. **Code extraction is
offline/no-API-key** (dogfooded on retort's own `src/`, 1292 nodes in ~20s); it ships a Claude Code
skill (`graphify install`) and an MCP server (`graphify-mcp`) — the two integration points the
experiment needs.

**Hypothesis (task-size interaction, not a mean shift).** Graphify's value is *comprehending an
existing large codebase*. On greenfield **bookshop** it should be a no-op/slightly negative (nothing
to graph). It should pay off on **brazil-bench** and, most of all, on the **large-existing-codebase
task** below — the regime Graphify targets.

**The paired large-codebase task (user decisions, 2026-07-17):**
- **Language: Python.**
- **Scoring: BOTH** — (a) req-coverage over the *new* capabilities the modification must add,
  layered on the seeded codebase, AND (b) a **no-regression gate**: the seed's existing test suite
  must still pass. This is a new scorer shape (bookshop is from-scratch only) — the gate must run
  the pre-existing suite against the modified tree and fail on any breakage. **Build/verify that
  regression gate before trusting results.**

**Design.** `task × tooling{none, beads, graphify}` on brazil-bench + the new large-codebase task
(one bookshop arm as the negative control). Hold the model fixed at a strong cloud stack first (to
isolate the tooling effect from local capability noise), then repeat on the local 80B.
n≥3/cell; pass = req-coverage.

**Plumbing to build + VERIFY first (a set-but-unverified tool is worse than none):**
1. A pre-run hook that builds `graphify-out/` in the playpen before the agent starts. Code-only =
   no key; the graph reflects the *seeded* code (built once for comprehension).
2. Expose it to the agent (mount `graph.json` + `GRAPH_REPORT.md` with instructions, or wire the
   Graphify MCP server so the agent queries it live).
3. **Smoke-test that the agent actually consults the graph** (grep the transcript for graph
   reads / MCP calls) — else `graphify` is silently identical to `none` and we publish a false null.
4. Confirm token accounting captures the claimed savings.

**Graph-freshness design point:** Graphify doesn't auto-update — `graphify update <path>` refreshes
only changed files (offline, fast). The graph built pre-run is for comprehending the *existing*
code; as the agent edits, it drifts. Default: build once at the start (the agent knows its own new
code; it needs the map of what's already there — where ~all the value is for a modify-existing
task). Optionally test re-running `graphify update` between turns as a second arm.

*Dogfood retort itself as the first Graphify target when building this — it validates the plumbing
and gives a maintained graph for future work.* Per incremental-experiments: add ONLY the new tooling
level / task; don't re-run existing cells.

**Groundwork VERIFIED (2026-07-22):** graphify 0.9.20 + graphify-mcp are installed (`~/.local/bin`,
a `uv` tool → package `graphifyy`, interpreter at `~/.local/share/uv/tools/graphifyy/bin/python`).
The offline, no-key AST extraction API is:
```python
from graphify.extract import collect_files, extract
files  = collect_files(Path(target))          # walks the tree, picks code files
result = extract(files, cache_root=Path(target))   # {nodes, edges, input_tokens, output_tokens}
```
Dogfooded on retort's `src/` → **1361 nodes, 2833 edges from 75 files in 0.7 s**, $0. **Gotcha
(must handle in the hook):** `extract()` uses a `multiprocessing` pool with the `spawn` start method
(macOS default), which re-imports the driver's `__main__` — so it MUST run from a real `.py` FILE,
not `python -c "…"` or a heredoc/stdin (those fail with `FileNotFoundError: …/<stdin>` per worker and
return 0 nodes). The prototype hook driver is `scratchpad/build_graph.py`. The full pipeline
(clustering + `GRAPH_REPORT.md` + god-node/blast-radius) is Part C of the skill on top of this AST
result; the pre-run hook can call `extract()` directly for the graph and generate the report from it.
The MCP server is `graphify-mcp` (stdio) for the live-query arm.

**PLUMBING BUILT + VERIFIED (2026-07-22) — the experiment is now runnable:**
1. ✅ **`tooling: graphify` capability** (`playpen/graphify_hook.py` + `LocalRunner.provision` +
   prompt injection): builds `graphify-out/{graph.json,GRAPH_REPORT.md}` on the seeded code before
   the agent starts, and tells the agent to consult it. Subprocess w/ graphify's own interpreter
   (isolates tree-sitter deps + the spawn gotcha). No-op if graphify absent.
2. ✅ **`no_regression` scorer** (`scoring/scorers/no_regression.py`, registered): runs the seed's
   existing suite (`.retort-regression.json`) under the process-group reaper + `ensure_python_env`,
   → 1.0 pass / 0.0 regressed / 1.0 N/A. **Verified it genuinely gates** (pristine→1.0, an injected
   bug→0.0) — an earlier version silently fell to neutral because bare `python` wasn't on PATH.
3. ✅ **`py-catalog-reservations` modify-existing task** (`tasks/py-catalog-reservations/`): a seeded
   `catalog/` library (models→store→loans→service) + a passing 6-test suite; TASK.md adds a
   reservations feature (blast radius spans the modules). `task_loader` now maps a task's `seed/`
   subdir → `support_dir`. End-to-end verified: provision seeds it → graphify builds a 45-node graph
   naming Catalog/Store/LoanService/borrow/return_book → no_regression gates the real suite.

**REMAINING (runtime, not build):**
- ✅ **Consultation smoke PASSED (2026-07-22, exp-44 rep1):** one Opus cell, `tooling: graphify`,
  catalog task — the transcript shows the agent genuinely used the graph (**4× read GRAPH_REPORT.md,
  4× graph.json, ran `graphify explain` ×3 / `query` ×2 / `path` ×2**), implemented reservations, and
  `no_regression=1.00` (existing suite still passes). graphify is NOT ≡ none — the full run is safe.
- ✅ **Frontier arm DONE (exp-44 → past-experiments):** `tooling{none,beads,graphify} × Opus × n=3`
  on the catalog task — all three **1.0 req_cov + 1.0 no_regression**; tooling is a pure no-op on
  correctness (beads +67% time, graphify +9%, for zero gain). A clean null on an easy/small task, as
  predicted — the control, not the headline.
- ✅ **Local-80B arm DONE (exp-45 → past-experiments):** same null — all tooling 1.0 on the 80B too.
  ✅ **Consultation now VERIFIABLE for local agents (2026-07-24):** `_export_hermes_session` writes
  `_hermes_session.jsonl` (from Hermes' SQLite session store, keyed by `.hermes_usage.json`'s
  `session_id`) after each Hermes run, and `agent_consulted()` greps it cross-agent. Retroactively
  confirmed: **all 3 exp-45 graphify cells DID consult the graph** (95–115 tool_call refs) — the 80B
  null is "used-but-didn't-help," like Opus. This unblocks the large-repo arm's consultation check.
- **REMAINING — the real test:** the **large-repo arm** — funkygibbon-port / the-goodies (~30K lines),
  where navigation is genuinely the bottleneck. Needs its PR-on-worktree run model built (see
  `tasks/funkygibbon-port/README.md`) + the user's seed work. Optionally: `graphify --update` between
  turns.

## 2. exp-41 — self-repair iteration-2  — DONE (see past-experiments)

Ran 2026-07-22 → past-experiments. **Verdict: iteration-2 self-repair is NOT a reliable lever.**
Rust's 0.9167 near-miss did not close (stayed 0.83–0.92), erlang flat (0.333); only java lifted
0.75→0.92 (still <1.0). The inline iter-1 second-chance already captures the repairable gain;
Rust stays cloud-only on the 80B. (Optional: a `--resume --retry-failed` re-run to complete the 3
cells INTERRUPTED by a ~23s hermes/oMLX hiccup — wouldn't change the Rust/Erlang verdict.)

## 3. Inference-lever sweep — remaining tiers (issue #40)  — OPEN

The sampling tier is done (exp-27). Remaining levers, by payoff:
- **Speculative decoding / MTP** — the top speed lever. Our runs are generation-bound, so faster
  tok/s converts wall-crashes and slow-but-terminating runs (esp. the 80B, and Rust/Go) into
  passes. oMLX 0.5.0 ships a Qwen3.5/3.6 MTP patch, but the unsloth 4-bit build has no MTP weights →
  needs a small draft model. Highest payoff, most setup.
- **Quant level (4-bit → 6/8-bit) and scheme (unsloth/bartowski/stock)** — tests the hard-task
  *capability* ceiling: is the last mile (Go reaches 0.92 req_cov but not 1.0) lost to 4-bit quant
  error? A 6-bit 35B (~26 GB) fits 64 GB.
- **MoE vs dense** (issue #40 ask) — a fair matched-size dense-vs-MoE on Hermes to isolate the
  architecture effect (the Devstral attempt was the wrong harness).
- **Deprioritised, with reason:** K/V + context quant (memory levers; context isn't our bottleneck
  and lossy KV risks reliability); SWA / convRot (research-y, weak serving support).
- **Meta-prize:** log each config's pass-proportion alongside its published perplexity → *which
  inference levers move real coding reliability, and how badly perplexity mispredicts it.* No public
  benchmark answers this.

## 4. gpt-oss-20b  — DONE (exp-47), see past-experiments

Ran 2026-07-24 → [past-experiments.md](past-experiments.md) (exp-47). Gate-probe passed (oMLX parses
its Harmony tool calls), then n=3 on bookshop: **go 3/3 @95s** (matches the 80B's 1.00 @345s from a
quarter the memory — 3.6x faster), **typescript 2/3** (beats the 35B's 0.00), **python 1/3** (both
Qwens are 1.00). **Verdict: fast and Go-solid, too uneven to displace the 80B** — keep the 80B
featured; gpt-oss earns the "fast Go option" slot and proves the OpenAI open-weights lineage is
viable locally.

**Follow-ups worth queueing:** (a) **n>=5 on Go** to firm up the headline speed/parity claim;
(b) probe whether **Python's 1/3 is a prompt/scaffold artifact** rather than capability (it produced
a 0.9167 near-miss, so it's close); (c) the **llama.cpp backend** could serve it too — a
serving-layer comparison on an identical model is a clean lever test.

## 5. More languages — C / C++ / Objective-C / Swift  — DONE (exp-43), see past-experiments

First systems/Apple-tier run landed 2026-07-22 → moved to [past-experiments.md](past-experiments.md) (exp-43). Full scorer support (build/test/coverage/lint) + toolchains for c/cpp/objc/swift shipped; the README has the per-language toolchain table
and the full-Xcode prerequisite. **Headline (after `retort recover` with the harness fixes):** cloud
(Opus 4.8) passes all four cleanly; the local 80B **fully implements C (ReqCov 1.0)** and near-misses
C++ (0.83) — the C 0.00→1.00 flip was a server-leak harness bug, not the model. ObjC/Swift are genuine
incompletes (no build system / broken Vapor build).

**Follow-ups worth queueing:**
- **ObjC/Swift-local a fair shot** — the 80B produced ObjC source with no build system and a Vapor
  Swift app that won't build in-env; a lighter task variant or build-scaffold nudge would separate
  "can't" from "didn't scaffold". (The server-reaping fix + clean re-score is DONE.)
- **C++-local repair (exp-41-style)** — cpp is at 0.83 (~5/6 reqs), a repair candidate like Rust.
- **More languages** (Kotlin, Zig, Scala, …) reuse the same scorer machinery — add on request.

## 6. Methodology: harness-orchestration factor (`retort-metaharness`)  — SIDE-BRANCH, staged

> **SHARPENED DIRECTION (2026-07-24, user) — metaharness belongs in the `tooling` factor, and the
> integration is a closed loop with `optimal-blog.md`.** metaharness is an **optimization + memory
> layer that ROUTES to the best harness/model per problem**, minimizing cost at a high success rate.
> So it's a **`tooling` level alongside `beads`** (`tooling: {none, beads, metaharness}`) — NOT the
> orchestration-strategy DoE sketched below, and NOT the generic `LocalModelRunner` I built (that's a
> stand-in, now superseded by this). How it works:
> 1. **A full metaharness install is the `tooling: metaharness` capability.** When enabled, the run
>    hands the model/harness choice to metaharness's router (our harnesses = claude-code / hermes).
> 2. **Feed retort → metaharness (BUILT, retort side):** metaharness currently routes on hand-heuristics;
>    we drive it *mechanistically* from measured results. `retort report optimal --routing-json` emits
>    the per (task, language) **cheapest measured stack that clears its pass-bar** — e.g. python/go →
>    free local 35B (\$0 @ 0.85), rust/systems/niche → cheapest cloud model @ 1.00. That IS the routing
>    table (`optimal.routing_config` / `per_language_routing`). This is the "best starting point per
>    language/task" feed.
> 3. **The experiment:** `tooling{none, beads, metaharness} × language × task`, measuring **cost AND
>    success** — does metaharness (fed by optimal-blog) hit the cost/success optimum vs a fixed choice?
> 4. **Contribute back:** the retort-derived routing table goes upstream to metaharness, replacing its
>    heuristics — the closed loop (retort measures → optimal-blog → metaharness routes → contribute back).
>
> **Still to build:** the `tooling: metaharness` playpen capability (install + hand it the routing JSON +
> let it pick per cell), coordinated with ruvnet on metaharness's routing-config format. The retort feed
> (`--routing-json`) is done and tested.

> **What metaharness ACTUALLY is (per ruvnet's explainer, https://metaharness-explainer.vercel.app/ —
> corrects the framing below).** It is *"a factory for agent frameworks,"* not an orchestration-strategy
> set: `npx metaharness` **generates a branded, npm-publishable agent harness** that wraps a model. Its
> real features are **Router** (difficulty-routing to the cheapest model that clears your quality bar,
> ~1/10 cost), **Darwin Mode** (the wrapper self-tunes its settings, sandbox-tests, keeps only what
> measurably helps), **project-scoped Memory**, **Skills/agents**, and **`harness genome <repo>`** (a
> fit/build/safety/cost report card). It runs a **local MCP tool server + a repo-aware CLI** (default-deny
> governance, signed receipts) — **no external cloud solver**, and it is **model-agnostic**.
> **KEY: Hermes is one of its six native host platforms** (Claude Code, Codex, pi.dev, **Hermes**,
> OpenClaw, RVM) — so evaluating metaharness on OUR local models via Hermes+oMLX is a first-class,
> intended path, not a workaround.
>
> **Reconciliation the factor model needs:** the `harness_config` levels below mix *generic ReAct*
> concepts (base-ReAct, self-consistency-N, scaffold — retort's own, NOT metaharness features) with the
> real metaharness features (routed≈**Router**, +agenticow-memory≈**Memory**, +darwin-genome≈**Darwin
> Mode**). To evaluate the REAL tool, the cleaner factor is metaharness's own toggles — **Router / Darwin
> / Memory / Skills on-vs-off** — measured on a `npx metaharness`-generated **Hermes-targeted** harness.
> The "external solver" in `metaharness_runner.py` is really "a metaharness-generated harness for a
> host." Do this reconciliation WITH ruvnet.
>
> **Path B local backend — PLUMBING VERIFIED END-TO-END (2026-07-25).** Smoke-tested
> `LocalModelRunner._one_attempt` against a real local model (gpt-oss-20b via oMLX+Hermes, spec gate
> stubbed since it needs cloud tokens): **provision → Hermes execution → retort scorers all worked**,
> producing go.mod/main.go/main_test.go in 187 s. The cell itself scored 0.00 — verified GENUINE, not a
> harness artifact: the 20B emitted `main.go:12: missing import path`, so the code doesn't compile
> (`go build` reproduces it). Also confirmed `_hermes_session.jsonl` is written on a fresh run, so
> tool-consultation is verifiable for local metaharness cells too. **What remains before a real grid:**
> wire the spec gate (needs quota) and run the first factor sweep.
>
> **Path B — a LOCAL backend (no OpenRouter, no external solver) — IN PROGRESS (2026-07-22, user-directed).**
> Aligned with the above (Hermes is native). NOTE: the `LocalModelRunner` built here is a valid *generic
> local-orchestration* harness (base-ReAct / self-consistency / routed / scaffold as a stand-in) — a
> useful foundation, but it is NOT ruvnet's actual metaharness-generated harness. The real local eval:
> `npx metaharness` → Hermes-targeted harness → retort's DoE toggles Router/Darwin/Memory.
> Keep the existing OpenRouter path (`MetaHarnessRunner` → the external `METAHARNESS_SOLVER`) untouched
> (the contributor, ruvnet, will sort the solver out) and ADD a `backend: local` runner that drives our
> own Qwen 35B/80B via **Hermes + oMLX**. **Foundation confirmed:** oMLX returns OpenAI-format
> `tool_calls` for the 80B (`finish_reason: tool_calls`), so a local model can drive an agentic
> tool-loop exactly like a cloud one. **Done:** local model factor levels (`qwen-80b-local`,
> `qwen-35b-local`) + `factors.served_id`/`is_local_model` helpers. **To build (`retort_metaharness/local_runner.py`,
> a `CellRunner`):** compose retort's OWN pipeline in-process — `LocalRunner` (provision + Hermes
> execute on the served model) → `ScoreCollector.collect` (code_quality/test_coverage) →
> `cli._spec_conformance_passes` (requirement_coverage via the Opus spec-gate) → cost from
> `local_inference_cost` (~\$0). Map the generic factors: **base-ReAct** = one run; **self-consistency-N**
> = N runs, best by test_coverage; **routed** = 35B draft → escalate to 80B on gate-fail; **scaffold**
> {none, plan-and-solve, reflexion} = prompt injection. `+agenticow-memory`/`+darwin-genome` are the
> external solver's proprietary features → mark N/A on the local backend. **Why it matters:** unlike the
> frontier (exp-44/45 showed tooling is a no-op on strong models), the *weak local* models are exactly
> where orchestration (self-consistency, routing, reflexion) has real headroom — the prompt-lever
> finding predicts it should bite here. First run: `harness_config{base-ReAct, self-consistency-5,
> routed, reflexion} × model{qwen-35b, qwen-80b} × rest-api-crud`, n≥3, on the local stack.

There is an in-repo but **unused** methodology layer, [`retort_metaharness/`](../retort_metaharness/)
(console script `retort-metaharness`; 13 passing tests; not referenced anywhere else until now). It
makes the **agentic-orchestration harness itself** a first-class DoE factor — the axis Retort's main
grid can't currently decompose. Where the `agent` factor is coarse (claude-code vs hermes-local), this
crosses *orchestration strategy* with model/language/task and lets the ANOVA attribute variance to
**harness vs model vs language + interactions**:

| factor | levels |
|---|---|
| **harness_config** | base-ReAct · self-consistency-N · routed (cheap→frontier) · +agenticow-memory · +darwin-evolved-genome |
| **scaffold** | none · plan-and-solve · reflexion |
| **model** | deepseek-v4-pro · glm-5.2 · opus-4.8 · gpt-5.2 (via OpenRouter) |

It **composes** Retort's engine (design generator + aliasing, `analysis.anova`, `analysis.pareto`,
`classify_phase`) rather than forking it. The per-cell adapter is `src/retort/playpen/metaharness_runner.py`.

**Why it's worth doing:** it's the natural generalization of Retort's own headline finding — *"prompt is
a lever only in proportion to model weakness"* — from prompt → full orchestration, and it puts the
`routed` cost-vs-reliability tradeoff directly on the Pareto front.

**Honest prerequisites / risks (why it's a side-branch, not a promotion):**
- **The real harness lives outside the repo.** `metaharness_runner.py` is only an adapter; the
  routing/memory/darwin-genome logic is the external `METAHARNESS_SOLVER`. **No solver → only the $0
  `LocalStubRunner` fixture runs, which is explicitly *not* a benchmark.** Blocker #1.
- **Cloud-only + metered** (OpenRouter, key in `/tmp/.orkey`) — a different serving path from the
  local-model spine, and `self-consistency-N × frontier × replicates` gets expensive: needs a hard $ cap.
- **Results island:** it emits `results.csv` and analyzes *that* — it does **not** yet feed `master.db` /
  `retort aggregate` / `report optimal`. Merging is real work, deferred to Stage 3.

**Staged plan (agreed — cheapest→most valuable, each stage gates the next):**
1. **Stage 0 — de-orphan (this entry + a README pointer).** Done: the capability is now discoverable
   with its prerequisites stated up front.
2. **Stage 1 — $0 pipeline bookend.** Run `retort-metaharness smoke` (LocalStubRunner) as the
   "plumbing is green" pre-flight — already passing, zero OpenRouter cost. Satisfies the CLAUDE.md
   "verify before you spend" rule for this sub-system.
3. **Stage 2 — first real screen** *(gated on: solver available + OR key + a hard $ cap).* Deliberately
   small: `model{deepseek-v4-pro, opus-4.8} × harness{base-ReAct, self-consistency-5, routed,
   +agenticow-memory} × scaffold{none, reflexion} × language{python, go}` on `rest-api-crud`,
   fractional (0.5), aliasing reported, n=3. **Hypothesis up front:** harness_config's main-effect
   variance share is non-trivial vs model — else orchestration is a no-op on these tasks (a publishable
   null, like the prompt study).
4. **Stage 3 — confirm + Pareto** *(only if Stage 2 shows a real harness effect).* Full-factorial
   confirmation on the winning config + a routed-vs-frontier cost-Pareto, and **merge its responses
   into `master.db`** so a "harness maturity" row lands in the optimal-blog.

**Promotion rule:** keep it a documented side-branch (cloud-orchestration experiments only, never
touching the local-model spine) **until a Stage-2 screen shows harness-config variance is real** — then
invest in the solver dependency, master.db merge, and first-class docs.

## Candidate models to test next

New open-weight coding models found by the daily scan that plausibly fit 64GB at 4-bit; promote to a
numbered experiment when prioritised.

- *(**Laguna XS 2.1** was gate-probed 2026-07-21 and is BLOCKED: its `laguna` arch isn't in
  mainline oMLX/llama.cpp yet (support PRs unmerged) — see past-experiments.)*
- 2026-07-22 — **Qwen3.6-27B (dense, MTP)** — Apache 2.0 dense 27B, flagship-level agentic
  coding (reported to beat the Qwen3.5-397B-A17B MoE on coding benchmarks); ~16.8 GB at
  Q4_K_M so it fits 64GB with huge headroom. Tool-calling / agentic-coding native. GGUF ships
  (e.g. `unsloth/Qwen3.6-27B-MTP-GGUF`) and **MTP is merged in mainline llama.cpp** (1.7–2.4×
  faster local inference) → directly servable via Retort's new `serving.backend: llamacpp`
  path, no oMLX arch gap. A strong dense-vs-MoE local coding probe distinct from the tested
  Qwen3.6-35B-A3B / Qwen3-Coder-Next-80B MoEs (also feeds the issue-#40 MoE-vs-dense question).
  Source: https://qwen.ai/blog?id=qwen3.6-27b — GGUF: https://huggingface.co/unsloth/Qwen3.6-27B-MTP-GGUF
- 2026-07-23 — **NVIDIA Nemotron-Cascade-2-30B-A3B** — 30B-total / 3B-active **hybrid
  Mamba-Transformer MoE**, NVIDIA Open Model License (permissive open weights + open training
  data). Explicitly coding-targeted: native function-calling + structured-JSON + FIM (trained on
  1.3M tool-calling samples), **87.2 LiveCodeBench v6** (vs Qwen3.5-35B-A3B 74.6), gold-tier
  IOI/ICPC 2025 claims. **Q4_K_M GGUF ≈ 24.5 GB → fits 64GB with big headroom**; community GGUFs
  ship (bartowski / mradermacher / freddm). First **NVIDIA-lineage** local candidate — a distinct
  architecture from the Qwen MoEs and a fresh dense-vs-hybrid probe. **Caveats:** (1) it's a March-2026
  release, not a last-cycle drop — it surfaced via current r/LocalLLaMA agentic-coding coverage, so
  judge priority accordingly; (2) the **hybrid Mamba-Transformer arch must be gate-probed for serving**
  — confirm `nemotron-h`/hybrid-SSM support in mainline llama.cpp (`serving.backend: llamacpp`) or oMLX
  before a full run (à la Laguna). Source: https://awesomeagents.ai/news/nvidia-nemotron-cascade-2-open-moe-30b/
  — GGUF: https://huggingface.co/bartowski/nvidia_Nemotron-Cascade-2-30B-A3B-GGUF

**Serving backends:** retort now supports **`serving.backend: omlx | llamacpp`** (2026-07-21). The
llama.cpp path (`llama-server`, Metal-native, GGUF, `--jinja` tool templates) serves models oMLX
can't — any GGUF whose arch + tool format are in *mainline* llama.cpp. It unblocks **Devstral**
(Mistral arch/parser are mainline) but NOT Laguna (arch unmerged). To add vLLM later (broadest
tool-parser incl. `poolside_v1`), extend `make_stack_manager` with a third backend — note vLLM's
Metal support is weak, so it suits a CUDA box, not this Mac.

---

## Standing method notes

- **Incremental design:** add ONE new model/factor at a time; run only the new cells; compare
  against `master.db`. Never re-run existing baselines.
- **Spec-gate always ON.** Clean archive bloat (truncate `_agent_stdout.log`, strip
  node_modules/target) before committing.
- **Self-repair second-chance is the universal default** (every task, every run) — don't opt out
  with `--no-second-chance` unless asked. It repairs *completed-but-failed* runs; *crashes*
  (wall-timeouts) don't get it, so raise the timeout to convert crashes into repairable runs.
- **Timeout is per-experiment and LOCAL runs need more time** (local models are slow). Set
  `playpen.timeout_minutes` generously (~60 min local vs ~30 cloud). It's a property of the stack,
  not the task.
- **After each experiment:** `retort recover` + `retort aggregate`, update the blogs, move the
  write-up to [`past-experiments.md`](past-experiments.md), push.
- **Suspect the harness before the model:** a model that produces *no code* looks identical to a
  blocked file-write tool. Run `retort diagnose` on any surprising zero; `retort recover` cleans up
  the scorer TOOLING false-failures after every local run.
