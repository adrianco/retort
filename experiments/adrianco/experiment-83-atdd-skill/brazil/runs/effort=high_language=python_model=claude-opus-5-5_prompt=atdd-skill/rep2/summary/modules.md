# Modules

## Source package: `brazilian_soccer_mcp`

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer_mcp/__init__.py | Package marker (empty) | — |
| brazilian_soccer_mcp/__main__.py | `python -m` entry; delegates to server.main | `main()` |
| brazilian_soccer_mcp/server.py | MCP server; declares 18 tools wrapping the knowledge base, CLI arg parsing, stdio run loop | `build_server()`, `main()`, `INSTRUCTIONS` |
| brazilian_soccer_mcp/knowledge.py | Core query engine: loads/merges datasets, builds in-memory indexes, answers all match/team/competition/stat/player queries | `SoccerKnowledge`, `QueryError`, `Answer`, `Match`, `Record`, `RIVALRIES` |
| brazilian_soccer_mcp/datasets.py | Per-file CSV loaders for the six Kaggle datasets into `RawMatch`/`Player` records | `load_all()`, `RawMatch`, `Player`, `DatasetInfo`, `PRIORITY` |
| brazilian_soccer_mcp/competitions.py | Canonical competition names + knockout stage name resolution | `resolve()`, `stage_name()`, `SERIE_A`, `CUPS`, `KNOCKOUT_STAGES`, `UnknownCompetition` |
| brazilian_soccer_mcp/teams.py | Team-identity registry: parse inconsistent club names into stable keys, resolve question text, display names | `TeamRegistry`, `parse_name()`, `TeamNotFound`, `DISPLAY_NAMES` |
| brazilian_soccer_mcp/text.py | Shared text/date helpers (accent folding, multi-format date/int parsing) | `plain()`, `parse_date()`, `parse_int()`, `strip_accents()`, `has_accents()` |

## Tests (ATDD acceptance suite + unit tests)

| Path | Purpose | Entry points |
|------|---------|--------------|
| tests/acceptance/conftest.py | Pytest fixtures: isolated `soccer` DSL (private data+server) and shared read-only `provided` DSL | `soccer`, `provided` fixtures |
| tests/acceptance/dsl/__init__.py | `SoccerDsl` — single DSL entry point grouping given/matches/teams/competitions/stats/players | `SoccerDsl` |
| tests/acceptance/dsl/given.py | DSL layer 2: describe what datasets record, in football language with defaults | `Given` |
| tests/acceptance/dsl/queries.py | DSL layer 2: ask questions and confirm answers, split by domain | `Matches`, `Teams`, `Competitions`, `Statistics`, `Players` |
| tests/acceptance/drivers/datasets.py | Protocol driver: writes football facts into each dataset's native CSV format | `DatasetsDriver` |
| tests/acceptance/drivers/mcp_client.py | Minimal JSON-RPC-over-stdio MCP client (reader threads, poll-with-timeout) | `McpStdioClient`, `soccer_server_command()`, `soccer_server_environment()` |
| tests/acceptance/drivers/soccer_server.py | Protocol driver: turns DSL calls into MCP tools/call requests and asserts on results | `SoccerServerDriver`, `Answer` |
| tests/acceptance/test_finding_matches.py | Acceptance specs for match search / meetings | 12 test functions |
| tests/acceptance/test_team_records.py | Acceptance specs for team records | 4 test functions |
| tests/acceptance/test_team_names.py | Acceptance specs for team-name normalization | 7 test functions |
| tests/acceptance/test_competitions.py | Acceptance specs for tables, champions, relegation, brackets | 8 test functions |
| tests/acceptance/test_statistics.py | Acceptance specs for aggregate statistics | 7 test functions |
| tests/acceptance/test_players.py | Acceptance specs for player search/profiles | 7 test functions |
| tests/acceptance/test_provided_datasets.py | Acceptance specs against the real Kaggle data | 7 test functions |
| tests/unit/test_team_names.py | Unit tests for `teams.parse_name` / registry | 6 test functions |
| tests/unit/test_text_and_competitions.py | Unit tests for `text` and `competitions` helpers | 4 test functions |

Supporting files not listed: `pyproject.toml`, `requirements.txt`, `README.md`, `brazilian-soccer-mcp-guide.md`, `docs/atdd-findings.md`, `TASK.md`, and the six CSVs under `data/kaggle/`.
