# Evaluation Report

Generated: 2026-05-30T20:46:46Z

## Summary

- **Language:** typescript
- **Status:** ok
- **Build:** pass (0.9s)
- **Tests:** 0 passed, 0 failed, 0 skipped
- **Lint:** fail (0 warnings)

## Build & Test

### Build
```
Command: npm install --no-audit --no-fund && npm run build
Exit code: 0

added 26 packages in 251ms

> book-collection-api@1.0.0 build
> tsc


```

### Tests
```
Command: npm test --silent
Exit code: 0
Results: 0 passed, 0 failed, 0 skipped
(node:13848) ExperimentalWarning: SQLite is an experimental feature and might change at any time
(Use `node --trace-warnings ...` to show where the warning was created)
✔ GET /health returns ok (10.438792ms)
✔ POST /books creates a book and returns 201 (5.971917ms)
✔ POST /books rejects missing title and author with 400 (1.334333ms)
✔ GET /books lists books and supports ?author= filter (3.74425ms)
✔ GET /books/:id returns a single book or 404 (2.137667ms)
✔ PUT /books/:id updates an existing book (2.034291ms)
✔ DELETE /books/:id removes a book (2.369667ms)
ℹ tests 7
ℹ suites 0
ℹ pass 7
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 205.457667

```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code | 331 |
| Files | 4 |
| Dependencies | 7 |
| Tests effective | 0 |
| Skip ratio | 0.0% |

## Reproduce

```bash
cd experiment-6/runs/language=typescript_model=claude-opus-4-8_tooling=none/rep1
npm install  # or equivalent for your language
npm run build
npm test
```