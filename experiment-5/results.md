# experiment-5 — results

Task: **brazil-soccer-mcp**  ·  36 scored runs  ·  generated from `master.db` (clean opus-4.6 second-opinion spec gate).

**Pass** = fraction of replicates that fully implement the spec (`requirement_coverage == 1.0`) = probability of a completely-correct run.

| Language | Model | Tooling | n | Pass | TestCov | Speed (s) | Cost ($) | CodeQual |
|---|---|---|---:|---:|---:|---:|---:|---:|
| clojure | opus-4.7 | none | 3 | 3/3 = 1.00 | 1.00 | 765 | 4.65 | 0.83 |
| clojure | opus-4.8 | none | 3 | 3/3 = 1.00 | 1.00 | 941 | 4.58 | 0.83 |
| go | opus-4.7 | none | 3 | 2/3 = 0.67 | 0.67 | 533 | 3.69 | 1.00 |
| go | opus-4.8 | none | 3 | 3/3 = 1.00 | 0.48 | 867 | 4.59 | 1.00 |
| java | opus-4.7 | none | 3 | 3/3 = 1.00 | 1.00 | 739 | 4.71 | 1.00 |
| java | opus-4.8 | none | 3 | 3/3 = 1.00 | 1.00 | 1220 | 6.36 | 1.00 |
| python | opus-4.7 | none | 3 | 3/3 = 1.00 | 0.93 | 765 | 4.64 | 0.83 |
| python | opus-4.8 | none | 3 | 3/3 = 1.00 | 0.92 | 899 | 5.10 | 0.67 |
| rust | opus-4.7 | none | 3 | 1/3 = 0.33 | 1.00 | 799 | 5.56 | 0.83 |
| rust | opus-4.8 | none | 3 | 3/3 = 1.00 | 1.00 | 1081 | 6.09 | 0.83 |
| typescript | opus-4.7 | none | 3 | 3/3 = 1.00 | 0.98 | 638 | 4.14 | 0.73 |
| typescript | opus-4.8 | none | 3 | 3/3 = 1.00 | 1.00 | 1227 | 6.86 | 0.73 |

Back to the [README](../README.md).
