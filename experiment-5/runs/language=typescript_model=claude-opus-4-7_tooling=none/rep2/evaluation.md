# Evaluation Report

Generated: 2026-05-30T10:15:40Z

## Summary

- **Language:** typescript
- **Status:** failed (build)
- **Build:** fail (0.5s)
- **Tests:** 0 passed, 0 failed, 2 skipped
- **Lint:** fail (0 warnings)

## Requirements

| ID | Requirement | Status | Evidence |
|----|----|----|----|
| R1 | Neymar Jr - Overall: 92, Position: LW, Club: Paris | ? cannot-verify | Build failed: node:internal/modules/cjs/ |
| R2 | Alisson - Overall: 89, Position: GK, Club: Liverpo | ? cannot-verify | Build failed: node:internal/modules/cjs/ |
| R3 | Casemiro - Overall: 89, Position: CDM, Club: Real  | ? cannot-verify | Build failed: node:internal/modules/cjs/ |
| R4 | Flamengo - 90 pts (28W, 6D, 4L) - Champion | ? cannot-verify | Build failed: node:internal/modules/cjs/ |
| R5 | Santos - 74 pts (22W, 8D, 8L) | ? cannot-verify | Build failed: node:internal/modules/cjs/ |
| R6 | Palmeiras - 74 pts (21W, 11D, 6L) | ? cannot-verify | Build failed: node:internal/modules/cjs/ |
| R7 | 2012-05-27: Santos 8-0 Bolivar (Libertadores) | ? cannot-verify | Build failed: node:internal/modules/cjs/ |
| R8 | 2015-09-13: Palmeiras 6-0 São Paulo | ? cannot-verify | Build failed: node:internal/modules/cjs/ |
| R9 | 2019-10-27: Flamengo 5-0 Grêmio | ? cannot-verify | Build failed: node:internal/modules/cjs/ |

## Build & Test

### Build
```
Command: npm install --no-audit --no-fund && npm run build
Exit code: 1

added 47 packages in 220ms

> brazilian-soccer-mcp@1.0.0 build
> tsc


node:internal/modules/cjs/loader:1423
  throw err;
  ^

Error: Cannot find module '../lib/tsc.js'
Require stack:
- /Users/adriancockcroft/Documents/GitHub/retort/experiment-5/runs/language=typescript_model=claude-opus-4-7_tooling=none/rep2/node_modules/.bin/tsc
    at Module._resolveFilename (node:internal/modules/cjs/loader:1420:15)
    at defaultResolveImpl (node:internal/modules/cjs/loader:1058:19)
    at resolveForCJSWithHooks (node:internal/modules/cjs/loader:1063:22)
    at Module._load (node:internal/modules/cjs/loader:1226:37)
    at TracingChannel.traceSync (node:diagnostics_channel:328:14)
    at wrapModuleLoad (node:internal/modules/cjs/loader:244:24)
    at Module.require (node:internal/modules/cjs/loader:1503:12)
    at require (node:internal/modules/helpers:152:16)
    at Object.<anonymous> (/Users/adriancockcroft/Documents/GitHub/retort/experiment-5/runs/language=typescript_model=claude-opus-4-7_tooling=none/rep2/node_modules/.bin/tsc:2:1)
    at Module._compile (node:in
```

### Tests
```
Command: npm test --silent
Exit code: 1
Results: 0 passed, 0 failed, 2 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code | 1584 |
| Files | 15 |
| Dependencies | 5 |
| Tests effective | 0 |
| Skip ratio | 200.0% |

## Reproduce

```bash
cd experiment-5/runs/language=typescript_model=claude-opus-4-7_tooling=none/rep2
npm install  # or equivalent for your language
npm run build
npm test
```