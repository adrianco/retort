# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server for Brazilian soccer data queries.

## Overview

This server provides a REST API for querying Brazilian soccer data including:
- Match data from Brasileirão, Copa do Brasil, and Copa Libertadores
- Player data from FIFA database
- Team statistics and standings
- Head-to-head records
- Big wins and statistical analysis

## Data Sources

The server uses the following datasets from Kaggle:

| Dataset | Matches | Description |
|---------|---------|-------------|
| Brasileirão | 4,180 | Brasileirão Serie A matches |
| Copa do Brasil | 1,337 | Copa do Brasil matches |
| Copa Libertadores | 1,255 | Copa Libertadores matches |
| BR Football | 10,296 | Extended match statistics |
| Campeonato Brasileiro | 6,886 | Historical matches (2003-2019) |
| FIFA Players | 18,207 | Player database |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Start the Server

```bash
python server.py
# or
uvicorn server:app --host 0.0.0.0 --port 8000
```

### API Endpoints

#### GET `/`
Root endpoint with server information.

#### GET `/health`
Health check endpoint.

#### GET `/stats`
Get data statistics for all loaded datasets.

#### POST `/query`
Execute a query with the following actions:

| Action | Description | Parameters |
|--------|-------------|------------|
| `find_matches_between_teams` | Find matches between two teams | `team1`, `team2` |
| `get_team_statistics` | Get team statistics | `team`, `season`, `competition` |
| `get_player_by_name` | Find a player by name | `name` |
| `get_players_by_club` | Get players by club | `club` |
| `get_brazilian_players` | Get all Brazilian players | - |
| `get_competition_standings` | Get competition standings | `competition`, `season` |
| `get_big_wins` | Get biggest wins | `limit` |
| `get_head_to_head` | Get head-to-head record | `team1`, `team2` |
| `find_matches_by_team` | Find matches for a team | `team`, `limit` |
| `get_team_match_history` | Get team match history | `team`, `season` |

### Example Queries

```bash
# Find matches between Flamengo and Fluminense
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"action": "find_matches_between_teams", "params": {"team1": "Flamengo", "team2": "Fluminense"}}'

# Get Palmeiras statistics for 2012
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"action": "get_team_statistics", "params": {"team": "Palmeiras", "season": 2012}}'

# Find Brazilian players
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"action": "get_brazilian_players"}'

# Get Brasileirão 2012 standings
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"action": "get_competition_standings", "params": {"competition": "Brasileirão", "season": 2012}}'
```

## Tests

Run the test suite:

```bash
python test_soccer.py
# or
pytest test_soccer.py -v
```

The tests cover all major functionality:

- Match queries
- Team queries and statistics
- Player queries
- Competition standings
- Big wins
- Team name normalization
- Date parsing

## Project Structure

```
.
├── data/
│   └── kaggle/
│       ├── Brasileirao_Matches.csv
│       ├── Brazilian_Cup_Matches.csv
│       ├── Libertadores_Matches.csv
│       ├── BR-Football-Dataset.csv
│       ├── novo_campeonato_brasileiro.csv
│       └── fifa_data.csv
├── server.py           # FastAPI server
├── data_loader.py      # Data loading and management
├── query_engine.py     # Query logic
├── test_soccer.py      # Test suite
├── requirements.txt    # Dependencies
└── README.md           # This file
```

## License

All data sources are subject to their respective licenses (CC BY 4.0, CC0, Apache 2.0).
