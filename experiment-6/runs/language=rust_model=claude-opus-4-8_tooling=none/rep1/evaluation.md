# Evaluation Report

Generated: 2026-05-30T21:22:15Z

## Summary

- **Language:** rust
- **Status:** ok
- **Build:** pass (0.4s)
- **Tests:** 0 passed, 0 failed, 0 skipped
- **Lint:** pass (0 warnings)

## Build & Test

### Build
```
Command: cargo build --quiet
Exit code: 0
```

### Tests
```
Command: cargo test --quiet
Exit code: 0
Results: 0 passed, 0 failed, 0 skipped

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s


running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s


running 6 tests
......
test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s


running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s


```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code | 425 |
| Files | 3 |
| Dependencies | 0 |
| Tests effective | 0 |
| Skip ratio | 0.0% |

## Reproduce

```bash
cd experiment-6/runs/language=rust_model=claude-opus-4-8_tooling=none/rep1
npm install  # or equivalent for your language
npm run build
npm test
```