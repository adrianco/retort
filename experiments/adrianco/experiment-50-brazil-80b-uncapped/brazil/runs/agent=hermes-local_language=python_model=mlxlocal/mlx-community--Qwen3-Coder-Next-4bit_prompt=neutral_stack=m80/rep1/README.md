# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server that provides a knowledge graph interface for Brazilian soccer data.

## Overview

This server enables natural language queries about players, teams, matches, and competitions using pre-downloaded Kaggle datasets.

## Features

- **Match Queries**: Search matches by team, date, competition, or season
- **Team Queries**: Get team statistics, win records, and head-to-head comparisons
- **Player Queries**: Search players by name, club, nationality, and position
- **Competition Queries**: Get standings and results for various competitions
- **Statistical Analysis**: Calculate averages, win rates, and big wins

## Data Sources

The server uses the following datasets from Kaggle:

1. **Brasileirão Serie A Matches** (4,180 matches)
2. **Copa do Brasil Matches** (1,337 matches)
3. **Copa Libertadores Matches** (1,255 matches)
4. **Extended Match Statistics** (10,296 matches)
5. **Historical Brasileirão (2003-2019)** (6,886 matches)
6. **FIFA Player Database** (18,207 players)

## Installation

```bash
cd /path/to/project
pip install -r requirements.txt
```

## Usage

### Start the Server

```bash
uvicorn src.api:app --reload
```

The server will be available at `http://localhost:8000`

### API Endpoints

- `GET /` - Root endpoint with API information
- `GET /health` - Health check
- `GET /api/matches` - Find matches
- `GET /api/matches/{id}` - Get match by ID
- `GET /api/teams/stats` - Get team statistics
- `GET /api/teams/comparison` - Get team comparison
- `GET /api/players/search` - Search players
- `GET /api/players/brazilian/top` - Get top Brazilian players
- `GET /api/competitions/standings` - Get competition standings
- `GET /api/stats/big-wins` - Get big wins
- `GET /api/stats/average-goals` - Get average goals
- `GET /api/stats/home-win-rate` - Get home win rate

### Example Queries

```bash
# Find Flamengo vs Fluminense matches
curl "http://localhost:8000/api/matches?team1=Flamengo&team2=Fluminense"

# Get Palmeiras statistics
curl "http://localhost:8000/api/teams/stats?team=Palmeiras&season=2012"

# Search for players
curl "http://localhost:8000/api/players/search?name=Neymar"

# Get competition standings
curl "http://localhost:8000/api/competitions/standings?competition=Brasileirão&season=2019"
```

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test class
pytest tests/test_api.py::TestQueryEngine
pytest tests/test_api.py::TestSampleQuestions
```

## Project Structure

```
src/
├── __init__.py          # Package initialization
├── models.py            # Data models
├── data_utils.py        # Data loading and query engine
├── api.py               # FastAPI endpoints
└── main.py              # Application entry point

tests/
├── conftest.py          # Test fixtures
└── test_api.py          # Test cases

data/
└── kaggle/              # CSV data files
    ├── Brasileirao_Matches.csv
    ├── Brazilian_Cup_Matches.csv
    ├── Libertadores_Matches.csv
    ├── BR-Football-Dataset.csv
    ├── novo_campeonato_brasileiro.csv
    └── fifa_data.csv
```

## Success Criteria

- [x] Can search and return match data from all provided CSV files
- [x] Can search and return player data
- [x] Can calculate basic statistics (wins, losses, goals)
- [x] Can compare teams head-to-head
- [x] Handles team name variations correctly
- [x] Returns properly formatted responses
- [x] Simple lookups respond quickly
- [x] All 6 CSV files are loadable and queryable
- [x] At least 20 sample questions can be answered
- [x] Cross-file queries work

## License

This project uses data from Kaggle datasets. Please refer to the individual dataset licenses for usage terms.
