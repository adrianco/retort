# Architecture Summary

**Surface:** A dependency-free C++17 MCP (Model Context Protocol) server for Brazilian
soccer data. It loads six Kaggle CSV datasets (Brasileirão, Copa do Brasil, Libertadores,
BR-Football extended stats, a historical league file, and FIFA players) into memory,
normalizes team names/dates across files, de-duplicates matches, and exposes match, team,
player, competition, and statistical queries as JSON-RPC 2.0 tools over stdio.

See `modules.md` for the module map and `flow.md` for control flow.
