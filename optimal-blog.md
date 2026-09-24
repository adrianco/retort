# The Optimal Stack

*Living document — last updated 2026-09-24 (first published 2026-07-14). This records **what to run today**: the leading stacks, and the exact configuration each one needs. It is not a history. Superseded stacks and rejected configurations are not discussed here; they are retired, and retirement is the point.*

---

## What this document is

A **stack** is the whole thing you actually deploy, not just a model:

> **language × model × quantization × serving layer × agent × context engine × sampling × prompt**

Retort scores stacks on **pass-proportion** — run a stack N times on a real task and count the fraction whose output *fully implements the spec*: every requirement on a fixed checklist, tests that actually execute, verified by an independent evaluator. A run that misses one requirement is a failure, not a 0.9. Read it as *the probability that a single unattended run comes out completely correct.*

That harsh bar is deliberate, because it is the number that decides whether you can let a stack work unattended.

## Lifecycle: how a stack gets here, and how it leaves

This document is the human-readable view of a lifecycle the tool already runs. Each stage is a retort command, so entries here are *derived*, not curated by taste:

```
CANDIDATE ──► SCREENING ──► TRIAL ──► PRODUCTION ──► RETIRED
```

| Stage | What it means | How it's decided |
|---|---|---|
| **Candidate** | a new model, agent or configuration appears | `retort intake --factor model --level <new>` augments the existing design rather than restarting it |
| **Screening** | Resolution III — do its main effects matter at all? | `retort run --phase screening` → `retort analyze` |
| **Trial** | Resolution IV/V — interactions estimated | `retort promote --from screening --to trial` (gate: p-value) |
| **Production** | **listed in this document** — the recommended stack for its niche | `retort promote --to production` (gate: posterior confidence); `retort maturity` scores readiness |
| **Retired** | dominated on *every* metric by a newer stack — removed, not demoted | `retort report pareto` identifies who is still non-dominated |

The gates are configuration, not opinion — they live in each `workspace.yaml`:

```yaml
promotion:
  screening_to_trial:   { p_value: 0.10 }
  trial_to_production:  { posterior_confidence: 0.80 }
```

**A stack earns a place here only by leading on an axis a developer actually chooses along** — a language, a task size, a cost or latency budget. Being new is not a qualification. When it leads on none, `retort report pareto` shows it dominated and it comes out. The list stays short on purpose.

Configurations that reliably degrade a stack are eliminated outright and recorded as **forbidden settings** (below). New model releases — frontier and local — trigger a re-qualification pass, so this document is expected to churn.

---

## Start here: the cheapest (model × thinking level) that clears each cell

**A stack is a model *and* a thinking level, and the dial costs far more than the model choice does.** The cleanest measurement is Opus 5.5's full ladder (exp-74, six levels × two languages, n=3 a cell): **every one of the 36 runs scored 1.00, and the bill spanned 27× — \$0.38 at `low` against \$10.26 at `max`, with wall-clock spanning 58×.** Identical output, 27× the money. An earlier sweep across four Claude versions on one cell found the same shape at 16×, so this is a property of the dial rather than of one release. **Turning the dial up buys nothing the gate can see; it is the single most expensive mistake available in this document.** So the recommendation is always a pair, never a model alone.

The machine-readable form of the table below is committed at **[`optimal.json`](optimal.json)** (regenerate with `retort report optimal --routing-json optimal.json`) so other tools — the metaharness router, CI, your own scripts — can consume the routing decision directly rather than scraping prose.

<!-- GEN:per-language-routing START -->
| Language | Routine → cloud | pass | $ | Routine → local | Hard → cloud | pass | $ |
|---|---|---:|---:|---|---|---:|---:|
| **c** | GPT-5.6 Terra @ `default` <sub>n=1</sub> | 1.00 | $0.26 | — | GPT-5.6 Terra @ `default` <sub>n=2</sub> | 1.00 | $0.57 |
| **clojure** | GPT-5.6 Terra @ `default` <sub>n=1</sub> | 1.00 | $0.33 | — | Opus 5.5 @ `low` <sub>n=1</sub> | 1.00 | $1.46 |
| **cpp** | GPT-5.6 Terra @ `default` <sub>n=1</sub> | 1.00 | $0.26 | — | Opus 5.5 @ `low` <sub>n=1</sub> | 1.00 | $2.30 |
| **csharp** | GPT-5.6 Terra @ `default` <sub>n=1</sub> | 1.00 | $0.26 | — | Opus 5.5 @ `low` <sub>n=1</sub> | 1.00 | $1.93 |
| **elixir** | GPT-5.6 Terra @ `default` <sub>n=1</sub> | 1.00 | $0.42 | — | Opus 5.5 @ `low` <sub>n=1</sub> | 1.00 | $1.97 |
| **erlang** | GPT-5.6 Terra @ `default` <sub>n=1</sub> | 1.00 | $0.34 | — | Opus 5.5 @ `low` <sub>n=1</sub> | 1.00 | $2.73 |
| **go** | GPT-5.6 Luna @ `default` <sub>n=3</sub> | 1.00 | $0.08 | Qwen3-Coder-Next 80B @ `default` <sub>n=3</sub> | GPT-5.6 Terra @ `low` <sub>n=1</sub> | 1.00 | $0.39 |
| **java** | GPT-5.6 Terra @ `default` <sub>n=1</sub> | 1.00 | $0.38 | — | GPT-5.6 Terra @ `default` <sub>n=2</sub> | 1.00 | $0.69 |
| **objc** | GPT-5.6 Terra @ `default` <sub>n=1</sub> | 1.00 | $0.24 | — | Opus 5.5 @ `low` <sub>n=1</sub> | 1.00 | $2.46 |
| **python** | GPT-5.6 Luna @ `default` <sub>n=3</sub> | 1.00 | $0.06 | Qwen3-Coder-Next 80B @ `default` <sub>n=3</sub> | GPT-5.6 Terra @ `high` <sub>n=1</sub> | 1.00 | $0.31 |
| **rust** | GPT-5.6 Terra @ `default` <sub>n=1</sub> | 1.00 | $0.14 | — | GPT-5.6 Terra @ `default` <sub>n=2</sub> | 1.00 | $0.36 |
| **swift** | GPT-5.6 Terra @ `default` <sub>n=1</sub> | 1.00 | $0.22 | — | Opus 5.5 @ `low` <sub>n=1</sub> | 1.00 | $1.33 |
| **typescript** | GPT-5.6 Terra @ `default` <sub>n=1</sub> | 1.00 | $0.22 | Qwen3-Coder-Next 80B @ `default` <sub>n=3</sub> | GPT-5.6 Terra @ `default` <sub>n=2</sub> | 1.00 | $0.44 |
<!-- GEN:per-language-routing END -->

> **Reading the `effort` column — it is the level to actually pass.** Each cell names the thinking level the winning runs used: `default` means they passed no `--effort` flag, and a named level means they used it. A cell measured at exactly one level used to be flattened to `default`, which told you to pass no flag when the runs behind the number had used, say, `low` — Opus 5.5's hard-task cells were mislabelled that way until 2026-09-24. Where a stack has been swept across levels, each level competes separately and the cheapest qualifying one wins; where it has not, a single level means *"this is what was measured"*, not *"this was compared and won"*.
>
> **The dial has now been swept four times, and the answer has not changed once:** exp-49 (four Claude versions, one cell), exp-55 (Terra and Opus 5, five levels, python and go), exp-65 (Fable 5.1, four languages) and exp-74 (Opus 5.5, six levels). Every sweep found the top of the dial buying nothing measurable and costing multiples. **Default to `low` on any model whose `low` clears your cell.**
>
> **A `null` means nothing measured clears the bar for that cell** — not "untested". And read the `n`: several cells are n=1, where a 1.00 is much weaker evidence than a 1.00 at n=9.
>
> ✅ **One bar for every stack: 1.00.** Local stacks used to qualify at **0.50**, on the view that a \$0 stack is worth a lower bar if you are watching it. That contradicted the metric's own definition — *the probability a single **unattended** run comes out completely correct*, where a single sub-1.0 run is a fail — and it let a coin flip outrank a perfect stack purely on price (python-on-hard-task recommended the local 35B at **0.50**). Being free is already expressed in the cost column; it should not also lower the standard.
>
> Raising local to 1.00 did **not** push local out of the recommendations — it picked a *better* local stack: routine python and go moved from the 35B (now measured at 0.72 / 0.75 over a much larger n) to the **80B at 1.00, still \$0**. The double standard had been hiding the more reliable free option. Hard-task python moved off the local 35B at 0.50 to a cloud stack at 1.00, which is the honest answer.

## The leading stacks

Reliability, cost and time are all reported **per task size** — routine and hard are different jobs, and a stack that is cheap-and-certain on routine work can be neither on a hard one. The **routine reliability here is a cross-language blend and is the least useful number in this document** — it hides a stack's weak languages inside its strong ones (local Qwen passes Python/Go but not Rust; Opus 4.8 dips on Java). Use it only as a rough sort; the [per-language success-rate matrix](#what-to-run-by-language-and-task-size) below is the number to actually decide on. (Hard reliability is single-task, measured on Python/Go.)

<!-- GEN:leading-stacks START -->
| Stack | Reliability (routine · hard) | Cost (routine · hard) | Time (routine · hard) |
|---|---:|---:|---:|
| **Claude Opus 5.5** | 1.00 · 1.00 | $1.41 · $1.92 | 275 s · 367 s |
| **Claude Opus 5** | 1.00 · 1.00 | $3.23 · $26.48 | 546 s · 2669 s |
| **Claude Fable 5** | 1.00 · 1.00 | $1.58 · $10.47 | 166 s · 1090 s |
| **GPT-5.6 Terra (codex)** | 1.00 · 0.79 | $0.24 · $1.18 | 163 s · 615 s |
| **GPT-5.6 Luna (codex)** | 0.67 · 0.33 | $0.09 · $0.17 | 153 s · 170 s |
| **Claude Sonnet 5** | 1.00 · 0.93 | $1.10 · $7.64 | 237 s · 1252 s |
| **Claude Opus 4.8** | 0.98 · 0.59 | $0.93 · $3.27 | 258 s · 608 s |
| **Claude Opus 4.7** | 1.00 · 0.40 | $0.92 · $2.95 | 165 s · 500 s |
| **Qwen3.6-35B-A3B (local, $0)** | 0.73 · 0.25 | $0.00 · $0.00 | 386 s · 1542 s |
| **Qwen3-Coder-Next 80B (local, $0, ctx 0.9)** | 1.00 · 0.00 | $0.00 · $0.00 | 604 s · 2014 s |
<!-- GEN:leading-stacks END -->

> ⚠️ **The cost and time columns pool whatever effort levels each stack was measured at, and those differ between stacks — so do not read them against each other as like-for-like.** Opus 5's `$26.48` hard figure averages its entire exp-55 effort ladder including `max` cells that cost \$85; Opus 5.5's `$1.92` averages `low` runs only. Compared properly — same task, same language, same `low` effort — Opus 5.5 is **3.5–5.8×** cheaper than Opus 5 on the hard task (python \$1.40 vs \$8.14, go \$1.99 vs \$7.03), not 13.8×. The same distortion inflates Opus 5.5's own routine figure to \$1.41 when its actual `low`-effort routine cost is **\$0.38–0.67**. The per-cell routing table above is filtered by effort and does not have this problem; this summary table is a sort key, not a quote.

*(Table generated from `master.db` by `retort report optimal` — do not hand-edit between the markers.)* Each local stack's routine number is scoped to the languages it is **recommended** for (35B: Python/Go; 80B: Python/Go/TypeScript) — the full per-language truth, including the languages they fail, is in the matrix below. **On the hard task local models are now measured and both do poorly** — 35B **0.25**, 80B **0.00** (see the per-stack bullets). Rust local is unqualified (80B 0.33, near-misses).

> ### ⚠️ Local + hard task: the wall holds unattended, but a repair loop gets through
>
> The 0.00 below is the **unattended, first-attempt** number and it stands — [exp-50](docs/past-experiments.md) re-ran it and got **0/6 on first attempts**, matching exp-39 exactly.
>
> What exp-50 adds: with retort's **self-repair second chance** — the cell re-seeded with its own code plus the evaluation's critique — the 80B reached full req-coverage on **3 of 6** runs. Every pass was a second attempt; none was unattended. At half credit for a second-try pass that is a pass-proportion of **0.25** against a published 0.00.
>
> Read it as: **the 80B reliably gets ~11 of 12 capabilities and cannot close the last one alone, but closes it about half the time when told what is missing.** "Hard tasks → cloud" remains right for unattended use; a local stack *with a repair loop* is a different and more promising proposition.
>
> (The re-test was launched on a theory — a 30-turn agent cap — that turned out to be wrong: the old runs took 32–90 turns and nothing truncated them. Kept visible in the write-up.)

**Pick by task size — the two columns tell different stories:**

* **Opus 5.5 — the hard-task pick, and it is not close on price.** 1.00 in all thirteen languages on both tasks, at **\$1.33–\$2.73 and 3.5–12 min** a hard cell, run at `effort: low`. Against Opus 5 on the identical cell it is **3.5–5.8× cheaper and 2.9–5.3× faster** for the same 1.00. **Read the hard number as a screen:** it is n=1 per language (13 hard observations total), where Fable 5 has 21. It is the recommendation because nothing measured beats it on cost at 1.00, not because it is the most-replicated.
* **Fable 5 — the better-replicated hard-task alternative** at 1.00 across thirteen languages, n=21, but **~\$10.47 and ~18 min** a cell. Choose it over Opus 5.5 when you want the deeper evidence behind the 1.00 more than you want the 5× saving.
* **GPT-5.6 Terra — the cheapest thing that is *nearly* right on hard work:** **0.79**, at \$1.18. That is roughly a 1-in-5 miss, so it needs a review loop; where it does clear a language it is the cheapest qualifying hard-task stack in the routing table.
* **Sonnet 5** lands **0.93 on hard** — the middle option when a ~1-in-14 miss is acceptable.
* **Routine work is now a solved, near-free problem.** Every cloud stack here reaches ~1.00 on routine, so the only live question is price: **GPT-5.6 Luna at \$0.06–0.08** where it qualifies, **Terra at \$0.14–0.42** elsewhere, or **\$0 locally** on the 80B for Python, Go and TypeScript. Paying Opus prices for routine work buys nothing.
* **Qwen 80B local (`Qwen3-Coder-Next`, `context_threshold: 0.9`) — the best free stack**, and the only one that clears **Python 1.00, Go 1.00 and TypeScript 1.00** (exp-38, n=3 each). TypeScript is the unlock: 0.33 below full context, 3/3 at 0.9. Slower than the 35B (~600 s routine). **Rust is 0.33 — near-misses, not stalls** (req-coverage 0.92; the code compiles and its tests pass, it misses 1–2 spec requirements). The other five languages → cloud: java/erlang near-miss, and **clojure/csharp/elixir score a genuine 0.00** — they cannot produce working code at all (diagnosed GENUINE, not harness). **On the hard task it is 0.00, verified config-invariant** (exp-39 at full context = 0/6, same as 0.7): Python reaches 11/12 capabilities but never 12.
* **Qwen 35B local — the faster free option for Python and Go only**, at **0.72 / 0.75**. Rust **0.18** and TypeScript **0.28** are unqualified, and on the hard task it scores **0.25**. Its blended routine figure (0.73) sits *below* both of its good languages because the blend includes the languages it fails — the clearest reason in this document to read the matrix rather than an average.

**Retired — dominated on every axis, and this document removes rather than demotes.** **Opus 5** (1.00/1.00 but 3.5–5.8× Opus 5.5's hard cost), **Opus 4.8** (routine 0.98, hard **0.59** — a coin flip) and **Opus 4.7** (routine 1.00, hard **0.40**) are each beaten outright by a cheaper stack at equal or better reliability. They remain in the generated tables below because those are the measured record, but **none of them is the right answer to any question this page asks.**

> **The 80B's stall was a fixable config artifact, not a capability wall — and raising the compaction threshold is a graded lever, not a switch.** The intermittent hang was lcm compaction firing too early: at the default `context_threshold: 0.35` it compacts live context at ~92K, truncating the agent's working history mid-build so it loses the thread and thrashes to the wall. Raising it walks the results up:
>
> * **0.35 → 0.7** kills the Go stalls: over **9 Go runs** (exp-34/36) **0 stalls, Go = 8/9 = 0.89** (up from 0.67-with-2-stalls), and Python holds at **1.00** (exp-37). But TypeScript was still only 0.33 here.
> * **0.7 → 0.9 ("full context", compact at ~236K) unlocks TypeScript.** The full-9-language re-baseline at 0.9 (exp-38, n=3) gives **Python 1.00, Go 1.00, TypeScript 1.00** — TS goes from 0.33 to 3/3 because at full context the agent keeps its whole working history through the longer TS build instead of being compacted mid-stream. **So `lcm.context_threshold: 0.9` is now the recommended config for the 80B**, and the featured table reflects it (the 0.7 runs remain the larger-n Go evidence and the proof that the fix is graded).
>
> The cost of going to 0.9: a run that *can't* finish thrashes longer before failing (6 M tokens on a failed Rust/niche cell) — but those languages go to cloud anyway, so it doesn't touch the recommended Python/Go/TS path. (The same lever only *partly* rescues the 35B on Rust — exp-35: first-ever Rust pass at 0.7, but 2/3 still stall. And it doesn't help the hard task: exp-39 re-ran brazil at 0.9 and got the same 0/6 as 0.7, with Go now hitting the late-compaction stall — full context helps the easy languages, not the hard ceiling.)
>
> **The same lever partly explains the "Rust wall" — but only partly.** At 0.35 the 35B thrashes to the wall on *every* Rust run (clean 0.00). At 0.7 it scored its **first-ever Rust pass** (exp-35 rep1 = 1.00, at 113K context — exactly the regime 0.35 truncates), so Rust is *not* a pure capability wall. But **2 of 3 still stalled** at 0.7 — unlike the 80B (0/6), the 35B on Rust is only partially rescued. Net: raising `context_threshold` is a real lever for local non-termination, but its strength is model- and language-dependent — a clean fix for the 80B on Go/TS, a partial one for the 35B on Rust. Rust stays → cloud.

> **On the Opus 4.8 hard number.** 0.59 is an honest blend: a small clean run scored 1.00 (n=6) while a larger one scored 0.50 (n=36). The optimistic single-run figure is not representative — treat hard-task Opus 4.8 as a coin flip, not a sure thing.

---

## What to run, by language and task size

**Task size** is the axis that matters most, more than language:

* **Routine** — CRUD, glue, well-trodden patterns, a few interacting requirements.
* **Hard** — a novel domain, many interacting capabilities, real data, a protocol to implement correctly (our reference: an MCP server over six datasets, twelve required capabilities).

**Start from the per-language success rate, not a single headline number.** This is the matrix that matters — routine pass-proportion for each language × stack, `pass (n)`, generated from `master.db`. A blank cell means we have no qualified runs there. Read *down* a column to see where a model is weak (Opus 4.8 dips on Java; the 35B is weak on Rust and TypeScript; the 80B is 1.00 on Python/Go/TypeScript and 0.33 on Rust), and *across* a row to pick the cheapest stack that actually passes *that* language:

<!-- GEN:per-language-matrix START -->
| Language | Opus 5.5 | Opus 5 | Fable 5 | Terra | Luna | Sonnet 5 | Opus 4.8 | Opus 4.7 | Qwen 35B local | Qwen 80B local |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **c** | 1.00 (3) | 1.00 (1) | 1.00 (1) | 1.00 (1) | — | — | 1.00 (1) | — | — | — |
| **clojure** | 1.00 (3) | 1.00 (1) | 1.00 (3) | 1.00 (1) | — | — | 1.00 (6) | 1.00 (6) | 0.00 (3) | 0.00 (3) |
| **cpp** | 1.00 (3) | 1.00 (1) | 1.00 (1) | 1.00 (1) | — | — | 1.00 (1) | — | — | — |
| **csharp** | 1.00 (3) | 1.00 (1) | 1.00 (1) | 1.00 (1) | — | 1.00 (3) | 1.00 (1) | — | 0.00 (3) | 0.00 (3) |
| **elixir** | 1.00 (3) | 1.00 (1) | 1.00 (1) | 1.00 (1) | — | — | 1.00 (3) | 1.00 (3) | 0.00 (3) | 0.00 (3) |
| **erlang** | 1.00 (3) | 1.00 (1) | 1.00 (1) | 1.00 (1) | — | — | 1.00 (3) | 1.00 (3) | 0.00 (3) | 0.00 (3) |
| **go** | 1.00 (18) | 1.00 (10) | 1.00 (3) | 1.00 (10) | 1.00 (3) | 1.00 (3) | 1.00 (7) | 1.00 (6) | 0.75 (36) | 1.00 (3) |
| **java** | 1.00 (3) | 1.00 (1) | 1.00 (1) | 1.00 (1) | — | — | 0.83 (6) | 1.00 (6) | 0.00 (3) | 0.00 (3) |
| **objc** | 1.00 (3) | 1.00 (1) | 1.00 (1) | 1.00 (1) | — | — | 1.00 (1) | — | — | — |
| **python** | 1.00 (18) | 1.00 (26) | 1.00 (18) | 1.00 (10) | 1.00 (3) | 1.00 (3) | 1.00 (22) | 1.00 (21) | 0.72 (54) | 1.00 (3) |
| **rust** | 1.00 (3) | 1.00 (1) | 1.00 (3) | 1.00 (1) | — | 1.00 (3) | 1.00 (6) | 1.00 (6) | 0.18 (17) | 0.33 (3) |
| **swift** | 1.00 (3) | 1.00 (1) | 1.00 (1) | 1.00 (1) | — | — | 1.00 (1) | — | — | — |
| **typescript** | 1.00 (3) | 1.00 (1) | 1.00 (1) | 1.00 (1) | 0.00 (3) | 1.00 (3) | 1.00 (7) | 1.00 (6) | 0.28 (18) | 1.00 (3) |
<!-- GEN:per-language-matrix END -->

**The language split: Python, Go and TypeScript run locally for free (on the 80B at full context); every other language means Claude.** The 80B (`Qwen3-Coder-Next`, at `context_threshold: 0.9`) is reliable on all three — **Python 1.00, Go 1.00, TypeScript 1.00** (exp-38, n=3 each) — the last only after raising compaction to full context (it was 0.33 below that). The 35B is the faster alternative but only on **Python 0.72 and Go 0.75**; it manages just **0.28** on TypeScript and **0.18** on Rust even at its tuned config, so its blended figure sits below both of its good languages — exactly why this document leads with the matrix, not an average. **Rust and the five niche languages (clojure/csharp/elixir/java/erlang) still go to cloud** — the 80B either near-misses (Rust 0.33, java/erlang) or can't produce working code at all (clojure/csharp/elixir score a genuine 0.00). So local has two stacks for Python/Go and one (the 80B at 0.9) that adds TypeScript.

**The hand-maintained per-language recommendation table that used to sit here has been deleted, not updated.** It recommended Opus 4.7 / 4.8 for routine work in ten languages and Fable 5 for every hard cell, while the generated routing table two screens above — built from the same database — said Terra, Luna and Opus 5.5. **Two tables in one document giving different answers is worse than one stale table**, because a reader cannot tell which is current. The generated table is the answer; it is regenerated from `master.db` on every experiment and cannot drift.

What the hand table carried that the generated one does not is the **prompt / testing method**, which is qualitative and comes from the prompt sweeps rather than the routing query. It collapses to one rule:

**Prompt / testing method — it matters only in proportion to how weak the model is.** **The prompt is a lever on a weak model and a no-op on a strong one.**

* **Strong models (all cloud, and the local 80B): flat line.** Every methodology passes — the 80B goes **1.00 on all four**, ATDD included. Pick **neutral** and spend nothing on methodology ceremony; it's the cheapest and loses nothing.
* **Weak models (the local 35B): the prompt bites.** neutral/BDD 0.67, TDD 0.33, and **ATDD 0.00** — a weak model can't carry ATDD's front-loaded discipline and burns the run. So on the 35B: neutral (cheapest) or BDD, and **never ATDD**.

The takeaway: reach for a disciplined methodology only when you're near a model's capability edge; on a model that clears the task comfortably, the prompt is ritual.

**The decision procedure:**

1. **Hard task, must be right unattended?** → **Opus 5.5 at `effort: low`** (1.00 across all thirteen languages, \$1.33–\$2.73 a cell). Want the deeper evidence behind the 1.00 instead of the 5× saving? → **Fable 5** (1.00, n=21, ~\$10.47).
2. **Hard task, cost dominates and a ~1-in-5 miss is tolerable?** → **GPT-5.6 Terra** (0.79, ~\$1.18) with a review-and-retry loop. At ~1-in-14, **Sonnet 5** (0.93).
3. **Routine, and you have the hardware?** → **Qwen 80B local at `context_threshold: 0.9`, \$0** for **Python, Go and TypeScript** (1.00 each). The **35B** is faster but only Python/Go, at 0.72/0.75. Everything else → cloud.
4. **Routine, cloud?** → the **cheapest qualifying cell in the routing table** — Luna at ~\$0.06–0.08 where it qualifies, Terra at ~\$0.14–0.42 otherwise. They all reach ~1.00, so paying more buys nothing. Use the **neutral** prompt.
5. **Whatever you picked, pass `effort: low` unless its `low` fails your cell.** Four independent sweeps agree the top of the dial buys nothing measurable; on Opus 5.5 it costs 27× and takes 58× as long for an identical result.

---

## Configuration

Reliability is a property of the *stack*, not the model. A leading model on a bad configuration is not a leading stack. These are the settings each one requires.

### Local: Qwen3.6-35B-A3B

| | |
|---|---|
| **Model** | `unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit` (4-bit MLX, ~20 GB) |
| **Serving** | oMLX 0.5.0 · served from `~/models/<name>` |
| **Agent** | Hermes v0.18 with the `hermes-lcm` plugin (`context.engine: lcm`). **v0.20.5 measured equivalent** — exp-61 re-ran the featured Python cells on 0.20.5 and found the same requirement coverage (1.00) and maintainability, with duration ranges that overlap the 0.18.2 baseline almost exactly (m80: 137–300 s vs 137–284 s). The figures below stand on either version. **On ≥ 0.20 you must set `TERMINAL_CWD`** to the working directory — the oneshot agent otherwise runs in `$HOME` and writes nothing to the workspace. |
| **Context** | `context_length: 262144` — set it explicitly; the default fallback is far lower |
| **Compaction** | `lcm.context_threshold: 0.9` **for the 80B** ("full context" — default 0.35 compacts at ~92K and causes intermittent stalls; 0.7 kills the stalls and 0.9 additionally unlocks TypeScript — see exp-34/38; env override: `LCM_CONTEXT_THRESHOLD=0.9`). The 35B is fine at 0.35. |
| **Hardware** | Apple Silicon, 64 GB. Raise the GPU wired limit: `sudo sysctl iogpu.wired_limit_mb=57344` |

**Sampling — this is not optional:**

```yaml
temperature:        0.6     # anything in 0.2–0.7; the requirement is: NOT 1.0
top_p:              0.95
top_k:              20
repetition_penalty: 1.0     # OFF. See forbidden settings.
```

**Harness settings that decide whether the model can work at all:**

```yaml
playpen_root:  ~/.retort/work   # NOT the system temp dir — see forbidden settings
timeout_minutes: 60             # a high wall: local models are slow, let good work finish
stall_minutes:   25             # kill unproductive loops, not slow-but-productive runs
```

**Operational — the local serving layer needs babysitting over long sessions:**

* **Restart oMLX between long runs.** After many hours of continuous serving, oMLX quality degrades — a normally-flawless language (Python is 21/21) starts throwing **fast all-zeros fails** (the model emits garbage in ~2 min). These look like a real result but are a serving artifact; the fix is to kill oMLX (the next run reloads a fresh server) — do it before any run whose result you intend to trust, and treat a sudden cluster of all-zeros on a reliable language as "restart the server," not "the model got worse."
* **Watch the disk — the paged-SSD cache is a trap.** oMLX's `--paged-ssd-cache` grows to its configured cap (a 120 GB default filled a 926 GB disk to 98% in one session) and, per exp-24, **it doesn't help these generation-bound runs at all** — set the cap small (~5–20 GB) or disable it. A full disk makes the agent's file writes fail → false zeros. `retort run` now does a **disk preflight** (aborts under 15 GB free, warns under 40 GB).
* **Configure Time Machine for a benchmarking box — or it will eat the disk.** On macOS/APFS, deleting a big cache doesn't free space if a Time-Machine **local snapshot** still pins the freed blocks (an hourly cadence pinned ~93 GB of already-deleted oMLX cache in one session). Two settings fix it, and everything large here is regenerable (models re-download from HF, the repo state lives in git), so exclude it all from backups:
  ```sh
  # exclude the big, regenerable, high-churn paths (‑p = sticky, survives recreation)
  sudo tmutil addexclusion -p ~/.cache/omlx-ssd     # oMLX paged-SSD prefix cache
  sudo tmutil addexclusion -p ~/.omlx/cache         # oMLX prefix-block cache
  sudo tmutil addexclusion -p ~/models              # MLX weights (re-download from HF)
  sudo tmutil addexclusion -p ~/.cache/huggingface  # HF download cache
  sudo tmutil addexclusion -p ~/.retort/work        # per-run playpens (transient)
  # reclaim space a snapshot is already pinning, now (df won't budge until you do):
  sudo tmutil thinlocalsnapshots / 100000000000 4
  ```
  Also drop the snapshot cadence from **hourly to daily** (e.g. TimeMachineEditor) so cache churn between runs can't pile up dozens of space-pinning snapshots. Exclusions shrink the backup and per-snapshot delta; the daily cadence caps how many pin space at once; thinning clears what's already stuck.

### Local: Qwen3-Coder-30B-A3B-Instruct — which build

Not a featured stack (0.80 on routine python/go, below the 1.00 bar), but the build choice is decided and the wrong one is forbidden above. Use **`mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ`** — 16 GB, zero stalls in 20 runs across four languages, and a pass rate statistically indistinguishable from the 30 GB 8-bit build (8/10 vs 7/10, p = 1.00). Not the 6-bit (0.40, 23 GB) and not the plain 4-bit. Same serving and agent settings as the 35B above; sampling `temperature: 0.6, top_p: 0.95, top_k: 20, repetition_penalty: 1.0`. See exp-64–69.

### Cloud: Opus 5.5, Fable 5, Sonnet 5, GPT-5.6 Terra / Luna

There is no single cloud winner — the pick is set by task size and budget (see the tables above): **Opus 5.5 at `low`** for hard work that must be right, **Fable 5** when you want the better-replicated 1.00, **Sonnet 5** or **Terra** for hard work on a budget, and **Luna / Terra** for routine work, where everything passes and only price differs.

| | |
|---|---|
| **Effort** | **`low`**, on every cloud stack, unless its `low` fails your cell. `claude --effort low`; `codex exec -c model_reasoning_effort=low`. This is the single largest cost lever on this page — 27× on Opus 5.5. |
| **Sampling** | Run the model as shipped. No tuning is required or recommended; unlike local, the provider's defaults are tuned for agentic use. |
| **Prompt** | Plain *neutral*. On cloud models the prompt methodology is a flat line — don't pay for ceremony. |

The stack that matters on cloud is the agent around the model, not the model's knobs.

---

## Forbidden settings

Configurations that measurably degrade a stack. These are eliminated, not tuned.

| Setting | Why it is forbidden |
|---|---|
| **`repetition_penalty` > 1.0** | Any repetition penalty derails an agentic tool-calling loop — the model stops converging, stalls, and produces nothing. This holds even at 1.05, and even when the model's own card recommends it: model-card sampling is tuned for single-turn generation, not multi-turn agent loops. **Set it to 1.0.** |
| **`temperature: 1.0`** (server default) | Costs roughly half the reliability of a local coding stack. Any value in 0.2–0.7 is fine; the precise value does not matter. |
| **Playpen under the system temp dir** (`/var/folders/...` on macOS) | Agents refuse to write to paths they consider system-owned, so the agent cannot create files *in its own workspace* — and a run that writes nothing scores a false zero indistinguishable from an incapable model. Keep playpens under `$HOME`. |
| **Plain 4-bit `Qwen3-Coder-30B-A3B-Instruct-4bit`** | Stalls in an unproductive tool loop until the guard kills it in **80% of agent runs** (32/40 across exp-64/66/69). The `-4bit-DWQ` build of the same model is the same 16 GB and stalls in **0%** (0/20). This is a property of quantization *error*, not bit-count — the 80B's 4-bit build stalls at 0.04 — so it is a per-build verdict: measure the stall rate before trusting any new local build. |
| **An unrecorded stack** | A pass-proportion without the stack it was measured on is not a result. Capture versions, model revision hashes, sampling, agent config, and harness settings — every run writes a `provenance.json`. |

---

## Measured data (auto-generated)

These tables are regenerated from `master.db` by `retort report optimal` — run `retort report optimal --write optimal-blog.md` to refresh everything between the `GEN` markers. The leading stacks table above is generated the same way.

**Per language — cheapest stack that clears its reliability bar (routine task):**

<!-- GEN:per-language START -->
| Language | Routine → cheapest qualifying stack | Reliability | n |
|---|---|---:|---:|
| **c** | GPT-5.6 Terra (codex) ($0.26) | 1.00 | 1 |
| **clojure** | GPT-5.6 Terra (codex) ($0.33) | 1.00 | 1 |
| **cpp** | GPT-5.6 Terra (codex) ($0.26) | 1.00 | 1 |
| **csharp** | GPT-5.6 Terra (codex) ($0.26) | 1.00 | 1 |
| **elixir** | GPT-5.6 Terra (codex) ($0.42) | 1.00 | 1 |
| **erlang** | GPT-5.6 Terra (codex) ($0.34) | 1.00 | 1 |
| **go** | Qwen3-Coder-Next 80B (local, $0, ctx 0.9) ($0) | 1.00 | 3 |
| **java** | GPT-5.6 Terra (codex) ($0.38) | 1.00 | 1 |
| **objc** | GPT-5.6 Terra (codex) ($0.24) | 1.00 | 1 |
| **python** | Qwen3-Coder-Next 80B (local, $0, ctx 0.9) ($0) | 1.00 | 3 |
| **rust** | GPT-5.6 Terra (codex) ($0.14) | 1.00 | 1 |
| **swift** | GPT-5.6 Terra (codex) ($0.22) | 1.00 | 1 |
| **typescript** | Qwen3-Coder-Next 80B (local, $0, ctx 0.9) ($0) | 1.00 | 3 |
<!-- GEN:per-language END -->

**Prompt / testing method — the local sweep (on cloud the prompt is a flat line):**

<!-- GEN:prompt-method START -->
| Prompt | 35B pass | 80B pass |
|---|---:|---:|
| **neutral** | 0.67 (n=3) | 1.00 (n=3) |
| **BDD** | 0.67 (n=3) | 1.00 (n=3) |
| **TDD** | 0.33 (n=3) | 1.00 (n=3) |
| **ATDD** | 0.00 (n=3) | 1.00 (n=3) |
<!-- GEN:prompt-method END -->

---

## Keeping this current

Each new frontier or local model release triggers a qualification pass on the standard tasks. A stack is added only when it leads on an axis someone chooses along, and is removed when it no longer leads on any. The tables are regenerated from `master.db` by `retort report optimal`; run `retort report optimal --health` to check the data before trusting a refresh.

**Known data-pipeline gaps** the generator has to work around (it curates the qualified config in `FEATURED_STACKS` because master.db can't express it):

* **Historical local runs carry a blank `model`** — older runs recorded `agent: hermes-local` but no model, so ~250 rows are attributed to a stack only via their experiment slug. *Fixed going forward*: the harness now always records the resolved model (`stack_metadata()`), so exp-29 and later land with a real model id.
* **No sampling / context columns** — temperature, top_p, top_k, repetition_penalty are absent and `max_context_tokens` is populated only on the newest runs, so "the qualified config" can't be filtered from the data; the tuned experiments are named in the script instead.
* **experiment-11 isn't ingested** — it has no `retort.db` (an empty/aborted experiment).

Backfilling the historical blank-model rows and re-ingesting would let the generator drop its slug curation and become a plain group-by.

*Next review: on the next frontier release, or the next local model that fits 64 GB and tool-calls cleanly.*
