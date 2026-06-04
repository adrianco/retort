# experiment-7 — results

**Opus-4.8 fast mode** (`/fast` — same model, faster output) on both tasks, vs the regular-4.8 baseline in experiments 5 & 6. 24 scored runs · generated from `master.db` (clean opus-4.6 second-opinion spec gate).

**Pass** = fraction of replicates that fully implement the spec (`requirement_coverage == 1.0`) = probability of a completely-correct run.

## Brazil-soccer-MCP (hard task)

| Language | Model | n | Pass | TestCov | Speed (s) | Cost ($) | CodeQual |
|---|---|---:|---:|---:|---:|---:|---:|
| clojure | opus-4.8-fast | 3 | 3/3 = 1.00 | 1.00 | 712 | 3.09 | 0.83 |
| go | opus-4.8-fast | 3 | 3/3 = 1.00 | 0.62 | 959 | 4.95 | 1.00 |
| python | opus-4.8-fast | 3 | 3/3 = 1.00 | 0.92 | 967 | 4.96 | 0.67 |
| rust | opus-4.8-fast | 3 | 3/3 = 1.00 | 1.00 | 909 | 4.45 | 0.83 |

## REST-API CRUD (bookshop, easy task)

| Language | Model | n | Pass | TestCov | Speed (s) | Cost ($) | CodeQual |
|---|---|---:|---:|---:|---:|---:|---:|
| clojure | opus-4.8-fast | 3 | 3/3 = 1.00 | 1.00 | 208 | 0.68 | 0.83 |
| go | opus-4.8-fast | 3 | 3/3 = 1.00 | 0.71 | 140 | 0.58 | 1.00 |
| python | opus-4.8-fast | 3 | 3/3 = 1.00 | 0.97 | 90 | 0.37 | 0.89 |
| rust | opus-4.8-fast | 3 | 3/3 = 1.00 | 1.00 | 135 | 0.53 | 0.83 |

Every cell holds pass-proportion **1.00** — fast mode matched regular-4.8's reliability on both tasks while running cheaper (and, on the easy task, much faster). See the [README](../README.md#fast-mode-same-reliability-less-time-and-money) for the fast-vs-regular comparison.
