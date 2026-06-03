# experiment-6 — results

Task: **rest-api-crud**  ·  71 scored runs  ·  generated from `master.db` (clean opus-4.6 second-opinion spec gate).

**Pass** = fraction of replicates that fully implement the spec (`requirement_coverage == 1.0`) = probability of a completely-correct run.

| Language | Model | Tooling | n | Pass | TestCov | Speed (s) | Cost ($) | CodeQual |
|---|---|---|---:|---:|---:|---:|---:|---:|
| clojure | opus-4.7 | beads | 3 | 3/3 = 1.00 | 1.00 | 237 | 1.21 | 0.83 |
| clojure | opus-4.7 | none | 3 | 3/3 = 1.00 | 1.00 | 188 | 0.92 | 0.83 |
| clojure | opus-4.8 | beads | 3 | 3/3 = 1.00 | 1.00 | 332 | 1.43 | 0.83 |
| clojure | opus-4.8 | none | 3 | 3/3 = 1.00 | 1.00 | 683 | 2.42 | 0.83 |
| go | opus-4.7 | beads | 3 | 3/3 = 1.00 | 0.68 | 179 | 1.02 | 1.00 |
| go | opus-4.7 | none | 3 | 3/3 = 1.00 | 0.68 | 152 | 0.76 | 1.00 |
| go | opus-4.8 | beads | 3 | 3/3 = 1.00 | 0.71 | 161 | 0.72 | 1.00 |
| go | opus-4.8 | none | 3 | 3/3 = 1.00 | 0.69 | 133 | 0.61 | 1.00 |
| java | opus-4.7 | beads | 3 | 3/3 = 1.00 | 1.00 | 194 | 1.00 | 1.00 |
| java | opus-4.7 | none | 3 | 3/3 = 1.00 | 1.00 | 168 | 0.83 | 1.00 |
| java | opus-4.8 | beads | 3 | 3/3 = 1.00 | 1.00 | 505 | 1.93 | 1.00 |
| java | opus-4.8 | none | 2 | 2/2 = 1.00 | 1.00 | 176 | 0.80 | 1.00 |
| python | opus-4.7 | beads | 3 | 3/3 = 1.00 | 1.00 | 116 | 0.68 | 0.75 |
| python | opus-4.7 | none | 3 | 3/3 = 1.00 | 1.00 | 84 | 0.50 | 0.78 |
| python | opus-4.8 | beads | 3 | 3/3 = 1.00 | 0.98 | 156 | 0.63 | 0.77 |
| python | opus-4.8 | none | 3 | 3/3 = 1.00 | 1.00 | 88 | 0.37 | 0.79 |
| rust | opus-4.7 | beads | 3 | 3/3 = 1.00 | 1.00 | 194 | 0.98 | 0.83 |
| rust | opus-4.7 | none | 3 | 3/3 = 1.00 | 1.00 | 154 | 0.73 | 0.83 |
| rust | opus-4.8 | beads | 3 | 3/3 = 1.00 | 1.00 | 156 | 0.67 | 0.83 |
| rust | opus-4.8 | none | 3 | 3/3 = 1.00 | 1.00 | 213 | 0.76 | 0.83 |
| typescript | opus-4.7 | beads | 3 | 3/3 = 1.00 | 0.88 | 180 | 0.93 | 0.73 |
| typescript | opus-4.7 | none | 3 | 3/3 = 1.00 | 0.91 | 128 | 0.57 | 0.73 |
| typescript | opus-4.8 | beads | 3 | 3/3 = 1.00 | 0.97 | 168 | 0.67 | 0.73 |
| typescript | opus-4.8 | none | 3 | 3/3 = 1.00 | 0.97 | 119 | 0.47 | 0.73 |

Back to the [README](../README.md).
