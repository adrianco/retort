# How Reliable Is Your AI Coding Stack? I Measured It

*June 2026, updated July 2026 — Adrian Cockcroft*

---

Every few weeks a new frontier model tops the leaderboards, and the implicit advice is "upgrade." Sites like **[llm-stats.com](https://llm-stats.com/)** rank models well across many benchmarks — but they answer a question most engineering teams aren't actually asking. They hold the *stack* constant: one prompt, one harness, a fixed benchmark. They don't tell you whether the newest model is worth 4× the cost **in Rust**, how *reliably* each model gets a Go MCP server completely right, or how long any of it takes.

Those are the variables that decide a real project. So I built **[retort](https://github.com/adrianco/retort)** to measure them properly — with statistical Design of Experiments, the same technique you'd use to tune a manufacturing process. Vary the factors you care about (here: programming **language** × **model version** × **tooling** — and, newly, the **coding agent**, the **prompt methodology**, and **local self-hosted models**), run a factorial grid on a real task, score every cell, and let the analysis tell you which factors actually matter. And because retort accumulates results across a shared database, each new model just gets *added* to what's already known — the point of the project is to measure how each new release behaves without re-running everything. It now spans two tasks, nine languages, the Claude Sonnet/Opus lines (plus a fast-mode variant and the tier-above Fable 5), and **local models running for free on a laptop**. **Newest first:** the most recent work took the whole thing down to an on-device local stack — an M5 laptop, $0 per token — and measured exactly how far it gets against the cloud frontier. That's the headline below; the cloud-model detail (Sonnet 5 and the rest) follows.

## The metric that matters: how often is it *completely* right?

Most code scores grade on a curve — 80% test coverage, a clean linter run, a plausible-looking diff. But for code you intend to ship, "mostly implemented" is a failure, not a B+. So retort's headline metric is **pass-proportion**: run a stack N times and count the fraction whose output *fully implements the spec* — every requirement on a fixed checklist, with tests that actually execute, verified by an independent evaluator.

Read it as **the probability that a single run comes out completely correct.** 3 of 3 → 1.00, 2 of 3 → 0.66, 1 of 3 → 0.33. A run that misses even one requirement counts as a fail, not a 0.9. That's a deliberately harsh bar, and it's the one that matters when you're deciding whether to trust an agent with a feature.

## The headline: the whole landscape, cloud frontier down to a laptop

Here is the full board, every model measured on the two tasks — **pass-proportion = the probability a single run comes out completely correct** — with the newest additions (local, on-device, $0) in bold at the bottom:

| Model | Serving | Brazil MCP (hard) | REST-API (easy) | Cost/run |
|---|---|---:|---:|---:|
| Claude Opus 4.8 | cloud | **1.00** | **1.00** | $5.54 |
| Claude Opus 4.7 | cloud | 0.85 | **1.00** | $4.92 |
| Claude Sonnet 5 *(newest cloud)* ⁴ | cloud | 0.93 | **1.00** | $7.64 |
| Claude Fable 5 ³ | cloud | **1.00** | **1.00** | $8.98 |
| Claude Opus 4.8 fast ² | cloud | **1.00** | **1.00** | $8.72 |
| Claude Sonnet 4.6 | cloud | 0.50 | 0.63 | $1.10 |
| Claude Opus 4.6 | cloud | 0.47 | 0.59 | $1.30 |
| **Qwen3.6-35B-A3B** *(best local)* ⁵ | **local · $0** | — | **0.38** | **$0** |
| **Qwen3-Coder-Next-80B-A3B** *(bigger ≠ better)* ⁷ | **local · $0** | — | 0.33 | **$0** |
| **Qwen3-Coder-30B-A3B** ⁶ | **local · $0** | — | **0.33** | **$0** |
| **Devstral-24B** *(agent-tuned, wrong harness)* ⁸ | **local · $0** | — | 0.17 | **$0** |

² Fast mode (`/fast`), 4 languages. Cost at fast mode's **2× per-token rate** ([announcement](https://www.anthropic.com/news/claude-opus-4-8)) — see [Fast mode](#fast-mode-speed-you-pay-double-for).
³ **Claude Fable 5** — a distinct model a *tier above* Opus 4.8, priced at the same $10/$50 rate as fast mode. More below.
⁴ **Sonnet 5** — experiment 15, a 15-cell language × prompt grid, spec-gated by an independent Opus-4.8 judge; 0.93 hard = 14 of 15 (the miss: Rust + TDD). See [Sonnet 5 in depth](#sonnet-5-in-depth-the-token-bill-the-tdd-lever-and-one-rust-miss).
⁵ **Qwen3.6-35B-A3B**, served with MLX/oMLX and driven by the Hermes agent on an **M5 / 64 GB laptop** — the *easy* task, four mainstream languages (python/go/typescript/rust). Across **all nine** languages it drops to **0.11** — the niche-language wall (Clojure/Java/C#/Elixir/Erlang all fail); a self-repair second chance lifts that to **0.22**, but only within the mainstream. It's the first local stack to crack TypeScript. Full story in the local-model sections just below.
⁶ **Qwen3-Coder-30B-A3B** via llama.cpp — **0.08** at a 32 K context, **0.33** at 128 K: context is the first-order lever for a local model.
⁷ **Qwen3-Coder-Next-80B-A3B** (exp-22), same stack as the 35B. Doubling the model *lowered* first-try reliability (0.33 vs the 35B's 0.50 on these languages) — slower and more prone to never terminating (a Rust run hit the wall at 3.9M tokens). The local mirror of "at the top, extra spend buys nothing."
⁸ **Devstral-24B** (exp-23), a *smaller but agent-tuned* Mistral coder — served via **llama.cpp** (oMLX can't parse its Mistral tool-call format). The lowest local result: 0.17, with **7 of 12 runs never terminating**. Big asterisk: Devstral is tuned for its native OpenHands scaffolding, not Hermes — so this is Devstral on the wrong harness, not its ceiling. Neither *bigger* (80B) nor *agent-tuned-different* (Devstral) beat the general 35B.

The one-line reading, newest first: **a good local model on a laptop gets about a third of the way to the cloud frontier for free — and only in the languages it actually knows** — while the cloud frontier is a solved ~1.00 on easy work, where extra spend (Sonnet 5, fast mode, the tier-above Fable 5) buys latency and cost but no more reliability. The rest of this piece works newest-first: the local-model arc (how it was built and where the wall is), then the cloud-frontier detail.

Two things worth pulling out of the board before the deep dives:

- **On the cloud frontier, newer is more reliable — and the older/cheaper models are coin-flips on hard work.** Opus 4.6 and Sonnet 4.6 got the hard task fully right only ~half the time; each generation buys reliability and charges time and money for it. But at the very top, extra spend buys nothing: Sonnet 5, fast mode, and Fable 5 all match Opus 4.8's 1.00/1.00 at higher prices, because where 4.8 is already perfect there's no reliability left to buy.
- **On a laptop, the whole stack around the model matters more than the model.** Going from 0.08 to 0.38 came from context size, an MLX serving layer that parses the model's tool calls, a model one size up, and an agent that doesn't throw away its own context — none of it a new model. But none of it moves the one hard limit either: language reach.

## Sonnet 5 in depth: the token bill, the TDD lever, and one Rust miss

Sonnet 5 (experiment 15) is the first model added *incrementally* — a 15-cell **language × prompt** grid per task (5 languages × {neutral, TDD, BDD}, one replicate), every cell spec-gated by an independent Opus-4.8 judge. Nothing else was re-run; the other models come from the accumulated database. That *is* the project: measure the new arrival against everything already known.

**Reliability: near-frontier.** Every easy cell fully correct (15/15, pass-proportion 1.00); on the hard task 14 of 15 (0.93), the lone miss Rust-with-TDD, confirmed GENUINE by `retort diagnose` (the code truly didn't pass — not a scoring artefact). That's a hair below Opus 4.8's perfect Brazil and a chasm above the previous Sonnet (0.50).

**Why it costs what it does — the token bill.** Same-tier, Sonnet 5 is a clean quality jump over Sonnet 4.6 — bought with a lot of tokens:

| metric | sonnet-5 | sonnet-4.6 | Δ |
|---|---:|---:|---|
| code_quality (easy / hard) | 0.88 / 0.88 | 0.77 / 0.86 | up on both |
| defect_rate (easy) | 1.00 | 0.82 | **+0.18** |
| cost / run (easy / hard) | **$1.10 / $7.64** | $0.41 / $2.05 | **~3× / ~4×** |
| tokens / run (easy / hard) | **2.0M / 16M** | 0.6M / 2.7M | **3.6× / ~6×** |

Cleaner code and a perfect defect rate — but 3.6–6× the tokens, and on the hard task **more dollars than Opus 4.8** ($7.64 vs $5.54 in the table above). Several cells ran past 20M tokens (C# 21.5M, Rust 22.4M) and $10. Sonnet 5 simply *thinks* more to land those scores; Sonnet's traditional cheaper-tier advantage is gone at the 5-series.

**TDD is the cheap lever.** Across both tasks a test-first prompt gave Sonnet 5 its best maintainability (easy 0.84, hard 0.87) and best coverage (easy 0.94), while neutral and BDD trailed — prompt methodology is a real, nearly-free knob. (The wrinkle: Rust + TDD is also where it failed — the strictest prompt on the fiddliest language.)

**By language**, the older patterns sharpen: Go and C# reach perfect build-quality but are the most token-hungry (token_efficiency ≈ 0); TypeScript is the most token-efficient; Python is cheapest and fastest; Rust is priciest and the sole failure site. Full per-cell tables: [`experiment-15-sonnet5/RESULTS.md`](experiment-15-sonnet5/RESULTS.md).

**How to read it.** Sonnet 5 drags the Sonnet line up to the reliability frontier — but pays for it, landing *above* Opus 4.8 on cost while a notch below on the hardest task. Buy it where its quality edge earns the token bill; for routine work that 4.6/4.7 already pass, it's overhead. *Caveats: single replicate (cells are noisy — one coverage score swung 1.0↔0.22 on a re-run); the `sonnet 4.6` baseline is the historical `sonnet` alias; the hard-task runs use the methodology-neutral Brazil fork vs the master's BDD-baked variant, so hard-task cross-model deltas are indicative, not exact.*

## The controlled view: same cells, two models

Those aggregates mix experiments, so the firm conclusions come from the *within-experiment* comparisons — identical language/tooling cells, run with two models, three replicates each.

**Hard task (Brazil, 6 languages × {4.7, 4.8}):** opus-4.8 passed **18/18** cells; opus-4.7 passed **15/18** — it dropped to 2-of-3 on Go and **1-of-3 on Rust**. So the newer model didn't just win on average; it closed specific, repeatable failure modes. But it took **~1040 s vs ~710 s** per run and cost **~$5.6 vs ~$4.6**.

**Easy task (REST API, 6 languages × {4.7, 4.8}):** both models passed essentially everything (1.00). The *only* measurable difference was that 4.8 was **~50% slower** (243 s vs 165 s) and a bit pricier. Identical result, higher bill.

The pattern is consistent: **each model generation buys you reliability on hard problems, and charges you time and money for it everywhere.** If your work is routine, the premium is wasted; if it's genuinely hard, it may be the difference between "ship it" and "rewrite it."

## Fast mode: speed you pay double for

Opus-4.8 ships a **fast mode** (the `/fast` toggle — same model weights, faster token output), and it's billed at **2× the standard per-token rate**: $10/$50 vs $5/$25 per million input/output tokens, [per the announcement](https://www.anthropic.com/news/claude-opus-4-8). So the real question isn't "is it faster?" — it's "is the speed worth double the price?" I re-ran the same languages on both tasks with fast mode on. Reliability was untouched — **every cell held pass-proportion 1.00, identical to regular 4.8** — but the economics are not what a casual reading suggests:

| Task | Language | Fast 4.8 (speed / cost) | Regular 4.8 (speed / cost) |
|---|---|---:|---:|
| REST-API (easy) | python | **90 s** / $0.74 | 122 s / $0.50 |
| REST-API (easy) | rust | **135 s** / $1.06 | 185 s / $0.71 |
| Brazil (hard) | go | 959 s / $9.90 | 867 s / $4.59 |
| Brazil (hard) | rust | 909 s / $8.90 | 1081 s / $6.09 |

Two things stand out. On the **easy** task, fast mode genuinely shaves wall-clock — roughly 20–40% — but at the 2× rate it still costs *more* in dollars (python: 26% faster, but 48% pricier). On the **hard** task it's the worst of both worlds: you pay about double **and you don't even get the speed** — Go and Python fast runs were *slower* than regular, because a reasoning-bound task is gated by the model thinking, not by how fast it emits tokens.

So fast mode buys **latency, not savings**, and only on routine work. The honest rule is: turn it on when a human is waiting on a quick task and you'll happily pay double to wait less; leave it off for anything hard, where it's pure overhead. (It's also a clean illustration of why you separate "speed" from "capability" as factors — averaging them together would have hidden that the premium pays off in exactly one quadrant and nowhere else.)

A confession is owed here, because it's the whole point of the project: my *first* pass at this section concluded fast mode was **cheaper** — a "free lunch." It wasn't; I'd trusted the cost number the CLI reported, which (I later confirmed by probe) prices fast-mode tokens at the *standard* rate and silently omits the 2× premium. The conclusion flipped completely once the cost was corrected. Measure, then check that what you measured is real — including when the measurement flatters the answer you were hoping for.

## A tier above 4.8: does paying *even more* buy reliability?

Fast mode raised an obvious follow-up. It charges the $10/$50 rate — double Opus 4.8 — for the *same model*, faster. But what about a genuinely *higher* model? **Claude Fable 5** sits a tier above Opus 4.8 and is priced at that same $10/$50 rate (the CLI prices it natively, so no correction needed). If 4.8 is the reliability frontier, does stepping up a tier — at the same premium fast mode charges — actually buy you anything? I ran Fable 5 on the identical grid: both tasks, the four shared languages, three replicates each.

The answer is a clean **no**:

| Task | Language | Fable 5 (pass / speed / cost) | Opus 4.8 (pass / speed / cost) |
|---|---|---:|---:|
| REST-API (easy) | python | 1.00 / 96 s / $0.76 | 1.00 / 88 s / $0.37 |
| REST-API (easy) | rust | 1.00 / 142 s / $1.00 | 1.00 / 213 s / $0.76 |
| Brazil (hard) | go | 1.00 / 998 s / $8.59 | 1.00 / 867 s / $4.59 |
| Brazil (hard) | rust | 1.00 / 1061 s / $9.63 | 1.00 / 1081 s / $6.09 |

Fable 5 passed **12 of 12 cells on each task** — a perfect 1.00, exactly matching Opus 4.8. That's the catch: **where 4.8 already gets it completely right every time, there is no reliability headroom for a better model to capture.** The ceiling is the ceiling. So the higher tier delivers an identical pass-proportion while costing roughly **double the dollars**, and — on the hard task — running *slower* than regular 4.8 (≈1039 s vs ≈947 s), making it the priciest *and* slowest option I measured. Fast mode at least buys latency on easy work; a tier-up here buys nothing measurable at all.

This isn't a knock on Fable 5 — it's a statement about the *task*. Both of these problems are inside Opus 4.8's reliable envelope, and you can't out-reliable 1.00. The place a higher tier would earn its premium is a task hard enough that **4.8 itself drops below 1.00** — and the honest read of this data is that neither task here is that hard. Which is exactly the decision the per-task framing is built to expose: the right model isn't the highest one, it's the cheapest one that clears *your* task's reliability bar. For these two tasks, that's plain Opus 4.8 (or, on the easy one, something cheaper still).

## Two more languages: Erlang and Elixir

I added the two big **BEAM languages** to the REST-API matrix (Erlang, Elixir, on Opus-4.7 and 4.8). They slot straight in at the top: **1.00 on pass-proportion, test coverage, *and* code quality** — every cell, both models. They're the most uniformly clean stacks I measured on the easy task, and Elixir on 4.8 was the cheapest-and-fastest of the pair ($0.85, 207 s). Two languages that weren't in the original grid, measured and ranked in an afternoon — which is the whole point of treating language as just another factor you can add.

## It's not just the model — it's the language *and* the task

Average a model over everything and you hide the most useful signal. Break reliability down by language **and** task and it swings wildly:

| Language | Task | n | Pass | CodeQual | TestCov | Speed (s) | Cost ($) |
|---|---|---:|---:|---:|---:|---:|---:|
| clojure | Brazil (hard) | 12 | 0.75 | 0.83 | 1.00 | 715 | 3.51 |
| clojure | REST-API (easy) | 21 | 0.62 | 0.75 | 0.90 | 302 | 1.10 |
| go | Brazil (hard) | 13 | 0.69 | 1.00 | 0.58 | 773 | 4.35 |
| go | REST-API (easy) | 20 | **1.00** | 1.00 | 0.67 | 142 | 0.61 |
| java | Brazil (hard) | 10 | 0.80 | 1.00 | 1.00 | 784 | 4.03 |
| java | REST-API (easy) | 23 | **0.52** | 1.00 | 1.00 | 208 | 0.78 |
| python | Brazil (hard) | 14 | 0.86 | 0.73 | 0.90 | 638 | 3.30 |
| python | REST-API (easy) | 20 | 0.90 | 0.65 | 0.80 | 97 | 0.43 |
| rust | Brazil (hard) | 10 | **0.50** | 0.83 | 0.93 | 717 | 3.97 |
| rust | REST-API (easy) | 23 | **0.96** | 0.83 | 1.00 | 169 | 0.60 |
| typescript | Brazil (hard) | 12 | 0.92 | 0.61 | 0.82 | 617 | 3.31 |
| typescript | REST-API (easy) | 20 | 1.00 | 0.73 | 0.89 | 168 | 0.56 |

Look at the spread:

- **Rust flips completely**: 0.96 on the easy task, **0.50 on the hard one.** The agents write clean, well-typed Rust for a CRUD API, but the harder knowledge-graph task trips them up half the time.
- **Java runs the other way**: 0.80 on the hard task but only **0.52 on the easy one** — counter-intuitive until you see *how* it fails (over-engineered scaffolding that misses a small requirement on the simple task).
- **TypeScript and Python are the all-rounders**: strong on both (0.92–1.00 and 0.86–0.90).
- And **code quality barely moves across tasks within a language** — Go and Java sit at 1.00 regardless of difficulty — even as their *reliability* swings. Clean code and complete code are not the same thing, and they're driven by different factors (see below).

There is **no single "best language."** "Use Rust, it's rigorous" is good advice for a service and bad advice for the hard task; the only way to know is to run your task.

## What the variance actually comes from (ANOVA)

Because this is a designed experiment, I can decompose *where each metric's variation comes from* — language vs. model vs. tooling — with a type-II ANOVA (cost and time log-transformed, since they scale multiplicatively). The separation of concerns is almost suspiciously clean:

| Response | Dominant factor (variance share) | Reading |
|---|---|---|
| **code_quality** | **language ≈ 94–96%** (p < 10⁻⁴⁰); model ≈ 0% | Quality is the *language's*, not the model's. |
| **test_coverage** | **language ≈ 92–95%** (p < 10⁻¹⁵); model ≈ 0% | Same — the language and its test ecosystem dominate. |
| **duration** | **task ≈ 75%**; model (on a fixed hard task) ≈ 37% | The task sets the clock; the newer model is the slower one. |
| **cost** | **task ≈ 82%**; tooling +10% (p < 0.001) | The task sets the bill; `beads` tooling measurably adds to it. |
| **requirement_coverage** | **model** (borderline, p ≈ 0.06) | The only metric the model meaningfully moves. |

Stated plainly: **language governs how clean the code is, the task governs how much it costs, and the model governs how reliably it's correct.** Three different factors, three different knobs. The practical consequence is sharp — reaching for a newer model to get "better code" is mostly wasted money. It doesn't write *cleaner* code (the language already decided that); it writes *more reliable* code, and charges you time and dollars for it. You can only see that by varying the whole stack and doing the statistics, instead of reading one number off a leaderboard.

(The `beads` issue-tracker tooling I tested showed up in exactly one place — extra cost and time, with no quality or reliability payoff — which is why it was dropped from the later experiments. Worth remembering the next time someone suggests bolting more scaffolding onto an agent "to be safe.")

## Which stacks are actually production-ready?

ANOVA tells you what *moves* each metric; the **stack maturity** view tells you which specific stacks you'd actually trust. `retort maturity` scores each `language × model × tooling × task` combination into a lifecycle phase from its reliability, reproducibility, and completion rate. Of 103 stacks in the combined data, **67 are "production" (ship it), 18 "trial", 12 "screening", and 6 "candidate" (avoid).** Every stack I added in this round — fast mode on both tasks, Erlang and Elixir — landed in production.

The interesting part is the bottom of the list, because it's not random: **the entire immature tail is the hard task, and overwhelmingly the hard task with `beads` tooling.** On Brazil, plain stacks average 0.88 maturity (18 of them production-ready); the same stacks *with `beads`* average **0.54, and only two stay production-ready**. Even Opus-4.8 — the model that aces Brazil bare — drops to "candidate" once you add the tooling. So `beads` isn't merely wasted money on a hard task; it actively *destabilizes the run*. That's a much stronger statement than the ANOVA's "+10% cost," and it's the kind of thing you only see when you score whole stacks instead of averaging a metric.

## A word on failures — and trusting your own harness

A strict bar ("a run only passes if its tests actually execute and it implements the whole spec") is the only honest way to score this — but it cuts both ways, because sometimes a *failure* is your measurement, not the model. Adding Erlang and Elixir and fast mode surfaced three such cases worth being candid about:

- **Elixir looked like a total failure — 0% on every run.** It wasn't: the models wrote valid Elixir (a sample project runs 17 tests, 0 failures). My scorer invoked the test suite with a `mix` sub-command syntax that a recent Elixir release had removed, so the tests never ran and the gate failed them all. One-line fix; all six runs then scored a clean 1.00.
- **The newest runs reported `$0.00`.** A refactor of the agent-runner had quietly stopped parsing the cost telemetry for runs that didn't pin an explicit agent name — the model ran and billed, but the number was dropped on the floor. Fixed and regression-tested.
- **The re-scorer silently did nothing** on the two newest experiments because a database query compared against SQL `NULL` (which is never equal to anything) for designs that had no tooling factor.

And the discipline kept paying off. When I went back to re-run a batch of old `beads`-tooling false-failures under the fixed harness, the rerun job itself broke — it never launched the model, and stamped every cell as a failure in ~1–4 seconds for **$0**. Worse, it *overwrote the good runs it was meant to repair*: one experiment dropped from 36 completed runs to 18. Two things saved the data. First, the runner snapshots each DB before a rerun, so I could restore from the `.pre-rerun.bak` files and lose nothing. Second — and this is the part that generalizes — **the failures were obviously the harness's, not the model's, on sight**: a real model failure on the hard task burns *minutes* of wall-clock and real dollars before it fails the gate, while these died instantly for nothing. That single tell — *time and cost spent* — is the cheapest harness-vs-model lie detector I have, and it caught a corruption that would otherwise have silently halved an experiment.

None of these were model failures; they were all mine, and all are now fixed (or, in the rerun's case, rolled back) — the genuine signal restored intact. The genuine failures, once the harness was honest, fell exactly where the rest of the data predicts: the hard task, with the cheaper models or the extra tooling. The meta-lesson is the same discipline the whole project is built on — **measure, then check that what you measured is real** before you draw a conclusion from it.

## The prompt lever: first data in

For most of these experiments I held one big lever constant: **the prompt** — every run got the same terse "implement TASK.md" instruction. The Sonnet 5 experiment above is the first to vary it as a real factor (neutral / TDD / BDD), and the first data point is encouraging: a **test-first prompt was the cheapest quality Sonnet 5 got** — best maintainability and coverage on both tasks, essentially for free. How you ask plausibly moves reliability as much as which model you pick, and it costs nothing to change.

What's still missing is the *cross-model* version. The high-value question is whether a better prompt lifts a **cheap** model's hard-task pass rate from 0.5 toward the expensive model's 1.0 — because if it does, a prompt change could be worth more than a model upgrade at a fraction of the cost. retort treats `prompt` as just another factor, so the study writes itself: **`prompt × model` on a hard task**, sweeping the full model range rather than one model. That's the experiment I'd run next, and the one with the most direct impact on an engineering budget.

I did get a first four-way sweep — all of neutral / TDD / ATDD / BDD on the local 35B stack, Python only. The ranking was clarifying: **neutral and BDD tied for best** (both 2/3, ~0.97 coverage), **TDD** was middling (1/3), and **ATDD was dead last** (0/3) — the *fourth* experiment running to show the front-loaded acceptance-test discipline actively hurts a local model rather than helping it. And where neutral and BDD tie on reliability, neutral wins on cost by ~2.5× the tokens. For a local model, then, the practical prompt advice inverts the usual "more discipline is better": keep it plain, and *don't* reach for ATDD.

## Beyond the model: varying the *agent* itself

There's a second constant I've started to relax. Every run above used one agent — Claude Code (`claude -p`) — and varied the *model* inside it. But the agent is its own variable: the harness around the model (its tools, its file-editing loop, its planning, its prompt scaffolding) plausibly moves results as much as the weights do. So the obvious question is whether a different **agent** — same class of task, different vendor — lands in a different place.

retort now treats `agent` as a first-class factor. I added a **Google Gemini** adapter (it shells out to the `gemini` CLI exactly the way the Claude path shells out to `claude -p`), so you can put `agent: [claude-code, gemini]` straight into the factor grid and let the same ANOVA decompose how much of quality, reliability, and cost is the *agent* versus the language versus the task. Building it was a good demonstration of why you run things rather than trust them: the integration looked done in a unit test, but the first *live* run caught two things the test couldn't — the CLI was reporting tokens under different field names than I'd assumed (so cost would've been silently wrong), and it quietly refuses to act autonomously in an "untrusted" folder until you pass an explicit flag. Both fixed against the real CLI's behavior.

What I *don't* have yet is the cross-agent data: the free-tier Gemini quota hit a capacity wall before a single cell finished, so the comparison itself is still pending a quota reset or a paid key. But the scaffold is wired and validated, and the more interesting point stands — once you can vary the agent, "which coding agent" becomes a measurable question on *your* task, not a Twitter argument.

## Down to the laptop: a local model on an M5

Everything above runs a frontier model in the cloud. The opposite question is just as interesting: how far does a **local** model — running entirely on a laptop, at $0 per token — get on the same measured bar? Birgitta Böckeler's [experiences with local coding models](https://martinfowler.com/articles/exploring-gen-ai/local-models-for-coding-experiences.html) pointed at **Qwen3-Coder-30B-A3B** (a 30B mixture-of-experts model, only ~3B parameters active per token) as the sweet spot on Apple Silicon, so I put it in the grid on a 64 GB M5 — served locally by `llama.cpp` and driven through the `omp` agent — against the easy bookshop CRUD task, on the four languages Claude aces at ~1.00.

The headline is a reality check. Aggregated over the four languages, the local model came out at **pass-proportion 0.33** — versus the Claude frontier's **~0.98** on the identical task. It is genuinely *agentic* — it plans, calls tools, writes files, runs tests — but it is not *reliable*: Python it can do (it eventually reached 3-of-3), Go it half-manages, and **TypeScript and Rust it fails outright**. And its failures are the dangerous kind: plausible-looking code with a `tests.py` that has no runnable tests, or Go tests that call handlers the model never wrote, so nothing compiles. The lesson Böckeler draws — *code review is not optional with a local model* — falls straight out of the numbers.

**The single biggest lever wasn't the model — it was the context window.** These models are startlingly verbose (one Rust run emitted hundreds of megabytes of repetitive output before it was stopped), and the agent's own preamble is ~23 K tokens before any code is written. At a 64 K context the agent kept *compacting its own history mid-task* and losing the thread; simply giving it room — one large context slot instead of the server's default four small ones — took the pass-proportion from **0.08 to 0.33**, a 4× gain from a config flag, no model change. Past 128 K there was no further gain, and a stricter prompt methodology (ATDD) actually made it *worse* and more expensive — the front-loaded discipline that helps a strong model just overwhelms a weak one.

Measuring this honestly took as much harness work as the runs did. A local runtime crashes under sustained load (a self-restarting server plus flash-attention fixed it); a slow model that never emits a "done" hits the wall and has its finished work discarded unless you cap it gracefully; and — the subtlest — a run that *completes but fails the spec* is a real data point, while a run that *crashes before completing* is not, and conflating the two breaks both your retry logic and your ETA. The strict gate cuts both ways: it's the only honest way to score a local model, but you have to be sure a failure is the model's and not yours.

Which local **agent** you wrap the model in is its own variable, so I ran the swap: **Hermes** (NousResearch) against `omp`, same 30B model and server, same grid. The pitch for Hermes is persistent, SQLite-backed context management — a plausible antidote to the mid-task compaction that hurt `omp`. The first cut was a caution against assuming the fancier harness wins: *default* Hermes came in leaner but **less** reliable — **0.12** pass-proportion vs `omp`'s **0.33** on the same model, Python regressing from 3/3 to 1/3. But that used Hermes' *standard* compression, not its `hermes-lcm` plugin — the lossless DAG-structured context engine that was the actual reason to try it.

So I built the whole "best option" stack and ran it: **Hermes with `hermes-lcm` enabled, driving Qwen3.6-35B-A3B (one size up) served by MLX via oMLX** — whose Qwen-specific kernels parse the tool-call format that stopped `mlx-lm` cold. This is the run that changed the story. It posted **the best local pass-proportion yet — 0.38 overall, 0.50 on the neutral prompt** (up from `omp`'s 0.33 and default-Hermes' 0.12), it ran the bigger model *faster and leaner* than the 30B on llama.cpp, and — the headline — it **cracked TypeScript**: every prior local configuration scored **0/3** there, and this one passes it on both prompts. The same agent that was the *worst* local result without its context engine became the *best* with it, on a stronger model. The one holdout is Rust, which the 35B simply never stops working on — several runs ran to the wall and were logged as *crashed* rather than failed (the harness now tells those apart). Still a long way from the cloud frontier's ~0.98, and Rust is still out of reach — but a free, private, on-device stack now clears an easy task's hardest language, which is a different answer than "local models can't." (Deep thanks to *kamihack* for the oMLX + model + tool-template pointers that unblocked all of this.)

Then I pushed the same stack across **every** language retort measures — the mainstream four plus Clojure, Java, C#, Elixir and Erlang — and hit a wall that no amount of agent or context machinery moves: the five less-common languages went **0 for 15**, every failure confirmed genuine (the toolchains were installed and working; the model just never produced buildable code). `requirement_coverage` was flat zero across all of them — the spec-gate never even had runnable code to grade. Meanwhile the mainstream four held, and Rust — with a tighter turn budget — even posted its **first-ever local pass**. The lesson is sharp: a local model's *language reach* is far narrower than a frontier model's, and it's the one dimension the surrounding stack can't rescue. Wrap it in the best agent, the best context engine, the best serving layer you like — if the weights didn't see enough Clojure, you get zero. Pick a local model for Python/Go/TypeScript glue on a laptop; don't reach for it in Erlang.

One more lever was worth testing, because it's how real agents work: give a failed run a **second chance, handed the evaluation feedback** — the exact requirements it missed and the build/test errors it produced — and let it fix its own code. Counting a repaired pass at half credit (it needed the answer handed to it), this **doubled the effective pass-proportion, 0.11 → 0.22**. That's a cheap, real win, and it's now retort's default: any failure gets one feedback-guided repair attempt before it's recorded. But the doubling came from exactly one place — the languages the model already knows. Python and Go had *every* first-shot failure rescued; hand the same precise feedback to Clojure, C#, Elixir or Erlang and **nothing moved — zero repaired.** The repair attempts even burned 7–30 minutes apiece before producing code that still wouldn't build. So self-repair amplifies competence; it doesn't create it. It patches the languages a local model can already write most of the way to done, and does nothing at all for the ones it can't — which is the whole story of local coding models in one number: the ceiling is *reach*, and feedback only helps you climb toward it where you were already standing.

## Pick the language first, then the model: the best local model *per language*

Developers rarely choose a model in a vacuum — you pick a **language** for the project, then optimize the stack around it. So the practical question isn't "what's the best local model" but "for *my* language, which local model is most reliable?" Broken down that way, across the four local models I ran on the mainstream languages, two things jump out:

| language | 30B | 35B | 80B | Devstral-24B | **best local model** |
|---|---:|---:|---:|---:|---|
| **python** | **1.00** | 0.67 | 0.33 | 0.67 | **30B — 1.00** |
| **go** | 0.33 | 0.50 | **1.00** | 0.00 | **80B — 1.00** |
| typescript | 0.00 | 0.17 | 0.33 | 0.00 | 80B — 0.33 |
| rust | 0.00 | 0.17 | 0.33 | 0.00 | 80B — 0.33 |
| clojure / java / c# / elixir / erlang | — | 0.00 | — | — | *none* |

*(Pass-proportion, neutral prompt, on the M5 laptop. Single-digit replicates, so read the per-cell picks as directional, not exact — but the tiers are robust.)*

- **Python is the most reliable local language, and it isn't close.** *Every* local model handles it — the 30B nails it outright (1.00), and even the models that flounder elsewhere clear it a good share of the time. If your project is Python, a local model is a genuinely viable, free option; it's the one language where a laptop model just works.
- **The best model is language-dependent — there is no universal winner.** The 80B was the *worst* model on average, yet it's the *best* model for **Go** (1.00, where the 30B is a coin-flip). That's the entire case for this view: optimize the model *per language*, not in aggregate, because the aggregate ranking would have told you to skip the 80B and you'd have picked the wrong model for Go.
- **TypeScript and Rust are marginal at best (~0.33)** — reachable, but you'll retry a lot; not something to rely on unattended.
- **The five less-common languages are a flat zero for every model** — the capability wall again. If your project is Clojure, Java, C#, Elixir or Erlang, no local model on this stack is viable today; use the cloud.

The developer takeaway is concrete: **choose the language, then choose the model for that language.** And if the language is yours to pick and you want to stay local and free, choose **Python** — it's where a laptop model is most likely to just get it right.

The bottom line: on a 64 GB laptop, a good local model is a **plan-with-a-big-model, execute-small, review-everything** tool — free and private, but a third as likely to get an *easy* task completely right as the cloud frontier, and no help at all on the languages it can't do. Worth knowing exactly where that line is *before* you rely on it.

## A cache trick that "should" have fixed the 80B — and didn't

Before closing the book on the 80B being *slower and crashier* than the smaller 35B, I chased a tempting explanation. A widely-shared [Mac-Studio tuning write-up](https://mrzk.io/posts/qmlx-maximising-ai-psychosis-minmaxing-mac-studio/) reports **~137×** speedups from an on-disk **KV prefix cache** — and it turned out oMLX's prefix cache is **off by default**. Every local run above had been re-processing its entire growing context *every turn*. That's exactly the kind of serving artifact that could make a big model look worse than it is, so I turned the cache on (`--paged-ssd-cache-dir`) and re-ran the identical 80B grid as a clean on-vs-off comparison.

**The cache works perfectly and it changed nothing.** First-try pass-proportion stayed at **0.33**, crashes went **2 → 3**, and completed-run durations were flat. The server log proves the cache is *hitting* — an **88,000-token prefix restored in ~2.5 seconds** (a cold prefill costs ~150 s), and oMLX even snapshots this hybrid architecture's tricky "non-sliceable" layers to disk correctly. So why no gain? Because our workload is **generation-bound, not prefill-bound**: the 80B generates at ~61 tokens/sec, the context grows to 75–88 K tokens, and each turn spends **~75 seconds *writing* its ~3,400-token reply** — over many turns, straight into the 30-minute wall, no matter how fast the prefix loads. The 137× result is the *mirror image* of agentic coding: it comes from a huge fixed prompt with almost no generation (all prefill), whereas coding is a moderate prompt with heavy multi-turn generation.

The lesson is methodological, and it's why the harness exists: **measure where the time actually goes before you blame the model — or credit a fix.** The 80B wasn't hobbled by a cache miss; it's genuinely throughput-bound in this loop. "Bigger isn't better" survives the ablation, now with a mechanism. And the real lever for slow big models is exposed as *generation* speed — speculative / multi-token decoding to convert wall-crashes into finished runs — not prefix caching, which is worth leaving on but simply isn't the bottleneck here. *(This ablation lives in its own database; it re-runs an existing model with one serving flag flipped, so it's deliberately kept out of the model grid to avoid double-counting the 80B.)*

## The hard task: can a laptop model build a real MCP server?

Everything above measured local models on the *easy* task — a CRUD API. The fair question is whether the best local stack can do something genuinely hard. So I pointed it at **brazil-bench**: a Brazilian-soccer **MCP server** built from a multi-file guide over six real kaggle datasets, with twelve required capabilities — match/team/player/competition queries, league standings computed from results, head-to-head records, aggregate stats, and a test suite (the guide prescribes BDD). This is a task cloud frontier models find non-trivial. I ran the champion 35B stack on **Python and Go** (its two strongest languages), three replicates each, at the model's full **256K context** — which the runs genuinely used, prompts reaching 108K tokens.

**The answer: it copes — in Python, about a third of the time; in Go, never.** One Python run built the whole thing clean — a proper `brazilian_soccer_mcp/` package (server, query engine, data loader) with a passing test suite, **requirement_coverage 1.0, test_coverage 0.90**, in 23 minutes. That's a complete, tested MCP server over real data, produced by a free model on a laptop — a genuinely impressive result for the hard task. But it was **1 of 6**. The other two Python runs got *close* (one a near-miss at 0.83 requirement coverage) but ran out of clock; both Go runs that didn't wall out still couldn't get their tests to execute, one burning **3.2 million tokens** without finishing.

The failure mode is the one the 80B ablation taught us to expect: **non-termination at the 30-minute wall — half the runs.** These runs are generation-bound, the 35B writes at ~54 tokens/sec, and twelve capabilities over six datasets is simply more code than it can finish in the budget. It's not that the model *can't* — the clean Python pass proves it can — it's that it can't *reliably* close a task this big before the clock. And the hard task widens the Python-Go gap into a chasm: on the easy task both languages worked; here Python still carries and **Go collapses to zero.** The through-line of the whole local-model arc, sharpened: a local model is a **Python-first** tool, and the harder the task, the more that's true.

But "Go collapses to zero" turned out to be an artifact of the clock, not the model — and the fix was a one-line config change. If the runs are generation-bound and hitting a 30-minute wall, give them a 60-minute wall. Local models are slow; a local experiment should simply budget more time. So I doubled the timeout and re-ran the identical grid. **Almost everything that mattered roughly doubled or halved in the right direction:** first-try passes went **0.17 → 0.33** (Python 1/3 → 2/3, two clean tested MCP servers), and crashes fell **3 → 1**. The most striking change was Go: at 30 minutes it was *all zeros* — no working code, tests never running — and at 60 minutes every Go run built **high-quality code with passing tests, reaching 0.92 requirement coverage**. Go wasn't incapable of the hard task; it just never had time to finish. The extra clock also *unlocked* self-repair for Go — the runs now complete-and-fail instead of crashing, so they finally qualify for the second chance (though on this hard last mile the repairs didn't quite convert, and one even regressed).

The clock bought the easy wins, and then it stopped. Even at 60 minutes with self-repair, reliability tops out at **0.33 first-try**: Go gets to 0.92 requirement coverage but not 1.0, and the occasional run is genuinely non-terminating (one still walled out at the full hour). The residual failures are now *capability* — the last mile of twelve requirements plus correct MCP wiring — not *budget*. From here the lever is faster generation (more finished turns per minute) or a stronger model, not more wall-clock. Which is the honest shape of local coding on a hard task: a generous time budget makes a laptop model genuinely useful, and then a real ceiling remains.

## So how should you actually choose?

The data suggests a simple decision procedure:

1. **Classify the task.** Is it routine (CRUD, glue, well-trodden patterns) or genuinely hard (novel domain, many interacting requirements)?
2. **Easy task → optimize for cost/speed.** Almost every model fully implements it, so take the cheapest fast one — here that's Opus-4.7, with 4.6 and Sonnet close behind. Paying for the newest model is wasted.
3. **Hard task → pay for reliability if you need it right.** Opus-4.8 was the only model that got the hard task completely right every time. If a half-chance of a subtly-incomplete implementation is unacceptable, that premium is the cost of trust.
4. **Pick the language for quality, not the model.** If you have latitude, Go/Java/Rust score top marks for code quality on these tasks — but check *reliability* for your specific task, because that's where languages diverge.
5. **Don't add tooling for its own sake.** It cost time and money here and changed nothing else.

## How it's measured

Each run gets its own isolated workspace; the agent implements the task, and the code is then built and tested in place. The spec check is the strict part: an independent evaluator verifies the code against a **fixed requirement checklist** for the task, and a run only counts as a pass if it implements *all* of it and its tests actually run. To keep that grading reproducible, the checklist is pinned (so the denominator is constant across runs), a strong model does the judging, and a borderline result gets a second opinion before it's recorded. Every number above is that gate applied across all 258 scored runs — not a hand-picked sample. Per-experiment tables and the combined dataset are in the [README](https://github.com/adrianco/retort) and `master.csv`.

## Try it on your own stack

The point of retort isn't my numbers — it's that you can get *yours*, on *your* task or codebase, in an afternoon:

```text
$ claude
> clone and install https://github.com/adrianco/retort here
> then compare opus 4.6/4.7/4.8 across Go, Rust and Python on this task
```

Claude designs the experiment, installs the toolchains, runs the cells (resuming across usage-limit windows), and scores each one for whether it actually implements the spec. Watch it live with `retort monitor`; roll it all up with `retort aggregate` and run the ANOVA with `retort report effects`.

Leaderboards tell you which model wins in the abstract. Retort tells you which **stack** wins for the code you're shipping — how reliably, how fast, and for how much. Sometimes the answer is the newest model; sometimes it's the one that's four times cheaper. You won't know until you measure it.

*Code, data, and full per-run results: [github.com/adrianco/retort](https://github.com/adrianco/retort)*

