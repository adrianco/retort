package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"strings"
)

const (
	serverName    = "brazilian-soccer-mcp"
	serverVersion = "1.0.0"
)

type MCPServer struct {
	service *SoccerService
}

func NewMCPServer(store *Store) *MCPServer { return &MCPServer{service: NewSoccerService(store)} }

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
	Data    any    `json:"data,omitempty"`
}

type toolDefinition struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
}

type toolCallParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

// Serve implements the JSON-RPC stream transport expected by MCP stdio clients.
// It emits protocol responses only on stdout; callers can reserve stderr for logs.
func (s *MCPServer) Serve(input io.Reader, output io.Writer) error {
	scanner := bufio.NewScanner(input)
	scanner.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)
	encoder := json.NewEncoder(output)
	for scanner.Scan() {
		line := bytes.TrimSpace(scanner.Bytes())
		if len(line) == 0 {
			continue
		}
		var request rpcRequest
		if err := json.Unmarshal(line, &request); err != nil {
			if err := encoder.Encode(rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &rpcError{Code: -32700, Message: "parse error"}}); err != nil {
				return err
			}
			continue
		}
		if request.JSONRPC != "2.0" || strings.TrimSpace(request.Method) == "" {
			if !isNotification(request) {
				if err := encoder.Encode(rpcResponse{JSONRPC: "2.0", ID: request.ID, Error: &rpcError{Code: -32600, Message: "invalid request"}}); err != nil {
					return err
				}
			}
			continue
		}
		result, responseError := s.handle(request)
		if isNotification(request) {
			continue
		}
		response := rpcResponse{JSONRPC: "2.0", ID: request.ID, Result: result, Error: responseError}
		if err := encoder.Encode(response); err != nil {
			return err
		}
	}
	return scanner.Err()
}

func isNotification(request rpcRequest) bool { return len(request.ID) == 0 }

func (s *MCPServer) handle(request rpcRequest) (any, *rpcError) {
	switch request.Method {
	case "initialize":
		return s.initialize(request.Params), nil
	case "notifications/initialized":
		return map[string]any{}, nil
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		return map[string]any{"tools": toolDefinitions()}, nil
	case "tools/call":
		var params toolCallParams
		if err := json.Unmarshal(request.Params, &params); err != nil {
			return nil, &rpcError{Code: -32602, Message: "invalid tools/call parameters", Data: err.Error()}
		}
		if strings.TrimSpace(params.Name) == "" {
			return nil, &rpcError{Code: -32602, Message: "tool name is required"}
		}
		value, err := s.callTool(params.Name, params.Arguments)
		if err != nil {
			return errorToolResult(err), nil
		}
		return successToolResult(value), nil
	case "resources/list":
		return map[string]any{"resources": []map[string]any{
			{"uri": "soccer://datasets", "name": "Supplied datasets", "mimeType": "application/json", "description": "CSV source files and loaded row counts."},
			{"uri": "soccer://competitions", "name": "Available competitions", "mimeType": "application/json", "description": "Competitions, seasons, source files, and match-row counts."},
		}}, nil
	case "resources/read":
		return s.readResource(request.Params)
	default:
		return nil, &rpcError{Code: -32601, Message: "method not found", Data: request.Method}
	}
}

func (s *MCPServer) initialize(params json.RawMessage) map[string]any {
	protocol := "2024-11-05"
	var request struct {
		ProtocolVersion string `json:"protocolVersion"`
	}
	_ = json.Unmarshal(params, &request)
	if request.ProtocolVersion == "2025-06-18" {
		protocol = request.ProtocolVersion
	}
	return map[string]any{
		"protocolVersion": protocol,
		"capabilities": map[string]any{
			"tools":     map[string]any{"listChanged": false},
			"resources": map[string]any{},
		},
		"serverInfo": map[string]any{"name": serverName, "version": serverVersion},
	}
}

func (s *MCPServer) readResource(params json.RawMessage) (any, *rpcError) {
	var request struct {
		URI string `json:"uri"`
	}
	if err := json.Unmarshal(params, &request); err != nil || strings.TrimSpace(request.URI) == "" {
		return nil, &rpcError{Code: -32602, Message: "resource uri is required"}
	}
	var value any
	switch request.URI {
	case "soccer://datasets":
		value = map[string]any{"source_rows": s.service.Store.SourceRows, "matches": len(s.service.Store.Matches), "players": len(s.service.Store.Players)}
	case "soccer://competitions":
		value = s.service.Store.ListCompetitions()
	default:
		return nil, &rpcError{Code: -32002, Message: "resource not found", Data: request.URI}
	}
	encoded, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return nil, &rpcError{Code: -32603, Message: "could not serialize resource", Data: err.Error()}
	}
	return map[string]any{"contents": []map[string]any{{"uri": request.URI, "mimeType": "application/json", "text": string(encoded)}}}, nil
}

func (s *MCPServer) callTool(name string, arguments json.RawMessage) (any, error) {
	switch name {
	case "search_matches", "matches_search":
		var input matchSearchInput
		if err := decodeArguments(arguments, &input); err != nil {
			return nil, err
		}
		return s.service.Store.SearchMatches(input.MatchFilter())
	case "get_team_statistics", "team_stats":
		var input teamStatisticsInput
		if err := decodeArguments(arguments, &input); err != nil {
			return nil, err
		}
		return s.service.Store.TeamStatistics(TeamStatsQuery{Team: input.Team, Competition: input.Competition, Source: input.Source, Season: input.Season, Venue: input.Venue})
	case "compare_teams", "teams_compare":
		var input compareTeamsInput
		if err := decodeArguments(arguments, &input); err != nil {
			return nil, err
		}
		return s.service.Store.CompareTeams(input.TeamA, input.TeamB, input.Competition, input.Source, input.Season)
	case "search_players", "player_search":
		var input playerSearchInput
		if err := decodeArguments(arguments, &input); err != nil {
			return nil, err
		}
		return s.service.Store.SearchPlayers(PlayerFilter{Name: input.Name, Nationality: input.Nationality, Club: input.Club, Position: input.Position, PositionGroup: input.PositionGroup, MinOverall: input.MinOverall, MaxOverall: input.MaxOverall, Sort: input.Sort, Limit: input.Limit, Offset: input.Offset})
	case "get_competition_standings", "competition_standings":
		var input standingsInput
		if err := decodeArguments(arguments, &input); err != nil {
			return nil, err
		}
		return s.service.Store.Standings(input.Competition, input.Season, input.Source)
	case "analyze_statistics", "soccer_stats":
		var input statisticsInput
		if err := decodeArguments(arguments, &input); err != nil {
			return nil, err
		}
		return s.service.Store.Analyze(StatisticsQuery{Metric: input.Metric, Competition: input.Competition, Source: input.Source, Season: input.Season, Team: input.Team, Opponent: input.Opponent, Limit: input.Limit})
	case "list_competitions", "competitions_list":
		return s.service.Store.ListCompetitions(), nil
	case "list_derbies":
		var input derbiesInput
		if err := decodeArguments(arguments, &input); err != nil {
			return nil, err
		}
		matches, err := s.service.Store.Derbies(input.Season, input.Limit)
		return map[string]any{"matches": matches, "season": input.Season, "definition": "Traditional rivalries from the server's documented rivalry list."}, err
	case "ask_soccer_question", "answer_question":
		var input questionInput
		if err := decodeArguments(arguments, &input); err != nil {
			return nil, err
		}
		return s.service.Ask(input.Question)
	default:
		return nil, fmt.Errorf("unknown tool %q", name)
	}
}

func decodeArguments(raw json.RawMessage, output any) error {
	if len(raw) == 0 || string(raw) == "null" {
		raw = json.RawMessage("{}")
	}
	if err := json.Unmarshal(raw, output); err != nil {
		return fmt.Errorf("invalid tool arguments: %w", err)
	}
	return nil
}

func successToolResult(value any) map[string]any {
	encoded, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return errorToolResult(fmt.Errorf("serialize tool result: %w", err))
	}
	return map[string]any{
		"content":           []map[string]any{{"type": "text", "text": string(encoded)}},
		"structuredContent": value,
	}
}

func errorToolResult(err error) map[string]any {
	return map[string]any{
		"content": []map[string]any{{"type": "text", "text": err.Error()}},
		"isError": true,
	}
}

type matchSearchInput struct {
	Team        string         `json:"team"`
	Opponent    string         `json:"opponent"`
	Competition string         `json:"competition"`
	Source      string         `json:"source"`
	Venue       string         `json:"venue"`
	Season      int            `json:"season"`
	DateFrom    string         `json:"date_from"`
	DateTo      string         `json:"date_to"`
	Round       stringOrNumber `json:"round"`
	Stage       string         `json:"stage"`
	Limit       int            `json:"limit"`
	Offset      int            `json:"offset"`
}

func (m matchSearchInput) MatchFilter() MatchFilter {
	return MatchFilter{Team: m.Team, Opponent: m.Opponent, Competition: m.Competition, Source: m.Source, Venue: m.Venue, Season: m.Season, DateFrom: m.DateFrom, DateTo: m.DateTo, Round: string(m.Round), Stage: m.Stage, Limit: m.Limit, Offset: m.Offset}
}

type teamStatisticsInput struct {
	Team        string `json:"team"`
	Competition string `json:"competition"`
	Source      string `json:"source"`
	Venue       string `json:"venue"`
	Season      int    `json:"season"`
}
type compareTeamsInput struct {
	TeamA       string `json:"team_a"`
	TeamB       string `json:"team_b"`
	Competition string `json:"competition"`
	Source      string `json:"source"`
	Season      int    `json:"season"`
}
type playerSearchInput struct {
	Name          string `json:"name"`
	Nationality   string `json:"nationality"`
	Club          string `json:"club"`
	Position      string `json:"position"`
	PositionGroup string `json:"position_group"`
	MinOverall    int    `json:"min_overall"`
	MaxOverall    int    `json:"max_overall"`
	Sort          string `json:"sort"`
	Limit         int    `json:"limit"`
	Offset        int    `json:"offset"`
}
type standingsInput struct {
	Competition string `json:"competition"`
	Source      string `json:"source"`
	Season      int    `json:"season"`
}
type statisticsInput struct {
	Metric      string `json:"metric"`
	Competition string `json:"competition"`
	Source      string `json:"source"`
	Season      int    `json:"season"`
	Team        string `json:"team"`
	Opponent    string `json:"opponent"`
	Limit       int    `json:"limit"`
}
type derbiesInput struct {
	Season int `json:"season"`
	Limit  int `json:"limit"`
}
type questionInput struct {
	Question string `json:"question"`
}

type stringOrNumber string

func (s *stringOrNumber) UnmarshalJSON(data []byte) error {
	var stringValue string
	if err := json.Unmarshal(data, &stringValue); err == nil {
		*s = stringOrNumber(stringValue)
		return nil
	}
	var number json.Number
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	if err := decoder.Decode(&number); err != nil {
		return fmt.Errorf("must be a string or number")
	}
	*s = stringOrNumber(number.String())
	return nil
}

func toolDefinitions() []toolDefinition {
	return []toolDefinition{
		{Name: "search_matches", Description: "Find supplied match rows by team, opponent, venue, date range, competition, source, season, stage, or round. Names are accent- and state-suffix-normalized; source provenance is preserved.", InputSchema: objectSchema(map[string]any{
			"team": stringSchema("Team that played home, away, or either."), "opponent": stringSchema("Opponent when finding a head-to-head fixture."), "venue": enumSchema([]string{"home", "away", "either"}), "competition": stringSchema("Brasileirão, Copa do Brasil, Libertadores, Série B, or Série C."), "source": stringSchema("Optional source file or: brasileirao, cup, libertadores, extended, historical."), "season": integerSchema(), "date_from": stringSchema("Inclusive date: YYYY-MM-DD, timestamp, or DD/MM/YYYY."), "date_to": stringSchema("Inclusive date: YYYY-MM-DD, timestamp, or DD/MM/YYYY."), "round": map[string]any{"description": "Round number or label.", "anyOf": []any{map[string]any{"type": "string"}, map[string]any{"type": "integer"}}}, "stage": stringSchema("Stage substring such as group stage or final."), "limit": integerSchema(), "offset": integerSchema(),
		}, nil)},
		{Name: "get_team_statistics", Description: "Calculate a team's completed-match wins, draws, losses, goals, points, win rate, and scheduled rows from deduplicated data.", InputSchema: objectSchema(map[string]any{"team": stringSchema("Team name."), "competition": stringSchema("Optional competition."), "source": stringSchema("Optional source file."), "season": integerSchema(), "venue": enumSchema([]string{"home", "away", "either"})}, []string{"team"})},
		{Name: "compare_teams", Description: "Compare two teams' overall records and their order-independent head-to-head results.", InputSchema: objectSchema(map[string]any{"team_a": stringSchema("First team."), "team_b": stringSchema("Second team."), "competition": stringSchema("Optional competition."), "source": stringSchema("Optional source."), "season": integerSchema()}, []string{"team_a", "team_b"})},
		{Name: "search_players", Description: "Search the supplied FIFA snapshot by name, nationality, club, position, position group, and rating. Includes numeric skill attributes when supplied.", InputSchema: objectSchema(map[string]any{"name": stringSchema("Partial player name."), "nationality": stringSchema("Partial nationality."), "club": stringSchema("Partial club name."), "position": stringSchema("Position such as ST or LW."), "position_group": enumSchema([]string{"forwards", "midfielders", "defenders", "goalkeepers"}), "min_overall": integerSchema(), "max_overall": integerSchema(), "sort": enumSchema([]string{"overall_desc", "name_asc"}), "limit": integerSchema(), "offset": integerSchema()}, nil)},
		{Name: "get_competition_standings", Description: "Calculate a league table for a supplied Brasileirão Série A/B/C season. Cup and Libertadores standings are explicitly unsupported because the source format is not a league table.", InputSchema: objectSchema(map[string]any{"competition": stringSchema("League competition, usually Brasileirão."), "season": integerSchema(), "source": stringSchema("Optional source file.")}, []string{"competition", "season"})},
		{Name: "analyze_statistics", Description: "Calculate aggregate scoring, head-to-head, biggest wins, top-scoring teams, best home/away records, and derived relegation candidates. Metrics: summary, head_to_head, biggest_wins, top_scoring_teams, best_home_record, best_away_record, relegation_candidates.", InputSchema: objectSchema(map[string]any{"metric": stringSchema("Requested metric."), "competition": stringSchema("Optional competition."), "source": stringSchema("Optional source."), "season": integerSchema(), "team": stringSchema("Optional team."), "opponent": stringSchema("Opponent for head_to_head."), "limit": integerSchema()}, []string{"metric"})},
		{Name: "list_competitions", Description: "List queryable competitions, seasons, source files, and loaded match-row counts.", InputSchema: objectSchema(map[string]any{}, nil)},
		{Name: "list_derbies", Description: "Find traditional-rivalry fixtures using the server's documented rivalry list; derbies are not labelled by the source datasets.", InputSchema: objectSchema(map[string]any{"season": integerSchema(), "limit": integerSchema()}, nil)},
		{Name: "ask_soccer_question", Description: "Answer supported natural-language soccer questions deterministically, including last match, score follow-up, player lookup, derbies, team competitions, season comparisons, and common statistics.", InputSchema: objectSchema(map[string]any{"question": stringSchema("Natural-language question about the supplied data.")}, []string{"question"})},
	}
}

func objectSchema(properties map[string]any, required []string) map[string]any {
	result := map[string]any{"type": "object", "properties": properties, "additionalProperties": false}
	if len(required) > 0 {
		result["required"] = required
	}
	return result
}

func stringSchema(description string) map[string]any {
	return map[string]any{"type": "string", "description": description}
}
func integerSchema() map[string]any { return map[string]any{"type": "integer"} }
func enumSchema(values []string) map[string]any {
	options := make([]any, len(values))
	for i := range values {
		options[i] = values[i]
	}
	return map[string]any{"type": "string", "enum": options}
}
