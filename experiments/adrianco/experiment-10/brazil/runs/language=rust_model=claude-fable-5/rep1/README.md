# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server, written in Rust, that answers natural
language questions about Brazilian soccer: matches, teams, players,
competitions and statistics. See `TASK.md` for the full specification.

## Build, test, run

```sh
cargo build --release
cargo test                       # unit + BDD + 25 sample-question tests
./target/release/brazilian-soccer-mcp            # serves MCP over stdio
./target/release/brazilian-soccer-mcp --data-dir /path/to/data/kaggle
```

The data directory defaults to `data/kaggle` relative to the working
directory; override with `--data-dir` or the `BRAZILIAN_SOCCER_DATA`
environment variable. All six CSV files load at startup (~1s, ~18k unique
matches + 18k players); every query is served from memory, well inside the
2s/5s latency budgets in the spec.

### Connecting to an MCP client

Example entry for a client such as Claude Desktop / Claude Code
(`mcpServers` config):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/target/release/brazilian-soccer-mcp",
      "args": ["--data-dir", "/path/to/repo/data/kaggle"]
    }
  }
}
```

## Tools exposed

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "Find all Copa do Brasil finals" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_stats` | "What is Corinthians' home record in 2022?" |
| `league_standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Santos" |
| `player_info` | "Who is Casemiro?" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `list_competitions` | "What data do you have?" |

## Implementation notes

- **Team-name normalization** (`src/normalize.rs`): the datasets spell the
  same club many ways (`Palmeiras-SP` / `Palmeiras`, `São Paulo` /
  `Sao Paulo`, `Atlético - MG` / `Atletico Mineiro`, `C. R. B. - AL` /
  `CRB`, `Fortaleza EC` / `Fortaleza FC`). Every name is folded to a
  canonical key — accent folding, state/country suffix handling, club-type
  token stripping, and explicit aliases (including Atlético-PR → Athletico-PR
  after the 2019 rename). Ambiguous bases (Atlético, América, Botafogo, ...)
  keep their state in the key so distinct clubs never merge.
- **Cross-file deduplication** (`src/data.rs`): the Série A files overlap
  (2012-2019 appears in three files) and sometimes disagree on the exact date
  of a fixture, so fixtures are deduplicated by (competition, season, home,
  away) across files — in Brazilian leagues a pairing occurs once per season.
  Same-file repeats are kept (they are real second matches), and extended
  statistics (corners, shots) are merged into the surviving record.
  The 2022 Brasileirão file is a mid-season snapshot whose last 81 fixtures
  have `NA` scores; the extended dataset fills them, so calculated standings
  for 2003-2022 match the official tables (2023 is missing 3 matches in the
  source data).
- **Dates**: ISO (`2023-09-24`), Brazilian (`29/03/2003`) and datetime
  formats are all parsed; all text is handled as UTF-8.
- **MCP layer** (`src/mcp.rs`): JSON-RPC 2.0 over stdio, newline-delimited,
  protocol version `2024-11-05`; supports `initialize`, `tools/list`,
  `tools/call`, `ping`, and empty `resources/list`/`prompts/list`.
- **Tests**: `tests/bdd_tests.rs` implements the Gherkin scenarios from the
  spec as Given/When/Then tests against the real data (including the 2019
  table: Flamengo 90 pts, 28W 6D 4L); `tests/sample_questions.rs` answers 25
  sample questions end-to-end through the MCP tool dispatch.

## Specification
brazilian-soccer-mcp-guide.md

## Data Sources
Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv
- data/kaggle/Brazilian_Cup_Matches.csv
- data/kaggle/Libertadores_Matches.csv

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv
