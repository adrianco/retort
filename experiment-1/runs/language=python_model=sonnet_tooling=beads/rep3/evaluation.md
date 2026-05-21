# Evaluation Report

Generated: 2026-05-21T17:29:24Z

## Summary

- **Language:** python
- **Status:** failed (build)
- **Build:** fail (0.1s)
- **Tests:** 0 passed, 0 failed, 0 skipped
- **Lint:** fail (0 warnings)

## Build & Test

### Build
```
Command: python -m py_compile **/*.py
Exit code: 1
[Errno 2] No such file or directory: '**/*.py'
```

### Tests
```
Command: pytest -q
Exit code: 2
Results: 0 passed, 0 failed, 0 skipped

==================================== ERRORS ====================================
_ ERROR collecting experiment-1/runs/language=python_model=sonnet_tooling=beads/rep3/test_books.py _
/usr/local/python/3.12.1/lib/python3.12/site-packages/pytest_asyncio/plugin.py:667: in _patched_collect
    module = collector.obj
/usr/local/python/3.12.1/lib/python3.12/site-packages/_pytest/python.py:284: in obj
    self._obj = obj = self._getobj()
/usr/local/python/3.12.1/lib/python3.12/site-packages/_pytest/python.py:546: in _getobj
    return importtestmodule(self.path, self.config)
/usr/local/python/3.12.1/lib/python3.12/site-packages/_pytest/python.py:493: in importtestmodule
    mod = import_path(
/usr/local/python/3.12.1/lib/python3.12/site-packages/_pytest/pathlib.py:582: in import_path
    importlib.import_module(module_name)
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._boots
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code | 236 |
| Files | 5 |
| Dependencies | 0 |
| Tests effective | 0 |
| Skip ratio | 0.0% |

## Reproduce

```bash
cd experiment-1/runs/language=python_model=sonnet_tooling=beads/rep3
npm install  # or equivalent for your language
npm run build
npm test
```