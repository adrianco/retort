# experiment-4 — results

Task: **brazil-soccer-mcp**  ·  6 scored runs  ·  generated from `master.db` (clean opus-4.6 second-opinion spec gate).

**Pass** = fraction of replicates that fully implement the spec (`requirement_coverage == 1.0`) = probability of a completely-correct run.

| Language | Model | Tooling | n | Pass | TestCov | Speed (s) | Cost ($) | CodeQual |
|---|---|---|---:|---:|---:|---:|---:|---:|
| clojure | opus-4.8 | none | 2 | 2/2 = 1.00 | 1.00 | 1047 | 5.04 | 0.83 |
| go | opus-4.8 | none | 2 | 2/2 = 1.00 | 0.44 | 1054 | 5.85 | 1.00 |
| python | opus-4.8 | beads | 2 | 2/2 = 1.00 | 0.86 | 959 | 5.19 | 0.83 |

Back to the [README](../../../README.md).
