# Retort Experiment Report

Generated: 2026-04-10 21:37

## Experiment Configuration

| Setting | Value |
|---------|-------|
| Factors | language (python, typescript), agent (claude-code, copilot) |
| Responses | code_quality, build_time |
| Task | bundled://rest-api-crud |
| Runner | docker (simulation mode) |
| Design | 2x2 full factorial, screening phase |
| Replicates | 5 per design point |

## Summary

| Metric | Value |
|--------|-------|
| Total runs | 28 |
| Completed | 21 |
| Failed | 7 |
| Completion rate | 75% |

## Main Effects: code_quality

| Factor | Level | Mean | N |
|--------|-------|------|---|
| agent | claude-code | 0.5050 | 10 |
| agent | copilot | 0.5455 | 11 |
| language | python | 0.6667 | 10 |
| language | typescript | 0.3985 | 11 |

## Main Effects: build_time

| Factor | Level | Mean | N |
|--------|-------|------|---|
| agent | claude-code | 1.0000 | 10 |
| agent | copilot | 1.0000 | 11 |
| language | python | 1.0000 | 10 |
| language | typescript | 1.0000 | 11 |

## ANOVA Results

### code_quality
```
R² = 0.9994  Adj R² = 0.9993

               sum_sq    df             F        PR(>F)
C(language)  0.368170   1.0  27460.393915  4.120e-30  ***
C(agent)     0.000011   1.0      0.834879  3.729e-01
Residual     0.000241  18.0

Significant factors (p < 0.10): language
```

### build_time
```
No significant factors (all completed runs scored 1.0 — zero variance)
```

## Aliasing Structure
```
Resolution: Full (2 factors, 4 runs)
All effects clear — no confounding
```

## Promotion Gate
```
Screening → Trial: PASS (p_value 0.0000 <= threshold 0.10)
Language is the dominant factor for code_quality
```

## Residual Diagnostics

| Check | code_quality | build_time |
|-------|-------------|------------|
| Shapiro-Wilk normality | FAIL (W=0.49) | FAIL (W=0.81) |
| Durbin-Watson autocorrelation | PASS (1.81) | FAIL (0.11) |
| Outliers (|z|>3) | 1 | 6 |

> **Note:** Residual failures are expected with simulated data —
> the simulation produces fixed scores per factor level with no
> random noise, violating ANOVA's normality assumption.

## Per-Run Results

| Run | Language | Agent | code_quality | build_time | Status |
|-----|----------|-------|-------------|------------|--------|
| 6 | python | copilot | 0.6667 | 1.0000 | completed |
| 7 | typescript | claude-code | 0.3833 | 1.0000 | completed |
| 8 | typescript | copilot | 0.4000 | 1.0000 | completed |
| 9 | python | claude-code | 0.6667 | 1.0000 | completed |
| 10 | python | claude-code | 0.6667 | 1.0000 | completed |
| 11 | python | claude-code | 0.6667 | 1.0000 | completed |
| 12 | python | claude-code | 0.6667 | 1.0000 | completed |
| 14 | python | copilot | 0.6667 | 1.0000 | completed |
| 15 | python | copilot | 0.6667 | 1.0000 | completed |
| 16 | python | copilot | 0.6667 | 1.0000 | completed |
| 17 | python | copilot | 0.6667 | 1.0000 | completed |
| 18 | python | copilot | 0.6667 | 1.0000 | completed |
| 19 | typescript | claude-code | 0.4000 | 1.0000 | completed |
| 20 | typescript | claude-code | 0.4000 | 1.0000 | completed |
| 21 | typescript | claude-code | 0.4000 | 1.0000 | completed |
| 22 | typescript | claude-code | 0.4000 | 1.0000 | completed |
| 23 | typescript | claude-code | 0.4000 | 1.0000 | completed |
| 24 | typescript | copilot | 0.4000 | 1.0000 | completed |
| 25 | typescript | copilot | 0.4000 | 1.0000 | completed |
| 27 | typescript | copilot | 0.4000 | 1.0000 | completed |
| 28 | typescript | copilot | 0.4000 | 1.0000 | completed |