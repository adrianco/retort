# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `main.py` | FastAPI application: Pydantic models, SQLite schema init, all six HTTP route handlers | `app`, `Book`, `BookCreate`, `BookUpdate`, `init_db()`, `startup_event()`, `health_check()`, `create_book()`, `get_books()`, `get_book()`, `update_book()`, `delete_book()` |
| `tests.py` | pytest integration suite driving `main.app` through `fastapi.testclient.TestClient` | 10 test functions (`test_health_check` … `test_filter_books_by_author`) |
| `basic_test.py` | Import-and-model smoke checks; each function wraps its body in `try/except` and returns a bool | 3 test functions (`test_database_setup`, `test_book_operations`, `test_main_logic`) |
| `validate.py` | Self-written "validator" that regex-greps source files for required substrings | `check_file_content()`, `check_main_file()` |
| `final_validate.py` | Second self-written substring-grep validator over the same files | `check_main_file()` |
| `requirements.txt` | Pinned dependencies: `fastapi==0.104.1`, `uvicorn==0.24.0`, `pydantic==2.5.0` | — |
| `README.md` | Setup, run, endpoint and test instructions | — |
| `FINAL_SUMMARY.md` | Agent-authored completion report | — |

Excluded: `.coverage`, `__pycache__/`, and retort harness files (`_meta.json`, `_hermes_session.jsonl`, `_judge/`, `scores.json`, `stack.json`, `TASK.md`, `_agent_*.log`, `_effective_stack.json`, `.hermes_usage.json`, `.idiomatic_cache.json`).
