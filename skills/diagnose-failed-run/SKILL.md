---
name: diagnose-failed-run
description: Determine the TRUE cause of a failed retort run before attributing it. Ground-truth every failure (run its tests, read its agent logs, inspect its workspace) and classify it as an infrastructure false-fail, a genuine model miss, or an environment issue — never trust the gate verdict or a log signature alone. Use whenever a run is recorded failed (test_coverage=0 / gate fail), a pass rate looks low, or you're deciding whether a "failure" is real before reporting or proceeding.
type: anthropic-skill
version: "1.0"
---

# Diagnose a Failed Retort Run

## Overview

A run failing the mechanical gate (`test_coverage=0` → all metrics zeroed → `status=failed`)
says **only** that the tests didn't *run/pass under the scorer* — **not** that the model
produced bad code. Historically most "failures" in this repo were **harness/measurement
artifacts**, not model defects. This skill is the judgment layer on top of `retort diagnose`:
it establishes the *real* cause with **direct evidence** before anyone attributes, reports,
or gates on it.

It exists because we repeatedly drew wrong conclusions by inferring from a signature
("flaky", "concurrency", a wrong env var, a wrong tool-permission fix) that end-to-end
checks later overturned. The cost of guessing here is hours and bad decisions.

## Cardinal rules

1. **Ground-truth before concluding.** Run the tests yourself, inspect the workspace, read
   the agent logs. Never attribute a cause from the gate verdict, a duration, or a single
   log line alone.
2. **Label every claim `[DIRECT]` (observed: command output, file state, a reproduced
   result) vs `[HYPOTHESIS]` (inferred, not yet tested).** Don't ship a hypothesis as a
   cause. If a cause is unconfirmed, say so and name the experiment that would confirm it.
3. **Read the DB *and* the agent logs.** The recorded scores/session show *which* tool or
   step failed; the agent stderr shows *why* (the permission type, the error). You usually
   need both — e.g. the session said "read rejected", but only `--print-logs` stderr
   revealed the real permission was `external_directory`.
4. **Verify any fix end-to-end (through the harness), not just CLI/unit.** A fix that
   passes a CLI probe can still fail in the runner (a wrong env var passed both).

## Inputs in each `runs/<cell>/repN/`

| File | Use |
|------|-----|
| `TASK.md` | What the agent was asked to build |
| `stack.json` | language / agent / model / tooling for this cell |
| `scores.json` | recorded metrics (all 0 ⇒ gate-failed) |
| generated source | what the agent actually produced — **check it exists and *where*** (subdirs/packages count) |
| `_agent_stdout.log` | the agent's full `--format json` / `--mode json` event stream (tool calls + their status, errors, the final text) |
| `_agent_stderr.log` | the agent's internal logs (permission evaluations, hangs, provider errors) — for opencode, requires `--print-logs` |

If `_agent_*.log` are absent, the run predates log capture; reconstruct from the agent's
own session db (e.g. opencode's `OPENCODE_DB` sibling) and **add capture before re-running**.

## Procedure

1. **Mechanical pass first:** `retort diagnose --experiment-dir <dir>` labels each failed
   run `TOOLING` (recovers with `retort rescore --only-failed`) vs `GENUINE`. Start here;
   this skill handles the cases it can't auto-resolve.
2. **Ground-truth each failure** (do NOT skip even for `GENUINE`):
   - **Does code exist, and where?** A "no code" verdict is often just a package subdir
     (`app/`, `src/`) the eye/glob missed.
   - **Run the tests yourself** in a clean copy with deps installed
     (`pytest` / `cargo test` / `go test ./...` / `mvn test` / …). Passing tests ⇒ it's a
     **scorer false-fail**, not a model miss.
   - **Read `_agent_stdout.log`** for the failing tool call + status; **read
     `_agent_stderr.log`** for the *reason*.
3. **Classify the cause** (see taxonomy). State it `[DIRECT]` with the evidence.
4. **Isolate intermittent/ambiguous causes with a controlled A/B** — change exactly one
   variable (e.g. shared vs isolated db; baseline vs with-fix batch) and compare. Log what
   you dropped; don't conclude from n=1.
5. **Reproduce-with-full-capture** before declaring an intermittent cause — run it enough
   times to catch one with `_agent_*.log` captured, then read the events at the abort.
6. **Verify the fix end-to-end** through the harness, then re-score / re-run.

## Cause taxonomy

**A. Infrastructure false-fail** (code works; the harness mis-scored it → fix the harness, then rescore):
- *Scorer gap* — language/runner the scorer doesn't handle (e.g. a Bun `bun:test` project the TS scorer can't measure).
- *Undeclared / transitive deps* — model omits `requirements.txt`; tests fail at import (incl. transitive deps like `httpx` for fastapi/starlette TestClient).
- *Permission auto-deny* — headless agent denies a tool (opencode's `external_directory: ask`→deny on the temp workspace) → aborts with no code.
- *Concurrency/env contention* — shared state (opencode's single `opencode.db`) → fast-fail at startup under parallelism.
- *Mis-measurement* — coverage parsed as 0 on passing tests, etc.

**B. Genuine model miss** (real, count it; not fixable in the harness):
- Won't compile / tests genuinely fail / no tests written / no or partial deliverable / code in the wrong place the task didn't ask for.

**C. Environment** (transient/operational, not the model or harness logic):
- Rate-limit / credit cutoff (check the provider key's usage/limit), stray processes, resource exhaustion, OS cleanup.

## Tells (and their trap)

The classic tell — *fails instantly for ~$0 ⇒ harness; burns model time ⇒ genuine* — is a
**starting hint, not a verdict**. It breaks when **scoring** is the failure point: a run can
burn minutes producing working code and still be scored 0 (scorer false-fail). And a fast
no-code abort can be a harness permission denial, not a model giving up. **Always
ground-truth.**

## Output

Per failure, report: cell · cause (one of the taxonomy) · `[DIRECT]`/`[HYPOTHESIS]` with the
evidence · recommended action (`retort rescore`; fix scorer/harness then rescore; count as
genuine; re-run with capture). Then the rolled-up verdict: how many failures are infra vs
genuine, and whether the infrastructure is trustworthy enough to proceed.

## Logging setup (prerequisite)

- The runner persists `_agent_stdout.log` / `_agent_stderr.log` per run (`_persist_agent_output`).
- For **opencode**, the harness passes `--print-logs` so stderr carries the diagnostic logs
  (permission evaluations, step loop). Raising opencode's level (`--log-level DEBUG`,
  `OPENCODE_LOG_LEVEL=verbose`) adds ~nothing — the `--format json` stdout stream is the
  signal.

## See also

- `retort diagnose` / `retort rescore` — automated TOOLING/GENUINE triage + recovery.
- `evaluate-run` skill — the per-run spec/quality evaluation (this skill is for *failures*).
