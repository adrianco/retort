# Future experiments — prioritized queue

**This file holds only what has NOT been run yet.** The moment an experiment finishes — or a model
candidate is rejected — its write-up moves to [`past-experiments.md`](past-experiments.md) (in
increasing experiment order) and its entry is **deleted from here**, not left behind marked DONE.
A queue that accumulates finished work stops being a queue; this file had grown to 570 lines of
which two thirds were already-completed experiments.

For what has already been measured, read [`past-experiments.md`](past-experiments.md) (28 write-ups)
or the living results in [`optimal-blog.md`](../optimal-blog.md).

**Workflow (CLAUDE.md):** before launching any experiment, write its plan / hypothesis here and
push; verify every tuning parameter takes effect with a smoke test first; after it lands, run
`retort recover` + `retort aggregate`, update the blogs, and move the entry to past-experiments.

**Current best local stack:** Qwen3-Coder-Next 80B via Hermes + oMLX at `context_threshold: 0.9`
("full context") — Python/Go/TypeScript all 1.00, Rust 0.33 (near-misses → cloud), niche languages
~0.00, hard task 0/6 (config-invariant). The 35B is the faster Python/Go alternative (0.85). See
[optimal-blog.md](../optimal-blog.md).

---

## 0z. RESOLVED — the `claude` CLI credential was blanked  — 2026-07-31

Kept as a diagnostic recipe, not an open item. `claude -p` returned **`Not logged in · Please run
/login`** while the *running* session kept working, which made it look like a retort or environment
bug. It was neither: the keychain item `Claude Code-credentials` still existed and still read
`subscriptionType: max`, but **`accessToken` and `refreshToken` were both empty strings and
`expiresAt` was 0**. Nothing to refresh. The live session was simply the last process holding an
in-memory token.

Ruled out along the way, in this order: retort's own venv change (the third crashed cell was **go**,
which never gets a venv), `ANTHROPIC_BASE_URL` (set, but to plain `api.anthropic.com`, and unsetting
it changed nothing), and keychain readability (`security find-generic-password` succeeded — the entry
was present, just hollow).

**Diagnostic worth reusing:** check token *lengths*, not the entry's existence. A blanked credential
passes every presence check.

Fixed by an interactive `/login` at the terminal; `/login` is local-only and does not work over
Remote Control. exp-55 brazil then resumed and completed 20/20.

## 0y. exp-56 — Terra across the remaining languages, both tasks  — LAUNCHED 2026-08-01

**Question.** exp-55 showed Terra matching Opus 5 at 1.00 on python and go for a fraction of the
cost, on *both* tasks. Does that hold across the rest of the language matrix — including the
languages that have historically separated models (Rust, Clojure, C#, Elixir, Erlang) and the
systems set (C, C++)?

**Design.** 9 languages × 2 tasks × 1 replicate = **18 runs**. `gpt-5.6-terra` via `codex`,
`effort: default`, prompt neutral, judge held at opus-4.8.

Only the gap is run — python and go already have Terra at five effort levels from exp-55. Effort is
**not** swept: exp-55 measured it as near-inert on Terra ($0.12–$0.29 across the whole dial, every
cell 1.00), so re-sweeping it would multiply 9 languages by 5 to re-measure a known flat factor.
`default` is Terra's own default (medium) and is what a user actually gets.

**swift and objc are EXCLUDED — harness, not model.** Verified at launch: full Xcode *is* installed
at `/Applications/Xcode.app`, but `xcode-select -p` points at `/Library/Developer/CommandLineTools`,
so `xcodebuild` errors with "requires Xcode, but active developer directory ... is a command line
tools instance", and a minimal SwiftPM package fails to build its tests with **"no such module
'XCTest'"** (reproduced directly, not assumed). Either language would have scored a HARNESS false
zero indistinguishable from a Terra capability wall. exp-46 passed objc, so this host changed after
that run.

To add them later — append the two rows per task to `design.csv` and `--resume`:

    sudo xcode-select -s /Applications/Xcode.app/Contents/Developer

That needs the account owner's password, so the harness cannot do it unattended.

**Expected cost** ~\$8–12 list; the real constraint is ChatGPT Plus quota. Wall clock may be long on
the hard task — Opus 5 needed 40–64 min per exotic-language brazil cell, and the wall is 150 min.

**Reading the result:** n=1 per cell. Any single 0.00 is a hypothesis, not a finding — re-run it
before publishing. This repo has reversed n=1 results repeatedly.

---

## 0a. DONE — provisioned python venv verified on a live agent run  — 2026-07-31

retort creates a `venv/` in every python workspace (pytest + pytest-cov preinstalled) and puts
`venv/bin` first on the agent's PATH. Verified on exp-55 brazil cell 14 (python `xhigh`, Opus 5)
rather than a synthetic probe: venv present with Python 3.14.6, pytest 9.1.1 + pytest-cov installed,
**zero** `command not found: python` in an 83 KB agent log, **5 bare `python` invocations and 0
`python3`**, and pip working — the agent installed and imported the `mcp` package.

**Comparability consequence, larger than the saved turn.** pip previously failed with
`externally-managed-environment` against the Homebrew interpreter, so agents avoided dependencies —
the record-holding brazil run wrote a *dependency-free* server partly for that reason. Agents can now
take dependencies they previously could not. Python runs before and after this change differ in more
than turn count; do not pool them.

Still unconfirmed (needs a fresh python run to check): that the archived rep contains no `venv/`, and
that the no-write guard still fires on an empty workspace.

---

## 0. brazil-bench checklist gap: the requirements don't test CORRECTNESS  — OPEN (proposal, do not act unilaterally)

Found 2026-07-30 while writing [tasks-blog.md](../tasks-blog.md), from the fastest-ever brazil pass
(exp-55, Terra/medium/python, 3m19s, scored **12/12**).

The six Kaggle files **overlap**: BR-Football covers 2014–2023, Brasileirao_Matches 2012–2022,
novo_campeonato 2003–2019. `load()` concatenates them, so the same real-world match exists 2–3
times (23,954 rows = the exact sum of the five files, i.e. no dedup anywhere). That run's own MCP
handshake returned **Corinthians 2022 home: 44 matches** — a Brasileirão club plays **19** home
league games; the spec's own worked example says 19. It double-counts.

It still scored 12/12 because:

- `REQUIREMENTS.json` asks whether a capability *exists* ("a tool filters matches by team name"),
  never whether its **numbers are right**. The word "graph" appears 0 times too, though the spec's
  overview asks for a "knowledge graph interface" — this solution has no graph at all, and passes.
- The agent's own tests assert **accounting identities** (`matches == wins+draws+losses`,
  `points == wins*3+draws`) which remain true when every match is counted twice.
- The judge flagged the overlap but as **low/enhancement**, scoped only to `standings()` (the one
  method the agent guarded). It is broader: `team_statistics`, `head_to_head`, `search_matches`,
  `aggregate_statistics` all double-count.

**Do not just edit `REQUIREMENTS.json`.** It is pinned precisely so `requirement_coverage` has a
constant denominator across all **284** brazil runs; changing it silently re-bases every historical
number and makes old and new runs incomparable — the exact failure this project keeps paying for.

Options, cheapest first:

1. **Add a golden-answer scorer** as a NEW response (not a change to the existing checklist), e.g.
   `factual_accuracy`: a handful of externally-verifiable assertions (Corinthians 2022 home = 19
   matches; Flamengo 2019 = 90 points — already used informally). New column, old numbers intact.
2. **Version the checklist** (`REQUIREMENTS.v2.json`) and record which version graded each run, so
   both can coexist in `master.db`.
3. Leave as-is and document the limitation — pass-proportion then means "implements the capability
   list", which is what it has always meant, and tasks-blog now says so explicitly.

Option 1 is preferred: it measures the thing that's missing without touching what's comparable.

**Still to verify** (deferred — exp-55 was running, and this repo runs ONE experiment at a time):
re-run the archived artifact and count matches per (competition, season, source) to confirm the
duplication factor per file pair. Evidence so far is from the run's own log, not a fresh execution.

---

## 1. exp-54 — does a Codex judge agree with the Opus judge?  — SCOPED DOWN (token budget)

`requirement_coverage` is an LLM's opinion, and PR #45 made the judge configurable — so it is a
variable nobody has measured. If two judges disagree about the same artifact, pass-proportions from
differently-judged experiments cannot be pooled and master.db's `judge` column becomes load-bearing.

**Scope reduced (user, 2026-07-28: limited Codex token budget).** Re-judge only the **6 passing
exp-53 runs** (python + go) with `codex:gpt-5.6-terra` and compare run-for-run against the opus-4.8
verdicts they already carry. The 3 TypeScript failures are excluded: they were never evaluated (the
mechanical gate stops before the judge), so there is no Opus verdict to compare against and judging
them would spend tokens for nothing.

Judge is the ONLY variable — same archived artifacts, same pinned checklist. Deliberately not fresh
runs, which would confound judge disagreement with run-to-run variance.

**Report:** per-run agreement, direction of bias, and the number that decides pooling — how many runs
would CHANGE pass/fail under the other judge.

**Standing decision: opus-4.8 remains the scoring judge here.** This measures the alternative rather
than adopting it. Note also that exp-53's code was *written* by a Codex model, so a Codex judge
agreeing is a same-vendor loop and weaker evidence than it looks.

## 2. Graphify tooling factor + large-existing-codebase task  — PLANNED (top priority)

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

## 4. Methodology: harness-orchestration factor (`retort-metaharness`)  — SIDE-BRANCH, staged

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

- 2026-07-28 — **Gemma 4 (31B dense / 26B MoE)** — Apache 2.0, Google's first family with
  **native function-calling + structured-JSON** (explicitly pitched for autonomous agents), 256K
  context, **80.0 LiveCodeBench**. **Q4 GGUF ≈ 18 GB → fits 64GB with enormous headroom** (a QAT
  4-bit build also ships). Serving is unblocked on both of retort's backends: **mainline llama.cpp
  supports it (MTP since b9549)** and MLX quants exist, so no arch gate-probe à la Laguna.
  First **Google-lineage** local candidate and the first *dense* 31B at this size class — a clean
  dense-vs-MoE partner to the Qwen3.6-27B entry above, and the only candidate here whose weights are
  small enough to leave room for a large draft model (feeds the §3 speculative-decoding lever).
  **Caveat, same as Nemotron:** this is an **April-2026 release, not a last-cycle drop** — it
  surfaced via current agentic-coding/local-LLM roundups and is simply a gap in this list rather
  than news; judge priority accordingly. It is also a *general* model with strong coding scores, not
  a coder-specialised one. Source: https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/
  — GGUF: https://huggingface.co/unsloth/gemma-4-31B-it-GGUF

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
