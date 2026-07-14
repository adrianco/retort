# Experiments

Every experiment lives under **`experiments/<owner>/experiment-NN-<slug>/`**, where
`<owner>` is the GitHub handle of whoever ran it.

```
experiments/
  adrianco/
    experiment-27-sampling-ff/
      bookshop/
        workspace.yaml      # the design: factors, responses, task, playpen
        design.csv          # the cells actually run
        stacks.yaml         # (optional) serving-stack presets
        REQUIREMENTS.json   # the pinned spec checklist
        retort.db           # the data
        provenance.json     # the exact stack it ran on
        runs/               # archived code per cell
      RESULTS.md            # what it found
  <your-handle>/
    experiment-NN-.../
```

## Why per-owner

* **Clean merges.** Two people running experiments at the same time never touch the
  same paths, so a pull request adding `experiments/<you>/…` merges without conflict.
* **Attribution.** `retort aggregate` records the `<owner>` segment as an `owner`
  column on every run in `master.db`, so who measured what is part of the data — you
  can filter to one contributor, or audit a contribution before merging it.

## Contributing an experiment

1. Create `experiments/<your-handle>/experiment-NN-<slug>/`. Numbering is global —
   take the next free `NN` so results are orderable across contributors.
2. Write the plan into [`docs/future-experiments.md`](../docs/future-experiments.md)
   **before** you run it. Recording intent up front is what makes a null result
   publishable rather than embarrassing.
3. Run it. Every run writes a `provenance.json` — the versions, model revision
   hashes, sampling parameters, agent config and harness settings it actually used.
   **Do not hand-edit it.** A pass-proportion without the stack it was measured on is
   not a result.
4. Write `RESULTS.md`: what you asked, what you found, and what would change your
   mind. Report null and negative results — several of the most useful findings here
   are things that *didn't* work.
5. Open a pull request.

## Before you trust a number

Two failure modes have burned this project, and both look exactly like a weak model:

* **A blocked file tool.** If the agent can't write into its own workspace it produces
  nothing and scores zero — indistinguishable from incapability. `retort diagnose`
  classifies these as **HARNESS**; run it on any surprising zero before believing it.
* **An unrecorded config.** Sampling defaults, a serving-layer setting, a different
  agent — any of these will move a score more than the model choice does. That's what
  `provenance.json` is for.

See [the optimal stack](../optimal-blog.md) for the configuration a stack should be
run at, and the settings that are forbidden.
