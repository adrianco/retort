# How Reliable Is Your AI Coding Stack? I Measured It

*June 2026 — Adrian Cockcroft*

---

Every few weeks a new frontier model tops the leaderboards, and the implicit advice is "upgrade." Sites like **[llm-stats.com](https://llm-stats.com/)** rank models well across many benchmarks — but they answer a question most engineering teams aren't actually asking. They hold the *stack* constant: one prompt, one harness, a fixed benchmark. They don't tell you whether the newest model is worth 4× the cost **in Rust**, how *reliably* each model gets a Go MCP server completely right, or how long any of it takes.

Those are the variables that decide a real project. So I built **[retort](https://github.com/adrianco/retort)** to measure them properly — with statistical Design of Experiments, the same technique you'd use to tune a manufacturing process. Vary the factors you care about (here: programming **language** × **model version** × **tooling** — and, newly, the **coding agent** itself), run a factorial grid on a real task, score every cell, and let the analysis tell you which factors actually matter. Nine experiments, **258 scored runs**, two tasks, eight languages, four Claude models (plus a fast-mode variant and a next-tier model, Fable 5). Here's what came out.

## The metric that matters: how often is it *completely* right?

Most code scores grade on a curve — 80% test coverage, a clean linter run, a plausible-looking diff. But for code you intend to ship, "mostly implemented" is a failure, not a B+. So retort's headline metric is **pass-proportion**: run a stack N times and count the fraction whose output *fully implements the spec* — every requirement on a fixed checklist, with tests that actually execute, verified by an independent evaluator.

Read it as **the probability that a single run comes out completely correct.** 3 of 3 → 1.00, 2 of 3 → 0.66, 1 of 3 → 0.33. A run that misses even one requirement counts as a fail, not a 0.9. That's a deliberately harsh bar, and it's the one that matters when you're deciding whether to trust an agent with a feature.

## The headline: newer is more reliable — and you pay for it

Aggregated per model per task:

| Model | Brazil MCP (hard) | REST API (easy) | Speed (hard) | Cost (hard) |
|---|---:|---:|---:|---:|
| opus-4.6 | 0.47 | 0.59 | 309 s | $1.30 |
| sonnet | 0.50 | 0.63 | 440 s | $1.10 |
| opus-4.7 | 0.85 | **1.00** | 774 s | $4.92 |
| **opus-4.8** | **1.00** | **1.00** | 1035 s | $5.54 |
| opus-4.8-fast² | **1.00** | **1.00** | 887 s | $8.72 |
| fable-5³ | **1.00** | **1.00** | 1039 s | $8.98 |

² Fast mode (`/fast`), 4 languages (clojure/go/python/rust). Cost is at fast mode's **2× per-token rate** ([announcement](https://www.anthropic.com/news/claude-opus-4-8)) — see [Fast mode](#fast-mode-speed-you-pay-double-for) below.
³ **Claude Fable 5** — a distinct model a *tier above* Opus 4.8 — same 4 languages, priced at the same $10/$50 rate as fast mode. More on it just below.

Three things jump out:

1. **Newer genuinely is more reliable — and the gap is enormous on hard tasks.** Opus-4.8 produced a completely-correct result **100% of the time, on both tasks.** The older, cheaper models (4.6 and Sonnet) got the *hard* task fully right only **about half the time.** On a difficult task, the cheap model is a coin-flip — it'll look fine in a demo and bite you in review.
2. **You pay through the nose for that reliability.** Opus-4.8 was **~3× slower and ~4× more expensive** than 4.6/Sonnet on the hard task. Reliability isn't free; it's a line item, and it grows fast across model generations.
3. **Opus-4.7 is the value sweet spot, and on easy work the newest model is pure overhead.** On the REST API, 4.7 and 4.8 are *tied* at 100% — so paying for 4.8 there buys you nothing but a slower, costlier run. On the hard task, 4.7 reaches 85% for noticeably less money than 4.8's 100%.
4. **Fast mode is the same reliability at the *highest* price — and so is a tier *above* 4.8.** Opus-4.8 fast matches 4.8's 1.00/1.00 and trims wall-clock, but its 2× per-token rate makes it one of the costliest rows ($8.72/run on the hard task) — it buys latency, not value. And **Claude Fable 5**, a model a whole tier above 4.8 at that same 2× rate, *also* lands at 1.00/1.00 — because where 4.8 is already perfect there's simply no reliability left to buy. It ends up the priciest *and* slowest option, with nothing to show for it (more below).

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

## The factor I haven't varied yet: the prompt

There's a large lever I deliberately held constant: **the prompt.** Every run got the same terse "implement TASK.md" instruction. But how you ask plausibly moves reliability as much as which model you pick — and it's nearly free to change. Does a test-first prompt, or one with a worked example, or a "list the requirements before you code" preamble, lift a cheap model's hard-task pass rate from 0.5 toward the expensive model's 1.0? If so, a better prompt could be worth more than a model upgrade, at a fraction of the cost. retort treats `prompt` as just another factor, so the next study writes itself: **`prompt × model` on a hard task.** That's the experiment I'd run next, and it's the one with the most direct impact on a real engineering budget.

## Beyond the model: varying the *agent* itself

There's a second constant I've started to relax. Every run above used one agent — Claude Code (`claude -p`) — and varied the *model* inside it. But the agent is its own variable: the harness around the model (its tools, its file-editing loop, its planning, its prompt scaffolding) plausibly moves results as much as the weights do. So the obvious question is whether a different **agent** — same class of task, different vendor — lands in a different place.

retort now treats `agent` as a first-class factor. I added a **Google Gemini** adapter (it shells out to the `gemini` CLI exactly the way the Claude path shells out to `claude -p`), so you can put `agent: [claude-code, gemini]` straight into the factor grid and let the same ANOVA decompose how much of quality, reliability, and cost is the *agent* versus the language versus the task. Building it was a good demonstration of why you run things rather than trust them: the integration looked done in a unit test, but the first *live* run caught two things the test couldn't — the CLI was reporting tokens under different field names than I'd assumed (so cost would've been silently wrong), and it quietly refuses to act autonomously in an "untrusted" folder until you pass an explicit flag. Both fixed against the real CLI's behavior.

What I *don't* have yet is the cross-agent data: the free-tier Gemini quota hit a capacity wall before a single cell finished, so the comparison itself is still pending a quota reset or a paid key. But the scaffold is wired and validated, and the more interesting point stands — once you can vary the agent, "which coding agent" becomes a measurable question on *your* task, not a Twitter argument.

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

## Sonnet 5 — the quality is real, but so is the token bill (experiment 15)

This is the first experiment run *incrementally*: we changed only one thing — added **Claude Sonnet 5** — and ran it across the same 5 languages × 3 prompt methodologies × 2 tasks grid. Sonnet 4.6 and Opus 4.8 aren't re-run; their numbers come straight from the accumulated `master.db`. That's the whole point of Retort: each new model is measured against everything already known, not benchmarked from scratch. 29 Sonnet 5 cells, one replicate. Full tables in [`experiment-15-sonnet5/RESULTS.md`](experiment-15-sonnet5/RESULTS.md).

**The headline: Sonnet 5 is the highest-quality model we've measured — and the most expensive to run, by a wide margin.**

On the easy CRUD task it's a clean step up over the current Sonnet:

| metric (rest-api-crud) | sonnet-5 | sonnet-4.6 | Δ |
|---|---|---|---|
| code_quality | 0.88 | 0.77 | **+0.11** |
| test_coverage | 0.87 | 0.78 | **+0.09** |
| defect_rate | 1.00 | 0.82 | **+0.18** |
| idiomatic | 0.72 | 0.64 | +0.08 |
| token_efficiency | 0.35 | 0.39 | −0.04 |
| **cost / run** | **$1.10** | **$0.40** | **+$0.70** |
| tokens / run | 2.0M | 0.56M | **3.6×** |

Every quality metric improves — a perfect defect rate, higher coverage, cleaner code — but it burns **3.6× the tokens** and costs nearly **3× more** per run. On the easy task Sonnet 5 is even pricier than Opus 4.8 ($1.10 vs $0.96), though Opus still edges it on raw test coverage (0.95).

The hard task (the Brazilian-soccer MCP server) is where the trade sharpens:

| model (brazil) | n | code_quality | test_coverage | maintainability | cost / run | tokens / run |
|---|---|---|---|---|---|---|
| **sonnet-5** | 14 | **0.88** | **0.92** | **0.68** | **$7.53** | **15.6M** |
| sonnet-4.6 | 48 | 0.86 | 0.91 | 0.60 | $2.05 | 2.7M |
| opus-4.8 | 26 | 0.86 | 0.87 | 0.58 | $5.53 | 5.3M |

Sonnet 5 tops every quality column on the hard task — but at **5.7× the tokens of Sonnet 4.6** and more cost than Opus 4.8. It's not a small effect: several cells ran to 20M+ tokens (csharp 21.5M, rust 22.4M) and $10+ each. Sonnet 5 "thinks" a great deal more to get there.

**Prompt methodology matters — and TDD is the lever.** Telling Sonnet 5 to work test-first gave it the best maintainability on *both* tasks (easy: 0.84, hard: 0.87) and the best coverage (easy: 0.94), while BDD and neutral prompts landed lower. If you run Sonnet 5, a TDD prompt is close to free quality.

**By language**, the patterns from earlier experiments hold and sharpen: Go and C# reach perfect build-quality but are the most token-hungry (token_efficiency ≈ 0); TypeScript is the most token-efficient; Python is cheapest and fastest; Rust is the priciest — and it's where Sonnet 5 hit its **one genuine failure** (rust + TDD on the hard task, 14/15 hard cells passed; classified GENUINE by `retort diagnose`, not a scoring artefact).

**How to read this.** If you're paying per token, Sonnet 5 is a *quality* upgrade you buy deliberately — best-in-class correctness and maintainability, especially on hard tasks, at 3–6× the token cost of Sonnet 4.6 and more than Opus 4.8. For routine work where 4.6 already passes, the extra spend may not pay for itself; for hard, correctness-critical builds, Sonnet 5 currently sets the bar.

*Caveats: single replicate, so treat individual cells as noisy (we saw a cell's coverage swing 1.0↔0.22 across re-runs earlier in this experiment). The `sonnet-4.6` baseline is the historical `sonnet` alias in master.db. The hard-task Sonnet 5 runs use the methodology-neutral brazil fork while the master baseline is the BDD-baked variant, so hard-task cross-model deltas are indicative, not exact.*

