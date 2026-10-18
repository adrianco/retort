# Summary: brazil · effort=low language=go model=claude-haiku-5-5 prompt=neutral · rep 3

- **Shape:** Go stdio MCP server (hand-rolled JSON-RPC 2.0) over an in-memory dataset loaded from six Kaggle CSVs; no third-party dependencies.
- **Structure:** 7 source modules + 6 test files (14 test functions total).
- **Interfaces:** 0 HTTP routes · 5 MCP protocol methods · 7 MCP tools (search_matches, team_record, head_to_head, standings, league_stats, biggest_wins, search_players).
- **Notable:** Substantial team-name normalization (accent map, noise-word stripping, UF state-suffix detection, token-subset matching) to reconcile differing club spellings across files; priority-ordered CSV loading with competition/season + fixture de-dup; standings/records computed on demand from matches. Plain-text tool output deliberately mirrors the spec's example answers.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
