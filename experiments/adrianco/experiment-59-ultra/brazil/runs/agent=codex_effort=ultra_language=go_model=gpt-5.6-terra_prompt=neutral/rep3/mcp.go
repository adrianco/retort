package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"strings"
	"time"
)

const (
	serverName    = "brazilian-soccer-mcp"
	serverVersion = "1.0.0"
)

// MCPServer implements the newline-delimited JSON-RPC transport required for
// local MCP stdio servers. It has no network dependency and keeps stdout pure
// protocol output so it can be safely launched by any MCP-capable client.
type MCPServer struct {
	store *DataStore
}

type sessionState uint8

const (
	sessionNew sessionState = iota
	sessionAwaitingInitializedNotification
	sessionOperational
)

func NewMCPServer(store *DataStore) *MCPServer {
	return &MCPServer{store: store}
}

type jsonRPCRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

type jsonRPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type jsonRPCResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *jsonRPCError   `json:"error,omitempty"`
}

type textContent struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type toolResult struct {
	Content           []textContent `json:"content"`
	StructuredContent any           `json:"structuredContent,omitempty"`
	IsError           bool          `json:"isError,omitempty"`
}

// Serve handles one MCP stdio session. The client closes stdin to terminate the
// server, which is the normal MCP stdio shutdown signal.
func (server *MCPServer) Serve(input io.Reader, output io.Writer) error {
	scanner := bufio.NewScanner(input)
	scanner.Buffer(make([]byte, 64*1024), 16*1024*1024)
	encoder := json.NewEncoder(output)
	state := sessionNew
	for scanner.Scan() {
		line := bytes.TrimSpace(scanner.Bytes())
		if len(line) == 0 {
			continue
		}
		var request jsonRPCRequest
		if err := json.Unmarshal(line, &request); err != nil {
			code, message := -32700, "parse error"
			if json.Valid(line) {
				code, message = -32600, "invalid request"
			}
			if err := encoder.Encode(jsonRPCResponse{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &jsonRPCError{Code: code, Message: message}}); err != nil {
				return err
			}
			continue
		}
		if request.JSONRPC != "2.0" || strings.TrimSpace(request.Method) == "" || !validRequestID(request.ID) {
			id := responseID(request.ID)
			if !validRequestID(request.ID) {
				id = json.RawMessage("null")
			}
			if err := encoder.Encode(jsonRPCResponse{JSONRPC: "2.0", ID: id, Error: &jsonRPCError{Code: -32600, Message: "invalid request"}}); err != nil {
				return err
			}
			continue
		}
		if methodRequiresRequestID(request.Method) && !hasResponseID(request.ID) {
			// A request method sent as a notification is invalid for this server;
			// ignore it rather than executing a state-changing or expensive call
			// without a channel on which to return its result.
			continue
		}
		if !validMethodParams(request.Method, request.Params) {
			if hasResponseID(request.ID) {
				if err := encoder.Encode(jsonRPCResponse{JSONRPC: "2.0", ID: responseID(request.ID), Error: &jsonRPCError{Code: -32602, Message: "invalid parameters"}}); err != nil {
					return err
				}
			}
			continue
		}
		if request.Method == "notifications/initialized" {
			if hasResponseID(request.ID) || state != sessionAwaitingInitializedNotification {
				if hasResponseID(request.ID) {
					if err := encoder.Encode(jsonRPCResponse{JSONRPC: "2.0", ID: responseID(request.ID), Error: &jsonRPCError{Code: -32600, Message: "invalid initialization notification"}}); err != nil {
						return err
					}
				}
				continue
			}
			state = sessionOperational
			continue
		}
		if request.Method == "initialize" && state != sessionNew {
			if err := encoder.Encode(jsonRPCResponse{JSONRPC: "2.0", ID: responseID(request.ID), Error: &jsonRPCError{Code: -32600, Message: "initialize may only be called once"}}); err != nil {
				return err
			}
			continue
		}
		if (request.Method == "tools/list" || request.Method == "tools/call" || request.Method == "ping") && state != sessionOperational {
			if err := encoder.Encode(jsonRPCResponse{JSONRPC: "2.0", ID: responseID(request.ID), Error: &jsonRPCError{Code: -32002, Message: "server is not initialized"}}); err != nil {
				return err
			}
			continue
		}

		result, rpcError := server.handle(request)
		if !hasResponseID(request.ID) {
			continue
		}
		response := jsonRPCResponse{JSONRPC: "2.0", ID: responseID(request.ID)}
		if rpcError != nil {
			response.Error = rpcError
		} else {
			response.Result = result
			if request.Method == "initialize" {
				state = sessionAwaitingInitializedNotification
			}
		}
		if err := encoder.Encode(response); err != nil {
			return err
		}
	}
	return scanner.Err()
}

func methodRequiresRequestID(method string) bool {
	return method == "initialize" || method == "ping" || method == "tools/list" || method == "tools/call"
}

func validMethodParams(method string, raw json.RawMessage) bool {
	if method == "initialize" {
		return isJSONObject(raw)
	}
	if method == "tools/list" || method == "ping" || method == "notifications/initialized" || method == "notifications/cancelled" {
		return len(raw) == 0 || string(raw) == "null" || isJSONObject(raw)
	}
	if method == "tools/call" {
		return isJSONObject(raw)
	}
	return true
}

func isJSONObject(raw json.RawMessage) bool {
	return len(bytes.TrimSpace(raw)) > 0 && bytes.TrimSpace(raw)[0] == '{'
}

func hasResponseID(id json.RawMessage) bool {
	return len(id) > 0
}

func validRequestID(id json.RawMessage) bool {
	if len(id) == 0 {
		return true
	}
	decoder := json.NewDecoder(bytes.NewReader(id))
	decoder.UseNumber()
	var value any
	if err := decoder.Decode(&value); err != nil {
		return false
	}
	switch value.(type) {
	case string:
		return true
	case json.Number:
		_, err := value.(json.Number).Int64()
		return err == nil
	default:
		return false
	}
}

func responseID(id json.RawMessage) json.RawMessage {
	if len(id) == 0 {
		return json.RawMessage("null")
	}
	return id
}

func (server *MCPServer) handle(request jsonRPCRequest) (any, *jsonRPCError) {
	switch request.Method {
	case "initialize":
		return server.initialize(request.Params)
	case "notifications/initialized", "notifications/cancelled":
		return map[string]any{}, nil
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		return map[string]any{"tools": toolDefinitions()}, nil
	case "tools/call":
		return server.handleToolCall(request.Params)
	default:
		return nil, &jsonRPCError{Code: -32601, Message: "method not found"}
	}
}

func (server *MCPServer) initialize(raw json.RawMessage) (any, *jsonRPCError) {
	var params struct {
		ProtocolVersion string          `json:"protocolVersion"`
		Capabilities    json.RawMessage `json:"capabilities"`
		ClientInfo      struct {
			Name    string `json:"name"`
			Version string `json:"version"`
		} `json:"clientInfo"`
	}
	if err := json.Unmarshal(raw, &params); err != nil {
		return nil, &jsonRPCError{Code: -32602, Message: "invalid initialize parameters"}
	}
	if params.ProtocolVersion == "" || len(params.Capabilities) == 0 || !isJSONObject(params.Capabilities) || params.ClientInfo.Name == "" || params.ClientInfo.Version == "" {
		return nil, &jsonRPCError{Code: -32602, Message: "initialize requires protocolVersion, capabilities, and clientInfo"}
	}
	protocolVersion, ok := negotiatedProtocolVersion(params.ProtocolVersion)
	if !ok {
		return nil, &jsonRPCError{Code: -32602, Message: "unsupported MCP protocol version"}
	}
	return map[string]any{
		"protocolVersion": protocolVersion,
		"capabilities": map[string]any{
			"tools": map[string]any{"listChanged": false},
		},
		"serverInfo": map[string]any{
			"name":    serverName,
			"version": serverVersion,
		},
		"instructions": "Query Brazilian soccer matches, teams, competitions, and FIFA players with the provided read-only tools. Match results include source provenance; calculated statistics select a canonical source by default to avoid overlap double counting.",
	}, nil
}

func negotiatedProtocolVersion(clientVersion string) (string, bool) {
	switch clientVersion {
	case "2024-11-05", "2025-06-18", "2025-11-25":
		return clientVersion, true
	default:
		return "", false
	}
}

func toolDefinitions() []map[string]any {
	return []map[string]any{
		toolDefinition("dataset_summary", "Show the supplied datasets and the number of loaded match and player records.", objectSchema(map[string]any{})),
		toolDefinition("search_matches", "Find fixtures by team, opponent, date range, competition, season, round, stage, or source. Results retain source provenance.", matchFilterSchema()),
		toolDefinition("team_statistics", "Calculate a team's wins, draws, losses, goals, and home/away record. Incomplete fixtures are reported but excluded from calculations.", withProperties(matchFilterSchema(), map[string]any{
			"team":  stringSchema("Team name; matching ignores accents, case, and punctuation, and respects a supplied state suffix."),
			"venue": enumSchema("Restrict the record to all matches, home matches, or away matches.", "all", "home", "away"),
		}, "team")),
		toolDefinition("team_profile", "Follow a team across match results and the FIFA club snapshot, returning recent fixtures, calculated statistics, competitions, and matching players.", withProperties(matchFilterSchema(), map[string]any{
			"team":         stringSchema("Team name; matching ignores accents, case, and punctuation, and respects a supplied state suffix."),
			"player_limit": integerSchema("Maximum FIFA players to return, up to 500."),
		}, "team")),
		toolDefinition("head_to_head", "Compare two teams head-to-head and return the matching fixtures plus win/draw totals.", withProperties(matchFilterSchema(), map[string]any{
			"team_a": stringSchema("First team name."),
			"team_b": stringSchema("Second team name."),
		}, "team_a", "team_b")),
		toolDefinition("search_players", "Search the FIFA player data by name, nationality, club, position, or minimum overall rating.", objectSchema(map[string]any{
			"name":        stringSchema("Full or partial player name."),
			"nationality": stringSchema("Full or partial nationality."),
			"club":        stringSchema("Full or partial club name."),
			"position":    stringSchema("Full or partial playing position."),
			"min_overall": integerSchema("Minimum FIFA overall rating."),
			"limit":       integerSchema("Maximum number of players to return, up to 500."),
		})),
		toolDefinition("competition_standings", "Calculate season standings from completed match results using points, wins, goal difference, goals scored, then alphabetical order as tie-breakers.", objectSchema(map[string]any{
			"competition":         stringSchema("Competition, for example Brasileirão, Copa do Brasil, or Copa Libertadores."),
			"season":              integerSchema("Four-digit season year."),
			"source":              stringSchema("Optional source file or source alias. Defaults to the canonical source for the competition-season."),
			"include_all_sources": booleanSchema("Use every overlapping source instead of the default source policy."),
		}, "competition", "season")),
		toolDefinition("competition_statistics", "Calculate goals per match, home and away win rates, and the largest victories for a competition or season.", matchFilterSchema()),
		toolDefinition("team_rankings", "Rank teams by goals scored, best home record, or best away record for the selected match set.", withProperties(matchFilterSchema(), map[string]any{
			"metric": enumSchema("Ranking metric.", "goals_scored", "best_home_record", "best_away_record"),
		}, "metric")),
		toolDefinition("soccer_query", "Answer common natural-language soccer questions deterministically. For nuanced requests, prefer the focused structured tools above.", objectSchema(map[string]any{
			"query": stringSchema("A natural-language question about the supplied Brazilian soccer data."),
			"limit": integerSchema("Maximum number of returned records, up to 500."),
		}, "query")),
	}
}

func toolDefinition(name, description string, schema map[string]any) map[string]any {
	return map[string]any{
		"name":        name,
		"description": description,
		"inputSchema": schema,
		"annotations": map[string]any{
			"readOnlyHint":    true,
			"destructiveHint": false,
			"idempotentHint":  true,
			"openWorldHint":   false,
		},
	}
}

func objectSchema(properties map[string]any, required ...string) map[string]any {
	schema := map[string]any{
		"type":       "object",
		"properties": properties,
	}
	if len(required) > 0 {
		schema["required"] = required
	}
	return schema
}

func withProperties(schema map[string]any, extra map[string]any, required ...string) map[string]any {
	properties := make(map[string]any)
	if existing, ok := schema["properties"].(map[string]any); ok {
		for key, value := range existing {
			properties[key] = value
		}
	}
	for key, value := range extra {
		properties[key] = value
	}
	schema["properties"] = properties
	if len(required) > 0 {
		schema["required"] = required
	}
	return schema
}

func matchFilterSchema() map[string]any {
	return objectSchema(map[string]any{
		"team":                stringSchema("Team playing home or away."),
		"opponent":            stringSchema("Optional opposing team."),
		"home_team":           stringSchema("Require this home team."),
		"away_team":           stringSchema("Require this away team."),
		"competition":         stringSchema("Competition name, such as Brasileirão, Copa do Brasil, or Copa Libertadores."),
		"source":              stringSchema("Optional source filename or alias such as historical or extended."),
		"season":              integerSchema("Season year."),
		"round":               stringSchema("Full or partial round name or number."),
		"stage":               stringSchema("Full or partial tournament stage."),
		"date_from":           stringSchema("Inclusive start date in YYYY-MM-DD format."),
		"date_to":             stringSchema("Inclusive end date in YYYY-MM-DD format."),
		"include_all_sources": booleanSchema("Include overlapping source records instead of the default source policy."),
		"limit":               integerSchema("Maximum returned records, up to 500."),
	})
}

func stringSchema(description string) map[string]any {
	return map[string]any{"type": "string", "description": description}
}

func integerSchema(description string) map[string]any {
	return map[string]any{"type": "integer", "description": description}
}

func booleanSchema(description string) map[string]any {
	return map[string]any{"type": "boolean", "description": description}
}

func enumSchema(description string, values ...string) map[string]any {
	return map[string]any{"type": "string", "description": description, "enum": values}
}

func (server *MCPServer) handleToolCall(raw json.RawMessage) (any, *jsonRPCError) {
	var params struct {
		Name      string         `json:"name"`
		Arguments map[string]any `json:"arguments"`
	}
	if len(raw) == 0 || string(raw) == "null" || json.Unmarshal(raw, &params) != nil || strings.TrimSpace(params.Name) == "" {
		return nil, &jsonRPCError{Code: -32602, Message: "tools/call requires a tool name"}
	}
	if params.Arguments == nil {
		params.Arguments = map[string]any{}
	}
	result, known := server.callTool(params.Name, params.Arguments)
	if !known {
		return nil, &jsonRPCError{Code: -32601, Message: "unknown tool: " + params.Name}
	}
	return result, nil
}

func (server *MCPServer) callTool(name string, args map[string]any) (toolResult, bool) {
	switch name {
	case "dataset_summary":
		return successTool(map[string]any{
			"datasets":      server.store.Datasets,
			"match_records": len(server.store.Matches),
			"players":       len(server.store.Players),
		}), true
	case "search_matches":
		filter, err := matchFilterFromArgs(args)
		if err != nil {
			return failureTool(err), true
		}
		matches, policy := server.store.selectMatches(filter)
		sortMatchesNewestFirst(matches)
		total := len(matches)
		limited := limitMatches(matches, filter.Limit)
		return successTool(map[string]any{
			"matches":       limited,
			"total_matches": total,
			"truncated":     len(limited) < total,
			"source_policy": policy,
			"sources":       sourcesFor(matches),
		}), true
	case "team_statistics":
		team, err := requiredString(args, "team")
		if err != nil {
			return failureTool(err), true
		}
		filter, err := matchFilterFromArgs(args)
		if err != nil {
			return failureTool(err), true
		}
		venue, err := optionalString(args, "venue")
		if err != nil {
			return failureTool(err), true
		}
		stats, err := server.store.TeamStatistics(team, filter, venue)
		if err != nil {
			return failureTool(err), true
		}
		return successTool(stats), true
	case "team_profile":
		team, err := requiredString(args, "team")
		if err != nil {
			return failureTool(err), true
		}
		filter, err := matchFilterFromArgs(args)
		if err != nil {
			return failureTool(err), true
		}
		playerLimit, err := optionalInt(args, "player_limit")
		if err != nil {
			return failureTool(err), true
		}
		profile, err := server.store.TeamProfile(team, filter, playerLimit)
		if err != nil {
			return failureTool(err), true
		}
		return successTool(profile), true
	case "head_to_head":
		teamA, err := requiredString(args, "team_a")
		if err != nil {
			return failureTool(err), true
		}
		teamB, err := requiredString(args, "team_b")
		if err != nil {
			return failureTool(err), true
		}
		filter, err := matchFilterFromArgs(args)
		if err != nil {
			return failureTool(err), true
		}
		result, err := server.store.HeadToHead(teamA, teamB, filter)
		if err != nil {
			return failureTool(err), true
		}
		return successTool(result), true
	case "search_players":
		filter, err := playerFilterFromArgs(args)
		if err != nil {
			return failureTool(err), true
		}
		players := server.store.SearchPlayers(filter)
		return successTool(map[string]any{
			"players": players,
			"count":   len(players),
		}), true
	case "competition_standings":
		competition, err := requiredString(args, "competition")
		if err != nil {
			return failureTool(err), true
		}
		season, err := requiredInt(args, "season")
		if err != nil {
			return failureTool(err), true
		}
		includeAll, err := boolArg(args, "include_all_sources")
		if err != nil {
			return failureTool(err), true
		}
		source, err := optionalString(args, "source")
		if err != nil {
			return failureTool(err), true
		}
		result, err := server.store.Standings(competition, season, source, includeAll)
		if err != nil {
			return failureTool(err), true
		}
		return successTool(result), true
	case "competition_statistics":
		filter, err := matchFilterFromArgs(args)
		if err != nil {
			return failureTool(err), true
		}
		return successTool(server.store.Statistics(filter)), true
	case "team_rankings":
		filter, err := matchFilterFromArgs(args)
		if err != nil {
			return failureTool(err), true
		}
		limit, err := optionalInt(args, "limit")
		if err != nil {
			return failureTool(err), true
		}
		metric, err := optionalString(args, "metric")
		if err != nil {
			return failureTool(err), true
		}
		rankings, err := server.store.TeamRankings(filter, metric, limit)
		if err != nil {
			return failureTool(err), true
		}
		return successTool(map[string]any{"metric": metric, "rankings": rankings}), true
	case "soccer_query":
		query, err := requiredString(args, "query")
		if err != nil {
			return failureTool(err), true
		}
		limit, err := optionalInt(args, "limit")
		if err != nil {
			return failureTool(err), true
		}
		result, err := server.store.AnswerNaturalQuery(query, limit)
		if err != nil {
			return failureTool(err), true
		}
		return successTool(result), true
	default:
		return toolResult{}, false
	}
}

func successTool(value any) toolResult {
	encoded, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return failureTool(fmt.Errorf("could not encode tool result: %w", err))
	}
	result := toolResult{Content: []textContent{{Type: "text", Text: string(encoded)}}}
	if len(bytes.TrimSpace(encoded)) > 0 && bytes.TrimSpace(encoded)[0] == '{' {
		result.StructuredContent = value
	}
	return result
}

func failureTool(err error) toolResult {
	return toolResult{
		Content: []textContent{{Type: "text", Text: "Error: " + err.Error()}},
		IsError: true,
	}
}

func matchFilterFromArgs(args map[string]any) (MatchFilter, error) {
	if err := validateStringArgs(args, "team", "opponent", "home_team", "away_team", "competition", "source", "round", "stage", "date_from", "start_date", "date_to", "end_date"); err != nil {
		return MatchFilter{}, err
	}
	season, err := optionalInt(args, "season")
	if err != nil {
		return MatchFilter{}, err
	}
	limit, err := optionalInt(args, "limit")
	if err != nil {
		return MatchFilter{}, err
	}
	includeAll, err := boolArg(args, "include_all_sources")
	if err != nil {
		return MatchFilter{}, err
	}
	startDate, err := dateArg(args, "date_from", "start_date")
	if err != nil {
		return MatchFilter{}, err
	}
	endDate, err := dateArg(args, "date_to", "end_date")
	if err != nil {
		return MatchFilter{}, err
	}
	return MatchFilter{
		Team:              stringArg(args, "team"),
		Opponent:          stringArg(args, "opponent"),
		HomeTeam:          stringArg(args, "home_team"),
		AwayTeam:          stringArg(args, "away_team"),
		Competition:       stringArg(args, "competition"),
		Source:            stringArg(args, "source"),
		Season:            season,
		Round:             stringArg(args, "round"),
		Stage:             stringArg(args, "stage"),
		StartDate:         startDate,
		EndDate:           endDate,
		Limit:             limit,
		IncludeAllSources: includeAll,
	}, nil
}

func playerFilterFromArgs(args map[string]any) (PlayerFilter, error) {
	if err := validateStringArgs(args, "name", "nationality", "club", "position"); err != nil {
		return PlayerFilter{}, err
	}
	minimum, err := optionalInt(args, "min_overall")
	if err != nil {
		return PlayerFilter{}, err
	}
	limit, err := optionalInt(args, "limit")
	if err != nil {
		return PlayerFilter{}, err
	}
	return PlayerFilter{
		Name:        stringArg(args, "name"),
		Nationality: stringArg(args, "nationality"),
		Club:        stringArg(args, "club"),
		Position:    stringArg(args, "position"),
		MinOverall:  minimum,
		Limit:       limit,
	}, nil
}

func stringArg(args map[string]any, name string) string {
	value, ok := args[name]
	if !ok || value == nil {
		return ""
	}
	if text, ok := value.(string); ok {
		return strings.TrimSpace(text)
	}
	return ""
}

func requiredString(args map[string]any, name string) (string, error) {
	value, err := optionalString(args, name)
	if err != nil {
		return "", err
	}
	if value == "" {
		return "", fmt.Errorf("%s is required", name)
	}
	return value, nil
}

func optionalString(args map[string]any, name string) (string, error) {
	value, ok := args[name]
	if !ok || value == nil {
		return "", nil
	}
	text, ok := value.(string)
	if !ok {
		return "", fmt.Errorf("%s must be a string", name)
	}
	return strings.TrimSpace(text), nil
}

func validateStringArgs(args map[string]any, names ...string) error {
	for _, name := range names {
		if _, err := optionalString(args, name); err != nil {
			return err
		}
	}
	return nil
}

func optionalInt(args map[string]any, name string) (int, error) {
	value, ok := args[name]
	if !ok || value == nil || value == "" {
		return 0, nil
	}
	switch converted := value.(type) {
	case float64:
		if converted != float64(int(converted)) {
			return 0, fmt.Errorf("%s must be an integer", name)
		}
		return int(converted), nil
	case float32:
		if converted != float32(int(converted)) {
			return 0, fmt.Errorf("%s must be an integer", name)
		}
		return int(converted), nil
	case int:
		return converted, nil
	case int64:
		return int(converted), nil
	case json.Number:
		integer, err := converted.Int64()
		if err != nil {
			return 0, fmt.Errorf("%s must be an integer", name)
		}
		return int(integer), nil
	default:
		return 0, fmt.Errorf("%s must be an integer", name)
	}
}

func requiredInt(args map[string]any, name string) (int, error) {
	value, err := optionalInt(args, name)
	if err != nil {
		return 0, err
	}
	if value == 0 {
		return 0, fmt.Errorf("%s is required", name)
	}
	return value, nil
}

func boolArg(args map[string]any, name string) (bool, error) {
	value, ok := args[name]
	if !ok || value == nil || value == "" {
		return false, nil
	}
	switch converted := value.(type) {
	case bool:
		return converted, nil
	default:
		return false, fmt.Errorf("%s must be true or false", name)
	}
}

func dateArg(args map[string]any, names ...string) (timeValue time.Time, err error) {
	for _, name := range names {
		value := stringArg(args, name)
		if value == "" {
			continue
		}
		parsed := parseDate(value)
		if parsed.IsZero() {
			return time.Time{}, fmt.Errorf("%s must be an ISO date or supported source date", name)
		}
		return parsed, nil
	}
	return time.Time{}, nil
}
