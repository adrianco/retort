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

## Principle: ONE experiment at a time on this machine

**Never run two experiments concurrently — not even a cloud run alongside a local one,
and not even a "cheap" one-cell smoke test alongside a full run.**

retort measures wall-clock seconds, turns and tokens as first-class responses. A second
concurrent run contends for CPU, memory, disk and API rate limits, so it corrupts the very
timing numbers the experiment exists to produce — and the corruption is **invisible
afterwards**: the run completes, the numbers look plausible, and nothing in the archive
records that something else was competing for the machine. Local runs additionally contend
for the single oMLX server on port 8080.

How to apply: before launching anything — full experiment, gate-probe, or smoke test —
check for a live run (`pgrep -f "retort run"`, plus any driver script) and **wait**. Queue
follow-on work in a driver script rather than starting it alongside. "It's only one cell"
and "that one's local, this one's cloud" are both wrong.

*(Written after a one-cell `--effort` smoke test was run during exp-48's brazil half. Its
turns/tokens/cost survived — those are properties of the model's work — but its wall-clock
time had to be thrown away.)*

**Checking for a live `retort run` is not enough — check for ORPHANS.** A previous run's
children can outlive it and keep working, and an orphan is invisible to every check that
looks for `retort run`:

    pgrep -fl "retort|codex|claude -p|scripts/" | grep -v grep   # anything still alive?
    ps -eo pid,etime,command | grep retort/experiments | grep -v grep

Found on 2026-08-17: `scripts/brazil_dedup_verdict.py` had been running **14 days**,
orphaned to init (ppid 1), wedged on a server that never answered and holding one MCP
server process resident the whole time — through every experiment in that window. It sat
at 0% CPU, so nothing looked wrong; it was the resident server, not the CPU, that
contended. Separately, the runtime probe leaked its own servers because `proc.kill()`
kills `npm`, not the `node` it forked (fixed: `start_new_session=True` + `killpg`).

Kill orphans before launching, and prefer a driver script that reaps its children.

## Publishing: blogs are ONE LINE PER PARAGRAPH

The `*-blog.md` files are published to dev.to, which treats a hard-wrapped source
line as a literal line break instead of reflowing it — so a paragraph wrapped at
~95 columns arrives with ragged breaks mid-sentence. **Never hard-wrap prose in a
`*-blog.md` file.** One paragraph = one line, however long.

This applies to anything you write or edit in those files, including a one-word
fix to an existing wrapped paragraph — rewrap the whole paragraph onto one line.
Tables, code fences, list items, footnotes and `<!-- GEN:… -->` markers keep their
own lines; only prose is joined.

    python scripts/reflow_blogs.py           # fix every blog in place
    python scripts/reflow_blogs.py --check   # exit 1 if any are wrapped (CI)

**A blog you edit MUST carry today's date in its header.** `--check` enforces
this: any `*-blog.md` that differs from HEAD must say `updated <today>`. A
published page whose content changed while its byline still claims an older date
is quietly wrong in a way no reader can detect — and it happened four times in
one week, including twice when `retort report optimal --write` regenerated a GEN
table and nobody touched the header.

The script is idempotent and refuses to run if it would change the number of
links, table rows, code fences or headings. Run `--check` before pushing blog
edits. Other markdown (README, docs/) is unaffected — it is read on GitHub, which
reflows normally.

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

## Code layout — where CLI commands live

`src/retort/cli.py` holds the **`run` command** (the core experiment pipeline) plus the
**shared helpers** (`_archive_run_workspace`, `_persist_*`, `_spec_conformance_passes`, …)
and the click **group definitions** (`main`, `report`, `design`, `export`, `tasks`, `plugin`).
Every **other command lives in `src/retort/commands/<area>.py`** — `scoring` (evaluate/
reevaluate/rescore/diagnose/recover), `reporting` (report *), `analysis` (analyze/aggregate/
maturity), `workspace` (init/visibility-check/design generate/promote/intake), `monitoring`,
`utility` (plugin/export/tasks), `rebuild` (rebuild/report runtime). cli.py imports these at its **bottom** (after the groups +
helpers are defined, so it isn't circular) and re-exports moved names for back-compat.

**Adding a command: put it in the matching `commands/` module, not cli.py** (keep cli.py to
the run pipeline). Register it on the shared group (`from retort.cli import <group>`); if it
needs a cli.py helper/constant, reference it through the module — `cli._helper(...)` (do
`from retort import cli`), never `from retort.cli import _helper` — so monkeypatching in tests
still reaches it. The `test_every_command_is_registered_and_imports` guard invokes `--help`
on every command, so a broken import/registration fails loudly.
