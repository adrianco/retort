# Evaluation Report

Generated: 2026-05-21T17:30:02Z

## Summary

- **Language:** typescript
- **Status:** failed (tests)
- **Build:** pass (4.5s)
- **Tests:** 0 passed, 1 failed, 0 skipped
- **Lint:** fail (0 warnings)

## Build & Test

### Build
```
Command: npm install --no-audit --no-fund && npm run build
Exit code: 0

up to date in 2s

> books-api@1.0.0 build
> tsc


```

### Tests
```
Command: npm test --silent
Exit code: 1
Results: 0 passed, 1 failed, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code | 232 |
| Files | 5 |
| Dependencies | 12 |
| Tests effective | 1 |
| Skip ratio | 0.0% |

## Reproduce

```bash
cd experiment-1/runs/language=typescript_model=opus_tooling=beads/rep3
npm install  # or equivalent for your language
npm run build
npm test
```