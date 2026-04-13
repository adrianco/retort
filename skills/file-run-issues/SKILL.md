---
name: file-run-issues
description: Turn a retort run's findings.jsonl into tracked issues. By default files beads issues under the retort project; with --github mirrors each finding as a GitHub issue on the retort repo.
type: anthropic-skill
version: "1.0"
---

# File Run Issues

## Overview

`evaluate-run` produces a `findings.jsonl` per run — one JSON object per observation. On its own that file isn't actionable. This skill turns findings into tracked work items so regressions and patterns across runs become visible in whatever issue tracker you use.

Retort's canonical tracker is **beads** (the `re` project). GitHub issues are an optional mirror for items worth surfacing to external contributors — most findings are experimental noise and shouldn't pollute the GitHub tracker.

## Parameters

- **run_dir** (required): Same path `evaluate-run` used, e.g. `experiment-1/runs/language=rust_model=opus_tooling=beads/rep2/`
- **tracker** (optional, default: `beads`): `beads` | `github` | `both`
- **github_repo** (optional, default: `adrianco/retort`): Only used when tracker includes `github`
- **dry_run** (optional, default: `false`): Print what would be filed without creating anything
- **min_severity** (optional, default: `medium`): Skip findings below this severity. Options: `critical`, `high`, `medium`, `low`, `info`

## Steps

### 1. Load findings

```bash
test -f {run_dir}/findings.jsonl || { echo "no findings.jsonl — run evaluate-run first"; exit 1; }
```

Read the file line-by-line. Each line is one finding. Extract the cell and replicate from the directory path for use in issue titles.

### 2. Filter by severity

Drop findings whose `severity` is below `min_severity`. Report the count dropped so the user knows the filter applied.

### 3. De-duplicate against existing tracker state

Existing issues from prior runs of the same cell MUST NOT be re-filed.

For beads (default tracker), match on a stable key: `<cell>#<rep>#<finding.id>`. Stored in the issue body as a footer:

```
retort-finding: language=rust_model=opus_tooling=beads#rep2#R5
```

Before filing, grep the open issues for that footer:

```bash
bd list --json | jq -r '.[] | select(.body | contains("retort-finding: {key}"))'
```

For GitHub, use the same key in the body and check:

```bash
gh issue list -R {github_repo} --state all --search "retort-finding: {key}" --json number,title
```

Constraints:
- You MUST NOT file a duplicate. If the issue exists, log `skip: already tracked as <id>`.
- You MUST match on the exact stable key, not on title similarity. Agents produce slightly different titles on re-evaluation.
- You MUST check closed issues too — a closed issue with the same key means the problem was explicitly resolved; re-filing would be noise.

### 4. Map finding → tracker record

For each surviving finding, construct:

| Field | Beads | GitHub |
|-------|-------|--------|
| Title | `[{cell}#rep{N}] {finding.title}` (≤80 chars) | same |
| Type | `bug` for `*_failure`/`test_failure`, `task` for `skipped_test`, `enhancement` for `requirement_missing`/`enhancement`, `chore` otherwise | label instead (see below) |
| Priority | `1` (critical) / `2` (high) / `3` (medium) / `4` (low) / `5` (info) | no priority field — rely on label |
| Labels | `retort`, `auto-filed`, `severity:{sev}`, `kind:{kind}` | `retort`, `severity-{sev}`, `kind-{kind}` |
| Body | See template below | same |

Body template:

```markdown
## Finding

{finding.title}

**Severity:** {severity}
**Kind:** {kind}

## Evidence

{finding.evidence}

## Suggestion

{finding.suggestion}

## Context

- **Run:** {run_dir}
- **Cell:** {cell_name}
- **Replicate:** {replicate}
- **Factors:** {factors dict}
- **Evaluation:** See `{run_dir}/evaluation.md`
- **Summary:** See `{run_dir}/summary/index.md`

---

retort-finding: {stable_key}
```

### 5. File into beads

```bash
bd create "{title}" \
  --type={type} \
  --priority={priority} \
  --labels=retort,auto-filed,severity:{sev},kind:{kind} \
  --description="{body}" \
  --json
```

Capture the returned bead ID. On failure, log and continue — do not abort the whole batch on a single file failure.

### 6. File into GitHub (if enabled)

Use `gh` CLI. Labels are GitHub-flat (use `severity-high` not `severity:high`) since colons in labels are awkward:

```bash
gh issue create \
  -R {github_repo} \
  --title "{title}" \
  --body "{body}" \
  --label retort \
  --label severity-{sev} \
  --label kind-{kind}
```

Constraints:
- You SHOULD only enable GitHub for high/critical findings by default. The full firehose would spam the repo.
- You MUST verify the labels exist before filing (`gh label list`) and create missing ones once if needed. A single label-creation failure MUST NOT block issue creation — fall back to filing without the missing label.
- You SHOULD rate-limit to ≤5 GitHub issues per minute to stay well under the API quota.

### 7. Update the run's findings.jsonl

After filing, annotate each finding with the issue references:

```json
{"id": "R5", "kind": "requirement_missing", "severity": "high", "title": "...", "evidence": "...", "suggestion": "...",
 "filed": {"beads": "re-a1b", "github": "https://github.com/adrianco/retort/issues/42"}}
```

Constraints:
- You MUST write the annotated file atomically — write to `findings.jsonl.tmp` and rename.
- If the skill is re-invoked, the `filed` fields are used by Step 3 as a second source of dedup truth.

### 8. Emit a summary

Print a terminal-readable summary:

```
Filed from {run_dir}:
  beads:  3 new, 2 skipped (already tracked)
  github: 1 new (high/critical only), 4 below threshold
Dropped 6 findings below min_severity=medium.
See runs/.../findings.jsonl for filed issue links.
```

## Constraints Summary

- You MUST NOT file duplicates. Stable-key dedup is required.
- You MUST NOT file `info` severity findings to GitHub under any default.
- You MUST NOT abort on a single file-create failure. Log and continue.
- You MUST annotate the findings.jsonl with filed issue references for audit.
- You MUST be safe to re-run repeatedly. Step 3 dedup + Step 7 annotations guarantee idempotence.
- You MUST respect `--dry-run` by only *printing* what would be filed.

## Interaction with retort

- The retort CLI MAY invoke this skill automatically after `evaluate-run` completes. Policy (which findings auto-file) is set in `workspace.yaml`:
  ```yaml
  evaluation:
    auto_file_issues: true
    issue_tracker: beads        # beads | github | both
    min_severity: high          # auto-file only high+critical; lower severities stay in findings.jsonl
  ```
- Manual invocation SHOULD work on any `run_dir` regardless of whether the CLI invoked `evaluate-run` automatically.

## Troubleshooting

**Beads is unreachable**
- If `bd` returns an error, retry up to 3 times with 1s backoff.
- If all retries fail, skip beads, proceed with GitHub (if enabled), and exit non-zero so the CLI knows.

**GitHub issues disabled on the repo**
- Detect via `gh repo view --json hasIssuesEnabled`. Skip GitHub filing and log a single warning.

**Label creation fails**
- File the issue without the missing label. The tracker-level automation (saved searches, filters) will still work based on the body footer.

**Issue already exists with slightly different body**
- Do NOT update the existing issue. Filed issues are append-only from this skill's perspective — human curation is for humans.
