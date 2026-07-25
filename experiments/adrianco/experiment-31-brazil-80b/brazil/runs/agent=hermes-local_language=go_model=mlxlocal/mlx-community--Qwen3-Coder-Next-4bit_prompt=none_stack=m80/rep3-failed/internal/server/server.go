// Package server provides the MCP server implementation for the Brazilian Soccer MCP Server
package server

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"brazilian-soccer-mcp/internal/data"
	"brazilian-soccer-mcp/internal/models"
	"brazilian-soccer-mcp/internal/query"
)

// MCPServer represents the MCP server
type MCPServer struct {
	queryServer *query.Server
	httpServer  *http.Server
}

// New creates a new MCP server
func New() (*MCPServer, error) {
	matchData, playerData, err := data.LoadAllData()
	if err != nil {
		return nil, fmt.Errorf("failed to load data: %w", err)
	}

	queryServer := query.New(matchData, playerData)

	return &MCPServer{
		queryServer: queryServer,
	}, nil
}

// Start starts the MCP server
func (s *MCPServer) Start(port string) error {
	http.HandleFunc("/query", s.handleQuery)
	http.HandleFunc("/health", s.handleHealth)
	http.HandleFunc("/capabilities", s.handleCapabilities)

	s.httpServer = &http.Server{
		Addr: fmt.Sprintf(":%s", port),
	}

	log.Printf("Starting MCP server on port %s", port)
	return s.httpServer.ListenAndServe()
}

// Stop stops the MCP server
func (s *MCPServer) Stop() error {
	if s.httpServer != nil {
		return s.httpServer.Shutdown(nil)
	}
	return nil
}

func (s *MCPServer) handleQuery(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req models.QueryRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, fmt.Sprintf("Invalid request body: %v", err), http.StatusBadRequest)
		return
	}

	resp := s.queryServer.Query(req)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func (s *MCPServer) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func (s *MCPServer) handleCapabilities(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	capabilities := map[string]interface{}{
		"capabilities": map[string]interface{}{
			"match": map[string]interface{}{
				"description": "Query match data",
				"parameters": map[string]interface{}{
					"home_team":  "string - Filter by home team",
					"away_team":  "string - Filter by away team",
					"team":       "string - Filter by either home or away team",
					"competition": "string - Filter by competition",
					"season":     "int - Filter by season year",
					"round":      "int - Filter by round number",
				},
			},
			"team": map[string]interface{}{
				"description": "Query team statistics",
				"parameters": map[string]interface{}{
					"team":        "string - Team name",
					"competition": "string - Filter by competition",
				},
			},
			"player": map[string]interface{}{
				"description": "Query player data",
				"parameters": map[string]interface{}{
					"name":       "string - Player name",
					"nationality": "string - Filter by nationality",
					"club":       "string - Filter by club",
					"position":   "string - Filter by position",
				},
			},
			"competition": map[string]interface{}{
				"description": "Query competition standings",
				"parameters": map[string]interface{}{
					"competition": "string - Competition name",
					"season":      "int - Season year",
				},
			},
			"statistics": map[string]interface{}{
				"description": "Query match statistics",
				"parameters": map[string]interface{}{
					"competition": "string - Filter by competition",
				},
			},
		},
	}
	json.NewEncoder(w).Encode(capabilities)
}

// RunSampleQueries runs sample queries for testing
func (s *MCPServer) RunSampleQueries() error {
	queries := []struct {
		name  string
		query models.QueryRequest
	}{
		{
			name: "Flamengo vs Fluminense",
			query: models.QueryRequest{
				Type: "match",
				Params: map[string]interface{}{
					"home_team": "Flamengo",
					"away_team": "Fluminense",
				},
			},
		},
		{
			name: "Palmeiras 2023",
			query: models.QueryRequest{
				Type: "match",
				Params: map[string]interface{}{
					"team":   "Palmeiras",
					"season": 2023,
				},
			},
		},
		{
			name: "Corinthians home record 2022",
			query: models.QueryRequest{
				Type: "team",
				Params: map[string]interface{}{
					"team":        "Corinthians",
					"competition": "Brasileirao",
					"season":      2022,
				},
			},
		},
		{
			name: "Brazilian players",
			query: models.QueryRequest{
				Type: "player",
				Params: map[string]interface{}{
					"nationality": "Brazil",
				},
			},
		},
		{
			name: "2019 Brasileirão standings",
			query: models.QueryRequest{
				Type: "competition",
				Params: map[string]interface{}{
					"competition": "Brasileirao",
					"season":      2019,
				},
			},
		},
		{
			name: "Brasileirão statistics",
			query: models.QueryRequest{
				Type: "statistics",
				Params: map[string]interface{}{
					"competition": "Brasileirao",
				},
			},
		},
		{
			name: "Big wins",
			query: models.QueryRequest{
				Type: "statistics",
				Params: map[string]interface{}{
					"min_goal_difference": 5,
				},
			},
		},
	}

	for _, q := range queries {
		resp := s.queryServer.Query(q.query)
		fmt.Printf("Query: %s\n", q.name)
		fmt.Printf("  Success: %v\n", resp.Success)
		fmt.Printf("  Total: %d\n", resp.Total)
		if resp.Error != "" {
			fmt.Printf("  Error: %s\n", resp.Error)
		}
		fmt.Println()
	}

	return nil
}
