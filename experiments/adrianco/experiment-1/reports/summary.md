# Experiment 1: Full Results

Generated: 2026-04-10 22:32

## Configuration

| Setting | Value |
|---------|-------|
| Task | rest-api-crud (CRUD book collection API) |
| Runner | local (Claude Code CLI on host) |
| Factors | language (python, typescript, go) x model (opus, sonnet) x tooling (none, beads) |
| Design | 3x2x2 full factorial (12 runs) |
| Replicates | 1 |
| Total cost | $11.00 (see per-run reports for token costs) |

## Results

| # | Language | Model | Tooling | Quality | Status |
|---|----------|-------|---------|---------|--------|
| 1 | python | opus | none | 0.79 | completed |
| 2 | python | opus | beads | 0.62 | completed |
| 3 | python | sonnet | none | 0.67 | completed |
| 4 | python | sonnet | beads | 0.62 | completed |
| 5 | typescript | opus | none | 0.73 | completed |
| 6 | typescript | opus | beads | 0.73 | completed |
| 7 | typescript | sonnet | none | 0.73 | completed |
| 8 | typescript | sonnet | beads | — | failed |
| 9 | go | opus | none | 0.89 | completed |
| 10 | go | opus | beads | 0.96 | completed |
| 11 | go | sonnet | none | 0.96 | completed |
| 12 | go | sonnet | beads | 1.00 | completed |

## Factor Means (code_quality)

| Factor | Level | Mean | N |
|--------|-------|------|---|
| language | go | 0.950 | 4 |
| language | python | 0.675 | 4 |
| language | typescript | 0.733 | 3 |
| model | opus | 0.787 | 6 |
| model | sonnet | 0.796 | 5 |
| tooling | beads | 0.787 | 5 |
| tooling | none | 0.794 | 6 |

## Key Observations

- **Go dominated** quality scores (0.89–1.00) across all model/tooling combinations
- **Go + sonnet + beads** achieved a perfect 1.00 quality score
- **Beads helped Go** (0.89→0.96 opus, 0.96→1.00 sonnet) but **hurt Python** (0.79→0.62 opus, 0.67→0.62 sonnet)
- **Sonnet used more tokens** than Opus, especially for TypeScript
- **TypeScript + sonnet + beads** was the only failure

> **Caveat:** Single runs, no replicates. Treat as directional only.

## Reports Index

- [Per-run reports](runs/) — individual JSON and markdown for each run
- [Analysis](analysis/) — factor means and ANOVA summary