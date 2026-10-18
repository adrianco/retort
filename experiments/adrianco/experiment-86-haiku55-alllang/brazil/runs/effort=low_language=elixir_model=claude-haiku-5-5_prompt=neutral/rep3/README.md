# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## What this is

An MCP server (Elixir, stdio transport) that answers questions about Brazilian
soccer from the six CSV files in `data/kaggle/`. The LLM client chooses a tool
and its arguments. The server runs the query and returns formatted text.

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team, opponent, competition, season, venue or date range |
| `team_record` | W/D/L, goals and win rate for one team |
| `head_to_head` | Record between two teams and their recent meetings |
| `standings` | League table for a season, calculated from results |
| `league_stats` | Goals per match, home/draw/away rates |
| `biggest_wins` | Largest winning margins |
| `team_rankings` | Teams ranked by win rate, wins or goals scored |
| `search_players` | FIFA players by name, nationality, club, position, rating |
| `club_summary` | Brazilian players grouped by clubs in the match data |
| `team_overview` | Cross-file view: a team's match record and FIFA squad |

## Running

```sh
mix deps.get
mix test                    # 80 tests: BDD-style unit tests plus checks on the real CSVs
mix escript.build           # produces ./brazilian_soccer_mcp
SOCCER_DATA_DIR=$PWD/data/kaggle ./brazilian_soccer_mcp   # speaks MCP over stdin/stdout
```

Example client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brazilian_soccer_mcp",
      "env": { "SOCCER_DATA_DIR": "/absolute/path/to/data/kaggle" }
    }
  }
}
```

Startup takes about 2 seconds while the CSVs load. Each query runs in
milliseconds against the in-memory data.

### Layout

- `lib/brazilian_soccer_mcp/csv.ex`: RFC 4180 parser (quotes, CRLF, BOM)
- `team_name.ex`: club name normalization (state suffixes, accents, aliases)
- `competition.ex`: competition keys and friendly-name aliases
- `data_loader.ex`: merges the five match files and loads the FIFA players
- `queries.ex`: pure query functions
- `tools.ex`: MCP tool schemas, argument parsing and text formatting
- `server.ex`, `stdio.ex`, `cli.ex`: JSON-RPC handling and the stdio loop

## Design notes

- **Team identity.** Names are normalized to a key (accents, case, punctuation
  and aliases removed). Where a state is known, the key is qualified as
  `base|STATE`, so Atlético-MG and Athletico-PR stay separate. A bare name takes
  the state only if its base has exactly one state in the data.
- **Duplicates.** The Brasileirão files overlap, and the cup files overlap with
  BR-Football. Copies are matched on (competition, season, base names) and
  merged, keeping the n-th occurrence within each file.

## Known limitations

- Clubs that share a base name and appear with no state (for example the
  Libertadores or BR-Football rows for Botafogo or Atlético) can still stay
  unqualified, so their records are split.
- Some clubs keep two spellings across files, for example "4 de Julho" and
  "4 de Julho EC". Those matches can appear twice. The alias list in
  `team_name.ex` is short, and new cases are easy to add.
- The FIFA file is mostly European clubs and national-team players, so a
  club such as Flamengo may have no squad in it.
- The data has no goal-level records, so top-scorer queries are not supported.
- Natural-language understanding is left to the LLM client. The server does
  not parse free text.

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
