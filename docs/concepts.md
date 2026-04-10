# Concepts: Design of Experiments for AI Tooling

Retort applies classical Design of Experiments (DoE) methodology to the problem of evaluating AI-assisted development stacks. This guide explains the statistical foundations.

## The problem

With multiple languages, AI agents, frameworks, app types, and orchestration strategies, the combinatorial space is enormous. A full factorial of 6 factors at ~4 levels each is ~4,000+ runs. Each run costs time and API credits. You can't test everything.

## Fractional factorial designs

Fractional factorial designs test a carefully chosen subset of combinations that still lets you estimate the effects that matter:

- **Main effects**: Does the choice of language matter? Does the agent matter?
- **Two-factor interactions**: Does the effect of the agent depend on the language?

A Resolution III design aliases three-factor interactions with main effects but cleanly estimates all main effects. Resolution IV also cleanly estimates two-factor interactions.

### Screening vs. characterization

Retort uses a two-phase approach:

1. **Screening** (Resolution III) — Test all factors with minimal runs. Discard factors with negligible effects. If "orchestration style" doesn't matter, drop it.
2. **Characterization** (Resolution IV/V) — Test surviving factors with enough runs to estimate interactions. "Does Claude-Code + Python outperform Claude-Code + TypeScript?"

## Responses (metrics)

Each experiment run produces a vector of response metrics:

| Metric | What it measures |
|--------|-----------------|
| `code_quality` | Lint pass rate, complexity, type coverage |
| `token_efficiency` | Tokens consumed per unit of functionality |
| `build_time` | Wall clock to first green build |
| `test_coverage` | Generated test coverage percentage |
| `defect_rate` | Post-generation validation failures |
| `maintainability` | Cross-agent modification success rate |
| `idiomatic_score` | LLM-as-judge convention adherence |

## ANOVA: Which factors matter?

For each response, Retort fits a linear model:

```
y = mean + effect(language) + effect(agent) + effect(language x agent) + noise
```

ANOVA (Analysis of Variance) tests whether each factor's effect is statistically significant. A p-value below the threshold (default 0.10) means the factor has a real effect, not just noise from non-deterministic LLM outputs.

## Bayesian updating

Classical ANOVA gives yes/no significance. Bayesian analysis accumulates confidence continuously:

- Start with a prior belief about effect sizes
- Update as each replicate comes in
- Report posterior probability that a stack is competitive

This avoids the fixed-sample-size requirement of classical tests — you can stop when you're confident enough.

## Pareto frontier

With multiple response metrics, no single stack "wins" on everything. The Pareto frontier identifies stacks that aren't dominated — no other stack is better on every metric simultaneously. A stack on the frontier represents a real trade-off (e.g., fast but expensive vs. slow but cheap).

## Candidate lifecycle

Every stack combination follows a lifecycle:

```
Candidate → Screening → Trial → Production → Retired
```

Promotion gates are configurable:
- **Screening → Trial**: Main effect p-value < 0.10 on at least one response
- **Trial → Production**: 80% posterior probability of being Pareto-non-dominated
- **Production → Retired**: 95% posterior probability of being Pareto-dominated

When a new candidate appears (e.g., a new AI agent ships), D-optimal augmentation adds rows to the existing design matrix without re-running old experiments.

## Replicates and noise

LLM outputs are non-deterministic. The same prompt can produce different code quality each time. Retort handles this by:

1. Running multiple replicates per design point (default: 3)
2. Explicitly modeling run-to-run variance in the ANOVA
3. Using residual diagnostics to check model adequacy

If residuals show patterns, the model may need higher resolution or additional factors.
