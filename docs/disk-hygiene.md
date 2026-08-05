# Where retort's bytes live, and what to clean up

Survey of this machine on 2026-08-05, with a proposed layout and a staged cleanup.
**Nothing here has been executed.** Every destructive step is listed with its size,
its risk, and how to verify before running it.

Headline: `$HOME` holds ~**400 GB** of retort-adjacent state, of which roughly
**200 GB is recoverable** without losing a single experiment result. Separately —
and more importantly than the bytes — agents have been writing task artifacts
directly into `$HOME`.

## 1. The actual problem: retort has no single runtime root

Results live in the repo (`experiments/<owner>/…`, `master.db`) and that part is
tidy. Everything else scatters:

| what | where it lives now | size |
|---|---|---|
| playpen workspaces | `~/.retort/work/` | 33 GB, 3,326 dirs |
| oMLX SSD prefix caches | `~/.cache/omlx-ssd*` | 110 GB |
| model weights | `~/.cache/huggingface/hub/` | 145 GB |
| oMLX internal cache | `~/.omlx/cache/` | 25 GB |
| **task artifacts** | **loose in `$HOME`** | ~200 MB |

Only the first is namespaced to retort. The proposal is a single runtime root
that owns every machine-local byte retort creates — `work/` beside `cache/` and
`logs/` — so there is one directory to exclude from backup, one to measure, one
to purge, and one env var (`RETORT_HOME`) to relocate it.

**It should live in the repo: `<repo>/.retort/`, gitignored.** Everything scoped
to the project directory, so deleting the checkout leaves the machine clean and
two checkouts cannot contend. That is the right default — with two exceptions
and one precondition, all of them load-bearing.

### Precondition: playpens must become ephemeral first

Measured on this machine today:

| | files | `git status` |
|---|---:|---:|
| repo now | 245,190 (20,694 tracked) | 1.38 s |
| `~/.retort/work` | 510,863 | — |
| repo if playpens move in as-is | ~756,000 | ~4–5 s (est.) |

Git stats the working tree even for ignored paths, so moving 3,326 accumulated
workspaces inside would make **every** git command in this repo three times
slower. That is an argument against *accumulation*, not against *location*: with
guardrail 2 below (delete the playpen once its results are archived) the steady
state is one or two live workspaces, and the objection evaporates.

**So: adopt repo-scoping and prune-on-completion together.** Repo-scoping alone,
without pruning, makes the repo unpleasant to work in.

### Exception 1: model weights stay in the shared HF cache

`~/.cache/huggingface` holds 145 GB and is the Hugging Face convention — other
tools on this machine read it, and a second checkout would otherwise re-download
42 GB for the 80B alone. retort should *point* at it (`HF_HOME`) rather than own
it. This is the one place where machine-scoped beats project-scoped.

### Exception 2 to weigh: blast radius

Today an agent with a mis-set `cwd` wrote a bookshop into `$HOME` — untidy, but
it touched nothing that mattered. With playpens inside the repo, the same slip
puts a coding agent's writes next to `src/`, `experiments/` and `master.db`. The
`$HOME` incident cost a cleanup; the repo version could corrupt results.

That is not a reason to reject repo-scoping — it is a reason guardrail 1 (assert
the workspace path, abort otherwise) is mandatory rather than nice-to-have. If
only one guardrail gets built, build that one.

The oMLX SSD caches are retort-specific and move under the root unambiguously.

## 2. Task artifacts in `$HOME` — a bug, not clutter

These are in the home directory right now:

```
README.md          "# Book Collection REST API"      Jul 11
main.py  test_api.py  requirements.txt               Jul 11
books.db  test_books.db                              Jul 11
app.go  app_test.go  go.mod  go.sum                  Jul 12-24
package-lock.json                                    Mar 27
book-api/ (88M)  bookapi/ (13M)  book-collection/    Jul 10-13
erlang-workspace/  dev/ (93M, contains book-api/)
```

An agent ran with `cwd=$HOME` instead of a playpen and wrote a complete bookshop
implementation into the home directory. The dates (10–13 July, one straggler on
24 July) put it in the era when the playpen path was being moved — the same
class of bug as the `/var` write-refusal recorded in CLAUDE.md, except this one
wrote *successfully* to the wrong place, so nothing failed and nobody noticed.

None of it is a git repo; none of it is referenced by the repo. It is recoverable
scratch, but the *lesson* is the guardrail in §5: a run should refuse to start if
its workspace is not under the runtime root.

## 3. Cleanup, in order of safety

**Do none of this while a run or measurement sweep is active** — a sweep is live
right now and is rebuilding archived runs, which touches the language caches.

### Tier 1 — dead experiment caches · ~90 GB · very low risk

```
~/.cache/omlx-ssd-exp39   13 GB    ~/.cache/omlx-ssd-exp45   17 GB
~/.cache/omlx-ssd-exp41   20 GB    ~/.cache/omlx-ssd-exp49   20 GB
~/.cache/omlx-ssd-exp43   20 GB
```

Per-experiment snapshots of the oMLX paged-SSD prefix cache, from runs that
finished weeks ago. **exp-24 concluded that this cache does not help** — these
runs are generation-bound, not prefill-bound — so they are not even holding a
useful optimisation. Regenerable by definition: a cache.

**Keep `~/.cache/omlx-ssd`** (the unsuffixed one, 20 GB). It is the live path,
referenced by `docs/configuration.md`, `optimal-blog.md` and the disk preflight
in `cli.py`.

### Tier 2 — superseded model weights · ~57 GB · low risk, costs a re-download

| model | size | why it can go |
|---|---:|---|
| `Devstral-Small-2507-4bit` + GGUF | 29 GB | exp-23; superseded, never promoted |
| `Qwen3-Coder-30B-A3B-Instruct` MLX + GGUF | 33 GB | exp-16 era; superseded by the 35B and 80B |
| `gpt-oss-20b-MXFP4-Q8` | 11 GB | exp-47 ran and parked it — "fast, uneven, not a replacement" |

**Keep** `Qwen3-Coder-Next-4bit` (42 GB — the current best local stack) and
`Qwen3.6-35B-A3B` (20 GB — the faster Python/Go alternative, and the model
`stack_reload.py` addresses by name).

Deleting a model means re-downloading it to re-run its experiment. The archived
results and `provenance.json` survive regardless, so history is not lost — only
the ability to re-run without a download.

### Tier 3 — old playpens · ~25 GB · low risk

731 of the 3,326 workspaces under `~/.retort/work` are older than 14 days.
Playpens are scratch: results were archived into `experiments/` when each run
finished. Verify with `-print` before deleting:

```bash
find ~/.retort/work -maxdepth 1 -type d -mtime +30 -print
```

Note `retort rebuild` and the runtime probe operate on the **archived** copies
under `experiments/`, not on playpens — so pruning these does not break
measurement. Confirmed: the runtime sweep rebuilds inside `experiments/…/runs/`.

### Tier 4 — `$HOME` task artifacts · ~200 MB · low risk, read first

The §2 list. Small, but the reason to clear it is tidiness and the guardrail,
not space. Move rather than delete if you want to keep an example of what an
early agent produced.

### Not touching

`Library/Application Support` (27 GB), `Music` (15 GB), `Documents` (17 GB),
`~/.omlx/cache` (25 GB — oMLX's own store, owned by that tool, not retort),
`code/` (15 GB). Out of scope.

## 4. Security: a loose credential

`~/openaikey` — 165 bytes of ASCII, mode `-rw-r--r--` (**world-readable**), dated
2026-08-04, referenced by nothing in `~/.zshrc`, `~/.zprofile`, or this repo.

It has the shape of an API key sitting unprotected in the home directory. It is
not read here. Recommended: confirm what it is, and if it is a live key, rotate
it and store it in the keychain or a `600` file outside `$HOME`'s browsable
root. If it is a leftover, delete it. Either way it should not be `644`.

## 5. Guardrails, so this does not come back

1. **A runtime root, and a refusal.** `provision()` should assert the workspace
   is under the runtime root and abort otherwise. The `$HOME` litter exists
   because writing to the wrong place succeeded silently — the harness has a
   guard for *no* writes but none for writes to the *wrong place*. This becomes
   **mandatory** once the root is inside the repo: the same slip that scattered
   files in `$HOME` would then land beside `src/` and `experiments/`.
2. **Prune on completion.** `retort run` already archives a workspace when a
   cell finishes; it should then delete the playpen unless `--keep-playpen`.
   3,326 accumulated because nothing ever removes them — 510,863 files, which is
   what makes moving them into the repo untenable until this exists. Pair it
   with the move, not after.
3. **Namespace the SSD cache under the root** so a purge is one directory, and
   add `.retort/` to `.gitignore` plus a `tmutil addexclusion` line — a
   repo-scoped root inherits whatever backup policy covers `~/code`, which for
   caches is the wrong one.
4. **Report disk in the run summary.** The preflight already warns below 15 GB;
   printing bytes-created per run would have surfaced 110 GB of caches long ago.
5. **A `retort clean` command** with `--dry-run` by default, covering tiers 1–3.

## 6. Suggested order

```
1. wait for the active sweep to finish            (measurements need a quiet box)
2. Tier 1 — omlx-ssd-exp*                          ~90 GB
3. Tier 3 — playpens older than 30 days            ~25 GB   (--print first)
4. Tier 4 — $HOME task artifacts                   ~200 MB
5. inspect and resolve ~/openaikey                 (security, not space)
6. Tier 2 — superseded models, only if space is still wanted   ~57 GB
```

Stopping after step 3 recovers ~115 GB and touches nothing that cannot be
regenerated by a cache warm-up. Tier 2 is last because it is the only step that
costs a download to undo.
