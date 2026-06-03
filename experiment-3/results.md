# experiment-3 — results

Task: **brazil-soccer-mcp**  ·  7 scored runs  ·  generated from `master.db` (clean opus-4.6 second-opinion spec gate).

**Pass** = fraction of replicates that fully implement the spec (`requirement_coverage == 1.0`) = probability of a completely-correct run.

| Language | Model | Tooling | n | Pass | TestCov | Speed (s) | Cost ($) | CodeQual |
|---|---|---|---:|---:|---:|---:|---:|---:|
| go | opus-4.7 | none | 2 | 2/2 = 1.00 | 0.81 | 1385 | 8.13 | 1.00 |
| java | opus-4.6 | none | 1 | 1/1 = 1.00 | 1.00 | 731 | 2.21 | 1.00 |
| python | opus-4.6 | none | 2 | 1/2 = 0.50 | 0.86 | 352 | 1.07 | 0.67 |
| typescript | opus-4.6 | beads | 2 | 2/2 = 1.00 | 1.00 | 390 | 1.48 | 0.73 |

Back to the [README](../README.md).
