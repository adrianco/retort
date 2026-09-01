# How Reliable Is Your AI Coding Stack? I Measured It

*Published 2026-06-11 · updated 2026-09-01 — Adrian Cockcroft*

---

Every few weeks a new frontier model tops the leaderboards, and the implicit advice is "upgrade." Sites like **[llm-stats.com](https://llm-stats.com/)** rank models well across many benchmarks — but they answer a question most engineering teams aren't actually asking. They hold the *stack* constant: one prompt, one harness, a fixed benchmark. They don't tell you whether the newest model is worth 4× the cost **in Rust**, how *reliably* each model gets a Go MCP server completely right, or how long any of it takes.

Those are the variables that decide a real project. So I built **[retort](https://github.com/adrianco/retort)** to measure them properly — with statistical Design of Experiments, the same technique you'd use to tune a manufacturing process. Vary the factors you care about (here: programming **language** × **model version** × **tooling** — and, newly, the **coding agent**, the **prompt methodology**, and **local self-hosted models**), run a factorial grid on a real task, score every cell, and let the analysis tell you which factors actually matter. And because retort accumulates results across a shared database, each new model just gets *added* to what's already known — the point of the project is to measure how each new release behaves without re-running everything. It now spans two tasks, **thirteen** languages, the Claude Sonnet/Opus lines (plus a fast-mode variant, the tier-above Fable 5, and the newest Opus 5), **OpenAI's Codex line (GPT-5.6)**, and **local models running for free on a laptop**.

## What's new (2026-09-01)

- **Fable 5.1 landed, and the headline is: run it at low effort.** Across four languages with twelve runs per arm, **default effort costs 1.68× the wall-clock and 1.45× the money for statistically identical test coverage** (exact paired permutation test, p = 0.0015 for time and 0.0010 for cost; 11 of 12 matched pairs favour low). Turning the dial up on this model buys nothing measurable and bills you 45% more for it.
- **A caution on the new release itself.** On the one cell Fable 5 and 5.1 have both run, 5.1 used **1.74× the wall-clock and 2.19× the tokens** of 5.0. That is flagged rather than claimed — it is three runs a side, 5.1's own spread on that cell is wide, and the Claude Code CLI version moved between the two, so agent version is confounded with model version. Worth knowing before assuming a point release is a free upgrade.
- **A note on how these numbers are earned.** An earlier experiment the same week ran three runs per arm and could not have reached significance *whatever* the effect: with three-vs-three there are only twenty ways to split the runs, so the smallest achievable p-value is 0.10. It found perfect separation on one metric and still scored 0.10. The Fable 5.1 result above is trustworthy because the design was sized to be, not because the effect looked big.

### Earlier (2026-07-30)

- **A second vendor.** OpenAI's **Codex** (GPT-5.6 Terra and Luna, via `codex exec`) is now measured alongside Claude — the first non-Claude cloud lineage here. On the routine task **Terra scores 1.00 across all five thinking levels for \$0.15–0.35 a run**, against Opus 5's \$0.81–14.21 for the same result.
- **Thinking level is now a factor**, and it matters more than the model choice: a matched-effort comparison spans **40×** in cost at identical reliability. The unit of choice is *(model × effort)*, not model.
- **The dial is not the same instrument at both vendors.** Turning it up adds agentic steps on Opus 5 (16 → 92 turns) but leaves Terra's step count flat (10–19) — so cost compounds on one and barely moves on the other.
- Earlier: the local stack (Qwen3-Coder-Next 80B at full context) runs Python, Go *and* TypeScript at **1.00 for \$0** — the first time a free laptop stack matched the cloud frontier on those three.


## The metric that matters: how often is it *completely* right?

Most code scores grade on a curve — 80% test coverage, a clean linter run, a plausible-looking diff. But for code you intend to ship, "mostly implemented" is a failure, not a B+. So retort's headline metric is **pass-proportion**: run a stack N times and count the fraction whose output *fully implements the spec* — every requirement on a fixed checklist, with tests that actually execute, verified by an independent evaluator.

Read it as **the probability that a single run comes out completely correct.** 3 of 3 → 1.00, 2 of 3 → 0.66, 1 of 3 → 0.33. A run that misses even one requirement counts as a fail, not a 0.9. That's a deliberately harsh bar, and it's the one that matters when you're deciding whether to trust an agent with a feature.

## The headline: the whole landscape, cloud frontier down to a laptop

Here is the full board, every model measured on the two tasks — **pass-proportion = the probability a single run comes out completely correct** — with the newest additions (local, on-device, $0) in bold at the bottom:

<!-- GEN:model-board START -->
| Stack | Serving | Easy: pass | Easy: $ | Hard: pass | Hard: $ |
|---|---|---:|---:|---:|---:|
| Claude Opus 5 | cloud | **1.00 (47)** | $3.23 | **1.00 (23)** | $26.48 |
| Claude Fable 5 | cloud | **1.00 (36)** | $1.58 | **1.00 (21)** | $10.47 |
| GPT-5.6 Terra (codex) | cloud | **1.00 (29)** | $0.24 | **1.00 (19)** | $0.81 |
| GPT-5.6 Luna (codex) | cloud | 0.67 (9) | $0.09 | *not run* | — |
| Claude Sonnet 5 | cloud | **1.00 (15)** | $1.10 | 0.93 (15) | $7.64 |
| Claude Opus 4.8 | cloud | 0.98 (65) | $0.93 | 0.59 (44) | $3.27 |
| Claude Opus 4.7 | cloud | **1.00 (57)** | $0.92 | 0.40 (42) | $2.95 |
| **Qwen3.6-35B-A3B (local, $0)** | **local · $0** | 0.86 (57) | $0 | 0.25 (12) | $0 |
| **Qwen3-Coder-Next 80B (local, $0, ctx 0.9)** | **local · $0** | **1.00 (9)** | $0 | 0.00 (6) | $0 |
<!-- GEN:model-board END -->

*Table generated from `master.db` by `retort report optimal --write model-blog.md` — do not hand-edit between the markers. The same numbers are published machine-readably in [`optimal.json`](optimal.json) under `models`, so the table and the JSON cannot drift apart. Retired/legacy stacks that no longer lead on any axis (Opus 4.6, Qwen3-Coder-30B, Devstral-24B) are covered in the footnotes rather than the board.*

**Terra is the cheapest 1.00 on the board — by a factor of 4 to 15 against every Claude stack that also scores 1.00 on the routine task.** \$0.22 a run against Fable 5's \$1.58, Opus 5's \$3.23, and Opus 4.7's \$0.92, all at the same verified reliability. On matched thinking levels the gap runs from 4.3× to 40× (see [versions-blog](versions-blog.md)). If your work looks like the routine task, that is not a close call.

**But "Codex is the better model" is not what this table says yet, and it is worth being precise about why.** Terra's hard-task row reads *not run* — not 0.00, not a failure, simply unmeasured. Claude's advantage on this board is entirely in a column Terra has not entered. And Luna, the tier that *has* been pushed a little further, sits at 0.67, having shipped TypeScript whose tests it had watched fail.

This project has made exactly this mistake before, in the other direction. exp-46 crowned Opus 5 "the only model that clears the hard task in every language" — a claim that survived precisely as long as it took to *run* Fable 5 on the nine languages nobody had tried it on. Fable 5 cleared all nine, at half the cost. **An unrun cell and an unpassable cell look identical in a results table.** Terra's blank hard-task column is that same blank, and the honest reading is "cheapest thing that clears routine work, hard task pending" rather than "better model".

The hard-task run is in progress. If Terra holds 1.00 there at anything like these prices, the recommendation changes across the board; if it collapses the way local models do on brazil, Claude keeps the hard-task tier and Codex owns the routine one. Either way the table will say so.

> **Read the replicate counts (in brackets), and mind the language mix.** These are all-language averages, and the models have *not* all been run on the same languages. Opus 4.8 and 4.7 have been pushed across all thirteen — including the ones nothing handles well — while Opus 5 and Fable 5 have 13–14 hard-task cells each. A model tested only on the languages it is good at will look better than one tested everywhere. **The per-language matrix in [optimal-blog.md](optimal-blog.md) is the like-for-like comparison; this board is a summary.** This is also why Opus 4.8's hard-task number reads 0.57 here where an earlier version of this board said 1.00 — that figure came from a three-language subset (Python/Go/TypeScript), which is where 4.8 *is* reliable.

¹² **GPT-5.6 Terra / Luna** via `codex exec` — the first non-Claude cloud lineage here, and **routine-task only so far** (the hard-task column is genuinely unrun, not a failure). The cost column above is hard-task, so it is blank for both; on the routine task **Terra averages \$0.22 and Luna \$0.09 a run**. Terra is 20/20 at 1.00 across all five thinking levels on Python+Go. Luna is 1.00 on Python and Go but 0.00 on TypeScript — a genuine failure, not a harness artifact: it chose a native dependency that will not build on this machine's Node, watched its own tests fail, and shipped anyway — giving 0.67 over the three languages. Cost for both is **computed at list price per token**, since a ChatGPT subscription reports none; recording \$0 would have made them win every cheapest-stack ranking on a number nobody measured.

² Fast mode (`/fast`), 4 languages. Cost at fast mode's **2× per-token rate** ([announcement](https://www.anthropic.com/news/claude-opus-4-8)) — see [Fast mode](#fast-mode-speed-you-pay-double-for).
³ **Claude Fable 5** — a distinct model a *tier above* Opus 4.8, priced at the same $10/$50 rate as fast mode. More below.
⁴ **Sonnet 5** — experiment 15, a 15-cell language × prompt grid, spec-gated by an independent Opus-4.8 judge; 0.93 hard = 14 of 15 (the miss: Rust + TDD). See [Sonnet 5 in depth](#sonnet-5-in-depth-the-token-bill-the-tdd-lever-and-one-rust-miss).
⁵ **Qwen3.6-35B-A3B**, served with MLX/oMLX and driven by the Hermes agent on an **M5 / 64 GB laptop**. At correct sampling (temp 0.6, not the old 1.0) and a true 256K context it does **Python and Go at 0.85 each** — the *faster* local pick for those two — but scores **0.00 on TypeScript and Rust** even fully tuned, so its niche is Python/Go only. On the hard task (brazil) it manages **0.25** — it occasionally nails all 12 capabilities, not reliably. Full story in the local-model sections below.
⁶ **Qwen3-Coder-30B-A3B** via llama.cpp — **0.08** at a 32 K context, **0.33** at 128 K: context is the first-order lever for a local model.
⁷ **Qwen3-Coder-Next-80B-A3B** — now the **featured local stack**, once its compaction threshold was raised to full context (`lcm context_threshold: 0.9`). At that setting it runs **Python 1.00, Go 1.00, and TypeScript 1.00** (n=3 each) — TypeScript was only 0.33 at lower thresholds, so *full context, not a new model,* is what unlocked it. **Rust is 0.33** (genuine near-misses, → cloud) and the five niche languages (Clojure/C#/Elixir/Java/Erlang) stay ~0.00. It's slower than the 35B (~600 s routine). The earlier "bigger ≠ better" reading was a config artifact of over-early compaction, now fixed.
¹¹ **gpt-oss-20b** (exp-47) — the first **non-Qwen** local lineage that works end to end: oMLX parses its Harmony tool calls into proper OpenAI `tool_calls`, so unlike Laguna (architecture wall) and Devstral (unparseable Mistral format) it is both servable and drivable by Hermes. From a quarter the 80B's memory it is **3–7× quicker** — but at n=5 it is **reliable at nothing**: Go 0.80, TypeScript 0.60, Python 0.40. It is also this project's best argument for replicates: Go was **1.00 through three replicates** and was about to be published as "matches the 80B at 3.6× the speed" when replicates 4–5 took it to 0.80. All three of its zero-scoring runs were reproduced by hand and are genuine model errors — two `tsc` failures (one where the model appended a *second copy* of the app into `index.ts`) and a Python run where it wrote an `httpx` shim that imports itself.

¹⁰ **Claude Opus 5** (exp-46) — run across **all thirteen languages on both tasks**, 26/26. It was briefly the only model known to clear the hard task everywhere; **exp-48 removed that distinction.** Fable 5 had never been *run* on 9 of the 13 languages, and when it was, it cleared all 9 — reaching the same **13/13** at **$10.47 / 18.2 min** against Opus 5's **$21.67 / 43.8 min**. On the identical nine-language subset: **2.1× cheaper, 2.7× faster, same 1.00**. Languages only Opus 5 clears: **none**. It also takes ~2.3× the agentic turns of Fable 5 for an identical routine result (see [versions-blog.md](versions-blog.md)). On current evidence Opus 5 is the most expensive route to a result Fable 5 also reaches.

⁸ **Devstral-24B** (exp-23), a *smaller but agent-tuned* Mistral coder — served via **llama.cpp** (oMLX can't parse its Mistral tool-call format). The lowest local result: 0.17, with **7 of 12 runs never terminating**. Big asterisk: Devstral is tuned for its native OpenHands scaffolding, not Hermes — so this is Devstral on the wrong harness, not its ceiling. Neither *bigger* (80B) nor *agent-tuned-different* (Devstral) beat the general 35B.
⁹ **The hard task, local.** Both local models are now measured on brazil-bench and both do poorly: the 80B scores **0.00 (0/6)** and the 35B **0.25**. The 80B gets *closer on average* (consistently ~10–11 of 12 capabilities) but never lands all 12. Crucially the 80B's 0.00 is now **verified config-invariant** — re-run at full context (`context_threshold: 0.9`) it is still 0/6, identical to the lower threshold: full context lifts the *easy* languages, not the hard-task ceiling. Hard tasks stay a cloud-frontier niche (Fable 5 = 1.00).

The one-line reading, newest first: **a good local model on a laptop now matches the cloud frontier for free on the languages it knows — Python, Go and TypeScript all reach 1.00 on the easy task — but only there**; Rust, the niche languages, and the hard task all still need the cloud. Meanwhile the cloud frontier is a solved ~1.00 on easy work, where extra spend (Sonnet 5, fast mode, the tier-above Fable 5) buys latency and cost but no more reliability. The rest of this piece works newest-first: the local-model arc (how it was built and where the wall is), then the cloud-frontier detail.

Two things worth pulling out of the board before the deep dives:

- **On the cloud frontier, newer is more reliable — and the older/cheaper models are coin-flips on hard work.** Opus 4.6 and Sonnet 4.6 got the hard task fully right only ~half the time; each generation buys reliability and charges time and money for it. But at the very top, extra spend buys nothing: Sonnet 5, fast mode, and Fable 5 all match Opus 4.8's 1.00/1.00 at higher prices, because where 4.8 is already perfect there's no reliability left to buy.
- **On a laptop, the whole stack around the model matters more than the model.** The climb from 0.08 to a reliable Python/Go/TypeScript 1.00 came from context size, an MLX serving layer that parses the model's tool calls, a model one size up, an agent that doesn't throw away its own context, and — the final unlock — raising that agent's compaction threshold to full context. None of it a new capability; all of it configuration. What it still doesn't move is the last hard limit: Rust, the niche languages, and the hard task.

## Newest: the model is the wrong unit — it's (model × thinking level), and that spans 40×

Every frontier model now ships a **thinking-level dial**, and a second vendor has arrived in this corpus. Put those together and the headline question changes from *"which model?"* to *"which model at which setting?"* — because the setting moves the bill further than the model does.

**One routine task (Python + Go bookshop), two price-peer models, the same five effort levels set explicitly on both, n=2. Every one of the 20 cells scored 1.00.**

| effort | GPT-5.6 Terra | Claude Opus 5 | ratio | Terra time | Opus 5 time |
|---|---:|---:|---:|---:|---:|
| low | $0.19 | $0.81 | 4.3× | 112 s | 136 s |
| medium | **$0.15** | $1.15 | 7.5× | 105 s | 222 s |
| high | $0.18 | $1.84 | 10.4× | 132 s | 401 s |
| xhigh | $0.22 | $4.63 | 20.7× | 169 s | 909 s |
| **max** | $0.35 | **$14.21** | **40.1×** | 254 s | 1669 s |

**Terra's most expensive setting is half the price of Opus 5's cheapest.** At matched `max` the gap is 40×, for an identical, independently-judged 1.00.

**Why the gap widens with effort — the step counts give it away.** Terra's agent steps stay **flat across the entire dial: 10 to 19**. Opus 5's **explode: 15 → 23 → 22 → 43 → 140 turns.** The dial is doing structurally different things: on Opus 5 it buys *more agentic iteration*, and since every turn re-reads the accumulated conversation from cache, cost grows super-linearly in steps. On Terra it appears to buy *deeper reasoning inside a roughly constant number of steps*. So the per-token price difference (~2.4×) explains less than half the gap; the rest is turns.

**Comparing defaults would have hidden all of this.** `default` is not a shared operating point — Claude's sits near `high`, Terra's is `medium`, Sol's is `low`. Comparing out-of-the-box settings compares two vendors' product decisions, not two models. Setting effort explicitly on both sides is what turned a muddled ~9× into a clean 4×→40× interaction.

**The practical rule:** on work your stack already handles, run the dial *down*. Across four Claude generations, `low` matched `max` on reliability at a fraction of the cost — and the CLI default is not the cheap end.

*Caveats: n=2 per cell, one routine task, and every cell already at the 1.00 ceiling — so this measures what the dial COSTS, not what it BUYS. Whether thinking level earns its price on genuinely hard work is untested. Terra's cost also rests on a 92% cache-hit rate, which is partly an artifact of running many cells behind an identical prompt prefix.*

### Codex, briefly: a genuinely new lineage

Until this year every cloud result here was Claude. `codex exec` support (contributed by [@jschoch](https://github.com/adrianco/retort/pull/45)) added the OpenAI line, and its first outing was striking: **GPT-5.6 Luna reached 1.00 on Python ($0.062) and Go ($0.084)** against Opus 4.8's $0.67 on the same cell — roughly 11× cheaper.

Getting a trustworthy number out of it took four fixes, each only findable by running the real CLI: the telemetry parser was written to an event shape `codex exec --json` does not emit (it recorded **0 tokens, 0 turns** on real output); input and output tokens were double-counted against their own cached/reasoning subsets (~490% cost inflation); a ChatGPT subscription reports **no cost at all**, so Codex would have logged **$0** and won every cheapest-stack recommendation on an unmeasured number; and Codex's `turn.completed` fires **once per invocation**, so recording it as "turns" would have put it at the bottom of the turn axis looking impossibly efficient. Cost is now computed at list price per token — the same basis Claude's CLI reports and does not bill on a Max plan.

TypeScript is the exception: **0.00 across three replicates**, and it is a real failure rather than a harness artifact. The agent chose `better-sqlite3`, which will not build on this machine's Node 26; the transcript shows it ran `npm test`, saw `tsx: command not found`, tried a workaround, and shipped anyway — on a repair attempt where it had already been told it failed. It had the evidence and finished regardless.

## Newest: Opus 5 clears everything — and so, it turns out, does the cheaper model

The newest frontier model, **Claude Opus 5**, was run across **all thirteen supported languages on both tasks** — 26 cells, one replicate each. It got **26 out of 26**: every language on the routine task, and every language on the *hard* one (the Brazilian-soccer MCP server). Opus 4.8 manages only **0.57** there — reliable on Python/Go/TypeScript, a coin-flip on Rust (0.33), Java (0.33) and Clojure (0.45).

> **⚠️ This section originally read "no other model has cleared the hard task in more than six languages," and concluded that unique breadth was the one thing worth paying for. That was wrong, and the way it was wrong is worth more than the result.**
>
> Fable 5 hadn't failed those languages — it had never been **run** on them. It had only ever been tested on 4 of the 13. An unrun cell and an unpassable cell look identical in a results table, and I read the blank as a limit. **[exp-48](docs/past-experiments.md) ran them: Fable 5 cleared all nine, reaching the same 13/13 on the hard task — at \$10.47 and 18.2 min against Opus 5's \$21.67 and 43.8 min.** On the identical nine-language subset it is **2.1× cheaper and 2.7× faster for the same 1.00**.
>
> **Languages only Opus 5 can do: none.** The premium bought nothing but the appearance of exclusivity, and that appearance was an artifact of which questions had been asked.

**But look at the price of that coverage.** Per *solved* cell:

| | Opus 5 | Fable 5 | Opus 4.8 |
|---|---|---|---|
| routine task | \$2.91 · 10.1 min | **\$1.09 · 2.4 min** | \$0.99 · 4.9 min |
| hard task | \$20.00 · 43.8 min | **\$8.98 · 17.3 min** *(4 langs)* | \$5.53 · 10.1 min *(0.59 pass)* |

On routine work Opus 5 is **three times the price of Opus 4.8 for an identical 1.00** — there is no reason to reach for it. Even on the hard task it costs roughly **twice** what Fable 5 does per solved cell, in the languages where both have been measured. So the honest recommendation is narrow: **use the cheapest model that clears your language, and reach for Opus 5 only where nothing cheaper has been proven** — which today means the hard task outside Python/Go/TypeScript. (Fable 5 has only been run on four to five languages so far; a follow-up is filling those gaps, and if its lead holds it becomes the default for both task sizes.)

**The measurement story matters more than the model story here.** The raw run initially showed Opus 5 *failing* Python, Erlang and C on the hard task. All three were harness artifacts: Erlang and C were killed mid-work by a 60-minute timeout (Opus 5 is 3–5× slower than 4.8, and those cells needed ~53 minutes), and the Python "failure" was a project whose 239 tests all passed but whose `pyproject.toml` set `addopts = "-q"` — which combined with the scorer's own `-q` to suppress pytest's summary line entirely, so the pass-rate parser saw nothing and the mechanical gate failed a green suite. Raising the wall and making the **exit code** the universal pass signal turned three "capability failures" into three passes. Nothing about the model changed; only the measurement did. That is the fourth time in this project that a config artifact has masqueraded as a model result.

## A free laptop stack matches the cloud on Python, Go *and* TypeScript

The most recent work re-baselined the local stack on the newest local model — **Qwen3-Coder-Next 80B**, an 80B mixture-of-experts — and turned up the result that reorders the whole local story. Run across the easy-task languages at **full context** (the agent's `lcm` compaction threshold raised to 0.9, so it keeps its entire working history instead of compacting partway through a build), it posts **Python 1.00, Go 1.00, TypeScript 1.00** — three of three replicates each. That is the first time a free, on-device stack matches the cloud frontier's reliability on those three languages.

The unlock is a config lever, not a bigger brain. TypeScript scored only **0.33** at the default compaction threshold: the agent kept getting compacted midway through the longer TypeScript build and losing the thread. Raising the threshold to full context — the same one-line change, no new weights — walked it to 3/3. It's the local mirror of the whole project's thesis: the stack around the model moves the result as much as the model does.

Where the ceiling still is: **Rust is 0.33** on the 80B (its failures are genuine near-misses — the code compiles and its tests pass, it just misses a requirement or two — so Rust goes to the cloud), and the five niche languages (Clojure, C#, Elixir, Java, Erlang) still can't produce working code at all. The **35B** stays the *faster* local option for Python and Go (0.85 each), but it scores 0.00 on TypeScript and Rust, so the 80B-at-full-context is the stack to reach for whenever you want TypeScript local.

And a follow-up settled the obvious question — does full context also help the *hard* task? It does not. Re-running the Brazilian-soccer MCP server on the 80B at full context returned **0/6**, exactly the same as the lower threshold: Python gets as close as 11 of 12 capabilities but never all 12, and Go actually *regresses* (a run that can't finish just thrashes longer). So full context is strictly a lever for the easy languages; the hard-task ceiling is now **verified config-invariant**, and hard work stays a cloud-frontier job. The rest of the local-model arc — how the stack was built up to this point — follows below.

## The sampling settings we'd been getting wrong the whole time

Before adding any more models, a check on the *dials* — the request-time sampling parameters (temperature, top_p, top_k, repetition penalty). Every local result in this piece was measured at oMLX's default **temperature 1.0**, well above Qwen's own ~0.6–0.7 recommendation, with no repetition penalty. Do those dials move *reliability*? I ran a fractional factorial (Resolution IV, 8 configs) over the four levers on the 35B stack, bookshop, python+go, 48 runs.

**They move it a lot — and the settings we'd been using were among the worst.** Overall pass-proportion came out **0.83**, versus **~0.45** at the old temp=1.0 default: proper sampling nearly *doubles* how often the model gets an easy task completely right. The main effects, cleanly separated by the design:

- **Repetition penalty (1.1) is actively harmful** — the single biggest effect, dropping pass-proportion by a quarter, doubling run time, and causing *every* crash in the experiment. I'd added it expecting it to curb the verbose, runaway generation behind our timeout crashes; instead it did the opposite — on a model that reasons and calls tools, penalising repeated tokens derails the structured scaffolding into unproductive loops. Leave it off.
- **Temperature, within 0.2–0.7, doesn't matter at all** (0.83 either way). The entire win is from getting *off* 1.0, not from the precise value.
- **top_p 0.95 beats 0.85, and top_k 20 beats off** — both pointing back to Qwen's own recommended numbers.

The best configuration turned out to be, almost exactly, **the model author's recommendation** (temp ~0.6, top_p 0.95, top_k 20, no repetition penalty) — one config hit 6/6. The model shipped with good advice and we'd been ignoring it. There's a caveat attached to everything above this line: the 0.38–0.50 local numbers, the whole "a third of the way to the frontier" story, were all measured at that poor temperature 1.0, so they're **understated** — the local stack is likely more capable than the earlier arc concluded, and the recommended sampling is now the default going forward. And to the question that prompted this — do inference dials "resolve into reliability"? — yes, measurably, in a way a perplexity chart would never show you: a repetition penalty that looks harmless quietly quarters end-to-end coding reliability.

*(This sweep also stress-tested a new part of the harness: an unattended timeout policy that keeps a high wall for slow-but-productive work while killing unproductive loops fast. All four bad runs were caught as stalls at ~16 minutes instead of burning the 45-minute wall — the loops the repetition penalty created, cut short automatically.)*

## Can a laptop model build a real MCP server? (the hard task)

*An earlier milestone in the local arc — the first time the local stack was pointed at the hard task.* Everything else in this piece measured local models on the *easy* task — a CRUD API. The fair question is whether the best local stack can do something genuinely hard, so I pointed it at **brazil-bench**: a Brazilian-soccer **MCP server** built from a multi-file guide over six real kaggle datasets, with twelve required capabilities — match/team/player/competition queries, league standings computed from results, head-to-head records, aggregate stats, and a test suite (the guide prescribes BDD). This is a task cloud frontier models find non-trivial. I ran the champion **Qwen3.6-35B-A3B** stack on **Python and Go** (its two strongest languages), three replicates each, at the model's full **256K context** — which the runs genuinely used, prompts reaching 108K tokens.

**The answer: it copes — in Python about a third of the time, and in Go once it has enough clock.** One Python run built the whole thing clean: a proper `brazilian_soccer_mcp/` package (server, query engine, data loader) with a passing test suite, **requirement_coverage 1.0, test_coverage 0.96** — a complete, tested MCP server over real data, produced by a free model on a laptop. But at a 30-minute timeout that was only **1 of 6**: half the runs hit the wall (non-termination), and both Go runs produced *no working code at all*.

That "Go can't do it" turned out to be an artifact of the clock, not the model. These runs are **generation-bound** — the 35B writes at ~54 tokens/sec, and twelve capabilities over six datasets is more code than it can finish in 30 minutes (the same throughput limit the [80B cache ablation](#a-cache-trick-that-should-have-fixed-the-80b--and-didnt) isolates further down). So I doubled the timeout to 60 minutes — a per-experiment setting, because a slow local stack simply needs a bigger budget — and re-ran the identical grid. **Almost everything that matters roughly doubled or halved the right way:** first-try passes **0.17 → 0.33** (Python 1/3 → 2/3), crashes **3 → 1**, and Go went from *all zeros* to **high-quality code with passing tests, reaching 0.92 requirement coverage**. Go wasn't incapable; it just never had time to finish. The extra clock also *unlocked* self-repair for Go — runs that now complete-and-fail instead of crashing finally qualify for retort's default second chance (though on this hard last mile the repairs didn't quite convert, and one even regressed).

Then it stopped. Even at 60 minutes with self-repair, reliability tops out at **0.33 first-try**: Go reaches 0.92 requirement coverage but not 1.0, and the occasional run is genuinely non-terminating (one still walled out at the full hour). The residual failures are now *capability* — the last mile of twelve requirements plus correct MCP wiring — not *budget*. From here the lever is faster generation (more finished turns per minute) or a stronger model, not more wall-clock. **The honest shape of local coding on a hard task: a generous time budget makes a laptop model genuinely useful, and then a real ceiling remains** — and because the model is slow, "generous" means a local timeout set well above the cloud default. The rest of the local-model arc — how the stack was built up to this point, and the language wall it hits on the easy task — follows below.

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

**By language**, the older patterns sharpen: Go and C# reach perfect build-quality but are the most token-hungry (token_efficiency ≈ 0); TypeScript is the most token-efficient; Python is cheapest and fastest; Rust is priciest and the sole failure site. Full per-cell tables: [`experiment-15-sonnet5/RESULTS.md`](experiments/adrianco/experiment-15-sonnet5/RESULTS.md).

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

Re-baselined on the fixed stack (correct sampling, true 256K context, and the 80B at full context), the current picture is:

| language | 35B (tuned) | 80B (ctx 0.9) | **best local** |
|---|---:|---:|---|
| **python** | 0.85 | **1.00** | **80B — 1.00** (35B for more speed) |
| **go** | 0.85 | **1.00** | **80B — 1.00** (35B for more speed) |
| **typescript** | 0.00 | **1.00** | **80B — 1.00** (needs full context) |
| **rust** | 0.00 | 0.33 | *none reliable → cloud* |
| clojure / java / c# / elixir / erlang | 0.00 | 0.00 | *none → cloud* |

*(Pass-proportion, neutral prompt, on the M5 laptop, n=3 each. Read the picks as directional, but the tiers are robust.)*

- **Python, Go and TypeScript now run locally for free — reliably.** The 80B at full context clears all three at 1.00; the 35B is the *faster* alternative for Python and Go (0.85 each) but scores 0.00 on TypeScript, so it's the 80B when you want TypeScript on-device. If your project is one of these three, a local model is a genuinely viable, free option.
- **The compaction threshold is the lever, not the weights.** The same 80B scored only 0.33 on TypeScript until its agent was told to keep full context instead of compacting mid-build — a config change unlocked a whole language. Optimize the *stack*, not just the model.
- **Rust is marginal (~0.33) — reachable but not reliable,** so it goes to the cloud; its local failures are near-misses (compiles, tests pass, misses a requirement) rather than the old thrash-to-the-wall.
- **The five less-common languages are a flat zero for every local model** — the capability wall the stack can't move. If your project is Clojure, Java, C#, Elixir or Erlang, use the cloud.

The developer takeaway is concrete: **choose the language, then choose the model for that language.** For Python, Go or TypeScript you can stay local and free; for everything else, reach for the cloud.

The bottom line: on a 64 GB laptop, a good local model is now a genuinely reliable tool on Python, Go and TypeScript — free, private, and matching the cloud frontier on those three easy-task languages — while Rust, the niche languages, and the hard task still belong in the cloud. Worth knowing exactly where that line is *before* you rely on it.

## A cache trick that "should" have fixed the 80B — and didn't

Before closing the book on the 80B being *slower and crashier* than the smaller 35B, I chased a tempting explanation. A widely-shared [Mac-Studio tuning write-up](https://mrzk.io/posts/qmlx-maximising-ai-psychosis-minmaxing-mac-studio/) reports **~137×** speedups from an on-disk **KV prefix cache** — and it turned out oMLX's prefix cache is **off by default**. Every local run above had been re-processing its entire growing context *every turn*. That's exactly the kind of serving artifact that could make a big model look worse than it is, so I turned the cache on (`--paged-ssd-cache-dir`) and re-ran the identical 80B grid as a clean on-vs-off comparison.

**The cache works perfectly and it changed nothing.** First-try pass-proportion stayed at **0.33**, crashes went **2 → 3**, and completed-run durations were flat. The server log proves the cache is *hitting* — an **88,000-token prefix restored in ~2.5 seconds** (a cold prefill costs ~150 s), and oMLX even snapshots this hybrid architecture's tricky "non-sliceable" layers to disk correctly. So why no gain? Because our workload is **generation-bound, not prefill-bound**: the 80B generates at ~61 tokens/sec, the context grows to 75–88 K tokens, and each turn spends **~75 seconds *writing* its ~3,400-token reply** — over many turns, straight into the 30-minute wall, no matter how fast the prefix loads. The 137× result is the *mirror image* of agentic coding: it comes from a huge fixed prompt with almost no generation (all prefill), whereas coding is a moderate prompt with heavy multi-turn generation.

The lesson is methodological, and it's why the harness exists: **measure where the time actually goes before you blame the model — or credit a fix.** The 80B wasn't hobbled by a cache miss; it's genuinely throughput-bound in this loop. "Bigger isn't better" survives the ablation, now with a mechanism. And the real lever for slow big models is exposed as *generation* speed — speculative / multi-token decoding to convert wall-crashes into finished runs — not prefix caching, which is worth leaving on but simply isn't the bottleneck here. *(This ablation lives in its own database; it re-runs an existing model with one serving flag flipped, so it's deliberately kept out of the model grid to avoid double-counting the 80B.)*

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

