# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `server.js` | Express app: SQLite connection + schema bootstrap, all six route handlers, catch-all 404 and error middleware. Exports the app; listens only when run directly. | `app` (module.exports), `db` |
| `test.js` | Jest + supertest integration tests against the exported app. | 8 `describe` blocks, 14 `it` cases |
| `package.json` | Dependency + script manifest (`start`, `dev`, `test`, `test:watch`). | — |
| `README.md` | Setup, run, endpoint and database documentation. | — |
| `SUMMARY.md`, `FINAL_SUMMARY.md` | Agent-authored self-reports left in the workspace (not requested by the spec). | — |

Skipped as generated/non-source: `package-lock.json`, `node_modules/` (absent), `_hermes_session.jsonl`, `_agent_*.log`, `_judge/`, `_meta.json`, `_effective_stack.json`, `scores.json`, `.hermes_usage.json`.
