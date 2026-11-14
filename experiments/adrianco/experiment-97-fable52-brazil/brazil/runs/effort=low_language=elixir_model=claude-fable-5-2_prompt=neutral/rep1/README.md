# Brazilian Soccer MCP with spec and basic data sets

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

## Implementation (Elixir)

An MCP server (stdio, newline-delimited JSON-RPC 2.0) written in Elixir with no
dependencies beyond the standard library (Elixir >= 1.18 for the built-in `JSON`).

```bash
mix test                 # 71 BDD-style tests, incl. 26 sample questions answered through MCP
mix escript.build        # builds ./brazilian_soccer_mcp
./brazilian_soccer_mcp   # serve MCP on stdio (optional arg: data directory)
```

MCP client configuration:

```json
{"mcpServers": {"brazilian-soccer": {"command": "/path/to/brazilian_soccer_mcp"}}}
```

The data directory is `$BRAZILIAN_SOCCER_DATA_DIR`, else `./data/kaggle`, else the
`data/kaggle` folder of the checkout the escript was built from.

### Tools

`search_matches`, `head_to_head`, `team_stats`, `team_profile`, `standings`,
`knockout_bracket`, `team_rankings`, `biggest_wins`, `competition_stats`, `derbies`,
`search_players`, `player_details`, `brazilian_clubs_players`, `list_teams`, `dataset_info`.

### Layout

| File | Role |
|------|------|
| `lib/brazilian_soccer/csv.ex`, `text.ex` | CSV parser; accent folding, date/number parsing |
| `lib/brazilian_soccer/team_names.ex` | Team-name normalisation, aliases, derby list |
| `lib/brazilian_soccer/data.ex` | Loads the 6 CSVs, builds the team registry, merges duplicate fixtures |
| `lib/brazilian_soccer/queries.ex` | Match/team/competition/player queries and statistics |
| `lib/brazilian_soccer/tools.ex`, `format.ex` | MCP tool catalogue and text rendering |
| `lib/brazilian_soccer/mcp/server.ex`, `cli.ex` | JSON-RPC server and escript entry point |

### How the data is handled

- **Team names**: state suffixes ("Palmeiras-SP", "Flamengo - RJ", "Botafogo RJ"), accents,
  club prefixes/suffixes ("EC Bahia", "São Paulo FC") and aliases ("Atlético Mineiro",
  "Athletico Paranaense", "Sport Club do Recife") reduce to one canonical team. Clubs that
  share a name are separated by state (Flamengo vs Flamengo-PI, Atlético-MG/GO, Athletico-PR).
- **Duplicates**: the same fixture appears in up to three files. Rows are merged into one
  match (keeping round, stadium, corners, shots from whichever file has them), so standings
  and statistics are not double counted: 23,852 played rows become 16,803 unique matches.
- **Unplayed fixtures** (`NA` / `-` scores) and a few invalid rows (a club against itself)
  are skipped. The state columns of `novo_campeonato_brasileiro.csv` are ignored because
  they are wrong for some clubs (Bahia = "BH", Vitória = "ES").
- **Seasons**: files without a season column use the match year; domestic matches played
  from January to 8 March 2021 belong to the COVID-delayed 2020 season.
- **Cup finals**: the Copa do Brasil files do not mark the final; it is taken as the last
  round of the cup file, or inferred as the last tie of the season (2021-2023).

### Known limits of the data

- Standings come from results only; court-imposed point deductions are not in the data.
  Série A 2023 lacks three matches, so no champion is marked for it.
- FIFA 19 licenses only 15 Brazilian clubs (not Flamengo, Corinthians, Palmeiras or
  São Paulo) and uses fictional names for their squads.
- Some lower-division cup sides are spelled differently across files and a few of their
  matches stay unmerged.
- There is no goalscorer data, so top scorers cannot be answered.
