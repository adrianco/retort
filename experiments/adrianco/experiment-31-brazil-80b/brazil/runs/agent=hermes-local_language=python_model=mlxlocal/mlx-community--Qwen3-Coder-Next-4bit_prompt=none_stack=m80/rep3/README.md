# Brazilian Soccer MCP Server

A Model Context Protocol (MCP) server for Brazilian soccer data queries.

## Overview

This server provides a REST API for querying Brazilian soccer data including:
- Match data from multiple competitions (Brasileirão, Copa do Brasil, Libertadores)
- Player data from FIFA database
- Team statistics and standings
- Statistical analysis

## Data Sources

The following datasets are used:
1. **Brasileirão Serie A Matches** (4,180 matches)
2. **Copa do Brasil Matches** (1,337 matches)
3. **Copa Libertadores Matches** (1,255 matches)
4. **Extended Match Statistics** (10,296 matches)
5. **Historical Brasileirão (2003-2019)** (6,886 matches)
6. **FIFA Player Database** (18,207 players)

## Installation

```bash
pip install fastapi uvicorn pandas
```

## Usage

### Start the Server

```bash
python3 server.py
```

The server will start on `http://localhost:8000`

### API Endpoints

#### GET `/`
Root endpoint - returns server information

#### POST `/matches`
Query matches by criteria

**Example Request:**
```json
{
  "team1": "Flamengo",
  "team2": "Fluminense",
  "season": 2023,
  "limit": 20
}
```

#### POST `/teams`
Get team information and statistics

**Example Request:**
```json
{
  "team": "Palmeiras",
  "season": 2023
}
```

#### POST `/players`
Query player information

**Example Request:**
```json
{
  "name": "Neymar",
  "nationality": "Brazil",
  "limit": 10
}
```

#### POST `/competitions`
Get competition standings and results

**Example Request:**
```json
{
  "competition": "Brasileirão",
  "season": 2019
}
```

#### POST `/stats`
Get statistical analysis

**Example Request:**
```json
{
  "metric": "average_goals",
  "competition": "Brasileirão",
  "season": 2023
}
```

## Sample Queries

### Find matches between two teams
```bash
curl -X POST http://localhost:8000/matches \
  -H "Content-Type: application/json" \
  -d '{"team1": "Flamengo", "team2": "Fluminense", "limit": 10}'
```

### Get team statistics
```bash
curl -X POST http://localhost:8000/teams \
  -H "Content-Type: application/json" \
  -d '{"team": "Palmeiras", "season": 2023}'
```

### Find Brazilian players
```bash
curl -X POST http://localhost:8000/players \
  -H "Content-Type: application/json" \
  -d '{"nationality": "Brazil", "limit": 10}'
```

### Get competition standings
```bash
curl -X POST http://localhost:8000/competitions \
  -H "Content-Type: application/json" \
  -d '{"competition": "Brasileirão", "season": 2019}'
```

### Statistical analysis
```bash
curl -X POST http://localhost:8000/stats \
  -H "Content-Type: application/json" \
  -d '{"metric": "biggest_wins", "competition": "Brasileirão"}'
```

## Test Suite

Run the BDD-style test suite:

```bash
python3 -m pytest test_server.py -v
```

## Features

- **Team Name Normalization**: Handles variations like "Flamengo", "Flamengo-RJ", etc.
- **Date Format Handling**: Supports ISO and Brazilian date formats
- **UTF-8 Support**: Properly handles Brazilian Portuguese characters
- **Performance**: Optimized queries with response times < 2 seconds for simple lookups

## Success Criteria

- ✅ All 6 CSV files are loadable and queryable
- ✅ Match queries work across all competitions
- ✅ Team statistics are calculated correctly
- ✅ Player queries work with filtering
- ✅ Competition standings are calculated
- ✅ Statistical analysis functions work
- ✅ All 32 tests pass
- ✅ Query performance within requirements

## License

Data sources are licensed under their respective licenses (CC BY 4.0, Apache 2.0, CC0).
