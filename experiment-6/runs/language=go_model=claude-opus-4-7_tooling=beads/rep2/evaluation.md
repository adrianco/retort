# Evaluation Report

Generated: 2026-05-30T17:48:15Z

## Summary

- **Language:** go
- **Status:** ok
- **Build:** pass (0.5s)
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
ok  	books	0.365s

```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code | 524 |
| Files | 4 |
| Dependencies | 0 |
| Tests effective | 0 |
| Skip ratio | 0.0% |

## Reproduce

```bash
cd experiment-6/runs/language=go_model=claude-opus-4-7_tooling=beads/rep2
npm install  # or equivalent for your language
npm run build
npm test
```