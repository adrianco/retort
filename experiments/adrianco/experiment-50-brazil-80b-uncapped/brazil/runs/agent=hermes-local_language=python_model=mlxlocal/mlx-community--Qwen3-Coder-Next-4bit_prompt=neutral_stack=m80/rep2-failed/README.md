# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server that provides a knowledge graph interface for Brazilian soccer data. This server enables natural language queries about players, teams, matches, and competitions using pre-downloaded Kaggle datasets.

## Features

- **Match Queries**: Search matches by team, date range, competition, or season
- **Team Queries**: Get team statistics, home/away records, and head-to-head comparisons
- **Player Queries**: Search players by name, nationality, club, or position
- **Competition Queries**: Get standings, champions, and cup brackets
- **Statistical Analysis**: Calculate goals per match, win rates, biggest victories, and performance trends

## Data Sources

The server uses the following datasets from Kaggle:

1. **Brasileirão Serie A** (4,180 matches) - https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
2. **Copa do Brasil** (1,337 matches)
3. **Copa Libertadores** (1,255 matches)
4. **Extended Match Statistics** (10,296 matches) - https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
5. **Historical Brasileirão (2003-2019)** (6,886 matches)
6. **FIFA Player Database** (18,207 players)

## Installation

```bash
# Clone or copy the files to your project directory
cd /path/to/project

# Install dependencies (if not already installed)
pip install pandas
```

## Usage

### As a Python Library

```python
from brazilian_soccer_mcp.server import BrazilianSoccerMCP

# Initialize the server
server = BrazilianSoccerMCP()

# Query matches
result = server.handle_request('match.find', {
    'team1': 'Flamengo',
    'team2': 'Fluminense',
    'limit': 10
})

# Get team statistics
result = server.handle_request('team.get_statistics', {
    'team': 'Palmeiras',
    'season': 2022
})

# Search players
result = server.handle_request('player.search', {
    'name': 'Neymar',
    'limit': 5
})
```

### Available Methods

| Method | Description |
|--------|-------------|
| `match.find` | Find matches by criteria |
| `match.get_by_teams` | Get matches between two teams |
| `team.get_statistics` | Get comprehensive team statistics |
| `team.get_home_record` | Get team home record |
| `team.get_away_record` | Get team away record |
| `team.get_head_to_head` | Get head-to-head between two teams |
| `team.get_competitions` | Get competitions for a team |
| `player.search` | Search players by name/nationality/club |
| `player.get_brazilian_top_rated` | Get top rated Brazilian players |
| `player.get_by_club` | Get players by club |
| `competition.get_standings` | Get competition standings |
| `competition.get_champion` | Get champion of a competition |
| `competition.get_cup_bracket` | Get cup bracket for knockout competitions |
| `stats.get_average_goals` | Get average goals per match |
| `stats.get_biggest_victories` | Get biggest victories |
| `stats.get_home_win_rate` | Get home win rate |
| `stats.get_team_trend` | Get team performance trend |
| `stats.get_head_to_head_stats` | Get detailed head-to-head statistics |
| `stats.get_competition_summary` | Get competition or season summary |

### Server Methods

The server provides these methods for MCP integration:

```python
server.handle_request(method_name, params_dict)
```

## Tests

Run the test suite:

```bash
python3 -m pytest tests/test_brazilian_soccer_mcp.py -v
```

## Requirements

- Python 3.8+
- pandas
- pytest (for testing)

## Success Criteria

- ✅ Can search and return match data from all provided CSV files
- ✅ Can search and return player data
- ✅ Can calculate basic statistics (wins, losses, goals)
- ✅ Can compare teams head-to-head
- ✅ Handles team name variations correctly
- ✅ Returns properly formatted responses
- ✅ All 6 CSV files are loadable and queryable
- ✅ All tests pass (41 tests)

## Data Quality Notes

- Team names are normalized for consistent matching (e.g., "Palmeiras-SP" → "Palmeiras")
- Date formats are handled (ISO and Brazilian formats)
- UTF-8 encoding is supported for Brazilian Portuguese characters

## License

This implementation uses data from Kaggle under their respective licenses (CC BY 4.0, Apache 2.0, CC0).
