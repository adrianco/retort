# Experiment 14 — prompt methodology across the other six languages

Extends [exp-13](../experiment-13/results.md) (go + python) to **clojure, rust,
java, typescript, erlang, elixir** with the same two models (sonnet,
opus-4.8-fast) and the same `neutral / TDD / ATDD` prompts on the
methodology-neutral brazil fork. **1 replicate** (36 cells) — so per-cell results
are binary (pass/fail) and directional, not pass-proportions.

35 of 36 cells completed (graded by `claude-opus-4-8`). The one that didn't,
clojure/sonnet/TDD, ran during a usage-limit window and never finished — a
token casualty, not a graded failure.

## Reliability — did the single run fully implement the spec?

**opus-4.8-fast: 1.00 on every language × every prompt** — it saturates here just
as it did on go/python. There is nothing for the prompt to move on the strong
model.

**sonnet** (✓ = req_coverage 1.0, ✗ = short, — = didn't complete):

| language | neutral | TDD | ATDD |
|---|:--:|:--:|:--:|
| clojure | ✓ | — | ✓ |
| elixir | ✓ | ✓ | ✓ |
| erlang | ✓ | ✓ | ✓ |
| java | ✓ | ✓ | ✓ |
| rust | ✓ | ✓ | ✓ |
| typescript | ✗ (0.92) | ✓ | ✗ (0.92) |

- Sonnet clears the spec on **five of the six languages with every prompt**.
- The two genuine misses are both **TypeScript** (neutral and ATDD each landed at
  requirement_coverage 0.92 — one requirement short), and they are *not*
  prompt-specific: TDD passed TypeScript, but neutral and ATDD didn't. That reads
  as a TypeScript-Sonnet quirk, not a methodology effect.
- clojure/TDD is the lone unfinished cell (usage limit) — re-run when convenient.

## Takeaway (combined with exp-13)

Across **eight languages and two models**, the same pattern holds: **the prompt
is the smallest lever.** Opus saturates regardless of methodology; Sonnet is
mostly reliable regardless of methodology, and the few dips track the
*language* (TypeScript here, Go+ATDD in exp-13), not the prescribed test
discipline. Model and language dominate reliability; the methodology mainly
changes *what tests get written* and the token bill, not whether the run ships.
(Bump exp-14 to 3 replicates if you want pass-proportions rather than the
single-run signal here.)
