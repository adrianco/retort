# experiment-1 — results

Task: **rest-api-crud**  ·  56 scored runs  ·  generated from `master.db` (clean opus-4.6 second-opinion spec gate).

**Pass** = fraction of replicates that fully implement the spec (`requirement_coverage == 1.0`) = probability of a completely-correct run.

| Language | Model | Tooling | n | Pass | TestCov | Speed (s) | Cost ($) | CodeQual |
|---|---|---|---:|---:|---:|---:|---:|---:|
| clojure | opus-4.6 | beads | 2 | 0/2 = 0.00 | 1.00 | 182 | 0.68 | 0.83 |
| clojure | opus-4.6 | none | 3 | 0/3 = 0.00 | 1.00 | 179 | 0.58 | 0.83 |
| clojure | sonnet | beads | 2 | 0/2 = 0.00 | 0.50 | 230 | 0.48 | 0.42 |
| clojure | sonnet | none | 2 | 1/2 = 0.50 | 0.50 | 329 | 0.56 | 0.42 |
| go | opus-4.6 | beads | 2 | 2/2 = 1.00 | 0.61 | 117 | 0.49 | 1.00 |
| go | opus-4.6 | none | 2 | 2/2 = 1.00 | 0.63 | 94 | 0.36 | 1.00 |
| go | sonnet | beads | 2 | 2/2 = 1.00 | 0.64 | 147 | 0.31 | 1.00 |
| go | sonnet | none | 2 | 2/2 = 1.00 | 0.67 | 123 | 0.30 | 0.96 |
| java | opus-4.6 | beads | 3 | 0/3 = 0.00 | 1.00 | 150 | 0.55 | 1.00 |
| java | opus-4.6 | none | 3 | 1/3 = 0.33 | 1.00 | 131 | 0.44 | 1.00 |
| java | sonnet | beads | 3 | 0/3 = 0.00 | 1.00 | 182 | 0.36 | 1.00 |
| java | sonnet | none | 3 | 0/3 = 0.00 | 1.00 | 152 | 0.33 | 1.00 |
| python | opus-4.6 | beads | 2 | 2/2 = 1.00 | 0.97 | 79 | 0.37 | 0.70 |
| python | opus-4.6 | none | 2 | 1/2 = 0.50 | 0.47 | 44 | 0.20 | 0.48 |
| python | sonnet | beads | 2 | 2/2 = 1.00 | 0.12 | 110 | 0.26 | 0.40 |
| python | sonnet | none | 2 | 1/2 = 0.50 | 0.48 | 74 | 0.23 | 0.31 |
| rust | opus-4.6 | beads | 3 | 3/3 = 1.00 | 1.00 | 143 | 0.48 | 0.83 |
| rust | opus-4.6 | none | 3 | 2/3 = 0.67 | 1.00 | 106 | 0.33 | 0.83 |
| rust | sonnet | beads | 2 | 2/2 = 1.00 | 1.00 | 208 | 0.41 | 0.83 |
| rust | sonnet | none | 3 | 3/3 = 1.00 | 1.00 | 194 | 0.36 | 0.83 |
| typescript | opus-4.6 | beads | 2 | 2/2 = 1.00 | 0.54 | 219 | 0.51 | 0.73 |
| typescript | opus-4.6 | none | 2 | 2/2 = 1.00 | 0.92 | 181 | 0.32 | 0.73 |
| typescript | sonnet | beads | 3 | 3/3 = 1.00 | 0.91 | 168 | 0.38 | 0.73 |
| typescript | sonnet | none | 1 | 1/1 = 1.00 | 0.89 | 281 | 0.53 | 0.73 |

Back to the [README](../../../README.md).
