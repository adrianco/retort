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

## Run the Go MCP server

Requires Go 1.23 or newer. No external packages, API keys, network access, or
external database are needed. All code is in the repository root.

```sh
go build -o soccer-mcp .
go test ./...
go test -race ./...
./soccer-mcp -data ./data/kaggle
```

The process reads one JSON-RPC message per line on stdin and writes only protocol
responses to stdout. Startup diagnostics go to stderr. EOF shuts it down.
It supports the stdio MCP initialization lifecycle for protocol versions
2024-11-05, 2025-03-26, 2025-06-18, and 2025-11-25. It advertises tools only.
The implementation follows the [MCP tool protocol](https://modelcontextprotocol.io/specification/2025-03-26/server/tools).

Example client configuration (replace both absolute paths):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/soccer-mcp",
      "args": ["-data", "/absolute/path/to/data/kaggle"]
    }
  }
}
```

A connected LLM translates natural-language questions into tool arguments and
formats the returned JSON text into answers. The server does not require an LLM
API key or use a brittle natural-language parser. Follow-up questions such as
“What was the score?” use the LLM client's conversation context.

A minimal stdin session:

```jsonl
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"demo","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team":"Flamengo","opponent":"Fluminense","season":2023}}}
```

## Tools and query examples

All filters are optional unless stated. Match filters include `team`, `opponent`,
`venue` (`home`, `away`, `either`), `competition`, `season`, inclusive ISO dates
`from`/`to`, exact `stage` or round, `source` filename, and `derbies`.
Results default to 50 rows; `limit` accepts 1–500 (0 also means 50), and `offset`
selects the next page. Aggregates and totals use all matching rows before pagination.
Dates sort newest first; players sort by overall rating descending.

| Tool | Purpose |
|---|---|
| `search_matches` | Fixtures, scores, dates, provenance, stadiums and original statistics; `sort: biggest_win` ranks goal margins |
| `search_players` | Name substring, nationality, club substring, position (including `forward`), `min_rating`; original FIFA attributes |
| `team_profile` | Required `team`; links to matches, competition appearances, record, and historical FIFA players |
| `head_to_head` | Required distinct `team` and `opponent`; both directions of fixture and results |
| `standings` | Required league `competition` and `season`; calculated points, wins, goals and win rate |
| `statistics` | Goal averages, home/away outcomes, ranked team records; `group_by: season` or `competition` |
| `competition_results` | Required `competition`; paginated fixtures and counts by stage/round |
| `data_info` | Source row counts, date coverage, conflicts, limitations and source priority |

For team rankings, `sort` can be `points` (default), `goals`, or `win_rate`.
`venue` selects the team's home/away record. Without a team filter, statistics
summaries still describe all selected fixtures; the team records use the requested
venue. Win-rate rankings have no minimum-match threshold, so inspect `played`.

These 24 questions are exercised in the integration tests:

| Question | Tool and arguments |
|---|---|
| Show Flamengo vs Fluminense | `search_matches {"team":"Flamengo","opponent":"Fluminense"}` |
| What did Palmeiras play in 2023? | `search_matches {"team":"Palmeiras","season":2023}` |
| Find Copa do Brasil finals | `search_matches {"competition":"Copa do Brasil","stage":"final"}` |
| Corinthians home record in 2022? | `team_profile {"team":"Corinthians","venue":"home","season":2022}` |
| Most goals in Serie A 2023? | `standings {"competition":"Serie A","season":2023,"sort":"goals"}` |
| Compare Palmeiras and Santos | `head_to_head {"team":"Palmeiras","opponent":"Santos"}` |
| Find Brazilian players | `search_players {"nationality":"Brazil"}` |
| Highest-rated Flamengo players? | `search_players {"club":"Flamengo"}` |
| São Paulo forwards? | `search_players {"club":"São Paulo FC","position":"forward"}` |
| Who led the 2019 Brasileirão? | `standings {"competition":"Brasileirão","season":2019}` |
| 2018 Libertadores bracket results? | `competition_results {"competition":"Libertadores","season":2018}` |
| Which teams were at the bottom in 2020? | `standings {"competition":"Brasileirão","season":2020}` |
| Average Brasileirão goals? | `statistics {"competition":"Brasileirão"}` |
| Best away record? | `statistics {"venue":"away","sort":"win_rate"}` |
| Biggest wins? | `search_matches {"sort":"biggest_win"}` |
| Last Flamengo–Corinthians score? | `search_matches {"team":"Flamengo","opponent":"Corinthians","limit":1}` |
| Find Gabriel | `search_players {"name":"Gabriel"}` |
| Flamengo players and match history? | `team_profile {"team":"Flamengo"}` |
| Derbies in 2023? | `search_matches {"season":2023,"derbies":true}` |
| Palmeiras competition appearances? | `team_profile {"team":"Palmeiras"}` |
| Best home record? | `statistics {"venue":"home","sort":"win_rate"}` |
| Top Brazilian players? | `search_players {"nationality":"Brazil","min_rating":85}` |
| Compare 2018 and 2019 | `statistics {"from":"2018-01-01","to":"2019-12-31","group_by":"season"}` |
| What data is available? | `data_info {}` |

## Data model and limitations

The in-memory graph uses normalized teams as shared entities. Match home/away
edges, competition and season fields, and player club edges allow traversal via
`team_profile`; stable FIFA IDs and match IDs identify returned records. Original
CSV fields retain display names, player attributes, and extended match statistics.
No external graph database is required at this dataset size.

- All six files are required. Startup rejects missing columns, invalid dates,
  malformed rows and invalid goal values with source context. Empty/NA/dash scores
  remain unknown (`null`) and do not contribute to played-match statistics. A
  fixture with an unknown date is retained, sorts last, and is excluded by date filters.
- Names are case/accent insensitive, including combining accents. State suffixes
  and curated full-name aliases are normalized. Ambiguous names such as América
  and Atlético retain state qualifiers; supply them to distinguish clubs. Aliases
  and traditional rival pairs are curated, not exhaustive.
- Série A/B matches merge by competition, season, home and away team because each
  directed pairing occurs once per league season. This also handles dates that
  differ due to time zones or rescheduling. Extended records without a season
  use a known fixture season when dates match within one day, so early-2021
  fixtures from the extended 2020 season are assigned correctly. Otherwise the
  calendar year is used. Other competitions merge only when
  date, competition and directed pairing agree, to preserve multiple cup legs.
  Date disagreements in those competitions can still leave duplicates.
- Source priority is Brasileirão, Copa do Brasil, Libertadores, extended statistics,
  historical Brasileirão, then FIFA. The first score/date wins; later sources fill
  missing fields. All source filenames are retained and score conflicts are listed
  by `data_info`. Source filters select merged records carrying that provenance,
  rather than reconstructing the original raw source row.
- Tables award 3 points for wins, then rank by wins, goal difference, goals scored,
  and team name. They do not apply disciplinary adjustments or official tiebreaks.
  Filtered or incomplete tables cannot certify champions or relegation. Série C
  may contain distinct groups and is explicitly labeled as such.
- Copa do Brasil's numeric rounds vary by year. The maximum round in each season
  of the dedicated cup file is labeled `final` as an inference. Libertadores
  stages are explicit. Exact stage filtering distinguishes finals from semifinals.
  Available fixtures can describe bracket results but cannot establish a full
  advancement graph or resolve penalty shootouts.
- Player records are a historical FIFA snapshot, not current or season-specific
  squads. Individual goalscorer events are absent, so top scorers cannot be inferred.
  A name missing from FIFA must produce an empty result, not an invented biography.
  In particular, this FIFA file has no Flamengo roster; its player query is empty.
  Cross-file player/match relationships are tested with Fluminense.
- Demo/non-commercial use; dataset attribution and licenses are listed above.

Tests include known-result fixtures, filters and aliases, error handling, MCP
handshakes and tool errors, all six real source counts, cross-file relationships,
24 question mappings, and a regression verifying the complete 2019 league table
has 20 clubs with 38 matches each (Flamengo 90, Santos 74, Palmeiras 74 points).
Integration tests check every sample query completes within two seconds locally.
