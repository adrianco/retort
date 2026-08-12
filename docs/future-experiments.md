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

## 0. brazil-bench correctness gate — BUILT (2026-08-11), needs a run

`REQUIREMENTS.json` asks whether a capability *exists* ("a tool filters matches by team name"),
never whether its **numbers are right**, and the agents' own tests assert accounting identities
(`matches == wins+draws+losses`) that stay true when every match is counted twice. So a run can
score 12/12 with wrong answers.

**Built:** a `factual_accuracy` scorer (`scoring/scorers/factual_accuracy.py`, registered, in the
`retort init` template). It starts the finished server, finds a standings tool from the server's
**own advertised schema**, and checks two externally-verifiable facts about the 2019 Série A —
Flamengo's record is **28W-6D-4L** (which pins both 38 played and 90 points) and **all 20 clubs**
are present. Both are stated in the task's own worked example, so this tests the spec as written
rather than adding a requirement.

**Decision (user, 2026-08-11): it GATES.** A run that answers wrongly fails, and the failure is fed
to the self-repair second chance with the specific wrong figure so it can fix it —
`_seed_repair_workspace` folds `_factual.json` into `FEEDBACK.md`. **A server that cannot be started
also fails**: an artifact that does not run is a broken deliverable, and harness faults are handled
separately (the pipeline aborts rather than recording them). That is deliberately the opposite of
`runtime`, which returns NULL when it cannot measure — do not harmonise them.

**`REQUIREMENTS.json` is untouched**, so `requirement_coverage` keeps its meaning across all 284
historical brazil runs. But **pass/fail is now a different question than it was**, so brazil
pass-proportions from before and after this change are not strictly comparable. The user has
accepted that explicitly; say so in any write-up that pools them.

**What the evidence actually shows — narrower than this entry originally claimed.** The original
note inferred wholesale double-counting from one run's log. Measured directly across the archive:

- **Loading 23,954 rows does NOT imply wrong answers.** That number is exactly the sum of the five
  overlapping match files, but the cpp and rust runs load it and still answer 2019 correctly — they
  reconcile inside the standings computation, and cpp reports *"1562 (889 counted once after
  de-duplication)"* itself. Loading the sum is a smell, not a defect; the row-count assertion was
  dropped for this reason.
- **All 13 archived languages PASS the standings check.** No archived run is wrong on 2019.
- **The original evidence was a team match count**, not standings ("Corinthians 2022 home: 44" where
  19 is right). Probing that across implementations, they disagree with each other and cpp's own two
  tools disagree (58 vs 50 for 2022 all-competitions) — because the answer depends on which
  competitions the corpus covers. There is no clean golden answer there, so the 2019 table is the
  only fully-determined ground and is what the scorer uses.

**Building it produced four false failures**, each of which would have failed CORRECT work, all from
assuming a format the implementations do not share: looking for a literal "38" (rust prints no
played column and the points column was read instead); counting table-shaped lines for the club
total (a trailing "Bottom four (relegation zone): …" summary counted as a 21st club); one name token
per club (rust renders `Athletico` and `Atlético-MG`); and even with alternatives, typescript renders
**both** Atléticos as a bare `Atletico`, so they are only checkable as a pair. 11 unit tests pin all
of it, including fabricated double-counted / truncated / missing-club tables that must fail.

**REMAINING:** run it. Every archived run passes, so the gate has never fired on real data — the
first experiment that includes `factual_accuracy` in `responses:` is the real test of whether it
changes any verdict, and of whether the repair feedback actually helps a failing run recover.

---

## exp-57 — does the factual gate change any verdict?  — PLANNED, launching 2026-08-11

**Question.** `factual_accuracy` (§0) gates brazil runs on whether their ANSWERS are right, not just
present. It has never fired on real data: all 13 archived implementations pass it. So — does a
freshly generated run pass the facts as well as the checklist, and when one fails, does the repair
feedback actually let the second chance fix it?

**Hypothesis.** Terra clears `requirement_coverage` on brazil reliably (exp-55, exp-56: 18/18 at
1.00), so cells should reach the factual gate rather than dying earlier. Prediction: **most cells
pass both gates**, matching the archive. A cell that fails factual-but-not-checklist is the
interesting outcome — it is a run that would have been recorded as a PASS before today.

**Design.** brazil-bench × `gpt-5.6-terra` @ default effort × {python, go} × n=3 = **6 cells**.
Python and go because they have the most archive data to compare against, and because exp-55 already
measured Terra on exactly these cells *without* the factual gate — so any verdict change is
attributable to the gate rather than to a new stack. ~$0.41/cell on exp-56 evidence → **≈ $2.50**.

**What is NEW in `responses:`** — and both are first-run-ever, so treat their output as unproven:
- `factual_accuracy` — the gate under test.
- `runtime` — has only ever run over archives via `retort rebuild`; this is its first live
  invocation. NOTE its numbers here are contended by the agent running on the same box, so they are
  comparable within this experiment only, not against the rebuild sweeps.

**Held fixed:** judge = opus-4.8 (unchanged since exp-53, so `requirement_coverage` still pools);
prompt = neutral; effort = default; agent = codex.

**Comparability, stated up front:** pass/fail now answers a different question than it did for the
284 prior brazil runs, because a third gate can fail a run that the checklist passed. Accepted by
the user (2026-08-11). Any pooling of pass-proportions across that boundary must say so.

**Pre-flight (CLAUDE.md: verify before the grid).** One-cell smoke first, confirming that
`_factual.json` is written by a LIVE run, that `factual_accuracy` lands in `scores.json`, and that
the gate value is actually honoured — a gate that is registered but not wired would silently record
the old verdict, which is exactly the set-but-not-verified failure this repo keeps paying for.

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

<!-- SCAN-HEARTBEAT: the daily scan rewrites the next line on EVERY run, including
     days it finds nothing. Do not hand-edit it. If the date is more than ~2 days
     stale, the scan is not running — see "when the heartbeat goes stale" below. -->
**Daily scan last completed: 2026-08-11** (scanning for new 64GB-fittable coding models)

New open-weight coding models found by the daily scan that plausibly fit 64GB at 4-bit; promote to a
numbered experiment when prioritised.

**When the heartbeat goes stale.** A silent scheduler failure is the reason this line exists. The
scan stopped dispatching on 2026-07-28 and nobody noticed for six days, because a scan that finds
nothing used to leave *no trace at all* — an outage and a quiet week looked identical in this file.
The task also still listed as `enabled: true` with a healthy-looking `nextRunAt` throughout, so the
task list did not reveal it either. The cause was `per_task_limit (active=1, limit=1)`: a run from
2026-07-28 never terminated, so every later firing was skipped with
`[CCDScheduledTasks] Skipping dispatch … per_task_limit`. To diagnose a stale heartbeat: check
`~/Library/Logs/Claude/main*.log` for that line, then toggle the task off/on; if the counter
survives the toggle, restart the Claude desktop app, which clears the in-memory state.

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

- 2026-08-03 — **KAT-Coder-V2.5-Dev (Kwaipilot)** — *the strongest candidate this scan has found.*
  Apache 2.0, **35B total / 3B active MoE, post-trained directly on `Qwen3.6-35B-A3B`** — the exact
  base retort already serves in the hermes-lcm+35B stack — with a coding-specific SFT (127K examples)
  + RL recipe trained on 100K+ verifiable repo environments, explicitly to fix agentic pathologies
  (excessive parallel tool calls, content repetition). **SWE-bench Verified 69.40%**, Multilingual
  63.00%, Pro 45.96%, Terminal-Bench 2.1 41.02%; 262,144 native context (same as our 35B runs).
  bf16 is 70 GB → **4-bit ≈ 20–22 GB, fits 64GB with enormous headroom** (an NVFP4 build measures
  21.9 GB). GGUF ships (bartowski, mradermacher, plus APEX MoE-aware mixed-precision and an MTP
  build); **no mlx-community 4-bit quant yet** — but the arch is Qwen3.6-35B-A3B, which oMLX already
  serves, so `mlx_lm.convert` should be routine and **no Laguna-style arch gate-probe is needed on
  either backend**. **Why this is the highest-value local candidate on the list:** it is a *matched-
  base* comparison — same architecture, same size, same serving path, same context as a model
  already in `master.db`, with **post-training as the only variable**. That isolates "does agentic-
  coding post-training beat general post-training" from every confound the other candidates carry.
  Caveat: it thinks by default before responding (configurable) — record which mode was used, per
  the tuning-parameter rule. Released 2026-07-26.
  Source: https://www.marktechpost.com/2026/07/26/kwaikat-team-releases-kat-coder-v2-5-an-agentic-coding-model-trained-on-100000-verifiable-repository-environments/
  — weights: https://huggingface.co/Kwaipilot/KAT-Coder-V2.5-Dev
  — GGUF: https://huggingface.co/bartowski/Kwaipilot_KAT-Coder-V2.5-Dev-GGUF

- 2026-08-03 — **Bonsai 27B (PrismML)** — **not a new model: a 1-bit / ternary compression of
  Qwen3.6-27B** (the candidate two entries above), Apache 2.0, 262K context, released 2026-07-14.
  **3.9 GB at 1-bit / 5.9 GB ternary**, claiming 90% / 95% of full-precision quality. Listed here
  because it is a ready-made probe for the **quant-level-and-scheme lever in §3** rather than a new
  capability: paired against a stock 4-bit Qwen3.6-27B it measures quantization *directly*, with the
  weights and post-training held constant — the cleanest form of that comparison we could run. It is
  also the only entry small enough to leave ~58 GB free for a **large draft model**, which is exactly
  what the §3 speculative-decoding/MTP lever needs. **Gate-probe required before trusting it:** the
  build reportedly replaces ~75% of Qwen3.6-27B's attention with a *linear* mechanism, so it is not
  merely a requant — confirm mainline llama.cpp serves this GGUF *and* that tool-calling survives
  1-bit before scheduling a run (a model that emits malformed tool calls scores an indistinguishable
  false zero). Source: https://www.marktechpost.com/2026/07/14/prismml-releases-bonsai-27b-1-bit-and-ternary-builds-of-qwen3-6-27b-that-run-on-laptops-and-phones/
  — GGUF: https://huggingface.co/prism-ml/Bonsai-27B-gguf

- 2026-08-03 — **GLM-4.7-Flash (Zhipu / Z.ai)** — 30B total / 3B active MoE, open weights, 200K
  context, pitched by Zhipu specifically at *local* coding and agents. **SWE-bench Verified 59.2%**
  and **tau2-Bench 79.5%** (multi-step tool invocation) — the tool-calling number is what makes it
  worth a slot. **Q4 ≈ 18 GB → fits 64GB with enormous headroom**; GGUF and an Ollama library entry
  ship. First **Zhipu-lineage local candidate** (every GLM we have looked at so far — GLM-5.2 at
  744B-A40B, the leaked GLM-5.5 at >1T — is far too large to run here, so this is the only way that
  lineage enters the local leaderboard at all). **Caveat, stronger than the Nemotron/Gemma ones: this
  is a January-2026 release, roughly six months old — a gap in this list, not news.** It surfaced via
  current local-coding roundups where it is a standing recommendation. Judge priority accordingly:
  below KAT-Coder, which is both newer and a matched-base comparison. Confirm GLM-4.x MoE arch +
  tool-parser support on oMLX or mainline llama.cpp before committing to a run.
  Source: https://www.marktechpost.com/2026/01/20/zhipu-ai-releases-glm-4-7-flash-a-30b-a3b-moe-model-for-efficient-local-coding-and-agents/
  — weights: https://huggingface.co/zai-org/GLM-4.7-Flash

- 2026-08-04 — **North Mini Code 1.0 (Cohere Labs)** — Apache 2.0, **30B total / 3B active MoE**
  (128 experts, 8 active; sliding-window + global attention 3:1), **256K input / 64K output** context.
  Cohere's first developer-facing coding model, pitched squarely at agentic software engineering
  (sub-agent orchestration, code review, terminal work) with **native function-calling via the chat
  template + JSON-schema tool definitions** and interleaved thinking. **SWE-bench Verified 67.6%**,
  SWE-bench Pro 40.2%, Terminal-Bench v2 36%. **Q4 ≈ 18 GB → fits 64GB with enormous headroom**
  (unsloth GGUFs run 9 GB → BF16). First **Cohere-lineage** local candidate — a distinct training
  lineage from every Qwen-derived entry on this list, which makes it the natural *unrelated-base*
  counterpart to the KAT-Coder matched-base comparison above. Serving looks unblocked on both
  backends but the arch is new: `cohere2_moe` merged into mainline llama.cpp (PR #24260, first in
  build **b9626**), so `serving.backend: llamacpp` needs a build at or after that; MLX quants ship
  (an mxfp8 community build, with day-0 MLX support claimed) but **no `mlx-community` 4-bit yet** —
  confirm oMLX loads `cohere2_moe` before committing, or serve via llamacpp. **Caveat, same class as
  the Nemotron/Gemma/GLM entries: this is a 2026-06-09 release, not a last-cycle drop** — it is a gap
  in this list rather than news, surfaced via current local-coding roundups. Judge priority below
  KAT-Coder (newer, and matched-base) but above the general-purpose entries, since this one is
  coder-specialised and its tool-calling is native rather than inferred.
  Source: https://www.marktechpost.com/2026/06/11/meet-north-mini-code-coheres-30b-open-weight-mixture-of-experts-model-with-3b-active-parameters-for-agentic-coding/
  — weights: https://huggingface.co/CohereLabs/North-Mini-Code-1.0
  — GGUF: https://huggingface.co/unsloth/North-Mini-Code-1.0-GGUF

- 2026-08-07 — **BTL-3 (Bad Theory Labs)** — *a second matched-base probe, on the 27B this time.*
  Apache 2.0 **rank-32 PEFT LoRA adapter post-trained on `Qwen3.6-27B`** (pinned to base revision
  `6a9e13bd…`) explicitly for coding agents, repo work and structured tool use — single, sequential
  **and parallel** tool calls, with training aimed at recovering from failed tool results and at
  *stopping* when no action is needed. **BFCL v4 AST 88.5%, BFCL irrelevance 91.2%** (the
  don't-call-a-tool-you-don't-need metric, and the one that matters most for our agentic loop),
  **LiveCodeBench v6 88.1%**, HumanEval 95.12% pass@1 in thinking mode; 262,144 context, same as our
  35B/80B runs. **The adapter itself is 934 MB**, so merged-and-4-bit it is just the 27B base
  (~17 GB) — fits 64GB with enormous headroom; a "Compact edition" single 8.39 GB file (<2.5 bits
  per parameter) also ships for local inference. **Why it earns a slot:** exactly the KAT-Coder
  argument one size class down — same architecture, same context, same serving path as the
  Qwen3.6-27B candidate above, with **agentic post-training as the only variable** — and it pairs
  with KAT-Coder to ask whether that effect is size-dependent. **Serving caveat, and it is the real
  work here:** this is an *adapter*, not a model. Upstream ships Transformers/vLLM only; neither oMLX
  nor mainline llama.cpp serves a PEFT adapter usefully, so a run needs `merge_and_unload()` onto the
  base and then a fresh 4-bit convert — cheap, but it must happen before the cell, and the merged
  hash must be recorded like any other tuning parameter. Also verify the Compact edition's sub-2.5-bit
  quant does not break tool-call formatting (a malformed `<tool_call>` scores an indistinguishable
  false zero); prefer merging at 4-bit over trusting the Compact build for a headline number. Note
  the base, Qwen3.6-27B, is *itself* still untested here — run the base before or alongside, or the
  comparison has no control. Released 2026-07-26.
  Source: https://hackernoon.com/this-qwen-lora-adapter-is-built-for-autonomous-coding-agents
  — weights: https://huggingface.co/badtheorylabs/BTL-3

- 2026-08-07 — **Nanbeige4.2-3B (Nanbeige Lab / BOSS Zhipin)** — Apache 2.0, **4B total / ~3B
  non-embedding**, and by far the smallest thing on this list — a **looped transformer**: a 22-layer
  stack run twice with *shared* weights, so it does 44 layers of compute at 22 layers of memory.
  Pretrained from scratch on 28T tokens and post-trained for agents. **SWE-bench Verified 63.6%** —
  beating Qwen3.5-9B and Gemma4-12B, and within ~6 points of the 35B-A3B-derived KAT-Coder above at
  roughly a *tenth* the weights. 262,144 context; tool-calling supported (XML format recommended —
  **check Hermes' parser accepts that shape before a run**, it is the likeliest silent failure);
  configurable thinking mode, so record which was used. **~2–3 GB at 4-bit.** Serving is unblocked on
  both backends with **no arch gate-probe needed**: llama.cpp and Ollama are supported upstream, a
  bartowski GGUF ships, and — unusually for a new arch — an **`mlx-community/Nanbeige4.2-3B-OptiQ-4bit`
  quant already exists**, so oMLX is a straight load. **Two distinct reasons to want it:** (1) it is
  the first candidate small enough that the *whole* 64GB stays free, which makes it the natural
  **draft model** for the §3 speculative-decoding/MTP lever — the top speed lever, currently blocked
  on not having one; (2) as a subject in its own right it probes the far end of the size axis, where
  every local result so far sits at 27B–80B. Cheap to run and fast, so it costs little to find out.
  Released 2026-07-27; technical report arXiv:2607.22083.
  Source: https://arxiv.org/html/2607.22083
  — weights: https://huggingface.co/Nanbeige/Nanbeige4.2-3B
  — MLX 4-bit: https://huggingface.co/mlx-community/Nanbeige4.2-3B-OptiQ-4bit

- 2026-08-08 — **Devstral Small 2 / `Devstral-Small-2-24B-Instruct-2512` (Mistral)** — *the successor
  to the already-covered `Devstral-Small-2507`, and a different model, not a re-release.* Apache 2.0
  **24B dense**, 262K context, multimodal (image inputs), built with All Hands AI explicitly for
  code agents — exploring codebases, multi-file edits, tool-driven SWE loops. **SWE-bench Verified
  68.0%** (its 123B sibling Devstral 2 hits 72.2% but is far too large here). **Q4 ≈ 14 GB → fits
  64GB with enormous headroom**, the second-smallest entry on this list after Nanbeige. **Serving is
  the least-blocked of any candidate here:** Mistral arch + tool parser are mainline llama.cpp (the
  §"Serving backends" note already records that llamacpp *unblocks Devstral*), GGUFs ship from
  ggml-org / bartowski / unsloth / lmstudio-community, **and an `mlx-community/…-2512-4bit` exists**
  — so both retort backends are live paths. **Two caveats, both material:** (1) the mlx-community
  4-bit has an open discussion reporting a **tokenizer bug producing gibberish** — smoke-test its
  output *and* its `<tool_call>` formatting before trusting any number, or serve via llamacpp
  instead (a garbled tool call scores an indistinguishable false zero); (2) this is a **2025-12-09
  release, older than every gap entry already on this list** — it surfaced via current local-coding
  roundups that still call it the strongest non-Qwen local coder, so it is a gap here rather than
  news. Judge priority accordingly: below KAT-Coder and North Mini Code. **Why it still earns a
  slot:** every other entry on this list is a Qwen derivative or an MoE; this is the only *dense*,
  *Mistral-lineage*, coder-specialised candidate, which makes it the cleanest partner for the
  §3 **MoE-vs-dense** question — and §3 already notes the earlier Devstral attempt failed on the
  *wrong harness*, not the model, so this is unfinished business rather than a new idea.
  Source: https://mistral.ai/news/devstral-2-vibe-cli/
  — weights: https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512
  — GGUF: https://huggingface.co/bartowski/mistralai_Devstral-Small-2-24B-Instruct-2512-GGUF
  — MLX 4-bit: https://huggingface.co/mlx-community/Devstral-Small-2-24B-Instruct-2512-4bit

- 2026-08-09 — **Qwen3.8-27B (Alibaba)** — **ANNOUNCED, WEIGHTS NOT YET PUBLISHED — do not schedule
  a run yet; re-check after 2026-08-10.** Listed here because it *corrects a standing note in this
  file*: the exclusion block below records Qwen3.8 as closed-weight, and that is now out of date.
  Alibaba announced Qwen3.8-Max (2.4T MoE) on **2026-08-03** and committed to publishing open weights
  for **both** Max and a new **Qwen3.8-27B** during the week of **2026-08-10**, on Hugging Face and
  ModelScope — the first time a Max-class Qwen goes open. The Max is hopelessly oversized here
  (~1.2 TB at 4-bit); the **27B is the entry that matters**, as the direct successor to the
  already-listed Qwen3.6-27B candidate and pitched at "Coding and Cowork". Third-party quant plans
  put it at **~17 GB at 4-bit → fits 64GB with enormous headroom**, consistent with a 27B-class model
  (predecessor is dense; 3.8's architecture is **not yet disclosed**). **Nothing else is confirmed
  yet** — no license (Qwen3.6-27B was Apache 2.0, but Alibaba has not named one for the 3.8 open
  releases), no context length, no tool-calling/agentic spec, no benchmarks, and **no HF repo**: the
  only Qwen3.8-27B repos that exist today are reserved placeholders that say so on the card
  (`huginnfork/Qwen3.8-27B-FP8`: "there are no weights in this repository yet"). **Why it is worth a
  slot the moment weights land:** it would be the *third* matched-base probe on this list — the same
  27B size class as the Qwen3.6-27B and BTL-3 entries above, but with a **generation change** rather
  than post-training as the variable, which is the one comparison KAT-Coder and BTL-3 cannot make.
  Verify at drop: license, dense-vs-MoE, that the arch is in mainline llama.cpp / oMLX (a new
  generation is exactly where a Laguna-style arch gate appears), and tool-call formatting.
  Source: https://www.latent.space/p/ainews-qwen-38-max24t-and-27b-new
  — specs/status roundup: https://www.yottalabs.ai/post/qwen-3-8-27b-specs-hardware-requirements-how-to-run-2026

- 2026-08-11 — **Muse Glimmer 30B (Meta Superintelligence Labs)** — *the first genuinely
  last-cycle drop this list has seen in a while: weights published **2026-08-10**, yesterday.*
  Apache 2.0, **30B dense** (a 28B text decoder + a 2B perception encoder — it is multimodal, and the
  vision half is dead weight for retort's text-only tasks), **131,072 default context, 262,144 max**
  — the same window as our 35B/80B runs. Distilled from Meta's larger **Muse Spark** by logit
  distillation in pre-training, then mid-trained on longer contexts and agent-heavy data, then
  post-trained with SFT + on-policy distillation + RL — i.e. it is *built* for agent loops rather than
  scoring well on them incidentally. Explicitly pitched at multi-step reasoning, **reliable tool use
  with precise schemas over extended workflows**, and *failure recovery*. **MCP Atlas 75.5** vs
  Gemma4-31B 54.2 and Qwen3.6-27B 62.5 — both of which are candidates already on this list, so it
  arrives with a direct head-to-head against two entries here; **SWE-bench Pro 51.2**. **~17 GB at
  4-bit (under 20 GB), fits 64GB with enormous headroom.**
  **Serving is unblocked on both backends and needs no Laguna-style arch gate-probe** — Meta shipped
  optimized llama.cpp, MLX and ExecuTorch integrations at launch, official GGUFs
  (`muse-glimmer-30B-kquant-17gb.gguf`) plus unsloth UD-Q2…Q8 builds, an Ollama entry, and an
  `mlx-community` 4-bit.
  **Three caveats, and the first is a live false-zero trap of exactly the kind CLAUDE.md exists for:**
  (1) **do NOT use the `meta-models` oQ4e MLX checkpoint** — it was quantized with oMLX v0.5.8.dev1,
  before the embed-norm fix (mlx-vlm#1839, landed in 0.5.8.dev3), and it **emits no function calls at
  all** (it plans the call, then `</think>` → `<|eot|>`) while decoding at 9–12 tok/s instead of 38.
  A retort cell on that checkpoint would score a clean, plausible zero with nothing in the archive
  saying why. Use **`mlx-community/Muse-Glimmer-30B-4bit`** on **oMLX ≥ 0.5.8.dev3**, and smoke-test a
  real `<tool_call>` before the grid. (2) Meta's **default sampling is temperature 1.0** / top_p 0.95 /
  top_k 64 — the precise unrecorded default that cost this project half its local reliability; set and
  verify it. (3) It has **configurable reasoning effort (low/medium/high/xhigh)** — record which was
  used, like KAT-Coder's thinking mode. **Why it earns a high slot:** it is the first **Meta-lineage**
  local candidate, and the first *distilled-from-a-frontier-sibling* one — a different axis from every
  entry above, which are all either Qwen derivatives, post-training probes on a shared base, or
  other-lineage from-scratch models. It is also a 30B dense at the same size class as the Qwen3.6-27B
  / Gemma 4 / BTL-3 entries, so it slots straight into the §3 MoE-vs-dense question with published
  head-to-heads against two of them already in hand.
  Source: https://research.meta.ai/blog/introducing-muse-glimmer-open-agentic-model
  — via: https://thenewstack.io/meta-glimmer-distillation-agents/ (user, 2026-08-11)
  — weights: https://huggingface.co/meta-models/Muse-Glimmer-30B
  — MLX 4-bit: https://huggingface.co/mlx-community/Muse-Glimmer-30B-4bit
  — GGUF: https://huggingface.co/unsloth/Muse-Glimmer-30B-GGUF
  — the broken-quant issue: https://github.com/jundot/omlx/issues/2589

- 2026-08-11 — **NVIDIA Nemotron 3.5 Lightning / `NVIDIA-Nemotron-3.5-Lightning-30B-A3B`** — *weights
  published **2026-08-11**, today; and the only candidate this list has ever seen that NVIDIA says was
  **trained for the Hermes Agent harness** — retort's exact agent.* **OpenMDW-1.1** ("fully open —
  weights, data, and recipes"), **30B total / 3B active hybrid MoE**: interleaved **Mamba-2 + MoE**
  layers with select Attention layers, **1M context** (four times the 262K our 35B/80B runs use).
  Pitched at always-on agents doing high-volume specialized tasks: **up to 4× the output speed of
  similar-sized models**, and **PinchBench 86% while completing 10,000 tasks 30% faster than
  Qwen3.6-35B** — i.e. NVIDIA's own headline comparison is against **the exact model in our
  hermes-lcm+35B stack**, at matching accuracy. Tool-calling is native and, usefully, the deployment
  docs specify the **`qwen3_coder` tool-call parser** — the same parser family our 35B/80B cells
  already run through. **~17 GB at 4-bit → fits 64GB with enormous headroom** (NVIDIA's own checkpoint
  is **NVFP4**, W4A16 weights / FP8 activations; a BF16 checkpoint also ships).
  **Serving is the whole risk here, and it is a Laguna-class gate — probe before scheduling anything.**
  NVFP4 is a Blackwell/Hopper CUDA format and is **not servable on this Mac**, so a run needs either a
  community GGUF or an MLX convert from BF16, and **neither exists yet**. Worse, the arch is
  `nemotron-h`-MoE, and mainline llama.cpp has an **open, unresolved loading bug on the sibling
  `Nemotron-3-Nano-30B-A3B`** — `GGML_ASSERT(d_inner % (n_group*n_embd) == 0)` at
  `mamba-base.cpp:173`, filed 2026-03-15 and still `bug-unconfirmed` with no linked PR. That is the
  same "arch unmerged upstream" blocker that stopped Laguna XS 2.1, and it means the **already-listed
  Nemotron-Cascade-2-30B-A3B entry above shares this gate** — one probe settles both. Confirm oMLX
  handles interleaved Mamba-2 + MoE, or that a working GGUF lands, before committing a cell.
  **Two further caveats:** (1) NVIDIA's recommended sampling is **temperature 1.0 / top_p 0.95** —
  precisely the unrecorded default that cost this project half its local reliability; set and verify
  it per CLAUDE.md rather than inheriting it. (2) The headline speed numbers are NVIDIA's own, on
  NVIDIA GPUs at NVFP4; nothing about 4× transfers to oMLX/Metal at 4-bit, so treat throughput as
  unmeasured here. **Why it earns a high slot anyway:** it is the first candidate whose *vendor*
  targeted our agent harness, its headline benchmark is a direct head-to-head with our incumbent 35B,
  and a **`…-30B-A3B-DSpark` speculative-decoding variant ships alongside it** — which makes it the
  only entry that arrives with a matched draft model in hand, feeding §3's speculative-decoding/MTP
  lever, the top speed lever and currently blocked on exactly that.
  Source: https://developer.nvidia.com/blog/nvidia-nemotron-3-5-lightning-delivers-fast-accurate-specialized-task-execution-for-long-running-agents/
  — via: https://thenewstack.io/nvidia-nemotron-lightning-switchyard/ (user, 2026-08-11)
  — weights (NVFP4): https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4
  — the llama.cpp hybrid-Mamba blocker: https://github.com/ggml-org/llama.cpp/issues/20570

  *(**NeMo Switchyard**, announced in the same release, is **not a model** — it is an open-source
  routing library that picks a model per request mid-task, claiming frontier-level completion at ~⅓
  the cost of Opus 4.8 alone. It is out of scope for this candidate list, but it is a
  `harness_config`-level idea and belongs next to the §"harness maturity" side-branch above if
  cloud-orchestration work resumes. Source:
  https://blogs.nvidia.com/blog/nemotron-lightning-switchyard-rtx-dgx/)*

*Excluded this scan as too large for 64GB at 4-bit, recorded so they are not re-investigated:*
Kimi K3 (2.8T MoE, 2026-07-27), Inkling-Small (276B-A12B, 2026-08-02 — ~140 GB at 4-bit despite the
"Small" name; its parent Inkling is 975B-A41B), Tencent Hy3 (295B-A21B, 2026-07-06), and Mistral
Leanstral 1.5 (119B-A6B, 2026-07-02 — borderline on size *and* a Lean 4 theorem-prover, not an
agentic coder).

*Also excluded 2026-08-07, same reason:* **DeepSeek-V4-Flash-0731** (284B-A13B, MIT, 2026-07-31 —
~142 GB at 4-bit; its post-training update is explicitly coding/agent-targeted, so it is a shame
rather than an oversight), **Solar Open 2** (Upstage, 250B-A15B, 2026-07-23 — ~125 GB), **Motif-3-Beta**
(314B-A13B, 2026-07 — ~157 GB), and **Laguna S 2.1** (118B-A8B — ~60 GB, borderline *and* the `laguna`
arch is still unmerged upstream, the same blocker that stopped Laguna XS 2.1). Also excluded as
out-of-scope rather than oversized: **Qwen3.7 Flash** and **Qwen3.8 Max** (Alibaba, 2026-07-27 /
2026-08-02) are **closed weights** — Qwen's last open general-purpose release remains Qwen3.6-27B —
and **Antares 1B** (2026-07, security-specialised, not an agentic coder).

*Also excluded 2026-08-08:* **Ling-3.0-flash** (inclusionAI / Ant Group, announced 2026-07-23) —
124B-A5.1B hybrid-linear-attention MoE, coding-targeted, 256K native context, and the only genuinely
last-cycle open-weight coding release this scan found. **~62 GB at 4-bit leaves no room for context
or KV cache on a 64GB box** — the same borderline-oversize call as Laguna S 2.1 above. Weights were
also gated behind a free-API window through 2026-08-03 rather than published at announcement.
Re-open only if a sub-4-bit build with intact tool-calling appears. Source:
https://huggingface.co/inclusionAI/Ling-3.0-flash

*Also excluded 2026-08-09, out-of-scope rather than oversized:* **MiniMax H3 / Hailuo 3.0** (weights
published 2026-08-03, 33B dense and small enough to fit) — it is an **omni-modal video generation
model** (text/image/audio → 4–15 s clips), not a coding LLM, and its licence excludes several
jurisdictions. **Kimi K3** (Moonshot, weights 2026-07-27) is already recorded as oversized above;
noted again only because it dominated this cycle's coverage — ~1.4 TB of MXFP4 weights.
**Soofi S 30B-A3B** (2026-07-15) fits at 4-bit but is a German/English **base** foundation model with
no agentic-coding post-training, so it fails the coding-candidate bar rather than the size bar.

### Swiftlet — a third serving backend (expert streaming), NOT a model  — BUILT, NOT YET SMOKE-TESTED

Added 2026-08-03 (user). [github.com/leonickson1/Swiftlet](https://github.com/leonickson1/Swiftlet) —
Apache 2.0 Swift + Metal runtime that keeps only a small dense core resident and **streams routed MoE
experts from SSD on demand** (`.qpack` containers, fixed-stride expert packing, LFU+recency
eviction). It serves the two models we already benchmark, at **2.6 GB peak RAM (35B) / 4.3 GB peak
RAM (80B)** — 18 GB / 42 GB on *disk*. So it is a `serving.backend` level, not a candidate model:
it belongs next to `omlx`/`llamacpp`, and its real relevance is to the §3 inference-lever sweep.

**BUILT 2026-08-03 (`serving.backend: swiftlet`).** `SwiftletStackManager` in
[`stack_reload.py`](../src/retort/playpen/stack_reload.py) launches `swiftlet-server` on an internal
port and puts the new [`swiftlet_shim.py`](../src/retort/playpen/swiftlet_shim.py) on the public one
to translate tool calls in both directions. 25 unit tests, all offline (no binary, no weights); full
suite 887 passed. `cache_gb` is in the reload signature so a cache sweep actually restarts the
server, and a preset declaring `sampling:` now **raises** rather than running at Swiftlet's built-in
0.7/0.8 behind a provenance record claiming otherwise. See [`docs/configuration.md`](configuration.md).

**WHAT IS NOT VERIFIED — do not treat the backend as working yet.** Everything above is plumbing
tested against a *stub* upstream. Nothing has talked to a real `swiftlet-server`, because that needs
the Swift toolchain build plus an 18–42 GB qpack download. Specifically unverified: (a) that a real
Qwen3.6/Qwen3-Next emits `<tool_call>` reliably when the tools block arrives as *system text* rather
than through its native template — this is the fidelity gap and the likeliest failure; (b) the exact
`swiftlet-server` stderr log format `peak_prompt_tokens` parses; (c) whether the shim's max-tokens
default is enough for an agent turn; (d) end-to-end tok/s on this box. **Per CLAUDE.md this is a
set-but-unverified parameter set — run the staged probe below before any grid.**

**Discovered while building, and it changes the cache story:** `Sources/SwiftletServer/main.swift`
constructs a **`QwenCPUModel`** with `retainAllLayers = true` — the *CPU* path. The Metal expert
cache (`QwenMetalModel(modelDir:cacheBudgetGB:)`) and `--cache-gb` exist **only on the `swiftlet` CLI's
`--gpu` path**, not the server. So the cache sweep described below cannot be run through the OpenAI
endpoint until the server is taught to use the Metal model — a small upstream change, and the second
thing to fix after tool calls. retort emits `--cache-gb` already so it works the moment it lands.

**ORIGINAL BLOCKER (what the shim exists to work around).** `Sources/SwiftletServer/main.swift`
is 210 lines: it exposes OpenAI chat-completions on loopback, never parses a `tools` array, and only
ever emits `finish_reason: "stop"` — there is no `tool_calls` path at all. Hermes drives its agentic
loop on OpenAI-format `tool_calls` (that is exactly what we verified oMLX emits for the 80B), so a
retort cell on Swiftlet **as it ships today would produce no code and score a false zero**,
indistinguishable from an incapable model — the failure mode CLAUDE.md's "suspect the harness before
the model" rule exists for. Worse than first assessed: `Message.content` is a non-optional `String`,
so the `{"role": "assistant", "content": null, "tool_calls": […]}` turn Hermes replays after every
tool call does not merely lose information, it **fails to decode and 400s the whole request**. The
shim normalises that too.

**Speed — the reason to be sceptical, quantified.** Swiftlet's own README claims **7–11 tok/s (35B)**
and **4.5–5 tok/s (80B)** on "an M5 Mac". This box is an **M5 Pro / 64 GB**, so those are directly
comparable numbers rather than an extrapolation. Against retort's *measured* oMLX throughput —
**~54 tok/s (35B, exp-25/26)** and **~61 tok/s (80B, exp-24)** — that is **5–8× slower on the 35B and
~12× slower on the 80B**. exp-25/26 established these runs are **generation-bound**, and that at
54 tok/s the timeout had to go 30 → 60 min before Go converted from all-zeros to 0.92 req_cov. Scale
that: **~5–8 h/cell for the 35B and ~6–13 h/cell for the 80B**, before replicates. At n=3 across a
few languages, on a machine that runs one experiment at a time, a Swiftlet grid is days-to-weeks.
**Do not put Swiftlet on the critical path for any headline result.** (Note the README says the
decode loop is *dispatch* bound, not IO bound — so the gap is an optimization gap, not a fundamental
SSD limit. Worth re-timing later rather than dismissing permanently.)

**Why it is still worth a probe — RAM stops being the constraint on model SIZE.** That, not faster
35B/80B inference, is the prize:
1. It would un-exclude the models recorded as too large just above — **Hy3 (295B-A21B)** and
   **Inkling-Small (276B-A12B)** — which are otherwise unreachable here at *any* speed. Swiftlet's
   own `assets/model-configs/` already ships a **`qwen3.5-397b.json`**, i.e. the approach targets
   models ~6× larger than this box fits.
2. It frees ~60 GB for a **large draft model**, feeding §3's speculative-decoding/MTP lever — the
   top speed lever, and the one that could pay back Swiftlet's own slowness.
3. `assets/model-configs/qwen3-next-80b-mlx4bit.json` shows the repacker accepts **MLX 4-bit input**,
   so it can repack the exact `mlx-community--Qwen3-Coder-Next-4bit` weights already on disk — a
   genuinely matched-weights backend comparison with only the serving layer varying.

**CORRECTION (2026-08-03, user) — 2.6/4.3 GB is the iPhone floor, not the design point, and the
cache size is the interesting factor.** `SwiftletCLI` takes **`--cache-gb`, defaulting to 8**, and
`ExpertCache.init(budgetBytes:)` sizes slots as `min(max(budget/stride, 16), total)` — capped at the
*whole model*, so at a large enough budget the expert cache holds everything and **streaming stops
happening at all**. Against 18 GB (35B) / 42 GB (80B) of qpack on disk that means: 24 GB M4 → ~12–14
GB cache (35B ~75% resident); **32 GB M1 Max → ~20–22 GB, the entire 35B resident**; 64 GB M5 Pro →
the entire 80B resident. So the published 7–11 / 4.5–5 tok/s are numbers at *some small cache*, not
a ceiling, and the speed claim above should be treated as unmeasured at our configuration.

**The measurement this makes cheap — and it is already instrumented.** `swiftlet` prints
`expert cache: N slots (X GB), H hits / M misses (P% hit rate)` after every run. So sweep
`--cache-gb` and watch whether tok/s tracks hit rate: if throughput stays flat as hit rate → 100%,
decode is **dispatch-bound** (as Swiftlet's own README claims) and no amount of RAM rescues it — the
fix would be batching expert matmuls, not caching. If throughput scales with hit rate, it was
IO-bound and the big-cache configuration is simply the right way to run it. **This is a textbook
`cache_gb` inference-lever factor with hit rate as a mediator response** — it belongs in §3
alongside quant level, and it is a ~10-minute smoke test, not an experiment. Note the README's
dispatch-bound claim predicts the pessimistic outcome; test it anyway, the counters are free.

**Sampling defaults differ from ours — record them.** `SwiftletSession` hardcodes temperature 0.7 /
top-p 0.8 for quantized non-thinking chat, and *bans EOS until a minimum length* (a guard against
quantized models stopping after 1–2 tokens). There is a `--greedy` flag. Per CLAUDE.md this is
exactly the set-but-unverified footgun that cost us the temp-1.0 result — pin and verify sampling
before comparing any Swiftlet number to an oMLX one.

**Tool calling is a smaller fix than it first looked.** `SwiftletSession` already calls
`tokenizer.applyChatTemplate(messages:)` — the model's real Jinja template — and already handles the
Qwen3.6-thinking vs Qwen3-Next-Instruct template split and `<think>` suppression. Qwen's own template
takes a `tools` argument and makes the model emit `<tool_call>{"name":…,"arguments":…}</tool_call>`.
So the work is: pass `tools` through to the template, parse those tags out of the generated text, and
emit OpenAI `tool_calls` with `finish_reason: "tool_calls"` instead of `"stop"`. That is the one
change that unlocks Swiftlet for Hermes.

**Verify before trusting a comparison:** the published qpack is named `Qwen3-Next-80B-A3B-qpack`. If
that is the *non-Coder* Qwen3-Next-80B, benchmarking it against our Qwen3-Coder-Next-80B numbers
confounds serving backend with model. **Repack our own weights rather than downloading theirs.**

**Staged probe (~1 h, do not skip to a grid) — the backend is built, so this is now a verification
sequence, in order:**
1. Build the Swiftlet checkout; fetch or repack a 35B qpack (repack *our* MLX 4-bit weights, per the
   confound above, rather than downloading theirs).
2. `swiftlet-server` up, then `retort`'s shim in front of it: POST a chat-completion **carrying a
   `tools` array** and confirm a real `<tool_call>` comes back and the shim converts it. This is the
   one that decides whether the whole backend is viable — the tools block reaches the model as system
   text, not through its native template.
3. Check the stderr log lines actually match `_SWIFTLET_PROMPT_RE`, else `peak_prompt_tokens` returns
   None and the context telemetry silently goes blank.
4. One full agentic cell on the CRUD task at a generous timeout, then `retort diagnose` on the result
   — confirm any zero is GENUINE, not TOOLING.
5. Only then the `cache_gb` sweep — and only after the server is switched to `QwenMetalModel`, since
   on the stock CPU-path binary the flag does nothing.

Steps 2–5 produce wall-clock numbers, so per CLAUDE.md they need the machine to themselves.

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
