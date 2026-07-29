# The Optimal Stack

*Living document — last reviewed July 2026. This records **what to run today**: the
leading stacks, and the exact configuration each one needs. It is not a history.
Superseded stacks and rejected configurations are not discussed here; they are
retired, and retirement is the point.*

---

## What this document is

A **stack** is the whole thing you actually deploy, not just a model:

> **language × model × quantization × serving layer × agent × context engine × sampling × prompt**

Retort scores stacks on **pass-proportion** — run a stack N times on a real task and
count the fraction whose output *fully implements the spec*: every requirement on a
fixed checklist, tests that actually execute, verified by an independent evaluator. A
run that misses one requirement is a failure, not a 0.9. Read it as *the probability
that a single unattended run comes out completely correct.*

That harsh bar is deliberate, because it is the number that decides whether you can
let a stack work unattended.

## Lifecycle: how a stack gets here, and how it leaves

This document is the human-readable view of a lifecycle the tool already runs. Each
stage is a retort command, so entries here are *derived*, not curated by taste:

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

**A stack earns a place here only by leading on an axis a developer actually chooses
along** — a language, a task size, a cost or latency budget. Being new is not a
qualification. When it leads on none, `retort report pareto` shows it dominated and it
comes out. The list stays short on purpose.

Configurations that reliably degrade a stack are eliminated outright and recorded as
**forbidden settings** (below). New model releases — frontier and local — trigger a
re-qualification pass, so this document is expected to churn.

---

## Start here: the cheapest (model × thinking level) that clears each cell

**A stack is a model *and* a thinking level.** Measured on one cell across four Claude
versions × five effort levels, every one of the 21 combinations passed — and the bill spanned
**16×**, from \$0.42 to \$6.75, for identical output. The dial moves cost more than the
version does, and it moves the result not at all. So the recommendation is a pair, never a
model alone.

The machine-readable form of the table below is committed at **[`optimal.json`](optimal.json)**
(regenerate with `retort report optimal --routing-json optimal.json`) so other tools — the
metaharness router, CI, your own scripts — can consume the routing decision directly rather
than scraping prose.

<!-- GEN:per-language-routing START -->
| Language | Routine → model @ effort | pass | cost | Hard task → model @ effort | pass | cost |
|---|---|---:|---:|---|---:|---:|
| **c** | Opus 4.8 @ `default` <sub>n=1</sub> | 1.00 | $1.28 | Fable 5 @ `default` <sub>n=1</sub> | 1.00 | $10.59 |
| **clojure** | Opus 4.7 @ `default` <sub>n=6</sub> | 1.00 | $1.06 | Opus 5 @ `default` <sub>n=1</sub> | 1.00 | $2.55 |
| **cpp** | Opus 4.8 @ `default` <sub>n=1</sub> | 1.00 | $1.08 | Opus 5 @ `default` <sub>n=1</sub> | 1.00 | $17.50 |
| **csharp** | Opus 4.8 @ `default` <sub>n=1</sub> | 1.00 | $0.65 | Sonnet 5 @ `default` <sub>n=3</sub> | 1.00 | $9.96 |
| **elixir** | Opus 4.8 @ `default` <sub>n=3</sub> | 1.00 | $0.85 | Fable 5 @ `default` <sub>n=1</sub> | 1.00 | $13.21 |
| **erlang** | Opus 4.8 @ `default` <sub>n=3</sub> | 1.00 | $1.35 | Fable 5 @ `default` <sub>n=1</sub> | 1.00 | $12.06 |
| **go** | Qwen3-Coder-Next 80B (local) @ `default` <sub>n=3</sub> | 1.00 | $0 | Opus 4.8 @ `default` <sub>n=6</sub> | 1.00 | $5.30 |
| **java** | Opus 4.7 @ `default` <sub>n=6</sub> | 1.00 | $0.92 | Fable 5 @ `default` <sub>n=1</sub> | 1.00 | $12.01 |
| **objc** | Opus 4.8 @ `default` <sub>n=1</sub> | 1.00 | $1.52 | Fable 5 @ `default` <sub>n=1</sub> | 1.00 | $13.30 |
| **python** | Qwen3-Coder-Next 80B (local) @ `default` <sub>n=3</sub> | 1.00 | $0 | Opus 4.7 @ `default` <sub>n=3</sub> | 1.00 | $4.64 |
| **rust** | Opus 4.8 @ `default` <sub>n=6</sub> | 1.00 | $0.71 | Fable 5 @ `default` <sub>n=3</sub> | 1.00 | $9.63 |
| **swift** | Opus 4.8 @ `default` <sub>n=1</sub> | 1.00 | $1.25 | Fable 5 @ `default` <sub>n=1</sub> | 1.00 | $9.24 |
| **typescript** | Qwen3-Coder-Next 80B (local) @ `default` <sub>n=3</sub> | 1.00 | $0 | Opus 4.7 @ `default` <sub>n=3</sub> | 1.00 | $4.14 |
<!-- GEN:per-language-routing END -->

> **Reading the `effort` column.** Almost every cell says `default`, and that is an honest
> statement rather than a recommendation: **thinking level has only ever been *varied* on one
> cell** (python × bookshop, exp-49). Everywhere else the corpus has exactly one measured
> level, so the router reports the level those runs actually used and does not imply a
> comparison nobody made. Where the dial *was* swept, the finding was consistent — `low` cost
> ~1.6× less than the CLI default at identical reliability, and the default is not the cheap
> end. Expect these to shift toward `low` as the sweep widens.
>
> **A `null` means nothing measured clears the bar for that cell** — not "untested". And read
> the `n`: several cells are n=1, where a 1.00 is much weaker evidence than a 1.00 at n=9.
>
> ✅ **One bar for every stack: 1.00.** Local stacks used to qualify at **0.50**, on the view
> that a \$0 stack is worth a lower bar if you are watching it. That contradicted the metric's
> own definition — *the probability a single **unattended** run comes out completely correct*,
> where a single sub-1.0 run is a fail — and it let a coin flip outrank a perfect stack purely
> on price (python-on-hard-task recommended the local 35B at **0.50**). Being free is already
> expressed in the cost column; it should not also lower the standard.
>
> Raising local to 1.00 did **not** push local out of the recommendations — it picked a *better*
> local stack: routine python and go moved from the 35B (0.87 / 0.85) to the **80B at 1.00,
> still \$0**. The double standard had been hiding the more reliable free option. Hard-task
> python moved from the 35B at 0.50 to **Opus 4.7 at 1.00**, which is the honest answer.

## The leading stacks

Reliability, cost and time are all reported **per task size** — routine and hard are
different jobs, and a stack that is cheap-and-certain on routine work can be neither on a
hard one. The **routine reliability here is a cross-language blend and is the least useful
number in this document** — it hides a stack's weak languages inside its strong ones (local
Qwen passes Python/Go but not Rust; Opus 4.8 dips on Java). Use it only as a rough sort;
the [per-language success-rate matrix](#what-to-run-by-language-and-task-size) below is the
number to actually decide on. (Hard reliability is single-task, measured on Python/Go.)

<!-- GEN:leading-stacks START -->
| Stack | Reliability (routine · hard) | Cost (routine · hard) | Time (routine · hard) |
|---|---:|---:|---:|
| **Claude Opus 5** | 1.00 · 1.00 | $2.68 · $21.67 | 500 s · 2630 s |
| **Claude Fable 5** | 1.00 · 1.00 | $1.58 · $10.47 | 166 s · 1090 s |
| **Claude Sonnet 5** | 1.00 · 0.93 | $1.10 · $7.64 | 237 s · 1252 s |
| **Claude Opus 4.8** | 0.98 · 0.59 | $0.93 · $3.27 | 258 s · 608 s |
| **Claude Opus 4.7** | 1.00 · 0.40 | $0.92 · $2.95 | 165 s · 500 s |
| **Qwen3.6-35B-A3B (local, $0)** | 0.86 · 0.25 | $0.00 · $0.00 | 355 s · 1542 s |
| **Qwen3-Coder-Next 80B (local, $0, ctx 0.9)** | 1.00 · 0.00 | $0.00 · $0.00 | 604 s · 2014 s |
<!-- GEN:leading-stacks END -->

*(Table generated from `master.db` by `retort report optimal`
— do not hand-edit between the markers.)* Each local stack's routine number is scoped to the
languages it is **recommended** for (35B: Python/Go; 80B: Python/Go/TypeScript) — the full
per-language truth, including the languages they fail, is in the matrix below. **On the hard
task local models are now measured and both do poorly** — 35B **0.25**, 80B **0.00** (see the
per-stack bullets). Rust local is unqualified (80B 0.33, near-misses).

> ### ⚠️ Local + hard task: the wall holds unattended, but a repair loop gets through
>
> The 0.00 below is the **unattended, first-attempt** number and it stands — [exp-50](docs/past-experiments.md)
> re-ran it and got **0/6 on first attempts**, matching exp-39 exactly.
>
> What exp-50 adds: with retort's **self-repair second chance** — the cell re-seeded with its own code
> plus the evaluation's critique — the 80B reached full req-coverage on **3 of 6** runs. Every pass was
> a second attempt; none was unattended. At half credit for a second-try pass that is a
> pass-proportion of **0.25** against a published 0.00.
>
> Read it as: **the 80B reliably gets ~11 of 12 capabilities and cannot close the last one alone, but
> closes it about half the time when told what is missing.** "Hard tasks → cloud" remains right for
> unattended use; a local stack *with a repair loop* is a different and more promising proposition.
>
> (The re-test was launched on a theory — a 30-turn agent cap — that turned out to be wrong: the old
> runs took 32–90 turns and nothing truncated them. Kept visible in the write-up.)

**Pick by task size — the two columns tell different stories:**

* **Fable 5** clears the hard task **every time (1.00), in all thirteen languages**. When a
  hard, multi-capability job has to be right unattended, this is the one — ~$10.47 and ~18 min
  a run, and the certainty is what you're buying.
* **Opus 5** also clears the hard task 1.00 in all thirteen, at **~$21.67 and ~44 min** — twice
  the money and 2.4× the time for the same outcome. It held this slot briefly on the strength of
  being the only stack measured across all 13 languages; once Fable 5 was actually run on the
  nine it had been missing, that distinction vanished. **There is no language here where Opus 5
  is the necessary choice.**
* **Sonnet 5** lands **0.93 on hard** at ~15% less than Fable and comparable time — the
  cost-aware hard-task pick when roughly 1-in-14 misses is acceptable.
* **Opus 4.8** is the cheapest *hard-capable* cloud stack, but hard reliability is only
  **~0.59 — a coin flip**, so budget for review-and-retry. On **routine** work it is ~1.00
  and cheap; that's its real niche.
* **Opus 4.7** is a fine, cheap **routine** stack (1.00, ~$0.97) but **weak on hard (0.40)**
  — don't send hard work to it.
* **Qwen 35B local** does **routine** Python / Go for **$0** at **0.85 each** — its real
  niche. Its leading number (0.78) is *lower* than either language because the blend now
  includes its Rust and TypeScript runs, which score **0.00** — the clearest example in this
  doc of why you must read the per-language matrix, not the average. On the **hard task it
  scores 0.25** (3/12) — occasionally nails all 12 capabilities, but not reliably. Rust and
  TypeScript unqualified.
* **Qwen 80B local (`Qwen3-Coder-Next`) — the best local stack for *Python, Go and
  TypeScript* (`context_threshold: 0.9`, "full context").** The featured numbers above are
  now at 0.9, the clean full-9-language baseline (exp-38, n=3/language): **Python 1.00, Go
  1.00, TypeScript 1.00** — all three reliable, all $0. **TypeScript is the unlock**: it was
  0.33 at ctx 0.35/0.7, and raising compaction to full context makes it pass 3/3. It's slower
  than the 35B (~600 s routine). **Rust is 0.33 (1/3) → cloud** — but note its 2 failures are
  *near-misses* (req-coverage 0.92/0.92; the code compiles and its tests pass 100%, it just
  misses 1–2 spec requirements), **not** the thrash-to-the-wall stalls of the old story
  (confirmed via `retort diagnose`+`rescore`+`reevaluate`, which caught them as scorer
  tooling false-failures and recovered their true near-miss scores). The other five languages
  → cloud: java/erlang are near-misses (0/3), and **clojure/csharp/elixir score a genuine
  0.00** — they can't produce working code at all (diagnosed GENUINE, not harness). On the
  **hard task it scores 0.00, and that is now *verified* config-invariant** — re-run at full
  context (exp-39, brazil at 0.9) it is still **0/6**, same as 0.7 (exp-31): Python gets as
  close as **11/12** but never all 12, and Go actually *regresses* (a stall — the same
  late-compaction downside that bites any run that can't finish). So full context is strictly
  for the easy languages; it does not raise the hard-task ceiling. Rule: **80B for local
  Python, Go and TypeScript (at `context_threshold: 0.9`); Rust, the niche languages, and hard
  tasks → cloud.**

> **The 80B's stall was a fixable config artifact, not a capability wall — and raising the
> compaction threshold is a graded lever, not a switch.** The intermittent hang was lcm
> compaction firing too early: at the default `context_threshold: 0.35` it compacts live
> context at ~92K, truncating the agent's working history mid-build so it loses the thread and
> thrashes to the wall. Raising it walks the results up:
>
> * **0.35 → 0.7** kills the Go stalls: over **9 Go runs** (exp-34/36) **0 stalls, Go = 8/9 =
>   0.89** (up from 0.67-with-2-stalls), and Python holds at **1.00** (exp-37). But TypeScript
>   was still only 0.33 here.
> * **0.7 → 0.9 ("full context", compact at ~236K) unlocks TypeScript.** The full-9-language
>   re-baseline at 0.9 (exp-38, n=3) gives **Python 1.00, Go 1.00, TypeScript 1.00** — TS goes
>   from 0.33 to 3/3 because at full context the agent keeps its whole working history through
>   the longer TS build instead of being compacted mid-stream. **So `lcm.context_threshold:
>   0.9` is now the recommended config for the 80B**, and the featured table reflects it (the
>   0.7 runs remain the larger-n Go evidence and the proof that the fix is graded).
>
> The cost of going to 0.9: a run that *can't* finish thrashes longer before failing (6 M
> tokens on a failed Rust/niche cell) — but those languages go to cloud anyway, so it doesn't
> touch the recommended Python/Go/TS path. (The same lever only *partly* rescues the 35B on
> Rust — exp-35: first-ever Rust pass at 0.7, but 2/3 still stall. And it doesn't help the hard
> task: exp-39 re-ran brazil at 0.9 and got the same 0/6 as 0.7, with Go now hitting the
> late-compaction stall — full context helps the easy languages, not the hard ceiling.)
>
> **The same lever partly explains the "Rust wall" — but only partly.** At 0.35 the 35B
> thrashes to the wall on *every* Rust run (clean 0.00). At 0.7 it scored its **first-ever
> Rust pass** (exp-35 rep1 = 1.00, at 113K context — exactly the regime 0.35 truncates), so
> Rust is *not* a pure capability wall. But **2 of 3 still stalled** at 0.7 — unlike the 80B
> (0/6), the 35B on Rust is only partially rescued. Net: raising `context_threshold` is a
> real lever for local non-termination, but its strength is model- and language-dependent —
> a clean fix for the 80B on Go/TS, a partial one for the 35B on Rust. Rust stays → cloud.

> **On the Opus 4.8 hard number.** 0.59 is an honest blend: a small clean run scored 1.00
> (n=6) while a larger one scored 0.50 (n=36). The optimistic single-run figure is not
> representative — treat hard-task Opus 4.8 as a coin flip, not a sure thing.

---

## What to run, by language and task size

**Task size** is the axis that matters most, more than language:

* **Routine** — CRUD, glue, well-trodden patterns, a few interacting requirements.
* **Hard** — a novel domain, many interacting capabilities, real data, a protocol to
  implement correctly (our reference: an MCP server over six datasets, twelve required
  capabilities).

**Start from the per-language success rate, not a single headline number.** This is the
matrix that matters — routine pass-proportion for each language × stack, `pass (n)`,
generated from `master.db`. A blank cell means we have no qualified runs there. Read *down*
a column to see where a model is weak (Opus 4.8 on Java; the 35B local passes Python/Go but
scores 0.00 on Rust/TypeScript; the 80B local is strong on Python but drops on Go/TS), and
*across* a row to pick the cheapest stack that actually passes *that* language:

<!-- GEN:per-language-matrix START -->
| Language | Opus 5 | Fable 5 | Sonnet 5 | Opus 4.8 | Opus 4.7 | Qwen 35B local | Qwen 80B local |
|---|---:|---:|---:|---:|---:|---:|---:|
| **c** | 1.00 (1) | 1.00 (1) | — | 1.00 (1) | — | — | — |
| **clojure** | 1.00 (1) | 1.00 (3) | — | 1.00 (6) | 1.00 (6) | — | 0.00 (3) |
| **cpp** | 1.00 (1) | 1.00 (1) | — | 1.00 (1) | — | — | — |
| **csharp** | 1.00 (1) | 1.00 (1) | 1.00 (3) | 1.00 (1) | — | — | 0.00 (3) |
| **elixir** | 1.00 (1) | 1.00 (1) | — | 1.00 (3) | 1.00 (3) | — | 0.00 (3) |
| **erlang** | 1.00 (1) | 1.00 (1) | — | 1.00 (3) | 1.00 (3) | — | 0.00 (3) |
| **go** | 1.00 (1) | 1.00 (3) | 1.00 (3) | 1.00 (7) | 1.00 (6) | 0.85 (27) | 1.00 (3) |
| **java** | 1.00 (1) | 1.00 (1) | — | 0.83 (6) | 1.00 (6) | — | 0.00 (3) |
| **objc** | 1.00 (1) | 1.00 (1) | — | 1.00 (1) | — | — | — |
| **python** | 1.00 (16) | 1.00 (18) | 1.00 (3) | 1.00 (22) | 1.00 (21) | 0.87 (30) | 1.00 (3) |
| **rust** | 1.00 (1) | 1.00 (3) | 1.00 (3) | 1.00 (6) | 1.00 (6) | 0.00 (2) | 0.33 (3) |
| **swift** | 1.00 (1) | 1.00 (1) | — | 1.00 (1) | — | — | — |
| **typescript** | 1.00 (1) | 1.00 (1) | 1.00 (3) | 1.00 (7) | 1.00 (6) | 0.00 (3) | 1.00 (3) |
<!-- GEN:per-language-matrix END -->

**The language split: Python, Go and TypeScript run locally for free (on the 80B at full
context); every other language means Claude.** The 80B (`Qwen3-Coder-Next`, at
`context_threshold: 0.9`) is reliable on all three — **Python 1.00, Go 1.00, TypeScript 1.00**
(exp-38, n=3 each) — the last only after raising compaction to full context (it was 0.33
below that). The 35B is the faster alternative but only on **Python and Go (0.85 each)**; it
scores **0.00** on TypeScript and Rust even at its tuned config, so its cross-language average
(0.85 when scoped to Python/Go; lower if you blend in the languages it can't do) is exactly
why this document leads with the matrix, not an average. **Rust and the five niche languages
(clojure/csharp/elixir/java/erlang) still go to cloud** — the 80B either near-misses (Rust
0.33, java/erlang) or can't produce working code at all (clojure/csharp/elixir score a genuine
0.00). So local has two stacks for Python/Go and one (the 80B at 0.9) that adds TypeScript.

The recommendation table distills the matrix into, per language, the **cheapest model that
clears routine work**, the **hard-task** pick, and the **prompt / testing method** (the
last is qualitative, from the prompt experiments):

| Language | Routine → cheapest qualifying | Hard task | Prompt / testing method |
|---|---|---|---|
| **Python** | **Qwen 80B local ($0)** 1.00 for reliability, or **35B** 0.85 for more speed | **Fable 5** (1.00); Opus 4.8 cheaper but ~0.59 | **80B:** *neutral* (prompt is a no-op — all pass). **35B:** *neutral*/BDD, never ATDD. Cloud: *neutral* |
| **Go** | **Qwen 35B ($0)** 0.85, or **80B @ ctx 0.9 ($0)** 1.00 — both local-viable | **Fable 5**; Opus 4.8 cheaper / riskier | **35B:** *neutral* or BDD, never ATDD. **80B:** *neutral*. Cloud: *neutral* |
| **TypeScript** | **Qwen 80B @ ctx 0.9 ($0)** 1.00 (n=3) — newly local-viable, or **Opus 4.8 (~$0.65)** | **Fable 5** | **80B:** *neutral* (needs `context_threshold: 0.9`). Cloud: *neutral* |
| **Rust** | **Opus 4.8 (~$0.71)** — local 0.33 (near-misses, → cloud) | **Fable 5** | Cloud: *neutral* |
| **Clojure** | **Opus 4.7 (~$1.06)** | **Fable 5** | Cloud: *neutral* |
| **Java** | **Opus 4.7 (~$0.92)**† | **Fable 5** | Cloud: *neutral* |
| **C#** | **Opus 4.8 (~$0.65)**‡ | **Fable 5** | Cloud: *neutral* |
| **Elixir** | **Opus 4.8 (~$0.85)** | **Fable 5** | Cloud: *neutral* |
| **Erlang** | **Opus 4.8 (~$1.35)** | **Fable 5** | Cloud: *neutral* |
| **C** ᴱ | **Opus 4.8 (~$1.28, n=1)** | **Fable 5** | Cloud: *neutral* |
| **C++** ᴱ | **Opus 4.8 (~$1.08, n=1)** | **Fable 5** | Cloud: *neutral* |
| **Objective-C** ᴱ | **Opus 4.8 (~$1.52, n=1)** | **Fable 5** | Cloud: *neutral* |
| **Swift** ᴱ | **Opus 4.8 (n=1)** | **Fable 5** | Cloud: *neutral* |

† On our routine Java runs Opus 4.8 dipped to 0.83 while 4.7 held 1.00 — small n; review
Java output whichever you use. ‡ C# Opus 4.8 is n=1; Sonnet 5 (~$1.57, n=3) is the
better-sampled fallback. ᴱ C / C++ / Objective-C / Swift are the newer exploratory
languages (exp-43); their routine picks are n=1, so treat them as "known to work once,"
not as reliability estimates.

**Why Fable 5 in every hard-task cell, and not Opus 5?** Both clear all thirteen languages at
1.00. Fable 5 does it for **$10.47 / 18.2 min** per cell against Opus 5's **$21.67 / 43.8 min**
— 2.1× cheaper and 2.7× faster on the identical nine-language subset, using 2.3× fewer agentic
turns. **There is no language in this dataset where Opus 5 is the necessary choice.** (Opus 5
briefly held this column on the strength of being the only model measured across all 13; that
was a gap in *coverage of the comparison*, not a capability difference — see
[exp-48](docs/past-experiments.md).)

**Prompt / testing method — it matters only in proportion to how weak the model is.** The
table above (Python routine) makes the rule concrete: **the prompt is a lever on a weak
model and a no-op on a strong one.**

* **Strong models (all cloud, and the local 80B): flat line.** Every methodology passes —
  the 80B goes **1.00 on all four**, ATDD included. Pick **neutral** and spend nothing on
  methodology ceremony; it's the cheapest and loses nothing.
* **Weak models (the local 35B): the prompt bites.** neutral/BDD 0.67, TDD 0.33, and
  **ATDD 0.00** — a weak model can't carry ATDD's front-loaded discipline and burns the run.
  So on the 35B: neutral (cheapest) or BDD, and **never ATDD**.

The takeaway: reach for a disciplined methodology only when you're near a model's capability
edge; on a model that clears the task comfortably, the prompt is ritual.

**The decision procedure:**

1. **Hard task, must be right the first time, unattended?** → **Fable 5** (1.00). Costliest
   and slowest; certainty is what the premium buys.
2. **Hard task, but cost matters and ~1-in-14 misses is tolerable?** → **Sonnet 5** (0.93),
   ~15% under Fable. Opus 4.8 is cheaper again but only ~0.59 — budget a review-and-retry
   loop if you use it.
3. **Routine, local & free?** (run the 80B at `context_threshold: 0.9`) → **Python: 80B (1.00)**
   for reliability or the **35B (0.85)** for more speed. **Go: 80B (1.00) or 35B (0.85)** — both
   viable. **TypeScript: 80B (1.00)** — newly local-viable at full context (below 0.9 it's a
   coin-flip). Review the output; you'll still see a miss every few runs. (Rust, the niche
   languages, everything else → cloud.)
4. **Routine, any other language?** → cheapest current cloud (Opus 4.7 / 4.8, ~$1); they all
   reach ~1.00, so paying more buys nothing. Use the **neutral** prompt.

---

## Configuration

Reliability is a property of the *stack*, not the model. A leading model on a bad
configuration is not a leading stack. These are the settings each one requires.

### Local: Qwen3.6-35B-A3B

| | |
|---|---|
| **Model** | `unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit` (4-bit MLX, ~20 GB) |
| **Serving** | oMLX 0.5.0 · served from `~/models/<name>` |
| **Agent** | Hermes v0.18 with the `hermes-lcm` plugin (`context.engine: lcm`) |
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

* **Restart oMLX between long runs.** After many hours of continuous serving, oMLX quality
  degrades — a normally-flawless language (Python is 21/21) starts throwing **fast
  all-zeros fails** (the model emits garbage in ~2 min). These look like a real result but
  are a serving artifact; the fix is to kill oMLX (the next run reloads a fresh server) — do
  it before any run whose result you intend to trust, and treat a sudden cluster of
  all-zeros on a reliable language as "restart the server," not "the model got worse."
* **Watch the disk — the paged-SSD cache is a trap.** oMLX's `--paged-ssd-cache` grows to
  its configured cap (a 120 GB default filled a 926 GB disk to 98% in one session) and, per
  exp-24, **it doesn't help these generation-bound runs at all** — set the cap small
  (~5–20 GB) or disable it. A full disk makes the agent's file writes fail → false zeros.
  `retort run` now does a **disk preflight** (aborts under 15 GB free, warns under 40 GB).
* **Configure Time Machine for a benchmarking box — or it will eat the disk.** On macOS/APFS,
  deleting a big cache doesn't free space if a Time-Machine **local snapshot** still pins the
  freed blocks (an hourly cadence pinned ~93 GB of already-deleted oMLX cache in one session).
  Two settings fix it, and everything large here is regenerable (models re-download from HF,
  the repo state lives in git), so exclude it all from backups:
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
  Also drop the snapshot cadence from **hourly to daily** (e.g. TimeMachineEditor) so cache
  churn between runs can't pile up dozens of space-pinning snapshots. Exclusions shrink the
  backup and per-snapshot delta; the daily cadence caps how many pin space at once; thinning
  clears what's already stuck.

### Cloud: Claude Fable 5, Sonnet 5, Opus 4.8 / 4.7

There is no single cloud winner — the pick is set by task size (see the tables above):
**Fable 5** for hard work that must be right, **Sonnet 5** for hard work on a budget,
**Opus 4.8 / 4.7** for cheap routine work.

Run the model as shipped. The stack that matters is the agent around it; **no sampling
tuning is required or recommended, and on cloud the prompt is a flat line** — use the
plain *neutral* prompt and don't pay for methodology ceremony.

---

## Forbidden settings

Configurations that measurably degrade a stack. These are eliminated, not tuned.

| Setting | Why it is forbidden |
|---|---|
| **`repetition_penalty` > 1.0** | Any repetition penalty derails an agentic tool-calling loop — the model stops converging, stalls, and produces nothing. This holds even at 1.05, and even when the model's own card recommends it: model-card sampling is tuned for single-turn generation, not multi-turn agent loops. **Set it to 1.0.** |
| **`temperature: 1.0`** (server default) | Costs roughly half the reliability of a local coding stack. Any value in 0.2–0.7 is fine; the precise value does not matter. |
| **Playpen under the system temp dir** (`/var/folders/...` on macOS) | Agents refuse to write to paths they consider system-owned, so the agent cannot create files *in its own workspace* — and a run that writes nothing scores a false zero indistinguishable from an incapable model. Keep playpens under `$HOME`. |
| **An unrecorded stack** | A pass-proportion without the stack it was measured on is not a result. Capture versions, model revision hashes, sampling, agent config, and harness settings — every run writes a `provenance.json`. |

---

## Measured data (auto-generated)

These tables are regenerated from `master.db` by
`retort report optimal` — run
`retort report optimal --write optimal-blog.md` to refresh everything between the `GEN` markers. The leading
stacks table above is generated the same way.

**Per language — cheapest stack that clears its reliability bar (routine task):**

<!-- GEN:per-language START -->
| Language | Routine → cheapest qualifying stack | Reliability | n |
|---|---|---:|---:|
| **c** | Claude Opus 4.8 ($1.28) | 1.00 | 1 |
| **clojure** | Claude Opus 4.7 ($1.06) | 1.00 | 6 |
| **cpp** | Claude Opus 4.8 ($1.08) | 1.00 | 1 |
| **csharp** | Claude Opus 4.8 ($0.65) | 1.00 | 1 |
| **elixir** | Claude Opus 4.8 ($0.85) | 1.00 | 3 |
| **erlang** | Claude Opus 4.8 ($1.35) | 1.00 | 3 |
| **go** | Qwen3-Coder-Next 80B (local, $0, ctx 0.9) ($0) | 1.00 | 3 |
| **java** | Claude Opus 4.7 ($0.92) | 1.00 | 6 |
| **objc** | Claude Opus 4.8 ($1.52) | 1.00 | 1 |
| **python** | Qwen3-Coder-Next 80B (local, $0, ctx 0.9) ($0) | 1.00 | 3 |
| **rust** | Claude Opus 4.8 ($0.71) | 1.00 | 6 |
| **swift** | Claude Opus 4.8 ($1.25) | 1.00 | 1 |
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

Each new frontier or local model release triggers a qualification pass on the standard
tasks. A stack is added only when it leads on an axis someone chooses along, and is
removed when it no longer leads on any. The tables are regenerated from `master.db` by
`retort report optimal`; run
`retort report optimal --health` to check the data before trusting a
refresh.

**Known data-pipeline gaps** the generator has to work around (it curates the qualified
config in `FEATURED_STACKS` because master.db can't express it):

* **Historical local runs carry a blank `model`** — older runs recorded `agent:
  hermes-local` but no model, so ~250 rows are attributed to a stack only via their
  experiment slug. *Fixed going forward*: the harness now always records the resolved
  model (`stack_metadata()`), so exp-29 and later land with a real model id.
* **No sampling / context columns** — temperature, top_p, top_k, repetition_penalty are
  absent and `max_context_tokens` is populated only on the newest runs, so "the qualified
  config" can't be filtered from the data; the tuned experiments are named in the script
  instead.
* **experiment-11 isn't ingested** — it has no `retort.db` (an empty/aborted experiment).

Backfilling the historical blank-model rows and re-ingesting would let the generator drop
its slug curation and become a plain group-by.

*Next review: on the next frontier release, or the next local model that fits 64 GB and
tool-calls cleanly.*
