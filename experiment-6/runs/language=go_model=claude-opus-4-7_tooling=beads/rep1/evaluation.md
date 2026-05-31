# Evaluation Report

Generated: 2026-05-30T17:44:38Z

## Summary

- **Language:** go
- **Status:** ok
- **Build:** pass (0.4s)
- **Tests:** 0 passed, 0 failed, 0 skipped
- **Lint:** pass (0 warnings)

## Build & Test

### Build
```
Command: go build ./...
Exit code: 0
```

### Tests
```
Command: go test ./...
Exit code: 0
Results: 0 passed, 0 failed, 0 skipped
ok  	bookapi	0.367s

```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code | 578 |
| Files | 4 |
| Dependencies | 0 |
| Tests effective | 0 |
| Skip ratio | 0.0% |

## Reproduce

```bash
cd /Users/adriancockcroft/Documents/GitHub/retort/experiment-6/runs/language=go_model=claude-opus-4-7_tooling=beads/rep1
npm install  # or equivalent for your language
npm run build
npm test
```