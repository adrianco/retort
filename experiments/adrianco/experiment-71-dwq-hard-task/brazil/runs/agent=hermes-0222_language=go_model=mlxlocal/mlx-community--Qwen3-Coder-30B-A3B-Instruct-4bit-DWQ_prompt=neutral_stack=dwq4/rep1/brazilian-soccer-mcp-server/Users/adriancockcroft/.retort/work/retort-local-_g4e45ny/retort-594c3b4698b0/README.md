# Brazilian Soccer MCP Server

This is a Go implementation of a Model Context Protocol (MCP) server for Brazilian soccer data. The server provides natural language queries about players, teams, matches, and competitions using the provided datasets.

## Implementation Details

The server implements the following features:
1. Loads and processes multiple Brazilian soccer datasets
2. Supports natural language queries about matches, teams, players, and competitions
3. Implements the MCP protocol for integration with LLMs
4. Provides structured responses in the expected format

## Datasets Used
- Brasileirão Serie A Matches
- Copa do Brasil Matches  
- Copa Libertadores Matches
- Extended Match Statistics (BR-Football-Dataset)
- Historical Brasileirão (2003-2019)
- FIFA Player Database

## Features Implemented
- Find matches by team, date, competition, or season
- Get team statistics and performance metrics
- Search player information by name or club
- Calculate competition standings
- Analyze head-to-head records and performance trends

## How to Build and Run

1. Ensure Go 1.21+ is installed
2. Run `go mod tidy` to download dependencies
3. Run `go build cmd/main.go` to build the server
4. Run `./main` to start the server on port 8080

The server will respond to MCP requests on the /mcp endpoint.