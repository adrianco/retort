# Evaluation Report

Generated: 2026-05-30T15:59:33Z

## Summary

- **Language:** python
- **Status:** failed (build)
- **Build:** fail (0.0s)
- **Tests:** 0 passed, 0 failed, 0 skipped
- **Lint:** fail (0 warnings)

## Build & Test

### Build
```
Command: python -m py_compile **/*.py
Exit code: 127
/bin/sh: python: command not found

```

### Tests
```
Command: pytest -q
Exit code: 0
Results: 0 passed, 0 failed, 0 skipped
.......                                                                  [100%]

```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code | 312 |
| Files | 2 |
| Dependencies | 2 |
| Tests effective | 0 |
| Skip ratio | 0.0% |

## Reproduce

```bash
cd experiment-6/runs/language=python_model=claude-opus-4-7_tooling=beads/rep2
npm install  # or equivalent for your language
npm run build
npm test
```