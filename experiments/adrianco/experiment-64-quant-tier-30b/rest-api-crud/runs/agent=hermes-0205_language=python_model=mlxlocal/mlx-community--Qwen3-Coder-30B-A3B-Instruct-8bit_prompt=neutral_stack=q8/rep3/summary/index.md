# Summary: agent=hermes-0205 · python · Qwen3-Coder-30B-A3B-Instruct-8bit · prompt=neutral · stack=q8 · rep 3

- **Shape:** Single-file FastAPI REST API over raw `sqlite3`, with Pydantic v2 request/response models.
- **Structure:** 1 application module (`main.py`, 198 lines), 2 test files (`tests.py`, `basic_test.py`), 2 self-written source-grep "validator" scripts (`validate.py`, `final_validate.py`).
- **Interfaces:** 6 HTTP routes, 1 SQLite table, 3 exported Pydantic models. No CLI beyond `python main.py`.
- **Notable:** The dependency pins (`fastapi==0.104.1`, `pydantic==2.5.0`) are from late 2023 and cannot be installed on this environment's Python 3.14 — `pydantic-core==2.14.1` has no wheel and its Rust build fails — so `import fastapi` raises and `tests.py` is never collected. The two sibling replicates in the same cell chose Flask and scored `test_coverage` 0.91 / 0.94, so the failure follows this run's framework and pinning choice rather than the harness. This run is also the only one in the cell to leave behind substring-grep self-validators in place of executable verification.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
