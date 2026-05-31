# Evaluation Report

Generated: 2026-05-30T18:04:37Z

## Summary

- **Language:** go
- **Status:** ok
- **Build:** pass (0.9s)
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
ok  	bookapi	0.384s

```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code | 549 |
| Files | 5 |
| Dependencies | 0 |
| Tests effective | 0 |
| Skip ratio | 0.0% |

## Reproduce

```bash
cd /Users/adriancockcroft/Documents/GitHub/retort/experiment-6/runs/language=go_model=claude-opus-4-8_tooling=none/rep3
npm install  # or equivalent for your language
npm run build
npm test
```