# Re-scoring earlier experiments after the scorer fixes

The scorer fixes (clojure `lein`, erlang Common Test, elixir `Result: N passed`,
BEAM `maintainability`/`defect_rate`) recover false-failures going forward. This
note records what could — and could **not** — be retroactively corrected on the
already-archived experiments (1–8), using `retort rescore` / `retort reevaluate`.

## What was redone

**experiment-8 (Erlang + Elixir, REST API):** `maintainability` and `defect_rate`
were `0.0` for all 12 BEAM runs — purely because those languages were missing
from the scorers' language tables when exp-8 ran. These runs *passed*
(`test_coverage=1.0`, `requirement_coverage=1.0`); only those two **static**
metrics were wrong. Recomputed directly from source (no rebuild needed):

```
retort rescore --experiment-dir experiment-8 --languages erlang,elixir \
               --metrics maintainability,defect_rate
```

Result: `maintainability` now 0.75–0.97, `defect_rate` 1.0 (were 0.0). The
corrected values are written to each run's `scores.json` (committed here);
`retort rescore` also updates `experiment-8/retort.db`, and `retort aggregate`
refreshes `master.db`/`master.csv` — regenerate those locally (they are not
re-committed here).

## What could NOT be faithfully redone (and why)

The other broken scores in exp-1…5 fall into two buckets that the committed
archives cannot support:

1. **Gating false-failures** (clojure `lein` / erlang CT runs scored
   `test_coverage=0`). Re-scoring needs to *re-run the tests*, but the archives
   were trimmed to **source + tests only** — their build dependencies (`deps/`,
   `_build/`, `~/.m2` state, lockfile-pinned versions) are gone, so a cold
   `lein test` / `rebar3` / `mix test` can't reproduce the original build.

2. **Spec-eval inconsistencies** (e.g. exp-1 `java/sonnet`: `test_coverage=1.0`,
   `code_quality=1.0`, yet `requirement_coverage≈0.083`). Re-running the spec
   eval doesn't help: the evaluate-run skill *verifies* requirements by building
   and exercising the code, and on a trimmed archive it can't build — so it
   returns noise (observed: the same cell scoring 0.083 on one replicate and 1.0
   on another). Re-grading made the data noisier, not better, so it was reverted.

**Conclusion:** trimming archives to source+tests (good for repo size) sacrificed
re-scorability for the rebuild-dependent metrics. The correct way to redo those
results is to **re-run the experiments** with the fixed scorers, not to re-score
the archives. **experiment-9** is exactly that: a fresh REST-API run (sonnet vs
opus-4.8, 8 languages) under the corrected pipeline from the start — see
`experiment-9/COMPARISON.md`. Its opus-4.8 results reproduce exp-6 exactly, and it
shows the early "sonnet is a coin-flip on REST" finding was a measurement artifact
of the bugs fixed here (the java/clojure false-failures above).

> Going forward, `retort rescore` keeps the DB and each run's `scores.json` in
> sync, so a scorer fix can be applied to any experiment **whose archives still
> contain their build environment** (e.g. one just run, before trimming).
