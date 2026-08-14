package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"strconv"
	"strings"
	"time"
)

const (
	serverName    = "brazilian-soccer-mcp"
	serverVersion = "1.0.0"
)

var supportedProtocolVersions = map[string]bool{
	"2024-11-05": true,
	"2025-03-26": true,
	"2025-06-18": true,
	"2025-11-25": true,
}

// MCPServer exposes the normalized data graph through the MCP stdio transport.
// It is intentionally dependency-free so `go run .` works in an offline demo.
type MCPServer struct {
	Database *Database
}

func NewMCPServer(database *Database) *MCPServer { return &MCPServer{Database: database} }

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  interface{}     `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

type textContent struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type toolResult struct {
	Content           []textContent `json:"content"`
	StructuredContent interface{}   `json:"structuredContent,omitempty"`
	IsError           bool          `json:"isError"`
}

type toolCall struct {
	Name      string                 `json:"name"`
	Arguments map[string]interface{} `json:"arguments"`
}

type toolExecutionError struct {
	Code    string
	Message string
}

func (e *toolExecutionError) Error() string { return e.Message }

type argumentKind string

const (
	stringArgumentKind  argumentKind = "string"
	integerArgumentKind argumentKind = "integer"
	booleanArgumentKind argumentKind = "boolean"
)

// validateToolArguments enforces the advertised JSON-schema shape before a
// query is executed. That keeps a malformed filter from degenerating into an
// accidental full-corpus search.
func validateToolArguments(toolName string, arguments map[string]interface{}) error {
	allowed, known := allowedToolArguments(toolName)
	if !known {
		return fmt.Errorf("unknown tool %q", toolName)
	}
	for name, value := range arguments {
		kind, ok := allowed[name]
		if !ok {
			return fmt.Errorf("unknown argument %q for tool %q", name, toolName)
		}
		if err := validateArgumentKind(name, value, kind); err != nil {
			return err
		}
	}
	for _, name := range []string{"limit", "offset", "season", "min_overall", "max_overall", "min_age", "max_age"} {
		value, provided := arguments[name]
		if !provided || value == nil {
			continue
		}
		integer, err := strictInteger(value)
		if err != nil {
			return fmt.Errorf("%s must be an integer", name)
		}
		switch name {
		case "limit":
			if integer < 1 || integer > 100 {
				return fmt.Errorf("limit must be between 1 and 100")
			}
		case "offset":
			if integer < 0 {
				return fmt.Errorf("offset cannot be negative")
			}
		case "season", "min_overall", "max_overall", "min_age", "max_age":
			if integer < 0 {
				return fmt.Errorf("%s cannot be negative", name)
			}
		}
	}
	return nil
}

func validateArgumentKind(name string, value interface{}, kind argumentKind) error {
	if value == nil {
		return fmt.Errorf("%s cannot be null", name)
	}
	switch kind {
	case stringArgumentKind:
		if _, ok := value.(string); !ok {
			return fmt.Errorf("%s must be a string", name)
		}
	case booleanArgumentKind:
		if _, ok := value.(bool); !ok {
			return fmt.Errorf("%s must be a boolean", name)
		}
	case integerArgumentKind:
		if _, err := strictInteger(value); err != nil {
			return fmt.Errorf("%s must be an integer", name)
		}
	}
	return nil
}

func strictInteger(value interface{}) (int, error) {
	switch number := value.(type) {
	case json.Number:
		return strconv.Atoi(number.String())
	case float64:
		if number != float64(int(number)) {
			return 0, fmt.Errorf("not an integer")
		}
		return int(number), nil
	case int:
		return number, nil
	default:
		return 0, fmt.Errorf("not an integer")
	}
}

func allowedToolArguments(toolName string) (map[string]argumentKind, bool) {
	common := map[string]argumentKind{
		"competition": stringArgumentKind, "source": stringArgumentKind, "source_scope": stringArgumentKind,
		"season": integerArgumentKind, "date_from": stringArgumentKind, "date_to": stringArgumentKind,
		"start_date": stringArgumentKind, "end_date": stringArgumentKind,
	}
	with := func(extra map[string]argumentKind) map[string]argumentKind {
		result := make(map[string]argumentKind, len(common)+len(extra))
		for name, kind := range common {
			result[name] = kind
		}
		for name, kind := range extra {
			result[name] = kind
		}
		return result
	}
	switch toolName {
	case "search_matches", "list_derbies":
		return with(map[string]argumentKind{"team": stringArgumentKind, "opponent": stringArgumentKind, "home_team": stringArgumentKind, "away_team": stringArgumentKind, "round": stringArgumentKind, "stage": stringArgumentKind, "include_unplayed": booleanArgumentKind, "limit": integerArgumentKind, "offset": integerArgumentKind}), true
	case "get_team_stats", "team_statistics", "get_team_statistics":
		return with(map[string]argumentKind{"team": stringArgumentKind, "venue": stringArgumentKind}), true
	case "compare_teams", "head_to_head":
		return with(map[string]argumentKind{"team_a": stringArgumentKind, "team_b": stringArgumentKind, "limit": integerArgumentKind, "offset": integerArgumentKind}), true
	case "search_players":
		return map[string]argumentKind{"name": stringArgumentKind, "nationality": stringArgumentKind, "club": stringArgumentKind, "position": stringArgumentKind, "min_overall": integerArgumentKind, "max_overall": integerArgumentKind, "min_age": integerArgumentKind, "max_age": integerArgumentKind, "sort_by": stringArgumentKind, "sort_order": stringArgumentKind, "limit": integerArgumentKind, "offset": integerArgumentKind}, true
	case "get_standings", "competition_standings", "get_competition_standings":
		return map[string]argumentKind{
			"competition": stringArgumentKind, "source": stringArgumentKind, "source_scope": stringArgumentKind,
			"season": integerArgumentKind, "limit": integerArgumentKind,
		}, true
	case "get_competition_stats", "analyze_statistics", "analyze_matches":
		return with(map[string]argumentKind{"metric": stringArgumentKind}), true
	case "list_team_competitions":
		return with(map[string]argumentKind{"team": stringArgumentKind}), true
	case "ask_brazilian_soccer", "natural_language_query":
		return map[string]argumentKind{"question": stringArgumentKind}, true
	case "list_data_sources":
		return map[string]argumentKind{}, true
	default:
		return nil, false
	}
}

// Serve implements newline-delimited JSON-RPC on standard input/output. It
// never writes diagnostics to out; a client can safely consume stdout as MCP.
func (server *MCPServer) Serve(in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 64*1024), 8*1024*1024)
	encoder := json.NewEncoder(out)
	for scanner.Scan() {
		line := bytes.TrimSpace(scanner.Bytes())
		if len(line) == 0 {
			continue
		}
		response, respond := server.HandleJSON(line)
		if !respond {
			continue
		}
		if err := encoder.Encode(response); err != nil {
			return err
		}
	}
	return scanner.Err()
}

// HandleJSON is exported for small embedding programs and protocol tests.
func (server *MCPServer) HandleJSON(message []byte) (rpcResponse, bool) {
	decoder := json.NewDecoder(bytes.NewReader(message))
	decoder.UseNumber()
	var request rpcRequest
	if err := decoder.Decode(&request); err != nil {
		return failureResponse(nil, -32700, "Parse error", err.Error()), true
	}
	if request.JSONRPC != "2.0" || strings.TrimSpace(request.Method) == "" {
		return failureResponse(request.ID, -32600, "Invalid Request", "jsonrpc must be 2.0 and method is required"), true
	}
	response, respond := server.handleRequest(request)
	return response, respond
}

func (server *MCPServer) handleRequest(request rpcRequest) (rpcResponse, bool) {
	// JSON-RPC notifications have no id and therefore receive no response.
	if len(request.ID) == 0 && (request.Method == "notifications/initialized" || strings.HasPrefix(request.Method, "notifications/")) {
		return rpcResponse{}, false
	}
	isNotification := len(request.ID) == 0
	if isNotification {
		return rpcResponse{}, false
	}

	switch request.Method {
	case "initialize":
		result, err := initializeResult(request.Params)
		if err != nil {
			return failureResponse(request.ID, -32602, "Invalid params", err.Error()), true
		}
		return successResponse(request.ID, result), true
	case "ping":
		return successResponse(request.ID, map[string]interface{}{}), true
	case "tools/list":
		return successResponse(request.ID, map[string]interface{}{"tools": toolDefinitions()}), true
	case "tools/call":
		call, err := decodeToolCall(request.Params)
		if err != nil {
			return failureResponse(request.ID, -32602, "Invalid params", err.Error()), true
		}
		result, protocolErr := server.callTool(call)
		if protocolErr != nil {
			return failureResponse(request.ID, -32602, "Invalid params", protocolErr.Error()), true
		}
		return successResponse(request.ID, result), true
	default:
		return failureResponse(request.ID, -32601, "Method not found", request.Method), true
	}
}

func initializeResult(params json.RawMessage) (map[string]interface{}, error) {
	var input struct {
		ProtocolVersion string          `json:"protocolVersion"`
		Capabilities    json.RawMessage `json:"capabilities"`
		ClientInfo      *struct {
			Name    string `json:"name"`
			Version string `json:"version"`
		} `json:"clientInfo"`
	}
	if len(params) == 0 || string(params) == "null" {
		return nil, fmt.Errorf("initialize requires protocolVersion, capabilities, and clientInfo")
	}
	if err := json.Unmarshal(params, &input); err != nil {
		return nil, err
	}
	if input.ProtocolVersion == "" || len(input.Capabilities) == 0 || string(input.Capabilities) == "null" || input.ClientInfo == nil || strings.TrimSpace(input.ClientInfo.Name) == "" || strings.TrimSpace(input.ClientInfo.Version) == "" {
		return nil, fmt.Errorf("initialize requires protocolVersion, capabilities, and clientInfo.name/clientInfo.version")
	}
	var capabilities map[string]json.RawMessage
	if err := json.Unmarshal(input.Capabilities, &capabilities); err != nil || capabilities == nil {
		return nil, fmt.Errorf("initialize capabilities must be an object")
	}
	version := input.ProtocolVersion
	if !supportedProtocolVersions[version] {
		// MCP version negotiation selects the newest version this server supports.
		version = "2025-11-25"
	}
	return map[string]interface{}{
		"protocolVersion": version,
		"capabilities":    map[string]interface{}{"tools": map[string]interface{}{}},
		"serverInfo":      map[string]string{"name": serverName, "version": serverVersion},
		"instructions":    "Use the soccer tools for historical Brazilian match and FIFA player data. Results include source provenance; unknown scores are excluded from aggregates.",
	}, nil
}

func decodeToolCall(params json.RawMessage) (toolCall, error) {
	if len(params) == 0 || string(params) == "null" {
		return toolCall{}, fmt.Errorf("tools/call requires name and arguments")
	}
	decoder := json.NewDecoder(bytes.NewReader(params))
	decoder.UseNumber()
	var call toolCall
	if err := decoder.Decode(&call); err != nil {
		return toolCall{}, err
	}
	if strings.TrimSpace(call.Name) == "" {
		return toolCall{}, fmt.Errorf("tools/call requires a tool name")
	}
	if call.Arguments == nil {
		call.Arguments = map[string]interface{}{}
	}
	return call, nil
}

func successResponse(id json.RawMessage, result interface{}) rpcResponse {
	return rpcResponse{JSONRPC: "2.0", ID: normalizedID(id), Result: result}
}

func failureResponse(id json.RawMessage, code int, message string, data interface{}) rpcResponse {
	return rpcResponse{JSONRPC: "2.0", ID: normalizedID(id), Error: &rpcError{Code: code, Message: message, Data: data}}
}

func normalizedID(id json.RawMessage) json.RawMessage {
	if len(id) == 0 {
		return json.RawMessage("null")
	}
	return id
}

func (server *MCPServer) callTool(call toolCall) (toolResult, error) {
	if err := validateToolArguments(call.Name, call.Arguments); err != nil {
		return toolResult{}, err
	}
	var (
		structured interface{}
		text       string
		execErr    *toolExecutionError
	)

	switch call.Name {
	case "search_matches":
		filter, err := parseMatchFilter(call.Arguments)
		if err != nil {
			execErr = invalidArgument(err)
			break
		}
		result := server.Database.SearchMatches(filter)
		structured = map[string]interface{}{
			"matches": result.Matches, "total": result.Total, "nextOffset": result.NextOffset,
			"sourceScope": sourceScopeForOutput(filter.Source), "dataSources": sourceNames(result.Matches),
		}
		text = formatMatchSearch(result)
	case "get_team_stats", "team_statistics", "get_team_statistics":
		team, err := requiredString(call.Arguments, "team")
		if err != nil {
			execErr = invalidArgument(err)
			break
		}
		filter, err := parseMatchFilter(call.Arguments)
		if err != nil {
			execErr = invalidArgument(err)
			break
		}
		stats, err := server.Database.TeamStatistics(team, filter, stringArgument(call.Arguments, "venue"))
		if err != nil {
			execErr = invalidArgument(err)
			break
		}
		structured, text = stats, formatTeamStats(stats)
	case "compare_teams", "head_to_head":
		teamA, errA := requiredString(call.Arguments, "team_a")
		teamB, errB := requiredString(call.Arguments, "team_b")
		if errA != nil {
			execErr = invalidArgument(errA)
			break
		}
		if errB != nil {
			execErr = invalidArgument(errB)
			break
		}
		filter, err := parseMatchFilter(call.Arguments)
		if err != nil {
			execErr = invalidArgument(err)
			break
		}
		summary, matches, err := server.Database.CompareTeams(teamA, teamB, filter)
		if err != nil {
			execErr = invalidArgument(err)
			break
		}
		page := pageMatches(matches, filter.Offset, filter.Limit)
		structured = map[string]interface{}{"headToHead": summary, "matches": page.Matches, "total": page.Total, "nextOffset": page.NextOffset, "dataSources": sourceNames(matches)}
		text = formatHeadToHead(summary, page)
	case "search_players":
		filter, err := parsePlayerFilter(call.Arguments)
		if err != nil {
			execErr = invalidArgument(err)
			break
		}
		players, total, next := server.Database.SearchPlayers(filter)
		structured = map[string]interface{}{"players": players, "total": total, "nextOffset": next, "source": "fifa_players", "snapshot": "historical/offline FIFA dataset"}
		text = formatPlayers(players, total)
	case "get_standings", "competition_standings", "get_competition_standings":
		season, err := integerArgument(call.Arguments, "season")
		if err != nil || season <= 0 {
			execErr = invalidArgument(fmt.Errorf("season is required and must be positive"))
			break
		}
		competition := stringArgument(call.Arguments, "competition")
		if competition == "" {
			competition = "brasileirao"
		}
		if err := validateSourceArguments(call.Arguments); err != nil {
			execErr = invalidArgument(err)
			break
		}
		source := sourceArgument(call.Arguments)
		standings, err := server.Database.CompetitionStandings(competition, season, source)
		if err != nil {
			execErr = invalidArgument(err)
			break
		}
		limit, limitErr := optionalIntegerArgument(call.Arguments, "limit")
		if limitErr != nil {
			execErr = invalidArgument(limitErr)
			break
		}
		if limit > 0 && limit < len(standings) {
			standings = standings[:normalizedLimit(limit)]
		}
		standingMatches, unplayedExcluded := server.Database.matchesWithUnknown(MatchFilter{Competition: competition, Season: season, Source: source})
		structured = map[string]interface{}{
			"competition": competition, "season": season, "standings": standings,
			"sourceScope": sourceScopeForOutput(source), "dataSources": sourceNames(standingMatches),
			"unplayedExcluded": unplayedExcluded, "tieBreaker": "points, wins, goal difference, goals scored, team name",
		}
		text = formatStandingsWithExclusions(competition, season, standings, unplayedExcluded)
	case "get_competition_stats", "analyze_statistics", "analyze_matches":
		filter, err := parseMatchFilter(call.Arguments)
		if err != nil {
			execErr = invalidArgument(err)
			break
		}
		result, err := server.Database.AnalyzeMatches(filter, stringArgument(call.Arguments, "metric"))
		if err != nil {
			if strings.HasPrefix(err.Error(), "unsupported metric") {
				execErr = &toolExecutionError{Code: "UNSUPPORTED_ANALYSIS", Message: err.Error()}
			} else {
				execErr = invalidArgument(err)
			}
			break
		}
		structured, text = result, formatStatistics(result)
	case "list_team_competitions":
		team, err := requiredString(call.Arguments, "team")
		if err != nil {
			execErr = invalidArgument(err)
			break
		}
		filter, err := parseMatchFilter(call.Arguments)
		if err != nil {
			execErr = invalidArgument(err)
			break
		}
		filter.Team = team
		filter.IncludeUnplayed = true
		matches := server.Database.filteredMatches(filter)
		competitions := competitionsFor(matches)
		structured = map[string]interface{}{"team": server.Database.displayName(normalizeTeam(team), team), "competitions": competitions, "matches": len(matches), "dataSources": sourceNames(matches)}
		text = fmt.Sprintf("%s has matches in: %s.", server.Database.displayName(normalizeTeam(team), team), strings.Join(competitions, ", "))
	case "list_derbies":
		filter, err := parseMatchFilter(call.Arguments)
		if err != nil {
			execErr = invalidArgument(err)
			break
		}
		matches := derbyMatches(server.Database, filter)
		page := pageMatches(matches, filter.Offset, filter.Limit)
		structured = map[string]interface{}{"matches": page.Matches, "total": page.Total, "nextOffset": page.NextOffset, "note": "Derbies use a small documented traditional-rivalry map; they are not inferable from match rows alone."}
		text = formatMatchSearch(page)
	case "ask_brazilian_soccer", "natural_language_query":
		question, err := requiredString(call.Arguments, "question")
		if err != nil {
			execErr = invalidArgument(err)
			break
		}
		structured, text, execErr = server.answerQuestion(question)
	case "list_data_sources":
		structured = map[string]interface{}{"sources": server.Database.Report.Sources, "matchesLoaded": len(server.Database.Matches), "playersLoaded": len(server.Database.Players), "defaultSourceScope": "canonical"}
		text = formatSources(server.Database)
	default:
		return toolResult{}, fmt.Errorf("unknown tool %q", call.Name)
	}

	if execErr != nil {
		return toolResult{
			Content:           []textContent{{Type: "text", Text: execErr.Message}},
			StructuredContent: map[string]string{"code": execErr.Code, "message": execErr.Message},
			IsError:           true,
		}, nil
	}
	return toolResult{Content: []textContent{{Type: "text", Text: text}}, StructuredContent: structured}, nil
}

func invalidArgument(err error) *toolExecutionError {
	return &toolExecutionError{Code: "INVALID_ARGUMENT", Message: err.Error()}
}

func parseMatchFilter(args map[string]interface{}) (MatchFilter, error) {
	filter := MatchFilter{
		Team: stringArgument(args, "team"), Opponent: firstStringArgument(args, "opponent", "team_b"),
		HomeTeam: stringArgument(args, "home_team"), AwayTeam: stringArgument(args, "away_team"),
		Competition: stringArgument(args, "competition"), Source: sourceArgument(args),
		Round: stringArgument(args, "round"), Stage: stringArgument(args, "stage"), Offset: 0, Limit: 20, IncludeUnplayed: true,
	}
	var err error
	if filter.Season, err = optionalIntegerArgument(args, "season"); err != nil {
		return MatchFilter{}, err
	}
	if filter.Limit, err = optionalIntegerArgument(args, "limit"); err != nil {
		return MatchFilter{}, err
	}
	if filter.Limit == 0 {
		filter.Limit = 20
	}
	if filter.Offset, err = optionalIntegerArgument(args, "offset"); err != nil {
		return MatchFilter{}, err
	}
	if filter.Offset < 0 {
		return MatchFilter{}, fmt.Errorf("offset cannot be negative")
	}
	if value, ok, boolErr := optionalBoolArgument(args, "include_unplayed"); boolErr != nil {
		return MatchFilter{}, boolErr
	} else if ok {
		filter.IncludeUnplayed = value
	}
	if filter.DateFrom, err = dateArgument(args, "date_from", "start_date"); err != nil {
		return MatchFilter{}, err
	}
	if filter.DateTo, err = dateArgument(args, "date_to", "end_date"); err != nil {
		return MatchFilter{}, err
	}
	if filter.DateFrom != nil && filter.DateTo != nil && filter.DateFrom.After(*filter.DateTo) {
		return MatchFilter{}, fmt.Errorf("date_from cannot be after date_to")
	}
	if err := validateSourceArguments(args); err != nil {
		return MatchFilter{}, err
	}
	return filter, nil
}

func parsePlayerFilter(args map[string]interface{}) (PlayerFilter, error) {
	filter := PlayerFilter{Name: stringArgument(args, "name"), Nationality: stringArgument(args, "nationality"), Club: stringArgument(args, "club"), Position: stringArgument(args, "position"), SortBy: stringArgument(args, "sort_by"), SortOrder: stringArgument(args, "sort_order"), Limit: 20}
	var err error
	if filter.MinOverall, err = optionalIntegerArgument(args, "min_overall"); err != nil {
		return PlayerFilter{}, err
	}
	if filter.MaxOverall, err = optionalIntegerArgument(args, "max_overall"); err != nil {
		return PlayerFilter{}, err
	}
	if filter.MinAge, err = optionalIntegerArgument(args, "min_age"); err != nil {
		return PlayerFilter{}, err
	}
	if filter.MaxAge, err = optionalIntegerArgument(args, "max_age"); err != nil {
		return PlayerFilter{}, err
	}
	if filter.Limit, err = optionalIntegerArgument(args, "limit"); err != nil {
		return PlayerFilter{}, err
	}
	if filter.Limit == 0 {
		filter.Limit = 20
	}
	if filter.Offset, err = optionalIntegerArgument(args, "offset"); err != nil {
		return PlayerFilter{}, err
	}
	if filter.Offset < 0 {
		return PlayerFilter{}, fmt.Errorf("offset cannot be negative")
	}
	if filter.MinOverall > 0 && filter.MaxOverall > 0 && filter.MinOverall > filter.MaxOverall {
		return PlayerFilter{}, fmt.Errorf("min_overall cannot exceed max_overall")
	}
	if filter.MinAge > 0 && filter.MaxAge > 0 && filter.MinAge > filter.MaxAge {
		return PlayerFilter{}, fmt.Errorf("min_age cannot exceed max_age")
	}
	switch normalizeText(filter.SortBy) {
	case "", "overall", "potential", "age", "name":
	default:
		return PlayerFilter{}, fmt.Errorf("sort_by must be overall, potential, age, or name")
	}
	switch normalizeText(filter.SortOrder) {
	case "", "asc", "desc":
	default:
		return PlayerFilter{}, fmt.Errorf("sort_order must be asc or desc")
	}
	return filter, nil
}

func stringArgument(args map[string]interface{}, name string) string {
	value, ok := args[name]
	if !ok || value == nil {
		return ""
	}
	text, ok := value.(string)
	if !ok {
		return ""
	}
	return strings.TrimSpace(text)
}

func firstStringArgument(args map[string]interface{}, names ...string) string {
	for _, name := range names {
		if value := stringArgument(args, name); value != "" {
			return value
		}
	}
	return ""
}

func requiredString(args map[string]interface{}, name string) (string, error) {
	value := stringArgument(args, name)
	if value == "" {
		return "", fmt.Errorf("%s is required", name)
	}
	return value, nil
}

func optionalIntegerArgument(args map[string]interface{}, name string) (int, error) {
	value, ok := args[name]
	if !ok || value == nil {
		return 0, nil
	}
	switch number := value.(type) {
	case json.Number:
		parsed, err := strconv.Atoi(number.String())
		if err != nil {
			return 0, fmt.Errorf("%s must be an integer", name)
		}
		return parsed, nil
	case float64:
		if number != float64(int(number)) {
			return 0, fmt.Errorf("%s must be an integer", name)
		}
		return int(number), nil
	case int:
		return number, nil
	case string:
		if strings.TrimSpace(number) == "" {
			return 0, nil
		}
		parsed, err := strconv.Atoi(number)
		if err != nil {
			return 0, fmt.Errorf("%s must be an integer", name)
		}
		return parsed, nil
	default:
		return 0, fmt.Errorf("%s must be an integer", name)
	}
}

func integerArgument(args map[string]interface{}, name string) (int, error) {
	if _, ok := args[name]; !ok {
		return 0, fmt.Errorf("%s is required", name)
	}
	return optionalIntegerArgument(args, name)
}

func optionalBoolArgument(args map[string]interface{}, name string) (bool, bool, error) {
	value, ok := args[name]
	if !ok || value == nil {
		return false, false, nil
	}
	parsed, ok := value.(bool)
	if !ok {
		return false, true, fmt.Errorf("%s must be a boolean", name)
	}
	return parsed, true, nil
}

func dateArgument(args map[string]interface{}, names ...string) (*time.Time, error) {
	for _, name := range names {
		value := stringArgument(args, name)
		if value == "" {
			continue
		}
		parsed, err := parseDate(value)
		if err != nil || parsed.IsZero() {
			return nil, fmt.Errorf("%s must be an ISO or Brazilian date", name)
		}
		return &parsed, nil
	}
	return nil, nil
}

func sourceArgument(args map[string]interface{}) string {
	return firstStringArgument(args, "source", "source_scope")
}

func validateSourceArguments(args map[string]interface{}) error {
	if stringArgument(args, "source") != "" && stringArgument(args, "source_scope") != "" && normalizeSourceScope(stringArgument(args, "source")) != normalizeSourceScope(stringArgument(args, "source_scope")) {
		return fmt.Errorf("source and source_scope must agree when both are supplied")
	}
	return nil
}
func sourceScopeForOutput(source string) string {
	source = normalizeSourceScope(source)
	if source == "" {
		return "canonical"
	}
	return source
}

func toolDefinitions() []map[string]interface{} {
	return []map[string]interface{}{
		tool("search_matches", "Find Brazilian soccer matches by team, opponent, competition, date, season, source, round, or stage. Results retain their dataset source and unknown-score status.", matchSchema()),
		tool("get_team_stats", "Calculate a team's played-match record, goals, and win rate. Unknown or scheduled fixtures are excluded.", teamStatsSchema()),
		tool("compare_teams", "Calculate a source-aware head-to-head record and list the corresponding matches.", headToHeadSchema()),
		tool("search_players", "Search the supplied historical FIFA player snapshot by name, nationality, club, position, age, or rating.", playerSchema()),
		tool("get_standings", "Calculate a season table from completed match results. Tie-breaks are points, wins, goal difference, then goals scored.", standingsSchema()),
		tool("get_competition_stats", "Calculate average goals, home advantage, best home/away records, biggest wins, or top-scoring teams.", statisticsSchema()),
		tool("list_team_competitions", "List the competitions in which a team appears in the supplied match data.", teamCompetitionSchema()),
		tool("list_derbies", "List matches from a documented static set of traditional Brazilian rivalries; rivalry status is not inferred from rows.", matchSchema()),
		tool("ask_brazilian_soccer", "Answer common natural-language questions by selecting the appropriate local soccer-data query. For broader questions, use the structured tools directly.", schema(map[string]interface{}{"question": stringProperty("Natural-language Brazilian soccer question.")}, []string{"question"})),
		tool("list_data_sources", "Show loading counts and the six local dataset sources used by this server.", schema(map[string]interface{}{}, nil)),
	}
}

func tool(name, description string, inputSchema map[string]interface{}) map[string]interface{} {
	return map[string]interface{}{"name": name, "title": strings.ReplaceAll(strings.Title(strings.ReplaceAll(name, "_", " ")), " ", " "), "description": description, "inputSchema": inputSchema}
}

func schema(properties map[string]interface{}, required []string) map[string]interface{} {
	result := map[string]interface{}{"type": "object", "properties": properties, "additionalProperties": false}
	if len(required) > 0 {
		result["required"] = required
	}
	return result
}

func stringProperty(description string) map[string]interface{} {
	return map[string]interface{}{"type": "string", "description": description}
}
func integerProperty(description string) map[string]interface{} {
	return map[string]interface{}{"type": "integer", "description": description}
}
func boolProperty(description string) map[string]interface{} {
	return map[string]interface{}{"type": "boolean", "description": description}
}

func matchSchema() map[string]interface{} {
	properties := commonMatchProperties()
	properties["team"] = stringProperty("Team appearing as home or away. Accent and state-suffix variations are normalized.")
	properties["opponent"] = stringProperty("Optional opposing team. With team, matches either home/away orientation.")
	properties["home_team"] = stringProperty("Optional exact home team filter.")
	properties["away_team"] = stringProperty("Optional exact away team filter.")
	properties["round"] = stringProperty("Round number or label, for example 8 for Copa do Brasil final.")
	properties["stage"] = stringProperty("Tournament stage, for example group stage or final.")
	properties["include_unplayed"] = boolProperty("Whether scheduled or unknown-score fixtures are included; defaults to true.")
	properties["limit"] = integerProperty("Maximum records returned, 1-100; defaults to 20.")
	properties["offset"] = integerProperty("Zero-based pagination offset.")
	return schema(properties, nil)
}

func teamStatsSchema() map[string]interface{} {
	properties := commonMatchProperties()
	properties["team"] = stringProperty("Required team name.")
	properties["venue"] = map[string]interface{}{"type": "string", "enum": []string{"all", "home", "away"}, "description": "Venue perspective; defaults to all."}
	return schema(properties, []string{"team"})
}

func headToHeadSchema() map[string]interface{} {
	properties := commonMatchProperties()
	properties["team_a"] = stringProperty("Required first team.")
	properties["team_b"] = stringProperty("Required second team.")
	properties["limit"] = integerProperty("Maximum listed matches, 1-100; defaults to 20.")
	properties["offset"] = integerProperty("Zero-based pagination offset.")
	return schema(properties, []string{"team_a", "team_b"})
}

func playerSchema() map[string]interface{} {
	return schema(map[string]interface{}{
		"name":        stringProperty("Case- and accent-insensitive player-name fragment."),
		"nationality": stringProperty("Nationality; Brazilian/Brazil both match Brazil in this FIFA snapshot."),
		"club":        stringProperty("Club name fragment."),
		"position":    stringProperty("Playing position fragment such as ST or GK."),
		"min_overall": integerProperty("Minimum FIFA overall rating."), "max_overall": integerProperty("Maximum FIFA overall rating."),
		"min_age": integerProperty("Minimum age."), "max_age": integerProperty("Maximum age."),
		"sort_by":    map[string]interface{}{"type": "string", "enum": []string{"overall", "potential", "age", "name"}, "description": "Sort field; defaults to overall."},
		"sort_order": map[string]interface{}{"type": "string", "enum": []string{"asc", "desc"}, "description": "Sort direction; defaults to desc."},
		"limit":      integerProperty("Maximum records returned, 1-100; defaults to 20."), "offset": integerProperty("Zero-based pagination offset."),
	}, nil)
}

func standingsSchema() map[string]interface{} {
	properties := map[string]interface{}{
		"competition":  stringProperty("League competition; defaults to Brasileirão."),
		"source":       stringProperty("canonical (default), brasileirao, historical_brasileirao, or another named source."),
		"source_scope": stringProperty("Alias for source; if both are set they must agree."),
	}
	properties["season"] = integerProperty("Required competition season, not calendar year.")
	properties["competition"] = stringProperty("Competition; defaults to Brasileirão.")
	properties["limit"] = integerProperty("Optional number of table rows, 1-100.")
	return schema(properties, []string{"season"})
}

func statisticsSchema() map[string]interface{} {
	properties := commonMatchProperties()
	properties["metric"] = map[string]interface{}{"type": "string", "enum": []string{"summary", "goals_per_match", "home_advantage", "home_away", "best_home_record", "best_away_record", "biggest_wins", "top_scoring_teams"}, "description": "Statistic to calculate; defaults to summary."}
	return schema(properties, nil)
}

func teamCompetitionSchema() map[string]interface{} {
	properties := commonMatchProperties()
	properties["team"] = stringProperty("Required team name.")
	return schema(properties, []string{"team"})
}

func commonMatchProperties() map[string]interface{} {
	return map[string]interface{}{
		"competition":  stringProperty("Brasileirão, Copa do Brasil, Copa Libertadores, or a source tournament name."),
		"source":       stringProperty("canonical (default), all, brasileirao, brazilian_cup, libertadores, extended_statistics, or historical_brasileirao."),
		"source_scope": stringProperty("Alias for source; if both are set they must agree."),
		"season":       integerProperty("Season supplied by the match source."),
		"date_from":    stringProperty("Inclusive start date in YYYY-MM-DD or DD/MM/YYYY."),
		"date_to":      stringProperty("Inclusive end date in YYYY-MM-DD or DD/MM/YYYY."),
		"start_date":   stringProperty("Alias for date_from."),
		"end_date":     stringProperty("Alias for date_to."),
	}
}
