# Experiment 13 — Prompt / test-methodology results

**Question:** does prescribing a test methodology in the prompt (neutral vs TDD
vs ATDD, against a BDD baseline) change how reliably an agent implements the hard
Brazilian-soccer MCP task?

**Design:** the methodology-neutral fork (`github://adrianco/brazil-bench-neutral`,
BDD stripped from the repo) so methodology comes *only* from the prompt.
`language[go, python] × model[sonnet, opus-4.8-fast] × prompt[neutral, TDD, ATDD]`,
3 replicates = 36 runs. All 36 completed; graded by the `claude-opus-4-8` spec
judge (requirement_coverage).

> ⚠️ **These numbers are post-fix.** The first scoring pass marked 7 of these runs
> "failed — tests did not run". Every one was a **scorer false-failure**, not a
> model failure: `go test -cover` without `-coverpkg` scored ATDD's cross-package
> acceptance tests at 0%, and python coverage ran without the project's deps /
> without `python -m`. With those bugs fixed the runs score 77–96% and all 36 are
> completed. The earlier "ATDD has near-zero coverage" signal was entirely that
> tooling bug. See the scorer fixes + `retort diagnose` for the full story.

## Reliability — pass-proportion (requirement_coverage == 1.0)

BDD folded in from the original brazil-bench runs (BDD prescribed in-repo),
re-graded on the same judge: opus-4.8-fast n=3 (exp-7), sonnet n=1 (exp-2,
tooling=none). neutral/TDD/ATDD n=3 each.

| model | language | BDD | neutral | TDD | ATDD |
|---|---|:--:|:--:|:--:|:--:|
| opus-4.8-fast | go | 1.00 | 1.00 | 1.00 | 1.00 |
| opus-4.8-fast | python | 1.00 | 1.00 | 1.00 | 1.00 |
| sonnet | go | 1.00 | 1.00 | 1.00 | **0.33** |
| sonnet | python | 1.00 | 1.00 | 1.00 | 1.00 |

**Headline: prescribing a methodology barely moves reliability on this task.**
Fifteen of the sixteen cells pass 1.00 regardless of methodology — BDD, TDD, and
neutral are interchangeable. The single
exception is **ATDD on the weakest stack (sonnet + go)**, which drops to 0.33 —
two of three replicates landed at requirement_coverage 0.92 (a real, small spec
gap, not a tooling artefact). ATDD front-loads the most work (write executable
acceptance tests through the public interface first), and the cheaper model on
the less-forgiving language occasionally didn't carry that all the way to a
complete implementation. Where the model is strong enough (opus-4.8-fast) or the
language is forgiving (python), every methodology gets there.

## Test coverage — mean, n=3 (the real methodology signature)

| model | language | BDD | neutral | TDD | ATDD |
|---|---|:--:|:--:|:--:|:--:|
| opus-4.8-fast | go | 0.71 | 0.57 | 0.67 | 0.50 |
| opus-4.8-fast | python | 0.92 | 0.97 | 0.95 | 0.79 |
| sonnet | go | 0.77 | 0.78 | 0.69 | 0.58 |
| sonnet | python | 0.96 | 1.00 | 1.00 | 1.00 |

Now that the scorer credits cross-package acceptance tests, the expected pattern
shows up cleanly: **ATDD produces lower unit-statement coverage** than BDD/TDD/neutral
(it writes acceptance tests that exercise the system through its public interface,
not exhaustive unit tests) — yet it still meets the functional spec everywhere
except sonnet/go. That is the point of the conformance/coverage split: low unit
coverage under ATDD is *expected*, not a defect, as long as the acceptance suite
passes and the spec is met.

## Cost — mean $/run, n=3

| model | language | neutral | TDD | ATDD |
|---|---|:--:|:--:|:--:|
| opus-4.8-fast | go | 17.3 | 11.6 | 14.2 |
| opus-4.8-fast | python | 10.3 | 11.7 | 8.0 |
| sonnet | go | 3.0 | 3.3 | 1.9 |
| sonnet | python | 1.3 | 1.3 | 1.8 |

Cost is dominated by the model (opus-4.8-fast is ~5–10× sonnet), not the
methodology. No methodology is reliably cheaper.

## BDD baseline — folded in

The BDD arm comes from the original brazil-bench runs (which prescribed BDD's
Given-When-Then scenarios *in the repo*, before the methodology-neutral fork),
re-graded on the **same judge** as neutral/TDD/ATDD so the pass-proportions are
comparable: opus-4.8-fast from exp-7/brazil (n=3), sonnet from exp-2
(tooling=none, n=1).

- It needed **re-grading, not re-scoring** — BDD's in-package tests were never a
  scorer false-failure (unlike ATDD's cross-package ones), so test_coverage was
  already fine; the only stale part was the older judge. Re-grading on the
  current judge flipped sonnet's borderline 0.92s to 1.00 — they were a
  judge-era artefact, not a real spec gap.
- **Result: BDD lands with TDD and neutral** — pass 1.00 across all four cells,
  unit coverage 0.71–0.96. It is *not* the ATDD-style coverage outlier.

Caveats: BDD ran on the original template (not the neutral fork), and its sonnet
arm is n=1, so treat it as a consistent reference rather than a perfectly matched
fourth arm. (Older experiments' python archives ship no `requirements.txt`, so
they cannot be *re-scored* — re-grading, which reads the code, is unaffected.)

## Takeaways

1. On a task the model already knows how to do, **the methodology you prescribe
   is mostly a wash for reliability** — strong models pass regardless.
2. The one place it bit: **ATDD × the weakest stack (sonnet/go)**, where the
   extra up-front discipline occasionally cost a complete implementation.
3. **ATDD trades unit coverage for acceptance coverage** — visible only once the
   scorer stopped miscounting cross-package tests as 0%.
4. The biggest lesson was about the harness, not the methodology: a coverage-tool
   blind spot made an entire methodology look broken. `retort diagnose` and the
   reevaluate health-check now catch that class of false-failure automatically.
