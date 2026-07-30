# The Unit of Choice Is Model × Thinking Level, Not Model

*Published 2026-07-25 · updated 2026-07-30 — Adrian Cockcroft*

For a year the question has been "which model should I use?" That question is underspecified. Every frontier model now has a **thinking-level** dial, and on the evidence below the dial moves cost more than the model choice does — while moving the result not at all.

One task (a "bookshop" REST API), one prompt, one judge throughout. First four Claude versions × five thinking levels, three replicates each — **21 cells, 63 runs, zero failures**. Then the same sweep against **OpenAI's GPT-5.6 Terra**, to see whether any of it is a Claude peculiarity. It isn't, but the two vendors turn out to have built the dial to do different things.

## Every cell passed. The bill spans 16×.

| model | effort | turns | tokens | **cost** | seconds |
|---|---|---:|---:|---:|---:|
| **Opus 4.8** | **default** | 9.3 | 245 K | **$0.42** | 79 |
| Opus 4.8 | low | 10.3 | 272 K | $0.57 | 83 |
| Opus 4.8 | high | 14.0 | 393 K | $0.60 | 117 |
| Opus 4.7 | low | 7.3 | 273 K | $0.61 | 56 |
| Opus 4.8 | medium | 12.7 | 348 K | $0.66 | 97 |
| Opus 4.7 | medium | 8.7 | 329 K | $0.67 | 65 |
| Opus 4.7 | default | 10.3 | 397 K | $0.75 | 91 |
| **Opus 5** | **low** | 15.7 | 432 K | **$0.75** | 114 |
| Opus 4.7 | high | 11.7 | 451 K | $0.79 | 97 |
| Opus 5 | medium | 18.0 | 436 K | $0.86 | 142 |
| Fable 5 | low | 8.0 | 131 K | $0.91 | 49 |
| Opus 4.8-fast | default | 11.5 | 204 K | $0.95 | 125 |
| Opus 4.7 | max | 14.0 | 588 K | $1.13 | 171 |
| Fable 5 | high | 13.3 | 369 K | $1.13 | 109 |
| Fable 5 | medium | 10.3 | 245 K | $1.16 | 75 |
| Fable 5 | default | 13.0 | 352 K | $1.21 | 107 |
| Opus 5 | default | 31.0 | 950 K | $1.38 | 270 |
| Opus 4.8 | max | 15.3 | 628 K | $1.45 | 326 |
| Opus 5 | high | 30.7 | 1,072 K | $1.77 | 399 |
| Fable 5 | max | 13.7 | 428 K | $2.28 | 241 |
| **Opus 5** | **max** | 43.7 | 2,337 K | **$6.75** | 1,110 |

**Every row is pass-proportion 1.00.** Not "mostly" — all 63 runs fully implemented the spec, tests executing, verified by an independent judge. The cheapest configuration costs **$0.42** and the dearest **$6.75**: a **16× spread buying literally nothing** on this task.

## The dial is a bigger lever than the version

Compare the two axes directly.

**Within one model, changing only the thinking level:**

| model | low → max | cost multiple |
|---|---|---:|
| Opus 4.7 | $0.61 → $1.13 | 1.9× |
| Opus 4.8 | $0.57 → $1.45 | 2.5× |
| Fable 5 | $0.91 → $2.28 | 2.5× |
| **Opus 5** | **$0.75 → $6.75** | **9.0×** |

**Between models, holding the thinking level fixed:**

| effort | cheapest → dearest | cost multiple |
|---|---|---:|
| low | $0.57 (4.8) → $0.91 (Fable 5) | 1.6× |
| default | $0.42 (4.8) → $1.38 (Opus 5) | 3.3× |
| max | $1.13 (4.7) → $6.75 (Opus 5) | 6.0× |

Two things fall out. **At `low`, the four model generations nearly converge** — 1.6× apart, and all perfect. Most of what looks like "the new model is expensive" is the new model *thinking harder by default*, not the weights being pricier. And **the two axes interact**: Opus 5 responds to the dial 9×, where the older models respond 2×. The newest model is both the most expensive at its default and by far the most sensitive to the setting.

The practical consequence is concrete: **Opus 5 at `low` ($0.75) is cheaper than Fable 5 at its default ($1.21) and half the price of Opus 5 at its own default.** If you want the newest model, the dial — not the version — is what decides your bill.

## Why cost tracks turns, and turns tracks the dial

The mechanism is unchanged from earlier versions of this post, and it is the part that has held up under every re-measurement.

Cost follows the **number of agentic turns**, not per-turn speed. Seconds-per-turn is roughly flat; what varies is how many steps the loop takes. And token cost grows *faster* than turns because **every turn re-reads the whole accumulated conversation from cache**. Opus 5 at `max`: 43.7 turns, and 2.34 M tokens against roughly 33 K actually generated. Cache reads are individually cheap, which is why the bill is $6.75 and not absurd — but they dominate the totals, and they scale with roughly the *square* of the step count.

So the dial's mechanism is simple: more thinking → more steps → quadratically more re-read context. That is why `max` costs 9× on the model that takes the most steps to begin with.

## What the dial does not buy

Nothing measurable here. Every level, every model: 1.00.

That is a real finding *and* a bounded one. This is **one language on a routine task**, where the ceiling was already saturated — with everything at 1.00 there is no headroom in which a difference could show. Thinking level may well earn its cost on genuinely hard work, and nothing in these 63 runs tests that. It is the obvious next experiment.

The honest summary: **on work your stack already handles, the dial is pure expense. On work it doesn't, we don't know yet.**

## The version story, corrected

An earlier version of this post described a smooth generational climb — Fable 5 10.7 turns → Opus 4.8 17.3 → Opus 5 36.0 — and built a narrative on it. Measured **in one batch**, with the thinking level held at the historical default, three of those generations are indistinguishable:

| model | in-batch turns (n=3) | previously published | ratio | source of the old figure |
|---|---:|---:|---:|---|
| Opus 4.8-fast | 11.5 | 11.3 | **1.02×** | exp-7 |
| Fable 5 | 13.0 | 10.7 | 1.21× | exp-10 |
| Opus 5 | 31.0 | 36.0 | **0.86×** | exp-46 |
| **Opus 4.7** | **10.3** | 17.2 | **0.60×** | **exp-6** |
| **Opus 4.8** | **9.3** | 17.3 | **0.54×** | **exp-6** |

Three of five replicate closely. The two that don't both come from **exp-6**, the oldest source — so the "gradual climb" was substantially one old experiment's inflated middle. Corrected: **4.7, 4.8 and Fable 5 all sit around 9–13 turns; Opus 5 alone takes ~2.7× that.** Not a trend across versions — one model behaving differently.

*(A note on how that was found: the cross-version comparison had been assembled from experiments run months apart on different harness versions. The fix was to re-run every arm in a single batch. If you take one methodological point from this post, take that one.)*

## A second vendor: the dial does something completely different at OpenAI

Everything above is Claude. If "the dial costs more than the model" were really about thinking level rather than about one vendor's tuning, it should show up elsewhere — so the same experiment was run against **OpenAI's GPT-5.6 Terra**, driven by `codex exec`.

Terra is the right comparison because GPT-5.6's three tiers price onto the Claude ladder rather than against it: **Luna (\$1/\$6) ↔ Sonnet · Terra (\$2.50/\$15) ↔ Opus · Sol (\$5/\$30) ↔ Fable.** Opus is the strongest Claude pick in most cells today, so Terra is its price-peer. Both CLIs expose exactly the same five levels — `low, medium, high, xhigh, max` — so the dial can be set identically on both sides. **Python and Go, n=2, 20 cells. Every one scored 1.00.**

| effort | Terra | Opus 5 | ratio | Terra time | Opus 5 time | Opus 5 turns |
|---|---:|---:|---:|---:|---:|---:|
| low | $0.19 | $0.81 | 4.3× | 112 s | 136 s | 16 |
| medium | **$0.15** | $1.14 | 7.6× | 105 s | 222 s | 20 |
| high | $0.18 | $1.84 | 10.2× | 132 s | 401 s | 30 |
| xhigh | $0.22 | $4.63 | 21.0× | 169 s | 909 s | 62 |
| **max** | $0.35 | **$14.21** | **40.6×** | 254 s | 1669 s | **92** |

**Terra's most expensive setting is half the price of Opus 5's cheapest.** At matched `max` the gap is forty-fold — for an identical, independently-judged 1.00 on the same task.

But the interesting column is the last one, because it shows the two dials are not the same instrument. **Terra's agent steps stay flat across the entire range — 10 to 19 — no matter where the dial is set. Opus 5's climb from 16 to 92.** Turning the dial up on Opus 5 buys *more agentic iteration*; turning it up on Terra appears to buy *deeper reasoning inside a roughly constant number of steps*.

That distinction is exactly the mechanism this post has been building toward. Cost tracks turns, and turns re-read the accumulated conversation, so a dial that adds steps compounds and a dial that doesn't, doesn't. The per-token price difference between the two models is only about 2.4×; the rest of the 40× is turns. **The thesis survives contact with a second vendor — but the vendors have made opposite choices about what the dial should do.**

There is a second, smaller surprise. **OpenAI's flagship tier defaults to the *lowest* reasoning setting** (Sol defaults to `low`, while the cheaper Terra and Luna default to `medium`), where Claude's default sits near `high`. So "newer models think harder by default" — the tempting explanation earlier in this post — is not a law about frontier models. It is a product decision, and two vendors made it in opposite directions.

This is also why the comparison had to set effort explicitly on both sides. `default` is not a shared operating point: comparing out-of-the-box settings would have compared two companies' packaging choices and called it a model difference, and would have shown a muddled ~9× instead of the clean 4×→40× interaction.

*(Getting a trustworthy number out of Codex took four fixes first, none of which were visible without running it: the telemetry parser was written to an event shape the CLI does not emit and recorded **0 tokens, 0 turns**; input and output tokens were double-counted against their own cached and reasoning subsets, inflating cost ~490%; a ChatGPT subscription reports **no cost at all**, so Codex would have logged \$0 and won every cheapest-stack ranking on an unmeasured number; and Codex's `turn.completed` fires once per invocation rather than per step, so recording it as "turns" would have placed it at the bottom of this post's own axis looking impossibly efficient. Cost here is list-price-per-token — the same basis Claude's CLI reports and does not bill on a Max plan.)*

## It isn't a Claude phenomenon

The same cell run on local models, driven by the Hermes agent over oMLX on a 64 GB laptop:

| stack | n | turns | replicates |
|---|---:|---:|---|
| Qwen3.6-35B (local) | 3 | **12.0** | 10, 8, 18 |
| Qwen3-Coder-Next 80B (local) | 3 | **24.7** | 44, 17, 13 |

Placed on the same axis: **Opus 4.8 9.3 · Opus 4.7 10.3 · 35B 12.0 · Fable 5 13.0 · 80B 24.7 · Opus 5 31.0.** A 35B open-weights model on a laptop sits in the same cluster as three Claude generations, and the 80B sits with Opus 5 well above it. Two vendors, a 20× parameter range, and the same two-group split — which points at **how a model was tuned to behave in an agent loop** rather than at scale or architecture. With Terra above, that is now three independent lineages saying the same thing: step count is a tuning decision, not a capability tier.

Caveat worth keeping: the 80B's replicates span 44/17/13, a 3.4× spread. A single 80B run tells you very little.

## What to actually do

1. **Pick a (model, effort) pair, not a model.** The pair spans 16× in cost here; the model alone explains a minority of that.
2. **On routine work, turn the dial down.** `low` cost 1.6× less than `default` on average and changed no outcome. The CLI default is not the cheap end.
3. **If you want the newest model, run it at `low`.** Opus 5 at `low` undercuts Fable 5 at its default. Opus 5 at `max` costs 16× the cheapest cell for the same passing app.
4. **Check what your vendor's dial actually does.** On Opus 5 it adds agentic steps and compounds; on Terra it doesn't move step count at all. Same five names, different instrument — so a rule of thumb learned on one model does not transfer.
5. **Don't generalise any of this to hard tasks.** Everything above saturated at 1.00. The dial's value, if it has one, lives where the ceiling isn't already hit — and nothing here tests that.

---

*Method: `python × bookshop × prompt=neutral`, n=3 per cell, judged by an independent Opus 4.8 against a pinned requirement checklist; a run passes only if it implements the whole spec. Cost is list-price-per-token — the basis every metered stack here is recorded on, and one that does not vary with whose subscription happened to pay. Data: [`master.db`](master.csv), experiments `adrianco/experiment-49-versions-cloud` (Claude × effort) and `adrianco/experiment-55-terra-vs-opus5-effort` (cross-vendor, matched effort).*
