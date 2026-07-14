# experiment-2 — results

Task: **brazil-soccer-mcp**  ·  22 scored runs  ·  generated from `master.db` (clean opus-4.6 second-opinion spec gate).

**Pass** = fraction of replicates that fully implement the spec (`requirement_coverage == 1.0`) = probability of a completely-correct run.

| Language | Model | Tooling | n | Pass | TestCov | Speed (s) | Cost ($) | CodeQual |
|---|---|---|---:|---:|---:|---:|---:|---:|
| clojure | opus-4.6 | beads | 1 | 0/1 = 0.00 | 1.00 | 343 | 1.39 | 0.83 |
| clojure | opus-4.6 | none | 1 | 0/1 = 0.00 | 1.00 | 178 | 0.81 | 0.83 |
| clojure | sonnet | beads | 1 | 1/1 = 1.00 | 1.00 | 410 | 1.03 | 0.83 |
| clojure | sonnet | none | 1 | 0/1 = 0.00 | 1.00 | 437 | 1.12 | 0.83 |
| go | opus-4.6 | beads | 1 | 0/1 = 0.00 | 0.33 | 269 | 1.23 | 1.00 |
| go | opus-4.6 | none | 1 | 0/1 = 0.00 | 0.42 | 274 | 1.39 | 1.00 |
| go | sonnet | none | 1 | 0/1 = 0.00 | 0.77 | 426 | 1.18 | 1.00 |
| java | opus-4.6 | beads | 1 | 0/1 = 0.00 | 1.00 | 341 | 1.75 | 1.00 |
| java | opus-4.6 | none | 1 | 1/1 = 1.00 | 1.00 | 218 | 1.26 | 1.00 |
| java | sonnet | beads | 1 | 0/1 = 0.00 | 1.00 | 674 | 1.84 | 1.00 |
| python | opus-4.6 | beads | 1 | 1/1 = 1.00 | 0.85 | 349 | 1.73 | 0.67 |
| python | opus-4.6 | none | 1 | 1/1 = 1.00 | 0.80 | 149 | 0.73 | 0.67 |
| python | sonnet | beads | 1 | 1/1 = 1.00 | 0.97 | 483 | 1.25 | 0.67 |
| python | sonnet | none | 1 | 0/1 = 0.00 | 0.96 | 329 | 0.72 | 0.67 |
| rust | opus-4.6 | beads | 1 | 0/1 = 0.00 | 1.00 | 350 | 1.57 | 0.83 |
| rust | opus-4.6 | none | 1 | 0/1 = 0.00 | 1.00 | 175 | 0.87 | 0.83 |
| rust | sonnet | beads | 1 | 0/1 = 0.00 | 0.33 | 533 | 1.11 | 0.83 |
| rust | sonnet | none | 1 | 1/1 = 1.00 | 1.00 | 471 | 1.14 | 0.83 |
| typescript | opus-4.6 | beads | 1 | 0/1 = 0.00 | 0.00 | 205 | 1.07 | 0.00 |
| typescript | opus-4.6 | none | 1 | 1/1 = 1.00 | 0.00 | 188 | 1.01 | 0.00 |
| typescript | sonnet | beads | 1 | 1/1 = 1.00 | 1.00 | 362 | 0.92 | 0.73 |
| typescript | sonnet | none | 1 | 1/1 = 1.00 | 0.96 | 274 | 0.71 | 0.73 |

Back to the [README](../../../README.md).
