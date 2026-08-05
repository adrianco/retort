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

Only the first is namespaced to retort. The decided layout has **three tiers**,
split by who owns a byte and what it costs to recreate:

### Global — shared, expensive, machine-wide (leave where they are)

**Language toolchains** — `~/.cargo`, `~/.rustup`, `~/.m2`, `~/.npm`, `~/go`,
`~/.nuget`, `~/.mix`, `~/.hex`, Homebrew. These are installs, not retort state.
Every project on the machine shares them and each is its ecosystem's convention;
relocating them per-project would mean re-downloading a Maven or npm universe per
checkout for no benefit.

**Local model weights** — `~/.cache/huggingface` (145 GB) and `~/.omlx` (25 GB).
Same logic, more sharply: the 80B alone is 42 GB, other tools on this machine
read the HF cache, and a second checkout re-downloading it would be absurd.
retort should *point* at these (`HF_HOME`) and never own them.

### Retort runtime root — `~/.retort/`, outside the repo, deliberately

Playpen workspaces, the oMLX SSD prefix caches, logs. One directory to exclude
from backup, measure and purge, relocatable via `RETORT_HOME`.

**Kept out of the repo to keep git fast.** Measured today:

| | files | `git status` |
|---|---:|---:|
| repo now | 245,190 (20,694 tracked) | 1.38 s |
| `~/.retort/work` | 510,863 | — |
| repo if playpens moved in | ~756,000 | ~4–5 s (est.) |

Git stats the working tree even for ignored paths, so a repo-local root would
make **every** git command here roughly three times slower. Results and source
stay in the repo; scratch stays out.

A second, quieter reason: an agent with a mis-set `cwd` wrote a whole bookshop
into `$HOME` (§2). That was untidy but harmless. Had the playpen root been inside
the repo, the same slip would have put agent writes next to `src/`,
`experiments/` and `master.db`. Keeping scratch outside the repo bounds the blast
radius of exactly the bug that has already happened once.

### Repo — source and results only

`src/`, `experiments/<owner>/…`, `master.db`, docs and blogs. Everything here is
either authored or a durable result.

### Nowhere — `$HOME`'s root

Currently holds a bookshop implementation (§2). Guardrail 1 in §5 makes that a
startup failure rather than a silent success.

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

`~/openaikey` — 165 bytes of ASCII, dated 2026-08-04, referenced by nothing in
`~/.zshrc`, `~/.zprofile`, or this repo. It was mode `-rw-r--r--`
(**world-readable**) when surveyed; the owner has since set it to `600`
(verified 2026-08-05). Its contents are not read here and the file stays where
it is — leaving it in place is the owner's decision.

## 5. Guardrails, so this does not come back

1. **A runtime root, and a refusal.** ✅ **Done** (`local_runner.py`).
   `_assert_inside_playpen_root()` runs at both `provision()` and `execute()`:
   it refuses any workspace that resolves to `$HOME`, `/`, `/Users`, `/tmp`,
   `/var` (and their `/private` symlink targets), or that falls outside the
   runner's playpen root — naming the expected root in the error. The root is
   `~/.retort/work` by default and relocatable via `RETORT_HOME`.

   The `$HOME` litter exists because writing to the wrong place succeeded
   silently — the harness had a guard for *no* writes but none for writes to
   the *wrong place*. Keeping the root outside the repo bounds the damage; the
   assertion is what turns a silent mis-write into a startup failure. Two
   details cost a test each and are worth keeping: the check validates against
   the runner's **own** `work_dir` (validating against the global default would
   reject a legitimately-configured runner), and it tests the forbidden list
   against both the raw **and** resolved path (on macOS `/tmp` resolves to
   `/private/tmp`, so resolving first let `/tmp` through).
2. **Prune on completion.** `retort run` already archives a workspace when a
   cell finishes; it should then delete the playpen unless `--keep-playpen`.
   3,326 accumulated because nothing ever removes them — 510,863 files across
   3,326 workspaces, holding 33 GB of scratch whose results were archived weeks
   ago.
3. **Move the SSD caches under `~/.retort/cache/`** so a purge is one directory
   instead of six glob-matched ones, and carry the existing `tmutil addexclusion`
   across with them.
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
