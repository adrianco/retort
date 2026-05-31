# Evaluation Report

Generated: 2026-05-30T21:27:53Z

## Summary

- **Language:** rust
- **Status:** ok
- **Build:** pass (0.4s)
- **Tests:** 7 passed, 0 failed, 0 skipped
- **Lint:** fail (2 warnings)

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
Results: 7 passed, 0 failed, 0 skipped

running 7 tests
.......
test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s


running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s


running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s


```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code | 450 |
| Files | 2 |
| Dependencies | 0 |
| Tests effective | 7 |
| Skip ratio | 0.0% |

## Reproduce

```bash
cd experiment-6/runs/language=rust_model=claude-opus-4-8_tooling=none/rep2
npm install  # or equivalent for your language
npm run build
npm test
```