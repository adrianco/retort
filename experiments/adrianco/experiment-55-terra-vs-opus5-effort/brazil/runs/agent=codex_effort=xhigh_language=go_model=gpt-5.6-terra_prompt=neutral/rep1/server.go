package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"strconv"
	"strings"
)

const serverName = "brazilian-soccer-mcp"
const serverVersion = "1.0.0"

type Server struct{ data *DataStore }

func NewServer(data *DataStore) *Server { return &Server{data: data} }

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type toolCallParams struct {
	Name      string         `json:"name"`
	Arguments map[string]any `json:"arguments"`
}

// RunServer serves JSON-RPC messages over the MCP stdio transport. Each JSON
// object may be newline-delimited (the normal transport) or simply adjacent,
// making it convenient to exercise in tests too. Diagnostics never go to out.
func (s *Server) RunServer(in io.Reader, out io.Writer) error {
	return s.runDecoded(json.NewDecoder(in), out)
}

// runDecoded is split out to keep protocol handling independently testable.
func (s *Server) runDecoded(decoder *json.Decoder, out io.Writer) error {
	writer := bufio.NewWriter(out)
	defer writer.Flush()
	for {
		var request rpcRequest
		if err := decoder.Decode(&request); err != nil {
			if err == io.EOF {
				return nil
			}
			return err
		}
		response := s.HandleRequest(request)
		if response == nil {
			continue
		} // JSON-RPC notifications have no response.
		if err := json.NewEncoder(writer).Encode(response); err != nil {
			return err
		}
		if err := writer.Flush(); err != nil {
			return err
		}
	}
}

func (s *Server) HandleRequest(request rpcRequest) *rpcResponse {
	if request.JSONRPC != "" && request.JSONRPC != "2.0" {
		return rpcFailure(request.ID, -32600, "invalid JSON-RPC version")
	}
	if request.Method == "" {
		return rpcFailure(request.ID, -32600, "method is required")
	}
	var result any
	var err error
	switch request.Method {
	case "initialize":
		result = initializeResult(request.Params)
	case "ping":
		result = map[string]any{}
	case "tools/list":
		result = map[string]any{"tools": toolDefinitions()}
	case "tools/call":
		var call toolCallParams
		if err = json.Unmarshal(request.Params, &call); err == nil {
			if call.Arguments == nil {
				call.Arguments = map[string]any{}
			}
			result = s.callTool(call.Name, call.Arguments)
		}
	case "notifications/initialized", "notifications/cancelled", "$/progress":
		return nil
	default:
		return rpcFailure(request.ID, -32601, "method not found: "+request.Method)
	}
	if err != nil {
		return rpcFailure(request.ID, -32602, "invalid params: "+err.Error())
	}
	if len(request.ID) == 0 {
		return nil
	}
	return &rpcResponse{JSONRPC: "2.0", ID: request.ID, Result: result}
}

func rpcFailure(id json.RawMessage, code int, message string) *rpcResponse {
	if len(id) == 0 {
		return nil
	}
	return &rpcResponse{JSONRPC: "2.0", ID: id, Error: &rpcError{Code: code, Message: message}}
}

func initializeResult(params json.RawMessage) map[string]any {
	version := "2025-03-26"
	var supplied struct {
		ProtocolVersion string `json:"protocolVersion"`
	}
	if len(params) > 0 && json.Unmarshal(params, &supplied) == nil && supplied.ProtocolVersion != "" {
		version = supplied.ProtocolVersion
	}
	return map[string]any{
		"protocolVersion": version,
		"capabilities":    map[string]any{"tools": map[string]any{"listChanged": false}},
		"serverInfo":      map[string]string{"name": serverName, "version": serverVersion},
		"instructions":    "Use the soccer tools to search the bundled Brazilian football datasets. Match results retain a source CSV; aggregate tools deduplicate fixtures found in more than one source.",
	}
}

func (s *Server) callTool(name string, args map[string]any) map[string]any {
	var value any
	var err error
	switch name {
	case "search_matches":
		filter, parseErr := matchFilterFromArgs(args)
		if parseErr != nil {
			err = parseErr
		} else {
			value = s.data.SearchMatches(filter)
		}
	case "team_statistics":
		team := stringArg(args, "team")
		if team == "" {
			err = fmt.Errorf("team is required")
		} else {
			venue := stringArg(args, "venue")
			if venue != "" && venue != "all" && venue != "home" && venue != "away" {
				err = fmt.Errorf("venue must be all, home, or away")
			} else {
				value = s.data.TeamStatistics(team, intArg(args, "season"), stringArg(args, "competition"), venue)
			}
		}
	case "head_to_head":
		a, b := stringArg(args, "team_a"), stringArg(args, "team_b")
		if a == "" || b == "" {
			err = fmt.Errorf("team_a and team_b are required")
		} else {
			value = s.data.HeadToHead(a, b, stringArg(args, "competition"), intArg(args, "season"), intArg(args, "limit"))
		}
	case "search_players":
		value = s.data.SearchPlayers(stringArg(args, "name"), stringArg(args, "nationality"), stringArg(args, "club"), stringArg(args, "position"), intArg(args, "limit"))
	case "get_standings":
		competition := stringArg(args, "competition")
		season := intArg(args, "season")
		if competition == "" || season == 0 {
			err = fmt.Errorf("competition and season are required")
		} else {
			value = s.data.Standings(competition, season)
		}
	case "team_rankings":
		value, err = s.data.TeamRankings(stringArg(args, "competition"), intArg(args, "season"), stringArg(args, "metric"), intArg(args, "limit"))
	case "competition_statistics":
		value = s.data.CompetitionStatistics(stringArg(args, "competition"), intArg(args, "season"))
	case "biggest_wins":
		value = s.data.BiggestWins(stringArg(args, "competition"), intArg(args, "season"), intArg(args, "limit"))
	case "find_derbies":
		value = s.data.Derbies(intArg(args, "season"), stringArg(args, "competition"), intArg(args, "limit"))
	case "team_competitions":
		team := stringArg(args, "team")
		if team == "" {
			err = fmt.Errorf("team is required")
		} else {
			value = s.data.TeamCompetitions(team)
		}
	case "data_summary":
		value = s.dataSummary()
	default:
		err = fmt.Errorf("unknown tool %q", name)
	}
	if err != nil {
		return toolError(err)
	}
	encoded, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return toolError(err)
	}
	return map[string]any{"content": []map[string]string{{"type": "text", "text": string(encoded)}}, "structuredContent": value}
}

func (s *Server) dataSummary() map[string]any {
	bySource := map[string]int{}
	for _, m := range s.data.Matches {
		bySource[m.Source]++
	}
	return map[string]any{"match_count": len(s.data.Matches), "player_count": len(s.data.Players), "matches_by_source": bySource}
}

func toolError(err error) map[string]any {
	return map[string]any{"isError": true, "content": []map[string]string{{"type": "text", "text": err.Error()}}}
}

func matchFilterFromArgs(args map[string]any) (MatchFilter, error) {
	filter := MatchFilter{Team: stringArg(args, "team"), Opponent: stringArg(args, "opponent"), HomeTeam: stringArg(args, "home_team"), AwayTeam: stringArg(args, "away_team"), Competition: stringArg(args, "competition"), Season: intArg(args, "season"), Round: stringArg(args, "round"), Stage: stringArg(args, "stage"), Limit: intArg(args, "limit")}
	var err error
	if value := stringArg(args, "date_from"); value != "" {
		filter.DateFrom, err = parseDate(value)
		if err != nil {
			return filter, fmt.Errorf("date_from: %w", err)
		}
	}
	if value := stringArg(args, "date_to"); value != "" {
		filter.DateTo, err = parseDate(value)
		if err != nil {
			return filter, fmt.Errorf("date_to: %w", err)
		}
	}
	if !filter.DateFrom.IsZero() && !filter.DateTo.IsZero() && filter.DateFrom.After(filter.DateTo) {
		return filter, fmt.Errorf("date_from must be before date_to")
	}
	return filter, nil
}

func stringArg(args map[string]any, key string) string {
	value, ok := args[key]
	if !ok || value == nil {
		return ""
	}
	return strings.TrimSpace(fmt.Sprint(value))
}
func intArg(args map[string]any, key string) int {
	value := stringArg(args, key)
	if n, err := strconv.Atoi(value); err == nil {
		return n
	}
	if n, err := strconv.ParseFloat(value, 64); err == nil {
		return int(n)
	}
	return 0
}

type toolDefinition struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
}

func toolDefinitions() []toolDefinition {
	stringProp := func(description string) map[string]any {
		return map[string]any{"type": "string", "description": description}
	}
	intProp := func(description string) map[string]any {
		return map[string]any{"type": "integer", "description": description}
	}
	tool := func(name, description string, properties map[string]any, required ...string) toolDefinition {
		schema := map[string]any{"type": "object", "properties": properties, "additionalProperties": false}
		if len(required) > 0 {
			schema["required"] = required
		}
		return toolDefinition{Name: name, Description: description, InputSchema: schema}
	}
	matchProperties := map[string]any{"team": stringProp("Team appearing at home or away; name variants and accents are normalized."), "opponent": stringProp("Opposing team; with team this returns their head-to-head fixtures."), "home_team": stringProp("Home team only."), "away_team": stringProp("Away team only."), "competition": stringProp("Brasileirão, Copa do Brasil, Libertadores, Serie B, or another dataset competition."), "season": intProp("Four-digit season."), "date_from": stringProp("Inclusive ISO date (YYYY-MM-DD)."), "date_to": stringProp("Inclusive ISO date (YYYY-MM-DD)."), "round": stringProp("Exact round."), "stage": stringProp("Tournament stage substring."), "limit": intProp("Maximum records, default 50 and maximum 500.")}
	return []toolDefinition{
		tool("search_matches", "Find match results across every supplied CSV. Results are newest first and include source data.", matchProperties),
		tool("team_statistics", "Calculate a team's wins, draws, losses, points, and goals. Aggregate calculations deduplicate overlapping source fixtures.", map[string]any{"team": stringProp("Team name."), "season": intProp("Optional season."), "competition": stringProp("Optional competition."), "venue": map[string]any{"type": "string", "enum": []string{"all", "home", "away"}, "description": "Optional venue filter; all is the default."}}, "team"),
		tool("head_to_head", "Compare two teams' records and return their most recent meetings.", map[string]any{"team_a": stringProp("First team."), "team_b": stringProp("Second team."), "competition": stringProp("Optional competition."), "season": intProp("Optional season."), "limit": intProp("Maximum match details, default 10.")}, "team_a", "team_b"),
		tool("search_players", "Search FIFA players by name, nationality, club, or position, ordered by overall rating.", map[string]any{"name": stringProp("Player name substring."), "nationality": stringProp("Nationality substring, for example Brazilian."), "club": stringProp("Club substring."), "position": stringProp("Position substring."), "limit": intProp("Maximum players, default 50 and maximum 500.")}),
		tool("get_standings", "Calculate a competition table for a season from match results.", map[string]any{"competition": stringProp("Competition, e.g. Brasileirão."), "season": intProp("Season year.")}, "competition", "season"),
		tool("team_rankings", "Rank teams by points, goals scored, home win rate, or away win rate.", map[string]any{"competition": stringProp("Optional competition."), "season": intProp("Optional season."), "metric": map[string]any{"type": "string", "enum": []string{"points", "goals_for", "home_win_rate", "away_win_rate"}, "description": "Ranking metric; points is default."}, "limit": intProp("Maximum teams, default 50.")}),
		tool("competition_statistics", "Calculate goal averages and home/draw/away result rates.", map[string]any{"competition": stringProp("Optional competition."), "season": intProp("Optional season.")}),
		tool("biggest_wins", "Return the largest winning margins, optionally by competition and season.", map[string]any{"competition": stringProp("Optional competition."), "season": intProp("Optional season."), "limit": intProp("Maximum matches, default 10.")}),
		tool("find_derbies", "Find supported traditional Brazilian derby fixtures (Fla-Flu, Grenal, Derby Paulista, and others).", map[string]any{"season": intProp("Optional season."), "competition": stringProp("Optional competition."), "limit": intProp("Maximum matches, default 50.")}),
		tool("team_competitions", "List competitions in which a team appears in any supplied match dataset.", map[string]any{"team": stringProp("Team name.")}, "team"),
		tool("data_summary", "Report loaded player and match counts for every source file.", map[string]any{}),
	}
}
