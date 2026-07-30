# The Experiment Index: What Was Measured, and What the Harness Was Doing at the Time

*Published 2026-07-30 · updated 2026-07-30 — Adrian Cockcroft*

An index, not an argument. Retort has run **1,014 scored runs across 56 experiment groups and 13 languages**; this page says what each group was for, where to read the detail, and — the part that matters most for reading an old number — **what the harness itself was doing at the time**. Several published figures moved because the tooling was fixed, not because a model changed.

Detail lives in [`docs/past-experiments.md`](docs/past-experiments.md). Current recommendations: [`optimal-blog.md`](optimal-blog.md) and the machine-readable [`optimal.json`](optimal.json). What the agents are asked to build, and the fastest passing run for each: [`tasks-blog.md`](tasks-blog.md). What's next: [`docs/future-experiments.md`](docs/future-experiments.md).

---

## The categories

| Category | The question | Experiments | Written up in |
|---|---|---|---|
| **Cloud models** | Which frontier model, at what cost and reliability? | `exp-1` (first grid: opus vs sonnet, 6 languages) · `exp-3/4/5/6/8` (Opus 4.6 → 4.7 → 4.8) · `exp-7` (**fast mode** as a factor) · `exp-10` (Fable 5) · `exp-15` (Sonnet 5) · `exp-46` (Opus 5, all 13 languages × both tasks) · `exp-48` (Fable 5 gap-fill) · `exp-53` (**Codex / GPT-5.6** — first non-Claude lineage) · `exp-55` (Terra vs Opus 5 at matched thinking levels) | [model](model-blog.md), [versions](versions-blog.md) |
| **Local models** | Can a laptop do this, and what does it take? | `exp-12` (Qwen2.5-Coder 7B via Ollama — first local run, n=1) · `exp-16/17/18` (Qwen3-Coder → Hermes → the lcm context engine) · `exp-20` (first all-9-language local sweep) · `exp-22/23` (Qwen-Next 80B, Devstral) · `exp-27/28` (sampling factorial, then the re-baseline) · `exp-29/30/33/36/37/38` (the 80B, language by language) · `exp-47` (gpt-oss-20b — first non-Qwen local lineage) | [harness](harness-blog.md), [model](model-blog.md) |
| **Config levers** | Same model, different stack — what actually moves? | `exp-34/35` (lcm `context_threshold` — the biggest local lever) · `exp-27` (temperature / top_p / top_k / repetition_penalty, Res IV) · `exp-24` (KV prefix cache — null: these runs are generation-bound, not prefill-bound) · `exp-16` (context 64K → 128K → 256K) · `exp-49` (**thinking level**) | [optimal](optimal-blog.md), [harness](harness-blog.md) |
| **Task difficulty** | Routine REST API vs a 12-capability MCP server | `exp-2` (introduces the hard task) · `exp-25/26` (hard task, local 35B) · `exp-31/39` (hard task, 80B — config-invariant) · `exp-50` (re-test with the turn cap removed) | [model](model-blog.md) |
| **Prompt / method** | Does prescribing BDD/TDD/ATDD change the outcome? | `exp-13/14` (cloud, hard task) · `exp-19` (local 35B) · `exp-32` (local 80B — does a weaker model need the scaffolding more?) | [prompt](prompt-blog.md) |
| **Agent & tooling** | What drives the run, and what does it get to use? | `exp-11` (Gemini — first cross-*agent* design; scaffolded, never run) · `exp-53` (codex, where the agent factor actually landed) · `exp-44/45` (**graphify** knowledge-graph, frontier and local arms) · `beads` throughout | [optimal](optimal-blog.md) |
| **Self-repair** | Does a second attempt with the evaluator's feedback help? | `exp-21` (35B) · `exp-41` (80B, iteration 2) — an inline second chance now runs by default, at half credit | [model](model-blog.md) |

Two candidates were **rejected before running**: Ornith-1.0-35B (vision-optimized, agent-hostile sampling) and Poolside Laguna XS 2.1 (architecture not in mainline serving). Both are documented with their gate-probe evidence at the end of [`docs/past-experiments.md`](docs/past-experiments.md), because a candidate ruled out cheaply is still a result.

---

## Harness changes that moved published numbers

Check this before comparing a number from one experiment against another. None of these involved a model changing.

| Era | Change | What it moved |
|---|---|---|
| exp-17 → exp-27 | **Three unrecorded stack variables at once** — playpen under `/var` (writes silently refused: 41/48 runs in exp-27, 6/6 in exp-26), oMLX `temperature: 1.0`, and context silently 128K while both the config and provenance read 256K | Every Hermes-era local result in this range is an understated **floor**, not a measurement. The exp-28 re-baseline supersedes them. It also overturned the "niche-language wall" — though exp-38 later confirmed clojure/csharp/elixir *are* genuinely 0.00 on a fixed stack. |
| exp-34 → exp-38 | **lcm `context_threshold` 0.35 → 0.9** | TypeScript on the 80B went 0.33 → 1.00. A config lever, not a capability. |
| exp-43 | **Test-command exit code as the universal pass signal**; 900s scorer timeout; process-group reaping | C/C++/Swift were being scored 0 for unparsed output, and leaked servers squatted ports and false-failed later cells. |
| exp-46 | **Run timeout 60 → 120 min** | Opus 5 is 3–5× slower and brazil cells average 47 min — the old wall was cutting off work in progress. |
| exp-46 | **pytest exit-code fallback** | A project whose 239 tests all passed scored `test_coverage=0` because its own pytest flags suppressed the summary line. |
| exp-49 | **`effort` became a factor** — and `aggregate` was silently dropping factor columns it didn't know | Everything before exp-49 ran at each CLI's default thinking level, uncontrolled; and all 63 exp-49 runs first landed in `master.db` *without* the very factor they were built to test. |
| exp-50 | **Hermes turn cap (30) never reconciled with the declared 200** | Local runs could be truncated mid-work and scored as model failures. |
| exp-53 | **Codex telemetry + per-token pricing** | Codex runs recorded 0 tokens, 0 turns and \$0 until the parser matched the real CLI event shape. Costs are now priced from published rates for every vendor, since Claude Max reports a price it doesn't bill and Codex reports nothing at all. |
| exp-55 | **`xhigh` was missing** from retort's effort levels | exp-49's "full sweep" had skipped a level that exists in both CLIs. |
| ongoing | **Attribution** — local runs wrote a blank `model`; experiment labels are now `<githubid>/exp#` | ~250 rows are identified by experiment slug rather than model id, and a stack predicate that enumerated local models *by exclusion* once counted exp-47's gpt-oss runs as the 35B's. |
| post-exp-55 | **Python workspaces get a provisioned venv** (`python`, `pip` and pytest on PATH) | Every earlier python run inherited a host with **no `python`** — only Homebrew's `python3`. The fastest recorded run of all three tasks, across two vendors and three models, spent a turn on `command not found` and a retry. Dependency installs were also luck: `pip` against a Homebrew interpreter fails `externally-managed-environment`, so whether an agent could install anything depended on whether it happened to build its own venv. And the scorer built a *different* interpreter than the agent's. Python runs before and after this are not turn-count comparable. |

The shape that keeps recurring: **a failing model and a broken harness are identical in the scores.** `retort diagnose` exists to separate them, and the standing rule is that a surprising zero gets reproduced by hand before it gets published. The full post-mortems are in [Historical: harness bugs & the local re-baseline saga](docs/past-experiments.md).

---

## Conclusions that were retracted

Kept visible, because the corrections are more useful than the originals.

- **"Opus 5 is the only model that clears the hard task everywhere"** (exp-46) — withdrawn by exp-48. Fable 5 had never been *run* on 9 of the 13 languages; when it was, it cleared them at roughly half the price. An unrun cell and an unpassable cell look identical in a table.
- **"Newer Claude versions take steadily more turns"** — corrected by exp-49. Three generations sit at ~9–13 turns; the apparent trend came from one old experiment's figures, which don't replicate.
- **"Thinking level explains the cross-version cost gap"** — retracted by the experiment run to test it. The single run that motivated it (33 turns at `max`) did not replicate: 14, then 18.
- **"gpt-oss matches the 80B on Go at 3.6× the speed"** (exp-47, n=3) — removed at n=5, where Go fell to 0.80.
- **"The local hard-task wall is a turn cap"** (exp-50's whole premise) — wrong. `api_calls` is 1:1 with turns, not 3:1, so nothing had been truncated. The wall is real.

Four of those five came from reading a single run as a result.

---

## The slowest successful run

[tasks-blog.md](tasks-blog.md) shows the fastest passing run for each task. The other end is more instructive, because nothing fails there either.

Both of these are the **same task** — `rest-api-crud`, python, a books CRUD API — and both score `requirement_coverage = 1.00`.

| | Fastest (Fable 5, `effort=low`) | Slowest (Opus 5, `effort=max`) | Ratio |
|---|---|---|---|
| Wall clock | 44.5 s | **45.6 min** | 61× |
| Cost | $0.86 | **$24.96** | 29× |
| Tokens | 105,745 | **18,448,183** | 174× |
| Turns | 7 | **94** (256 tool calls) | 13× |
| Source + test lines | 194 | **2,351** | 12× |
| Tests | 6 | **104** | 17× |
| `requirement_coverage` | 1.00 | 1.00 | — |
| `test_coverage` | 0.98 | 1.00 | |
| `maintainability` | 0.27 | 0.85 | |
| `token_efficiency` | 1.00 | 0.0019 | |

The slow run is **not a failure, and not slop**. It scores *better* on maintainability, idiomaticity and coverage. It built a seven-module package, ran `ruff` on itself unprompted, spawned a subagent, and performed **mutation testing** — on a books CRUD API. Every one of the judge's five findings is an `info` describing scope *beyond* the spec: a `PATCH` endpoint, filtering/sorting/pagination, a hand-written 304-line OpenAPI 3.0 document served at `GET /openapi.json`, WAL journaling and busy-timeouts on SQLite, and validation for NUL bytes and SQLite integer bounds.

Nobody asked for any of it. The task asked for five endpoints, a health check, and at least three tests.

**What actually goes wrong is that the gate cannot see the difference.** `requirement_coverage` is 1.00 for both, so pass-proportion — the headline metric of this whole project — rates a 44-second $0.86 run and a 46-minute $25 run as identical. That is correct by its own definition and still the most misleading number on the page unless you read cost beside it. `token_efficiency` is the response that *does* separate them, by a factor of 534.

**The dial also buys variance, not just cost.** Within exp-55, the same Opus 5 python cell run twice:

| `effort` | rep1 | rep2 | mean cost |
|---|---|---|---|
| low | 1.9 min | 2.2 min | $0.76 |
| medium | 3.0 min | 3.2 min | $1.04 |
| high | 6.2 min | 5.6 min | $1.68 |
| xhigh | 15.3 min | 8.6 min | $2.55 |
| max | **24.5 min** | **45.6 min** | **$19.21** |

At `low` the two replicates agree within 15%; at `max` they differ by 1.9×, and cost by 1.9×. Ten of ten cells score 1.00. On this task the thinking dial is a 25× cost multiplier that buys nothing measurable and becomes unpredictable at the top. *At n=2 the variance claim is suggestive, not established* — but the cost is not in doubt. Meanwhile GPT-5.6 Terra ran the same ten cells between 1.4 and 4.0 minutes for $0.10–$0.33, also 1.00 throughout.

One more thing the log shows: the slow run spent its opening turns probing the host interpreter and discovered that the preinstalled FastAPI was **broken** (pydantic v1 cannot build models on Python 3.14), then chose Flask instead. That is the environment leaking into the measurement again — and it is the same class of problem as the missing `python`, now addressed by [provisioning a clean venv per workspace](tasks-blog.md).

---

## Reading the numbers

**Pass-proportion** is the fraction of runs that *fully* implement the spec — every requirement on a pinned checklist, with tests that actually execute, verified by an independent LLM judge. A run that misses one requirement scores 0, not 0.9. Read a cell as *the probability that one unattended run comes out completely correct*.

Three things to check before trusting one: **`n`** (many cells are 1–3 runs, and results at n=1 have reversed repeatedly in this project), **the judge** (recorded per experiment in `master.db` since exp-53; `requirement_coverage` is one model's opinion, and only pools across experiments graded the same way), and **the language mix** (an all-language average silently compares models that were run on different sets of languages — the per-language matrix is the like-for-like view).
