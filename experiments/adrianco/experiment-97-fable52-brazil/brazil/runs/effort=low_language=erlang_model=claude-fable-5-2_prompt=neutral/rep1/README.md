# Brazilian Soccer MCP Server (Erlang)

An MCP (Model Context Protocol) server, written in Erlang/OTP with no external
dependencies, that answers questions about Brazilian soccer from the Kaggle
datasets in `data/kaggle/`: matches (Brasileirão, Série B/C, Copa do Brasil,
Libertadores, 2003-2023) and the FIFA player database. The specification is in
`TASK.md` / `brazilian-soccer-mcp-guide.md`.

## Build, test, run

Requires Erlang/OTP 27+ (uses the built-in `json` module) and `rebar3`.

```bash
rebar3 compile       # build
rebar3 eunit         # run the test suite (uses the real CSV files)
rebar3 escriptize    # build the server executable: _build/default/bin/brsoccer_mcp
```

The server speaks JSON-RPC 2.0 over stdio (one message per line). Run it from
the repository root, or point `BRSOCCER_DATA_DIR` at the directory holding the
six CSV files:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"limit":3}}}' \
  | ./_build/default/bin/brsoccer_mcp
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/repo/_build/default/bin/brsoccer_mcp",
      "env": { "BRSOCCER_DATA_DIR": "/path/to/repo/data/kaggle" }
    }
  }
}
```

## Tools

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "What matches did Palmeiras play in 2023?", "Find all Copa do Brasil finals" (team, opponent, venue, competition, season, date range, round, stage, source) |
| `head_to_head` | "Show me all Flamengo vs Fluminense matches", "When did Flamengo last play Corinthians?" |
| `team_stats` | "What is Corinthians' home record in 2022?" (W/D/L, goals, win rate, home/away split, per competition, corners/shots) |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `competition_bracket` | "Show the 2018 Copa Libertadores bracket" (stages, final, champion on aggregate) |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `team_rankings` | "Which team has the best away record?", "Which team scored the most goals in Serie A 2023?" |
| `team_competitions` | "What competitions has Palmeiras played in?" |
| `derbies` | "Show me all derbies in 2023" |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Santos", "Who are the highest-rated players at Grêmio?" |
| `player_details` | "Who is Neymar?" (profile, attributes, plus the club's recent matches when the club is in the match data) |
| `brazilian_clubs_players` | "Brazilian players at Brazilian clubs" (squad size / average rating per club) |
| `dataset_summary` | What is loaded: record counts, competitions, season ranges |

All tools return plain text in the answer formats shown in the specification;
invalid input (unknown team, bad date, wrong type) is returned as a tool error
(`isError: true`) with an explanatory message.

## Layout

| File | Purpose |
|------|---------|
| `src/brsoccer_csv.erl` | Streaming CSV parser (quotes, CRLF, BOM, UTF-8) |
| `src/brsoccer_norm.erl` | Accent folding, team-name canonicalisation, date parsing |
| `src/brsoccer_data.erl` | Loads the 6 CSV files into memory (`persistent_term`), de-duplicates matches |
| `src/brsoccer_query.erl` | Query layer: matches, records, standings, rankings, players |
| `src/brsoccer_tools.erl` | MCP tool schemas and text rendering |
| `src/brsoccer_mcp.erl` | JSON-RPC / MCP stdio server (escript entry point) |
| `test/brsoccer_tests.erl` | EUnit suite written as Given/When/Then scenarios |

## How the data is handled

- **Team names** are reduced to a canonical key: accents and case are ignored,
  state/country suffixes (`Palmeiras-SP`, `Palmeiras - SP`, `Nacional (URU)`)
  are split off, common affixes (`FC`, `EC`) are dropped and known aliases are
  mapped (`Atlético Mineiro` = `Atlético-MG`, `Sport Club Corinthians Paulista`
  = `Corinthians`, `Athletico Paranaense` = `Atletico-PR`). Namesakes from
  different states stay distinct (`Botafogo-RJ` vs `Botafogo-PB`,
  `Atlético-MG` vs `Atlético-GO`).
- **Dates**: `2023-09-24`, `2012-05-19 18:30:00` and `29/03/2003` are accepted,
  in the files and in tool arguments.
- **Duplicates**: the three Serie A sources and two Copa do Brasil sources
  overlap. A record is flagged as a duplicate when competition, home and away
  team match an already loaded record within two days (sources disagree on
  time zones). Queries use the 16.8k unique matches by default; pass `source`
  to `search_matches` to query one file's records as-is.
- **Seasons** in `BR-Football-Dataset.csv` are derived from the date; matches
  up to early March 2021 belong to the pandemic-delayed 2020 season.
- **Copa do Brasil stages**: that file only has round numbers, so the last
  rounds of each completed season are labelled final / semifinals / etc.

## Known limitations of the data

- Standings are computed purely from results (3 points per win; ties broken by
  wins, goal difference, goals for). Point deductions are not in the data.
- "Champion"/"Relegated" labels are only shown for complete seasons. The 2023
  Serie A data stops a few matches short, and 2016 contains one stray record
  from the source file, so those tables are slightly off.
- There is no goal-scorer data, so top scorers are reported per team only.
- Cup ties level on aggregate are reported as such: penalty shoot-outs are not
  recorded.
- The FIFA file (FIFA 19) does not license Flamengo, Palmeiras, Corinthians or
  São Paulo, so those clubs have no players in it, and several Brazilian
  clubs' squads carry generic player names.
- A few minor clubs still appear under two spellings (e.g. `Campinense` /
  `Campinense Clube`).

## Data sources

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro (CC BY 4.0):
  `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches (CC0): `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 (CC BY 4.0): `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data (Apache 2.0): `fifa_data.csv`
