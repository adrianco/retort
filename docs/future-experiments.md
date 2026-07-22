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

## 2. exp-41 — self-repair iteration-2 on the 80B ctx-0.9 near-misses  — SCAFFOLDED, ready to launch

Scaffolded at `experiments/adrianco/experiment-41-repair-80b-fullctx/` (m80 preset now uses the
`context_threshold: 0.9` field). Launch with `retort run --repair-from
experiments/adrianco/experiment-38-alllang-80b-fullctx/bookshop` on the near-miss languages
(rust/java/erlang), n=3.

**Key framing (discovered while analysing exp-38/39):** the default inline **second-chance already
does one feedback-driven repair** on every failing cell (confirmed via the `_second_try` metric —
set on all exp-38 near-misses). So our reported near-misses (Rust 0.917, hard-task python 11/12) are
*already post-one-repair*. exp-41 therefore tests **iteration 2**: does a second dedicated repair
pass, seeded with the iteration-1 code + a fresh FEEDBACK.md, close the last 1-2 requirements?

**Headline:** Rust at 0.92 (missing ~1 requirement) is the most-likely-to-flip and highest-value —
if a repair pass takes Rust from 1/3 to 2-3/3, **Rust becomes locally viable** on the 80B. java
(0.75) / erlang secondary. The all-zeros niche languages are excluded (no coherent code to repair).
Repair runs are `prompt=repair`, half-credit, excluded from the headline pass-proportion.

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

## 4. gpt-oss-20b — the one remaining fits-64GB new-model candidate  — LOW priority

The only untried model that both fits and isn't a Qwen3.5 VLM. Fits comfortably; **Harmony**
tool-format (oMLX has a `harmony` reasoning parser, tool-parse unverified — needs a gate-probe).
20B is unlikely to beat the 35B, so low priority — but it's a different lineage (OpenAI open
weights) and the only clean new-model probe left. To try a Mistral-family or Devstral coder instead,
the stack manager would need a llama.cpp / vLLM serving backend (they parse the Mistral tool format
oMLX can't).

## 5. More languages — C / C++ / Objective-C / Swift exploration  — SCHEDULED

Extend beyond the 9 current languages to the **systems + Apple** tier. Scaffolded at
`experiments/adrianco/experiment-43-morelangs/bookshop/`.

**Design (exploration, deliberately thin):** `language{c, cpp, objc, swift} × model{opus-4.8,
qwen-80B} × bookshop(rest-api-crud) × prompt=neutral × 1 replicate` = **8 runs**. One replicate
is enough for a first *comparison/exploration* — cloud frontier (Opus 4.8) vs the leading local
stack (Qwen3-Coder-Next 80B at `context_threshold: 0.9`) on each new language. Promote to n≥3 +
the hard task only for languages that look viable.

**PREREQUISITE — scorer support (DONE 2026-07-22, run is unblocked).** These 4 languages were new
to the harness. Now wired end-to-end:
- **Toolchains** (`toolchains.py`): c/cpp/objc/swift entries + `c++`/`cxx`/`objective-c` aliases, so
  the preflight checks/installs the compilers (clang/CMake/lcov; swift).
- **Extension maps**: all six per-file scorers (`token_efficiency`, `maintainability`, `idiomatic`,
  `defect_rate`, `code_quality`) know `.c/.h`, `.cpp/.cc/.cxx/.hpp`, `.m`, `.swift` — so they count
  source instead of scoring 0.
- **test_coverage (the mechanical gate)**: Swift runs `swift test --enable-code-coverage` via the
  standard command path; C/C++/ObjC go through a new `_native_coverage` that **detects the build
  system** — CMake+CTest first, then Makefile, then (ObjC) `xcodebuild` — and returns the **test
  pass-rate as the coverage proxy** (same approach as Rust). Regression test:
  `test_test_coverage_parses_native_and_swift_pass_rate`.
- **defect_rate / code_quality lint**: Swift fully wired (`swift build` warnings; `swiftlint`).
  *Follow-up:* C/C++/ObjC compiler-warning counting + `clang-tidy` need build-system/compile-db
  integration — deferred; their quality still comes from the other scorers + the coverage gate.

Swift is the cleanest (one canonical toolchain); C/C++ vary by build system; Objective-C is
macOS-only. **The run can launch** — remember to smoke-test one c + one swift stack end-to-end
(per CLAUDE.md) before the full 8-run grid.

**Build setup per language** (graduate to the README toolchain table once supported):

| Lang | ext | compiler / build | test + coverage the scorer runs | lint | install (macOS) |
|---|---|---|---|---|---|
| **Swift** | `.swift` | SwiftPM (`swift build`) | `swift test --enable-code-coverage`; coverage via `llvm-cov export` on `.build/*/codecov/*.profdata` | `swift-format lint` / `swiftlint` | `brew install swift` (or Xcode) |
| **C** | `.c` | `clang`/`gcc`, CMake or Makefile | build the agent's test target, run it; coverage `--coverage` (gcov) → `lcov`/`gcovr` | `clang-tidy` | Xcode CLT (`clang` preinstalled) + `brew install cmake lcov` |
| **C++** | `.cpp/.cc/.hpp` | `clang++`/`g++`, CMake | `ctest` on the agent's framework (Catch2 / GoogleTest / doctest); coverage gcov/`llvm-cov` | `clang-tidy` | Xcode CLT + `brew install cmake lcov` |
| **Objective-C** | `.m/.h` | `clang` + Foundation (**macOS only**) | XCTest via `xcodebuild test`, or a plain assert executable; coverage `llvm-cov` | `clang-tidy` | Xcode (full, for XCTest/Foundation) |

**Host prerequisite (verified 2026-07-22 on the exp-43 machine):** **Swift *and* Objective-C need a
full Xcode installed AND launched once** — XCTest/Foundation don't ship with the Command Line
Tools. Install Xcode, open it once (accept the license + let it install components), and confirm
`DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild -checkFirstLaunchStatus`
returns exit 0. No `sudo xcode-select -s` needed: the scorer's `_apple_env` auto-points
`DEVELOPER_DIR` at the installed Xcode when `xcode-select` still targets the CLT. Without a
launched Xcode, every Swift/ObjC run fails the gate with `no such module 'XCTest'` (a false zero).
C/C++ only need `clang` + `cmake` (CLT is enough).

**Notes / risks:** C and C++ have **no single canonical test runner** (Go's `go test` has no
equivalent) — the agent picks a framework, so the scorer must detect the build system (CMake vs
Makefile) and the test target, or run `bookshop`'s own provided harness. **Objective-C needs a
full Xcode** (Foundation + XCTest), so it can't run in a Linux CI — mark it macOS-only. **Swift**
is the safe first one to wire up. Expect the local 80B to be weaker here than on Python/Go/TS
(these languages are far less represented in training) — the point is to *measure* that gap.

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
