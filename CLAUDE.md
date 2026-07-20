# Working in this repo

Retort measures whole coding **stacks** (language × model × quantization × serving
layer × agent × context engine × sampling × prompt), scoring each on pass-proportion —
the fraction of runs that fully implement the spec. Guidance for running experiments
here, and for any Claude session helping with them.

## Principle: verify tuning parameters before a full experiment

**Before starting any full experiment, RECORD every tuning parameter and VERIFY each one
actually takes effect with a smoke test.** A parameter set-but-not-verified is worse than
none — it produces confident, wrong results.

Nearly every wrong conclusion this project has published came from a tuning parameter
that was set-but-not-verified, or never recorded at all:

- **temperature = 1.0** (the oMLX default, never recorded) — cost roughly half the local
  reliability. "The 35B scores 0.38" really meant "0.38 *at temp 1.0*".
- **playpen under `/var`** — the agent's file tool was silently refused (macOS temp dir
  is a "sensitive system path"), so it wrote nothing and scored a false zero,
  indistinguishable from a model that can't do the task. Read as a "capability wall".
- **context silently 128K, not 256K** — the stack-reload hook destroyed Hermes' per-model
  `context_length`; the config file AND `provenance.json` both still reported 262144 while
  the model actually ran at half that.
- **repetition_penalty** — derailed the agentic tool loop into stalls, *even at the value
  the model's own card recommended*. Model-card sampling is tuned for single-turn
  generation, not multi-turn agent loops.
- **lcm `context_threshold` = 0.35** — the real ~92K compaction ceiling (0.35 × 262144),
  mistaken for a residual 128K bug until traced.

How to apply:

1. **Record** every parameter that could move the result: sampling
   (temperature / top_p / top_k / penalties), context length **and the agent's compaction
   threshold**, the serving-layer settings, the model **revision hash** (not just its
   name), and the harness settings (playpen path, timeout, stall guard). This is what
   `provenance.json` captures — and it reports the **effective** value, because the config
   file's value and the value the model actually ran at have diverged.
2. **Verify each takes effect** with a cheap smoke test *before* the full grid: send a
   probe and confirm the server/agent honoured it — temp=0 → byte-identical output;
   settings survive a restart; the live context actually reaches the configured window.
   **"I set it" is not "it took effect":** oMLX silently STRIPS unsupported keys (e.g.
   `min_p`) and IGNORES others.
3. A parameter whose effect you cannot observe in a smoke test is not usable in the
   experiment — fix the plumbing or drop the factor.

## Experiment workflow

- **Before** launching: write the plan (intent, design, hypothesis) into
  [`docs/future-experiments.md`](docs/future-experiments.md) and push. Recording intent up
  front is what makes a null result publishable rather than embarrassing.
- Every run writes a `provenance.json` — the exact stack it ran on. Do not hand-edit it.
- **When a model produces NO code, suspect the harness before the model.** A blocked file
  tool and an incapable model are identical in the scores. `retort diagnose` classifies a
  failure as HARNESS / TOOLING / GENUINE — run it on any surprising zero.
- Experiments live under `experiments/<owner>/experiment-NN-<slug>/` so contributions
  merge cleanly and every run is attributable. See [`experiments/README.md`](experiments/README.md).
- **After** results land: run `retort recover` + `retort aggregate`, update the write-ups and
  push (the model/optimal blogs), and **move the experiment's entry from the
  [`future-experiments.md`](docs/future-experiments.md) queue to
  [`past-experiments.md`](docs/past-experiments.md)** (append in increasing experiment order). Do
  the same for a model candidate the moment you decide it isn't worth testing.
