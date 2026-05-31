# Evaluation Report

Generated: 2026-05-30T17:21:18Z

## Summary

- **Language:** typescript
- **Status:** failed (build)
- **Build:** fail (0.6s)
- **Tests:** 1 passed, 0 failed, 0 skipped
- **Lint:** fail (0 warnings)

## Build & Test

### Build
```
Command: npm install --no-audit --no-fund && npm run build
Exit code: 1

up to date in 255ms

> book-collection-api@1.0.0 build
> tsc


node:internal/modules/cjs/loader:1423
  throw err;
  ^

Error: Cannot find module '../lib/tsc.js'
Require stack:
- /Users/adriancockcroft/Documents/GitHub/retort/experiment-6/runs/language=typescript_model=claude-opus-4-8_tooling=beads/rep2/node_modules/.bin/tsc
    at Module._resolveFilename (node:internal/modules/cjs/loader:1420:15)
    at defaultResolveImpl (node:internal/modules/cjs/loader:1058:19)
    at resolveForCJSWithHooks (node:internal/modules/cjs/loader:1063:22)
    at Module._load (node:internal/modules/cjs/loader:1226:37)
    at TracingChannel.traceSync (node:diagnostics_channel:328:14)
    at wrapModuleLoad (node:internal/modules/cjs/loader:244:24)
    at Module.require (node:internal/modules/cjs/loader:1503:12)
    at require (node:internal/modules/helpers:152:16)
    at Object.<anonymous> (/Users/adriancockcroft/Documents/GitHub/retort/experiment-6/runs/language=typescript_model=claude-opus-4-8_tooling=beads/rep2/node_modules/.bin/tsc:2:1)
    at Module._compile (node:
```

### Tests
```
Command: npm test --silent
Exit code: 0
Results: 1 passed, 0 failed, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code | 389 |
| Files | 6 |
| Dependencies | 12 |
| Tests effective | 1 |
| Skip ratio | 0.0% |

## Reproduce

```bash
cd experiment-6/runs/language=typescript_model=claude-opus-4-8_tooling=beads/rep2
npm install  # or equivalent for your language
npm run build
npm test
```