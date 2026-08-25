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

## M3. Make the test suite fast  — 226.6s → 80s (2026-08-22), 20s short of the bar

**Measured 2026-08-17: `pytest tests/unit` takes 226.6 s.** That is slow enough that it stops being
run between edits, which is how a suite stops protecting anything. **Now 80 s** — same tests, none
removed, suite green. The 60 s done-criteria is not met; what remains is described at the end.

### The 53 s test was spending money, not just time

M3 said to explain it before optimising it, and the explanation is worse than slow. The test patched
`retort.cli._invoke_claude_skill` and `_invoke_claude_skill_prompt`. `_run_auto_evaluation` calls
neither — it calls `_invoke_judge_prompt`. Both stubs did nothing, the real function ran, and it
shelled out to a live judge. Proved by recording every subprocess the test launches:

```
35.38s  claude -p Follow skill at /private/var/.../pytest-851/test_auto_...
```

A real Claude invocation, **billed to whoever ran `pytest tests/unit`**, on every run, for weeks. The
53 s → 58.8 s "growth" was judge latency, nothing more. Nothing ever failed, because a stub that
silently stops matching the code it stubs is invisible — it surfaces only as a number in
`--durations` that nobody reads.

Fixed by patching the function actually called, and **guarded**: an autouse fixture in
`tests/conftest.py` fails any test that launches `claude`/`codex`/`gemini`/`opencode`/`hermes`/`omp`,
naming the command; integration tests opt out with `@pytest.mark.allow_billed_cli`.
`tests/unit/test_billed_cli_guard.py` pins the guard itself.

### One venv per session instead of one per test

`ensure_python_env` builds a throwaway venv per call and pip-installs the project's inferred imports.
`test_scoring.py` was creating eleven, and `successful_artifacts` writes `from fastapi import
FastAPI` — so four tests asserting metric *names and ranges* were each paying a real `pip install
fastapi`. A session-scoped venv is now built once and reused via a `venv` symlink.

**Deliberately not applied to `TestPythonEnvPreparation`:** the reuse path skips dependency
inference, which is the thing those tests exercise — sharing there would have made them pass without
testing anything. And deliberately not applied in production: one shared venv across projects would
let a project that forgot to declare a dependency pass on a neighbour's install.

### What is left, and why 60 s is not free

| remaining | cost | notes |
|---|---:|---|
| `test_runner.py` | ~24 s | many small real-toolchain provisions |
| `TestPythonEnvPreparation` | ~15 s | irreducible — it tests venv building **by building venvs** |
| `test_quiet_pytest_project_is_not_false_failed` | 7.4 s | runs a real pytest suite; that is the point of it |
| `test_no_regression_actually_runs_python_suite` | 5.1 s | same |

Closing the last 20 s means either sharing fixtures inside `test_runner.py`, or M3's option 3 —
marking the genuine integration tests and excluding them by default. **Option 3 does not satisfy this
entry's own done-criteria** ("under 60 s *with the same number of behaviours covered*"), so it needs
a deliberate decision rather than a quiet default change.

**The original profile (2026-08-17), for the record:**

| test | time | share |
|---|---:|---:|
| `test_evaluation.py::test_auto_evaluation_swallows_skill_failure` | **53.3 s** | 23% |
| `test_scoring.py::TestScoreCollector::test_collect_all_metrics` | **21.3 s** | 9% |

**The 53 s one is a SMELL, not just a slow test.** It patches both `_invoke_claude_skill` and
`_invoke_claude_skill_prompt` and still takes 53 seconds — so the time is going somewhere that is
NOT the path it thinks it is stubbing. Find out where before optimising it: either the test is
exercising a real subprocess/timeout nobody intended, or `_run_auto_evaluation` has a slow branch
that no one has looked at. Both are worth knowing independently of speed. Do not simply add a mock
until the 53 seconds is explained.

**`test_scoring.py` dominates the rest** — 10 of the 12 slowest tests, 108 test functions, most
shelling out to a real toolchain (pytest, go, npm) inside a temp project. Options, cheapest first:
1. **Share fixtures.** Many build a near-identical throwaway project per test; a session-scoped
   fixture per language would cut most of the repetition. Check they do not mutate it.
2. **Collapse the repetitive ones.** `TestPythonEnvPreparation` and `TestTestQualityScorer` each
   have several tests differing only in a fixture detail — parametrize.
3. **Mark the genuinely-integration ones** `@pytest.mark.slow` and default to excluding them, with
   CI running the full set. Keep the fast/slow split honest: a test that shells out to `go build` is
   not a unit test, and pretending otherwise is why the suite got here.

**What NOT to delete.** The recent additions are deliberately behaviour-pinning and cheap —
`test_go_entrypoint`, `test_factual_accuracy`, `test_promotion_*`, `test_pass_definition` are all
sub-second and each pins a bug that shipped. Low-value means *asserts a fixture's shape* or
*duplicates another test*, not *recently added*. The exact-list registry assertions were already
removed for exactly that reason (they were change-detectors that broke twice in a week while the
code was correct).

**Done-criteria:** `pytest tests/unit` under 60 s with the same number of behaviours covered, and no
test that patches a path and then spends its time somewhere else.

---


## 0. exp-62 — does Hermes 0.20.5's verify-on-stop change local pass rates?  — PLANNED

exp-61 established that Hermes 0.20.5 is a null against 0.18.2 on coverage, maintainability and
duration. It deliberately left one thing untested: 0.20.5 ships a real self-verification subsystem
(`agent/verify/` — recipes, runner, environment; ported from grok-cli) that detects a project's run
recipe, boots it, and proves it serves HTTP. Our config sets `agent.verify_on_stop: false`, so none
of exp-61 exercised it.

That is a **capability** change, not version drift, which is why it was held back — mixing it into
exp-61 would have produced a delta nobody could attribute.

**Hypothesis.** Verify-on-stop converts near-misses, so it should move the cells with headroom and do
nothing to cells already at ceiling. The natural targets are the ones exp-61 could not speak to:
rust (0.94 baseline, the standing near-miss language) and brazil-go (0.89, the only cell that is both
instrumented and off-ceiling).

**Design.** One variable: `agent.verify_on_stop` true vs false, both arms on 0.20.5.

**Harness gap — CLOSED 2026-08-25 (`0704f58f`).** The entry flagged that both arms share one
`serving.hermes_config` and the second would inherit the first. The mechanism turned out to be
`stack_reload.ensure()`: it early-returns when `_sig(preset)` is unchanged, and `_sig` covered
model/gguf/qpack/cache_gb/context_length/sampling but **nothing about the agent** — so two presets
differing only in `verify_on_stop` were indistinguishable, the reload was skipped, and arm B would
have run on arm A's config while reporting itself as arm B. Exactly the bug `cache_gb` was added to
`_sig` to fix, per that function's own docstring.

A preset can now carry a `hermes:` block of agent-config overrides; they are part of the reload
signature, are written into the config last, and land in `stack.json` so the effective value is
recorded. Per-arm `HERMES_HOME` is no longer needed. Two arms therefore look like:

```yaml
presets:
  m80-verify-off:
    model: mlx-community--Qwen3-Coder-Next-4bit
    context_length: 262144
    hermes: { verify_on_stop: false }
  m80-verify-on:
    model: mlx-community--Qwen3-Coder-Next-4bit
    context_length: 262144
    hermes: { verify_on_stop: true }
```

### Timeout must be raised for the grid — the confound is DIRECTIONAL (2026-08-25)

Measured across hermes/bookshop runs in master.db before launching the grid:

| language | n | min | avg | max |
|---|---:|---:|---:|---:|
| rust | 35 | 0.4 | **20.9 min** | **60.0 min** |
| go | 79 | 0.8 | 8.9 | 32.3 |
| python | 112 | 0.4 | 5.8 | 20.7 |

Rust's max is *exactly* 60.0 — the `timeout_minutes: 60` ceiling, i.e. a truncation, not a
completion. Only 1 of 35 (3%) actually hits it, so rust is genuinely slow rather than mass-truncated,
and ~21 min/cell makes a 6-cell grid roughly 3 hours with judge and second chances.

**But the exposure is not symmetric between the arms.** Verify-on-stop works by INJECTING a synthetic
follow-up turn, so the ON arm is systematically longer and therefore likelier to be truncated. A
truncated ON cell would score worse for running out of clock rather than for failing the task — the
experiment would measure the timeout and report it as the capability. `timeout_minutes` is therefore
raised to 90 for the grid so neither arm can be cut off. Both arms share the value, so internal
validity is unaffected; only cross-experiment duration comparisons need the note.

### The TURN cap binds too, and binds asymmetrically (2026-08-25)

Smoke arm A burned **204 turns against the 200 cap**. Python on this same stack averages 17 (max 44,
n=12) — rust is an order of magnitude more turn-hungry, and no rust turn baseline existed because the
column only populates from exp-49 onward.

Verify-on-stop works by injecting turns, so the ON arm reaches the ceiling sooner than the OFF arm
and loses real work the comparator keeps. That is the same directional confound as the timeout, so it
gets the same fix: `max_turns` raised to 400 for the grid, high enough that neither arm can reach it.
exp-39 is the precedent — three brazil runs stopped at exactly 90 api_calls and the cap, not the
model, was the thing being measured.

### Smoke-test pass criterion, fixed BEFORE the results (2026-08-25)

Traced how Hermes consumes the setting, so the smoke has a defined discriminator rather than a
post-hoc judgement:

- `agent/verification_stop.py::verify_on_stop_enabled()` reads `agent.verify_on_stop`, and an
  explicit bool forces the behaviour in either direction.
- When enabled, `build_verify_on_stop_nudge()` injects a synthetic follow-up turn whose text contains
  **`Run the relevant verification command now (`**. That string is the fingerprint.

**PASS = the string appears in the verify-ON arm's agent log and NOT in the verify-OFF arm's.** A
turn-count delta alone is not sufficient: turns move for unrelated reasons, and exp-61 showed
within-cell spread dominating on exactly this stack.

Three hazards checked and cleared while tracing:

| hazard | status |
|---|---|
| `HERMES_VERIFY_ON_STOP` env var **overrides the config entirely** | not set in the shell, profiles, or anywhere retort sets — config governs |
| migration v31 rewrites `verify_on_stop` | only touches `None`/`"auto"`; an explicit bool is preserved |
| migration v32 flips a literal `true` **to false** | version-gated and already past — live config is at `_config_version: 33`; v34-38 remain and none reference the key |

That last one would have silently forced arm B to false and produced a confident null.

**Still required before the grid: a smoke test that `verify_on_stop` actually takes effect** — run
one cell per arm and confirm from the agent log that the verify subsystem ran in the `true` arm and
did not in the `false` arm. "I set it" is not "it took effect"; that is the first principle in
CLAUDE.md and this factor is a capability toggle, exactly the kind that has silently no-op'd before.

**Cost note from exp-61.** Budget wall-clock, not agent time. exp-61's two-cell smoke pair took ~50
minutes for ~5 minutes of agent work — the Opus judge pass and the 42 GB stack reload dominate.

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
**Daily scan last completed: 2026-08-23** (scanning for new 64GB-fittable coding models)

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

- 2026-08-13 — **LFM2.5-2.6B (Liquid AI)** — *the smallest entry on this list, and a **borderline
  admit**: agentic and tool-calling native, but explicitly **not** coding-specialised.* Published
  **2026-08-04**, inside this scan's window. **2.69B total** (30 layers: 22 double-gated short-conv
  blocks + 8 GQA — a Liquid hybrid-conv arch, unlike every transformer/Mamba/MoE entry above),
  trained on 34T tokens, **131,072 context**, 128K vocab. **~1.5–2 GB at 4-bit** — it leaves
  essentially the entire 64GB free. Pitched squarely at on-device agents that "plan, call tools and
  work through multi-step tasks", with **day-one llama.cpp / MLX / vLLM / SGLang / ONNX support and
  official GGUF + MLX builds from Liquid themselves** — so **no arch gate-probe is needed on either
  retort backend**, unusually for a new architecture. Fastest thing measured in its class: **220
  tok/s decode on an M5 Max**. **Why it is only a borderline admit, stated plainly:** Liquid's own
  post concedes "larger models keep an edge" on coding, and its **LiveCodeBench v6 is 59.41%** —
  against 88.1% for the already-listed BTL-3 and 80.0% for Gemma 4. It also does **not** ship under
  Apache 2.0 but under Liquid's own **`lfm1.0` open licence** — read it before use rather than
  assuming permissive terms. **Where it could still earn a cell:** the §3 speculative-decoding/MTP
  lever wants a draft model, and this is the smallest, fastest candidate with a first-party MLX
  build. **But do not assume it can serve as one** — speculative decoding requires a draft sharing
  the target's tokenizer/vocabulary, and this is a 128K Liquid vocab, not Qwen's; verify vocab
  compatibility before treating it as a draft for the 35B/80B, or the lever stays blocked regardless.
  As a subject in its own right it is largely dominated by the already-listed **Nanbeige4.2-3B**
  (4B, SWE-bench Verified 63.6%, and an `mlx-community` 4-bit already shipping), which occupies the
  same far-end-of-the-size-axis slot with better coding numbers — so judge priority **below
  Nanbeige** and below every coder-specialised entry. Listed rather than excluded because it is
  genuinely last-cycle, its tool-calling is native rather than inferred, and its serving path is the
  least blocked of anything here.
  Source: https://www.liquid.ai/blog/lfm2-5-2-6b
  — via: https://www.marktechpost.com/2026/08/06/liquid-ai-lfm2-5-2-6b-on-device-agentic-model/
  — weights: https://huggingface.co/LiquidAI/LFM2.5-2.6B
  — GGUF: https://huggingface.co/LiquidAI/LFM2.5-2.6B-GGUF

- 2026-08-14 — **Macaron-V1-Tall (Mind Lab)** — *a third matched-base probe on the exact 35B in our
  stack, and the only one that changes the **serving topology** rather than the post-training recipe.*
  **MIT licence**, **50B total = a frozen `Qwen3.6-35B-A3B` base + four 3.7B LoRA specialists**
  (Chat, Agent, **Coding**, GenUI) under a **Mixture-of-LoRA (MoL)** design, **262,144 context** — the
  same base, same context and same serving path as the hermes-lcm+35B stack already in `master.db`.
  An **L0 router picks one specialist per user turn** and the conversation then stays on that branch;
  the pitch is continual learning (adapters added/updated without retraining the base). Evaluated on
  SWE-Verified, DeepSWE, SWE Atlas QnA and Terminal-Bench 2.1, though **Mind Lab's own write-up names
  coding as the area still needing work** — treat the coding numbers as unproven rather than a
  headline. **~25–28 GB at 4-bit with all four adapters resident (~20–22 GB with only the Coding LoRA
  merged) → fits 64GB with plenty of headroom.**
  **Serving is the real work, and it is the BTL-3 problem one size up.** Upstream ships **vLLM /
  SGLang / Transformers only**, and the L0 routing depends on their *native multi-LoRA* support —
  **neither oMLX nor mainline llama.cpp routes multiple adapters at inference time**. The HF card
  links community quantizations (llama.cpp / Ollama / LM Studio class); **no `mlx-community` 4-bit is
  confirmed**. So a retort cell realistically means `merge_and_unload()`-ing the **Coding** LoRA onto
  the base and converting to 4-bit — recording the merged hash like any other tuning parameter — and
  that **measures the adapter, not the MoL router**, which is the interesting half. Say which was run.
  **Why it earns a slot:** it is the cleanest *architecture-level* variable this list has — same base,
  same context, same serving path as an incumbent result, with **adapter composition** as the change,
  so it pairs with KAT-Coder (post-training on the same 35B) and BTL-3 (a single LoRA on the 27B) to
  ask whether adapters or full post-training buy more. **Caveats:** (1) verify the merged model still
  emits well-formed `<tool_call>` — the card documents "tool use" but no explicit tool-call format, and
  a malformed call scores an indistinguishable false zero; (2) dates disagree — Mind Lab's blog says
  **2026-07-21**, the arXiv paper was submitted **2026-08-11**, so treat it as recent-but-not-fresh;
  (3) its 748B GLM-5.2-based sibling **Macaron-V1-Venti** is hopelessly oversized here — Tall is the
  only variant in scope.
  Source: https://macaron.im/mindlab/research/introducing-macaron-v1
  — paper: https://arxiv.org/abs/2608.09819
  — weights: https://huggingface.co/mindlab-research/Macaron-V1-Tall

- 2026-08-14 — **Mellum2 (JetBrains)** — *a borderline admit like LFM2.5, but it is the only candidate
  here whose vendor documents our **exact tool-call parser**.* Apache 2.0, **12B total / 2.5B active
  MoE** (8 of 64 experts per token, GQA + sliding-window attention, 28 layers), **131,072 context**,
  trained from scratch on natural language and code. **~7 GB at 4-bit** — second-smallest entry after
  LFM2.5/Nanbeige, so essentially the whole 64GB stays free. **vLLM deployment supports tool-calling
  via the `hermes` parser** — the same parser family our 35B/80B cells run through — and it ships an
  **MTP head for speculative decoding**, which is the §3 speed lever directly. **Why it is only
  borderline, stated plainly:** JetBrains positions it as a *focal* model — a fast sub-agent inside a
  larger pipeline, explicitly not a standalone frontier replacement — and the coding numbers say the
  same thing: **LiveCodeBench v6 37.2** against 88.1 for BTL-3 and 59.4 for the already-borderline
  LFM2.5, with **BFCL v3 66.3** on tool use (EvalPlus 78.4 / MultiPL-E 67.1 are healthier, but those
  are single-shot generation, not agent loops). On a retort task it would likely score low as a
  *subject*. **Where it could still earn a cell:** the MTP head plus a 7 GB footprint make it the best
  **draft-model** candidate this list has produced — better-founded than LFM2.5, whose Liquid vocab
  almost certainly cannot pair with the Qwen targets. **Verify vocab/tokenizer compatibility with the
  35B/80B before treating it as a draft**, exactly as for LFM2.5; trained from scratch means its vocab
  is its own, so this is a real gate, not a formality. **Serving caveat:** only vLLM + Transformers are
  documented — **no GGUF, MLX or Ollama build is confirmed**, so both retort backends need a
  gate-probe (or a convert) before a cell, unlike most entries here. **Caveat on freshness: this is a
  2026-06-01 release, not a last-cycle drop** — it surfaced via a current state-of-open-coding-models
  roundup, so it is a gap in this list rather than news. First **JetBrains-lineage** candidate.
  Source: https://www.marktechpost.com/2026/06/02/jetbrains-releases-mellum2-a-12b-moe-model-for-fast-specialized-tasks-in-multi-model-ai-pipelines/
  — via: https://pub.towardsai.net/the-state-of-open-coding-ai-models-in-august-2026-b0858d798bda

- 2026-08-15 — **Qwen3.8-27B — WEIGHTS ARE NOW PUBLISHED (2026-08-14).** *This supersedes the
  2026-08-09 placeholder entry above, which said "ANNOUNCED, WEIGHTS NOT YET PUBLISHED — re-check
  after 2026-08-10"; it is the same model, now actually runnable, not a second candidate.* Alibaba
  published `Qwen/Qwen3.8-27B` on **2026-08-14 (15:00 UTC)** under **Apache 2.0** — the licence the
  placeholder could not confirm — and the other unknowns now resolve as follows. **27B dense, 64
  layers, hybrid attention (Gated DeltaNet + Gated Attention)**, **262,144 native context extensible
  to 1M via YaRN** — the same window as our 35B/80B runs. It is **multimodal** (text/image/video);
  as with Muse Glimmer the vision half is dead weight for retort's text-only tasks. **~17–19 GB at
  4-bit → fits 64GB with enormous headroom** (the BF16 repo is 55.6 GB).
  **The coding numbers are the reason this jumps the queue: Terminal-Bench 2.1 73.0 and SWE-bench Pro
  61.7.** Every coder-specialised entry on this list is far below that on the same benchmarks —
  KAT-Coder 41.02 and North Mini Code 36 on Terminal-Bench, Muse Glimmer 51.2 on SWE-bench Pro — so
  on published figures this is the strongest local candidate the scan has found, and it is a
  *general* model beating the specialists. (Agentic: CoWorkBench 70.7, OSWorld 84.3.) Tool-calling is
  first-class: **developer-role support for agentic harnesses and explicitly improved nested-object
  tool-argument parsing**.
  **Serving looks unblocked on both backends, with one caveat that is a live false-zero trap.**
  `mlx-community/Qwen3.8-27B-4bit` and `-8bit` ship, plus an lmstudio-community MLX 4-bit and unsloth
  GGUFs (Dynamic V3.0 preview, 2-bit → BF16). **But the MLX build was converted with `mlx-vlm` 0.6.8**
  — exactly the class of checkpoint that produced the Muse Glimmer failure two entries up, where a
  VLM-converted quant emitted **no function calls at all** while scoring a clean, plausible zero. Smoke-test
  a real `<tool_call>` on the specific quant before any grid. For `serving.backend: llamacpp`, Gated
  DeltaNet needs **very recent** llama.cpp operators — pin and verify the build.
  **Two more tuning parameters to record per CLAUDE.md:** (1) thinking is **on by default** with a
  `reasoning_effort` knob (`xhigh`/`medium`/`low`/`none`) — record which was used, as for KAT-Coder;
  (2) Qwen's recommended sampling is **temperature 1.0 / top_p 0.95 / top_k 20 in thinking mode**
  (0.7 / 0.80 / 20 for direct) — the precise unrecorded default that cost this project half its local
  reliability. Set and verify it rather than inheriting it.
  **Why it earns the top slot the moment it is smoke-tested:** it is the third matched-size 27B probe
  here, but the only one where the variable is a **generation change** on the same size class rather
  than post-training (the comparison KAT-Coder and BTL-3 structurally cannot make) — and its
  predecessor Qwen3.6-27B is itself still untested, so running both gives that comparison its control.
  Source: https://thenewstack.io/qwen38-27b-local-inference/
  — weights: https://huggingface.co/Qwen/Qwen3.8-27B
  — MLX 4-bit: https://huggingface.co/mlx-community/Qwen3.8-27B-4bit
  — GGUF: https://huggingface.co/unsloth/Qwen3.8-27B-GGUF
  — run/quant notes: https://unsloth.ai/docs/models/qwen3.8

- 2026-08-17 — **Agents-A1 (InternScience)** — *a borderline admit in the Mellum2/LFM2.5 class: a
  35B agentic model that fits easily and speaks our exact tool-call dialect, but coding is explicitly
  **not** what it was post-trained for.* Apache 2.0, **35.11B total / ~3B active MoE** on the
  `qwen3_5_moe` architecture (i.e. a **Qwen3.5** MoE base, *not* the Qwen3.6-35B-A3B our stack serves —
  so it is a sibling-generation lineage, **not** a matched-base probe), **262,144 context** — the same
  window as our 35B/80B runs. Multimodal, with a `--language-model-only` flag that skips the vision
  encoder and saves KV cache (use it; the vision half is dead weight for retort's text-only tasks).
  Trained by three-stage full-domain SFT + **multi-teacher on-policy distillation** across Long-horizon
  Search, Engineering, Scientific Research, Instruction Following and Tool-calling. **~20–22 GB at
  4-bit → fits 64GB with enormous headroom.** The deployment docs specify the **`qwen3_coder` tool-call
  parser** — the same parser family our 35B/80B cells already run through, which is the single strongest
  practical argument for a cell here.
  **Why it is only borderline, stated plainly: it does not report SWE-bench at all.** Its headline
  results are Seal-0 56.4, BrowseComp 75.5, GAIA 96.0, IFBench 80.6 — search, science and
  instruction-following, not repository coding. The one coding-adjacent number is **SciCode 44.33**,
  and the *plain* Qwen3.6-35B-A3B already in `master.db` scores **73.4 SWE-bench Verified**, so on
  published figures there is no reason to expect this to beat our incumbent as a coder.
  **Where it could still earn a cell — and this is the actual reason to list it:** it is the mirror
  image of the KAT-Coder probe. KAT-Coder asks "does *coding* post-training on a 35B-A3B base beat
  general post-training"; Agents-A1 asks the control question — **what does heavy *non-coding* agentic
  post-training do to coding on a comparable base?** A regression here would be as informative as a
  gain, and it is cheap to find out. Judge priority **below every coder-specialised entry** and below
  Nanbeige; run it only once the matched-base probes (KAT-Coder, BTL-3, Macaron) have landed and there
  is something to compare against.
  **Serving caveat, and it is real work:** upstream ships **BF16 safetensors with vLLM / SGLang only** —
  **no GGUF and no `mlx-community` build is confirmed** (HF's quantizations widget lists community
  quants, but sources conflict and none were verifiable at scan time). A cell needs a 4-bit convert, and
  the `qwen3_5_moe` arch plus the multimodal wrapper must be gate-probed on oMLX or mainline llama.cpp
  first — the vision half is exactly where a VLM-converted quant broke tool-calling on Muse Glimmer and
  Qwen3.8-27B above, so smoke-test a real `<tool_call>` on whatever quant is produced before any grid.
  **Caveat on freshness: this is a 2026-06-26 release (a 4B variant followed 2026-07-14), not a
  last-cycle drop** — it surfaced via current agentic-model coverage, so it is a gap in this list rather
  than news. First **InternScience / Shanghai-AI-Lab-lineage** candidate.
  Source: https://internscience.github.io/Agents-A1/
  — paper: https://arxiv.org/pdf/2606.30616
  — weights: https://huggingface.co/InternScience/Agents-A1

- 2026-08-18 — **Granite 4.1 30B (IBM)** — *a borderline admit in the Mellum2/Agents-A1 class, but with
  the **least-blocked serving path of any candidate on this list** and the first **IBM-lineage** entry.*
  Apache 2.0, **30B dense decoder-only** (note: unlike Granite 4.0, the 4.1 language family is *dense*,
  not the hybrid Mamba-2/transformer arch — so it carries **none** of the Nemotron/Laguna-style arch
  gate risk), 128K production context with a 512K extension (unsloth's local guide recommends running
  at **131,072**, the same class as our other candidates). **~17–18 GB at 4-bit → fits 64GB with
  enormous headroom.** IBM's own framing names **tool calling and coding** as core use cases and calls
  the 30B the variant "best for … agentic tool-calling use cases"; **BFCL v3 73.68** on the 30B — the
  highest tool-calling number of any borderline entry here (Mellum2 66.3, Granite's own 8B 68.27).
  **Serving is a straight load on both retort backends, with no gate-probe and no convert:** IBM ships
  **official GGUFs** (`ibm-granite/granite-4.1-30b-GGUF`, plus unsloth builds), the Granite arch is in
  mainline llama.cpp, **and `mlx-community/granite-4.1-30b-4bit` already exists** — the only candidate
  on this list where both backends are confirmed-live with a first-party quant. Its recommended
  sampling is also **temperature 0.0 / top_p 1.0 / top_k 0**, i.e. it is the one entry whose vendor
  default is *not* the temp-1.0 trap that cost this project half its local reliability (record and
  verify it anyway, per CLAUDE.md).
  **Why it is only borderline, stated plainly: there is no agentic-coding evidence.** IBM publishes
  **HumanEval 88.41–89.63 and MBPP 83–85** for the 30B — single-shot generation, not repo work — and
  reports **no SWE-bench, no Terminal-Bench and no LiveCodeBench** at all. It is a *general enterprise*
  family with no coder-specialised variant, and IBM deliberately chose predictable latency over
  reasoning, so these are **non-reasoning** models: on published figures there is no reason to expect it
  to beat the coder-specialised entries above, or our incumbent 35B, as a subject.
  **Caveat on freshness: this is a 2026-04-29 release, older than most gap entries here** — it surfaced
  via current open-weight comparison coverage (Granite 4.1 vs Gemma 4), so it is a gap in this list
  rather than news. Judge priority **below every coder-specialised entry and below Nanbeige**, alongside
  Mellum2 and Agents-A1. **Where it could still earn a cell:** it is the cheapest possible probe on this
  list — nothing to convert, nothing to gate-probe, no thinking-mode or temperature ambiguity — which
  makes it a useful *control* for whether "strong tool-calling + strong HumanEval, zero agentic-coding
  post-training" is enough to pass a retort task, and it adds a fifth vendor lineage (IBM) to a
  candidate pool that is still mostly Qwen derivatives.
  Source: https://research.ibm.com/blog/granite-4-1-ai-foundation-models
  — via: https://www.aimadetools.com/blog/granite-4-1-vs-gemma-4/
  — benchmarks: https://www.creativeainews.com/articles/ibm-granite-4-1-open-llm-512k-context-coding/
  — GGUF (official): https://huggingface.co/ibm-granite/granite-4.1-30b-GGUF
  — MLX 4-bit: https://huggingface.co/mlx-community/granite-4.1-30b-4bit
  — run notes: https://unsloth.ai/docs/models/ibm-granite-4.1

- 2026-08-22 — **Ornith-1.5-35B-A3B (Ornith / DeepReinforce)** — *a genuinely last-cycle drop (weights
  **2026-08-19/20**) with the least-blocked serving path on this list and the strongest published
  agentic-coding numbers of anything that fits 64GB.* **MIT licence**, **35B total / ~3B active MoE on a
  Qwen3.5 MoE base** (`qwen3_5_moe`), **262,144 native context** extensible to ~1M via YaRN — the same
  window as our 35B/80B runs. Third generation of a self-scaffolding RL recipe in which the model
  proposes its own scaffold and then a solution, with reward flowing back to both stages — i.e. the
  harness is *learned*, not fixed, which is an unusual thing to point at a harness-measuring project.
  **SWE-bench Verified 80.1, Terminal-Bench 2.1 74.8** (vendor-reported). Both beat every other entry on
  this list on the same benchmarks — the current leader here, Qwen3.8-27B, reports Terminal-Bench 73.0,
  and the coder-specialised entries are far below (KAT-Coder 41.02, North Mini Code 36). Ornith's own
  card claims it "significantly outperforms Qwen 3.6-35B across all coding and agentic benchmarks" —
  i.e. its headline comparison is against **the exact model in our hermes-lcm+35B stack**.
  **~19–21 GB at 4-bit → fits 64GB with enormous headroom** (the predecessor Ornith-1.0-35B ships a
  21.2 GB Q4_K_M).
  **Serving is a straight load on both backends, with no gate-probe and no convert — the only entry
  besides Granite 4.1 where that is true, and this one is first-party on *both* formats.** Ornith
  published day-one **`ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit`** (plus 6/8-bit) **and**
  `ornith-ai/Ornith-1.5-35B-A3B-GGUF`, with bartowski/AtomicChat mirrors and an APEX-MTP GGUF. Tool
  calling is native, with the **`qwen3_xml` parser (`qwen3_coder` on SGLang)** — the same parser family
  our 35B/80B cells already run through. Usefully, a working first-party MLX build of a `qwen3_5_moe`
  model **also settles the oMLX arch question the Agents-A1 entry above flags** — one load probe covers
  both. **Three caveats.** (1) **The numbers are vendor-reported and at least one independent run
  contradicts them** (DeepSWE 22.0 against a much higher claim) — treat the 80.1/74.8 as a reason to
  run it, not as a result. (2) Two tuning parameters to record per CLAUDE.md: recommended sampling is
  **temperature 0.6 / top_p 0.95 / top_k 20**, but the card says **temperature 1.0 for benchmark
  reproduction** — the precise unrecorded default that cost this project half its local reliability, so
  set and verify one deliberately and say which; and reasoning is on, returned in a separate
  `reasoning_content` field, so record the mode as for KAT-Coder and Qwen3.8-27B. (3) Smoke-test a real
  `<tool_call>` on the specific 4-bit MLX quant before any grid, as for every entry here.
  **Why it earns the top slot alongside Qwen3.8-27B:** it is the only candidate that is *both*
  last-cycle *and* zero-friction to serve, it is a 35B-A3B at exactly our incumbent's size class and
  context (so the comparison is like-for-like on everything but the base generation and post-training),
  and the self-scaffolding recipe makes it the one model whose pitch is about the harness — the thing
  retort measures. **A second variant is worth a cell too: `Ornith-1.5-9B` (dense, SWE-bench Verified
  71.8, Terminal-Bench 58.3, ~5–6 GB at 4-bit, first-party MLX 4-bit + GGUF)** — it beats the already-
  listed Nanbeige4.2-3B (63.6) at the far end of the size axis and leaves ~58 GB free, which is what
  the §3 speculative-decoding lever wants; its vocab is Ornith/Qwen-lineage, so unlike LFM2.5 and
  Mellum2 it is the first small entry with a *plausible* draft-model pairing for the Qwen targets —
  verify tokenizer compatibility before assuming it. *(Predecessor **Ornith-1.0**, 2026-06-25, MIT,
  also fits — 9B dense, **31B dense on a Gemma 4 base**, 35B MoE, 397B MoE; the 31B is the only
  matched-base probe available on the already-listed Gemma 4 candidate. Run 1.5 first; 1.0 is a
  fallback if 1.5's numbers do not survive contact.)*
  Source: https://ornith.ai/ornith_1_0.html
  — 1.5 coverage: https://www.explainx.ai/blog/ornith-1-5-self-improving-open-weight-model-august-2026
  — weights: https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B
  — MLX 4-bit (first-party): https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit
  — GGUF (first-party): https://huggingface.co/ornith-ai/Ornith-1.5-35B-A3B-GGUF

*Excluded 2026-08-18, closed weights and oversized:* **MAI-Code-1-Flash / MAI-Code-1.1-Flash**
(Microsoft, announced 2026-06-02) — Microsoft's first in-house coding model, 71.6% SWE-bench Verified
and shipping in GitHub Copilot, but it is a **137B-A5B closed-weight** MoE (~69 GB at 4-bit even if it
were published), so it fails both bars. Recorded so it is not re-investigated.
Source: https://microsoft.ai/models/mai-code-1-flash/

*Excluded 2026-08-17, out-of-scope rather than oversized:* **Needle 2** (Cactus Compute, weights
2026-08-13, Apache 2.0) — a **45M-parameter** tool-calling / structured-extraction model in a 14 MB
binary with a **256-token sliding window**, built to map a sentence onto a typed function signature on
phones and wearables. It is a tool-call *router*, not a coding model, and could not hold a retort task's
prompt, let alone write code. Source:
https://www.marktechpost.com/2026/08/13/cactus-compute-needle-2-45m-parameter-tool-calling-model/
**Muse Spark 1.2** (Meta) — the frontier sibling that **Muse Glimmer was distilled from**, and Meta has
committed to opening its weights "in the coming weeks"; but as of this scan there are **no weights, no
disclosed parameter count and no licence**, and a model large enough for Glimmer to be its 30B
distillate is very unlikely to fit here. Re-check when it lands and record the size before listing it —
do not schedule anything on it. Source: https://developer.meta.com/ai/models/muse-spark/
*(Also seen and out of scope: **Muse Code** and the **DeepSeek Harness** developer preview, 2026-08-17,
MIT — both are agent harnesses, not models; the DeepSeek one is already noted below and belongs next to
the §4 harness side-branch if that work resumes.)*

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

*Also excluded 2026-08-15, too large:* **GLM-5.3** (Z.ai / Zhipu, launched 2026-08-14) — the top
open-weights coding model by Z.ai's own benchmarks, and a genuinely last-cycle drop, but it **reuses
GLM-5.2's 743B-A40B MoE base unchanged and spends everything on post-training** → ~370 GB at 4-bit,
five times what this box holds. Same size verdict as the GLM-5.2 note in the GLM-4.7-Flash entry
above; **GLM-4.7-Flash (30B-A3B) remains the only way this lineage enters the local leaderboard.**
Weights were also staged behind a safety review (~two weeks from launch) rather than published at
announcement. Worth noting as *evidence* rather than as a candidate: a 50% coding gain from
post-training alone, on a frozen base, is the same effect the KAT-Coder / BTL-3 / Macaron matched-base
probes above exist to measure. Source: https://the-agent-report.com/2026/08/glm-5-3-zai-post-training-coding-cyber/
*(Also seen and out of scope: Alibaba's **Qwen3.8-2.4T-A95B** open weights, 2026-08-12 — ~1.2 TB at
4-bit; and DeepSeek's open-sourced plugin-based **agent harness**, 2026-08-13, which is a harness, not
a model — it belongs next to the §4 harness side-branch if that work resumes.)*

*Also excluded 2026-08-22:* **MiniMax M3** (428B-A23B multimodal MoE, 2026-06-01) — frontier coding and
agentic performance with 1M context, but **~214 GB at 4-bit**, three times what this box holds, and it
ships under MiniMax's own community licence rather than a permissive one. **LFM2.5-DSpark** (Liquid AI,
2026-08-20) — ~300M speculative-decoding drafters, out of scope as *models*, and they draft **only for
LFM2.5-1.2B / 2.6B / 8B-A1B targets**, so they do nothing for the §3 speculative-decoding lever on our
Qwen targets; recorded because it also settles the open question in the LFM2.5-2.6B entry above —
Liquid's own drafters are target-family-locked, which is further reason not to expect LFM2.5 to draft
for the 35B/80B. **Muse Spark 1.2** (Meta) remains re-check-only: shipped 2026-08-05 with weights
promised under a modified Llama Community License, but Meta still publishes **no parameter count and no
architecture**, so there is still nothing to size. Sources:
https://huggingface.co/MiniMaxAI/MiniMax-M3 ·
https://www.marktechpost.com/2026/08/20/liquid-ai-releases-lfm2-5-dspark-draft-models-that-deliver-up-to-3-18x-faster-decoding/

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
