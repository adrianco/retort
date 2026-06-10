# experiment-11 — Google Gemini on the REST-API task (ready-to-run)

The first **cross-agent** experiment: the REST-API CRUD (bookshop) task run by
**Google Gemini** (`gemini-2.5-pro`) instead of `claude-code`, so `agent`
becomes a factor the ANOVA can decompose against the existing claude-code
baselines (experiments 1 / 6 / 7) on the same task and languages.

**Status: scaffold only — no result rows yet.** The Gemini harness was built and
validated end-to-end against the live Gemini CLI 0.46 (command flags, the
`--skip-trust` workspace-trust fix, and the `stats.models.<model>.tokens` cost
parser are all confirmed — see PR #13). Actual cells did not complete because
the **free-tier (OAuth personal) capacity for Gemini was exhausted** at run time
(`429 No capacity available` / `You have exhausted your capacity on this model`)
for both `gemini-2.5-pro` and `gemini-2.5-flash`. Re-run when free-tier quota
resets, or with a paid `GEMINI_API_KEY`.

## Run

```bash
export PATH="/opt/homebrew/opt/openjdk/bin:/opt/homebrew/bin:$HOME/go/bin:$PATH"
export JAVA_HOME="/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home"
RUN='PYTHONPATH=src .venv/bin/python -c "from retort.cli import main; main()"'

# Go + Python first (gauge free-tier token use), then the rest:
eval $RUN run --phase screening --config experiment-11/bookshop/workspace.yaml \
  --design experiment-11/bookshop/design-gemini-gopy.csv --resume

# All six languages:
eval $RUN run --phase screening --config experiment-11/bookshop/workspace.yaml \
  --design experiment-11/bookshop/design-gemini-all.csv --resume
```

Cost is derived from token counts via `GEMINI_PRICING` in `local_runner.py`
(the CLI reports tokens, not dollars). The spec-gate judge stays on Claude
(`reevaluate --eval-model claude-opus-4-6`) so an independent model grades both
agents fairly.
