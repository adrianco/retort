# Brazilian Soccer MCP Server

A dependency-free Go server exposing the six supplied Kaggle CSV datasets through nine read-only MCP tools. All Go source files live in this directory. It runs locally over stdio; no API keys, database, network service, or LLM dependency is required.

## Build and run

Requires Go 1.22 or newer.

```sh
go build -o soccer-mcp .
./soccer-mcp -data ./data/kaggle

go test ./...
go test -race ./...
go vet ./...
go test -bench=. -benchmem ./...
```

If the environment restricts the default Go cache, prefix commands with `GOCACHE=/tmp/soccer-go-cache`.

Configure an MCP host using absolute paths:

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

The connected LLM translates natural-language questions into tool calls, formats the returned data, and maintains conversational context (such as “What was the score?”). This server deliberately exposes structured queries rather than pretending a keyword parser understands arbitrary language.

The transport follows [MCP stdio](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports): one UTF-8 JSON-RPC message per line, protocol-only stdout, diagnostics on stderr. Supported negotiated versions are `2024-11-05`, `2025-03-26`, and `2025-06-18`; unsupported versions receive `2025-06-18`. Initialize, send `notifications/initialized`, then call tools. Example input:

```jsonl
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"demo","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team":"Flamengo","opponent":"Fluminense","limit":5}}}
```

## Tools

| Tool | Result |
| --- | --- |
| `search_matches` | Paginated fixtures with scores, dates, competition, round/stage, stadium, and original source rows |
| `team_stats` | Team record, goals, win rate, home/away split, competition history, seasonal trends |
| `head_to_head` | Both teams' records over matching fixtures, plus paginated results |
| `standings` | Calculated league table for a competition and season |
| `statistics` | Goal averages, outcome rates, team records, home/away records |
| `competition_results` | Season results and fixture IDs grouped by stage/round |
| `search_players` | FIFA player ratings and all original attributes, with club counts and average ratings |
| `team_graph` | Typed team → match/competition and player → team relationships, paginated edges with endpoint nodes |
| `dataset_info` | Source attribution, row counts, coverage by competition/season, limitations and conflict warnings |

Match tools accept `team`, `opponent`, `venue` (`home`, `away`, `either`), `competition`, `season`, inclusive `date_from`/`date_to`, exact `round`/`stage`, `source` CSV filename, and `derbies`. Match sorting supports `date_desc` (default), `date_asc`, and `biggest_wins` (absolute goal margin). Player filters are `name` (substring), `nationality`, normalized `club`, `position` (including `forward`), and `min_overall`. Players are ordered by overall descending.

Page using `limit` (default 50, maximum 500) and `offset`; follow `next_offset` until null. Aggregates always use all matching records, regardless of pagination. Dates without times and ISO timestamps are supported, as are Brazilian DD/MM/YYYY dates. Date-range comparisons use calendar dates, inclusive of both boundaries.

## Twenty example questions

These tool calls are exercised against the real data in `TestTwentySampleQuestions`. Responses can legitimately be empty where a player/club/season is absent.

| Question | Tool and arguments |
| --- | --- |
| Show Flamengo vs Fluminense matches. | `search_matches {"team":"Flamengo","opponent":"Fluminense"}` |
| What matches did Palmeiras play in 2023? | `search_matches {"team":"Palmeiras","season":2023}` |
| Find Copa do Brasil finals. | `search_matches {"competition":"Copa do Brasil","stage":"final"}` |
| When did Flamengo last play Corinthians, and what was the score? | `search_matches {"team":"Flamengo","opponent":"Corinthians","limit":1}` |
| What is Corinthians' home record in 2022? | `team_stats {"team":"Corinthians","season":2022,"venue":"home"}` |
| Compare Palmeiras and Santos head-to-head. | `head_to_head {"team":"Palmeiras","opponent":"Santos"}` |
| Who are the highest-rated Brazilian players? | `search_players {"nationality":"Brazil"}` |
| Who are the highest-rated players at Flamengo? | `search_players {"club":"Flamengo"}` |
| Find forwards at São Paulo FC. | `search_players {"club":"São Paulo FC","position":"forward"}` |
| Find players named Gabriel. | `search_players {"name":"Gabriel"}` |
| Who leads the calculated 2019 Brasileirão table? | `standings {"competition":"Brasileirão","season":2019}` |
| Show the 2018 Libertadores stages and results. | `competition_results {"competition":"Libertadores","season":2018}` |
| What is the average goals per Brasileirão match? | `statistics {"competition":"Brasileirão"}` |
| Which team scored the most goals in Serie A 2023? | `statistics {"competition":"Serie A","season":2023}`; compare `goals_for` |
| Show the biggest wins in the dataset. | `search_matches {"sort":"biggest_wins","limit":10}` |
| Show derbies in 2023. | `search_matches {"derbies":true,"season":2023}` |
| What competitions has Palmeiras played in? | `team_stats {"team":"Palmeiras"}` |
| Which team had the best home record in 2018? | `statistics {"competition":"Brasileirão","season":2018}`; compare `home_records` win rates and games played |
| Compare the 2018 and 2019 seasons. | Previous call plus `statistics {"competition":"Brasileirão","season":2019}` |
| Connect Flamengo matches, competitions and players. | `team_graph {"team":"Flamengo","limit":500}`; follow `next_offset` |

For “Who is Gabriel Barbosa?”, search the recorded name, then shorter name fragments if necessary; never substitute a different player when the FIFA snapshot omits the requested identity. For relegation or an official champion, the host should distinguish a calculated table from official status. Individual top scorers and definitive knockout advancement are unavailable in the provided data.

## Data model and quality

- The store is an in-memory graph of canonical teams, matches, competitions, and FIFA player entities. Team adjacency indexes support match lookup and club relationships. No graph database is needed at this data volume.
- Club names are case/accent insensitive. Explicit aliases cover full names and variants across the Brazilian league sources. State suffixes are stripped except for ambiguous clubs such as América, Atlético and Botafogo. Returned canonical team names are lowercase; original spellings remain in provenance. Aliases and traditional rivalries are curated and not exhaustive.
- Cross-file fixtures merge on competition, season, normalized home/away teams and dates within one day (to accommodate timezone differences). For Serie A/B, a home/opponent pair occurs once per season, so cross-source fixtures also merge when a postponed date differs by more than one day; date conflicts are reported. Same-source league duplicates also merge; all original rows remain in provenance. Same-source cup fixtures remain separate. Source precedence is Brasileirão, Cup, Libertadores, historical Brasileirão, then extended statistics. Matching dated primary fixtures supply seasons for the extended file, including 2020 fixtures played in 2021. The first scored source wins a conflict; all alternative records remain visible and `dataset_info` reports warnings. Unmatched or substantially rescheduled cup fixtures may still be distinct; inspect provenance before treating aggregates as official records.
- Missing paired scores are retained as unplayed fixtures and excluded from numerical result statistics. One undated/unscored Libertadores fixture is preserved with empty date and season zero, and excluded from date-bounded queries. Malformed CSV, missing required columns, invalid dates/numbers, and one-sided scores fail loading with source/row context.
- Copa do Brasil numeric stage inference requires the largest recorded round to contain exactly two reciprocal fixtures. This avoids labeling the last round of an incomplete season as the final. Earlier stages are inferred relative to that final. Extended-only matches lacking stages remain unlabeled. `competition_results` provides stage groups rather than inventing an advancement tree, penalties, or aggregate winners.
- League tables award 3 points per win and 1 per draw, sorted by points, wins, goal difference, goals scored and name. No disciplinary deductions, full official tiebreakers, automatic champion/relegation claims, or cross-group cup standings. Data coverage and source labels can be imperfect.
- Player attributes and club links describe the supplied historical FIFA snapshot, not live squads. All skill/physical fields are preserved as source strings. Player goal-scoring events are not present.

## Sources and attribution

Provided datasets are used for this demo/non-commercial project. Source metadata is also returned by `dataset_info`.

| Files | Rows | Source | License |
| --- | ---: | --- | --- |
| `Brasileirao_Matches.csv` | 4,180 | [Ricardo Mattos / Kaggle](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | 1,337 | Same as above | CC BY 4.0 |
| `Libertadores_Matches.csv` | 1,255 | Same as above | CC BY 4.0 |
| `BR-Football-Dataset.csv` | 10,296 | [cuecacuela / Kaggle](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 Public Domain |
| `novo_campeonato_brasileiro.csv` | 6,886 | [macedojleo / Kaggle](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | 18,207 | [youssefelbadry10 / Kaggle](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

Derived records normalize names/dates, combine provenance, and calculate statistics; original datasets are unchanged. License descriptions follow the supplied task metadata.
