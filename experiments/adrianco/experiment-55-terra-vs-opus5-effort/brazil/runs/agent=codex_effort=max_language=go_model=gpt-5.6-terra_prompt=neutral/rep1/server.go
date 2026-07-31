package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
)

const serverName = "brazilian-soccer-mcp"

// MCPServer implements the JSON-RPC-over-stdio MCP transport using only the
// Go standard library. Keeping the protocol layer local avoids a dependency
// that could make a demo server harder to run in an offline environment.
type MCPServer struct {
	data        *DataStore
	stateMu     sync.RWMutex
	lastMatches []Match
}

func NewMCPServer(data *DataStore) *MCPServer {
	return &MCPServer{data: data}
}

func (s *MCPServer) rememberMatches(matches []Match) {
	if len(matches) == 0 {
		return
	}
	s.stateMu.Lock()
	s.lastMatches = append(s.lastMatches[:0], matches...)
	s.stateMu.Unlock()
}

func (s *MCPServer) mostRecentRememberedMatch() (Match, bool) {
	s.stateMu.RLock()
	defer s.stateMu.RUnlock()
	for _, match := range s.lastMatches {
		if match.HasScore {
			return match, true
		}
	}
	return Match{}, false
}

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

type toolContent struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type toolResult struct {
	Content           []toolContent `json:"content"`
	StructuredContent any           `json:"structuredContent,omitempty"`
	IsError           bool          `json:"isError,omitempty"`
}

type matchSearchResult struct {
	Total    int     `json:"total"`
	Returned int     `json:"returned"`
	Matches  []Match `json:"matches"`
}

type standingsResult struct {
	Competition string     `json:"competition"`
	Season      int        `json:"season"`
	Total       int        `json:"total_teams"`
	Standings   []Standing `json:"standings"`
}

type statisticsResult struct {
	Summary         CompetitionSummary `json:"summary"`
	BiggestWins     []BiggestWin       `json:"biggest_wins,omitempty"`
	BestHomeRecord  *TeamStatistics    `json:"best_home_record,omitempty"`
	BestAwayRecord  *TeamStatistics    `json:"best_away_record,omitempty"`
	MostGoalsScorer *TeamStatistics    `json:"most_goals_scorer,omitempty"`
}

type bracketStage struct {
	Stage   string  `json:"stage"`
	Matches []Match `json:"matches"`
}

type bracketResult struct {
	Competition string         `json:"competition"`
	Season      int            `json:"season"`
	Total       int            `json:"total_matches"`
	Stages      []bracketStage `json:"stages"`
}

// Run serves newline-delimited JSON-RPC requests until stdin is closed. It
// never writes diagnostic output to stdout because stdout is the MCP channel.
func (s *MCPServer) Run(input io.Reader, output io.Writer) error {
	scanner := bufio.NewScanner(input)
	scanner.Buffer(make([]byte, 4096), 16*1024*1024)
	encoder := json.NewEncoder(output)
	var writeMu sync.Mutex
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		var request rpcRequest
		if err := json.Unmarshal([]byte(line), &request); err != nil {
			writeMu.Lock()
			err = encoder.Encode(rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &rpcError{Code: -32700, Message: "parse error"}})
			writeMu.Unlock()
			if err != nil {
				return err
			}
			continue
		}
		result, protocolError := s.HandleRequest(request)
		if isNotification(request) {
			continue
		}
		response := rpcResponse{JSONRPC: "2.0", ID: request.ID, Result: result, Error: protocolError}
		writeMu.Lock()
		err := encoder.Encode(response)
		writeMu.Unlock()
		if err != nil {
			return err
		}
	}
	return scanner.Err()
}

func isNotification(request rpcRequest) bool {
	return len(request.ID) == 0 || string(request.ID) == "null"
}

// HandleRequest is intentionally public to make protocol-level integration
// tests possible without starting a subprocess.
func (s *MCPServer) HandleRequest(request rpcRequest) (any, *rpcError) {
	switch request.Method {
	case "initialize":
		return s.initializeResult(request.Params), nil
	case "ping":
		return map[string]any{}, nil
	case "notifications/initialized", "notifications/cancelled", "notifications/progress":
		return map[string]any{}, nil
	case "tools/list":
		return map[string]any{"tools": s.toolDefinitions()}, nil
	case "tools/call":
		return s.handleToolCall(request.Params), nil
	case "resources/list":
		return map[string]any{"resources": s.resources()}, nil
	case "resources/read":
		return s.readResource(request.Params)
	case "prompts/list":
		return map[string]any{"prompts": s.prompts()}, nil
	case "prompts/get":
		return s.getPrompt(request.Params)
	default:
		return nil, &rpcError{Code: -32601, Message: "method not found: " + request.Method}
	}
}

func (s *MCPServer) initializeResult(raw json.RawMessage) map[string]any {
	var parameters struct {
		ProtocolVersion string `json:"protocolVersion"`
	}
	_ = json.Unmarshal(raw, &parameters)
	protocolVersion := parameters.ProtocolVersion
	if protocolVersion == "" {
		protocolVersion = "2025-03-26"
	}
	return map[string]any{
		"protocolVersion": protocolVersion,
		"capabilities": map[string]any{
			"tools":     map[string]any{"listChanged": false},
			"resources": map[string]any{"subscribe": false, "listChanged": false},
			"prompts":   map[string]any{"listChanged": false},
		},
		"serverInfo":   map[string]any{"name": serverName, "version": "1.0.0"},
		"instructions": "Query Brazilian soccer matches, calculated team/competition statistics, and FIFA player data. Team matching ignores accents and common state/formal-name variants.",
	}
}

func (s *MCPServer) handleToolCall(raw json.RawMessage) toolResult {
	var parameters struct {
		Name      string         `json:"name"`
		Arguments map[string]any `json:"arguments"`
	}
	if err := json.Unmarshal(raw, &parameters); err != nil {
		return toolFailure("Invalid tools/call parameters: " + err.Error())
	}
	if parameters.Arguments == nil {
		parameters.Arguments = map[string]any{}
	}
	return s.CallTool(parameters.Name, parameters.Arguments)
}

// CallTool lets embedding Go programs use the same behavior as MCP clients.
func (s *MCPServer) CallTool(name string, arguments map[string]any) toolResult {
	switch strings.ToLower(strings.TrimSpace(name)) {
	case "query_brazilian_soccer", "ask_brazilian_soccer", "query_soccer":
		return s.naturalLanguageQuery(arguments)
	case "search_matches", "find_matches", "get_matches":
		return s.searchMatches(arguments)
	case "team_statistics", "get_team_statistics", "get_team_stats", "team_stats":
		return s.teamStatistics(arguments)
	case "head_to_head", "compare_teams", "team_head_to_head":
		return s.headToHead(arguments)
	case "search_players", "find_players", "player_search":
		return s.searchPlayers(arguments)
	case "competition_standings", "get_standings", "standings":
		return s.competitionStandings(arguments)
	case "competition_statistics", "get_competition_stats", "aggregate_statistics":
		return s.competitionStatistics(arguments)
	case "team_competitions", "get_team_competitions":
		return s.teamCompetitions(arguments)
	case "compare_seasons", "season_comparison":
		return s.compareSeasons(arguments)
	case "competition_bracket", "libertadores_bracket", "get_bracket":
		return s.competitionBracket(arguments)
	case "list_data_sources", "data_sources":
		return s.listDataSources()
	default:
		return toolFailure("Unknown tool " + strconv.Quote(name) + ". Call tools/list to see supported tools.")
	}
}

func toolSuccess(text string, data any) toolResult {
	return toolResult{Content: []toolContent{{Type: "text", Text: text}}, StructuredContent: data}
}

func toolFailure(message string) toolResult {
	return toolResult{Content: []toolContent{{Type: "text", Text: message}}, IsError: true}
}

func stringArg(arguments map[string]any, name string) string {
	value, ok := arguments[name]
	if !ok || value == nil {
		return ""
	}
	switch typed := value.(type) {
	case string:
		return strings.TrimSpace(typed)
	case json.Number:
		return typed.String()
	case float64:
		return strconv.FormatFloat(typed, 'f', -1, 64)
	default:
		return strings.TrimSpace(fmt.Sprint(typed))
	}
}

func intArg(arguments map[string]any, name string) int {
	value, ok := arguments[name]
	if !ok || value == nil {
		return 0
	}
	switch typed := value.(type) {
	case float64:
		return int(typed)
	case float32:
		return int(typed)
	case int:
		return typed
	case int64:
		return int(typed)
	case json.Number:
		integer, _ := typed.Int64()
		return int(integer)
	default:
		integer, _ := parseInteger(fmt.Sprint(value))
		return integer
	}
}

func boolArg(arguments map[string]any, name string) bool {
	value, ok := arguments[name]
	if !ok || value == nil {
		return false
	}
	switch typed := value.(type) {
	case bool:
		return typed
	case string:
		parsed, _ := strconv.ParseBool(typed)
		return parsed
	default:
		return false
	}
}

func intSliceArg(arguments map[string]any, name string) []int {
	value, ok := arguments[name]
	if !ok || value == nil {
		return nil
	}
	values := make([]int, 0)
	switch typed := value.(type) {
	case []any:
		for _, item := range typed {
			if integer, ok := parseInteger(fmt.Sprint(item)); ok {
				values = append(values, integer)
			}
		}
	case []int:
		values = append(values, typed...)
	default:
		for _, item := range strings.Split(fmt.Sprint(value), ",") {
			if integer, ok := parseInteger(item); ok {
				values = append(values, integer)
			}
		}
	}
	return values
}

func limitArg(arguments map[string]any, fallback, maximum int) int {
	limit := intArg(arguments, "limit")
	if limit <= 0 {
		limit = fallback
	}
	if limit > maximum {
		return maximum
	}
	return limit
}

func (s *MCPServer) parseMatchFilter(arguments map[string]any) (MatchFilter, error) {
	start, err := parseDateBound(stringArg(arguments, "start_date"), false)
	if err != nil {
		return MatchFilter{}, err
	}
	end, err := parseDateBound(stringArg(arguments, "end_date"), true)
	if err != nil {
		return MatchFilter{}, err
	}
	order := normalizeText(stringArg(arguments, "order"))
	return MatchFilter{
		Team: stringArg(arguments, "team"), Opponent: stringArg(arguments, "opponent"),
		HomeTeam: stringArg(arguments, "home_team"), AwayTeam: stringArg(arguments, "away_team"),
		Competition: stringArg(arguments, "competition"), Season: intArg(arguments, "season"),
		StartDate: start, EndDate: end, Round: stringArg(arguments, "round"), Stage: stringArg(arguments, "stage"),
		Source: stringArg(arguments, "source"), DerbiesOnly: boolArg(arguments, "derbies_only"),
		FinalsOnly: boolArg(arguments, "finals_only"), IncludeDuplicates: boolArg(arguments, "include_duplicates"), Descending: order != "asc" && order != "ascending",
	}, nil
}

func (s *MCPServer) searchMatches(arguments map[string]any) toolResult {
	filter, err := s.parseMatchFilter(arguments)
	if err != nil {
		return toolFailure(err.Error())
	}
	all := s.data.SearchMatches(filter)
	limit := limitArg(arguments, 20, 100)
	shown := all
	if len(shown) > limit {
		shown = shown[:limit]
	}
	result := matchSearchResult{Total: len(all), Returned: len(shown), Matches: shown}
	s.rememberMatches(shown)
	return toolSuccess(formatMatches(all, shown), result)
}

func (s *MCPServer) teamStatistics(arguments map[string]any) toolResult {
	team := stringArg(arguments, "team")
	if team == "" {
		return toolFailure("team is required")
	}
	filter, err := s.parseMatchFilter(arguments)
	if err != nil {
		return toolFailure(err.Error())
	}
	filter.Limit = 0
	scope := stringArg(arguments, "scope")
	stats := s.data.TeamStatistics(team, filter, scope)
	if stats.Matches == 0 {
		return toolFailure("No scored matches found for " + team + " with the supplied filters.")
	}
	return toolSuccess(formatTeamStatistics(stats), stats)
}

func (s *MCPServer) headToHead(arguments map[string]any) toolResult {
	team := stringArg(arguments, "team")
	opponent := stringArg(arguments, "opponent")
	if team == "" || opponent == "" {
		return toolFailure("team and opponent are required")
	}
	filter, err := s.parseMatchFilter(arguments)
	if err != nil {
		return toolFailure(err.Error())
	}
	filter.Limit = 0
	record := s.data.HeadToHead(team, opponent, filter)
	if record.Matches == 0 {
		return toolFailure("No scored head-to-head matches found for " + team + " and " + opponent + ".")
	}
	matchFilter := filter
	matchFilter.Team, matchFilter.Opponent = team, opponent
	all := s.data.SearchMatches(matchFilter)
	limit := limitArg(arguments, 20, 100)
	shown := all
	if len(shown) > limit {
		shown = shown[:limit]
	}
	s.rememberMatches(shown)
	data := map[string]any{"record": record, "total_matches": len(all), "matches": shown}
	text := formatHeadToHead(record) + "\n\n" + formatMatches(all, shown)
	return toolSuccess(text, data)
}

func (s *MCPServer) searchPlayers(arguments map[string]any) toolResult {
	filter := PlayerFilter{
		Name: stringArg(arguments, "name"), Nationality: stringArg(arguments, "nationality"),
		Club: stringArg(arguments, "club"), Position: stringArg(arguments, "position"),
		MinOverall: intArg(arguments, "min_overall"), Limit: limitArg(arguments, 25, 100),
	}
	result := s.data.SearchPlayers(filter)
	return toolSuccess(formatPlayers(result), result)
}

func (s *MCPServer) competitionStandings(arguments map[string]any) toolResult {
	competition := stringArg(arguments, "competition")
	if competition == "" {
		competition = "Brasileirão Série A"
	}
	season := intArg(arguments, "season")
	standings, err := s.data.Standings(competition, season, stringArg(arguments, "source"))
	if err != nil {
		return toolFailure(err.Error())
	}
	limit := limitArg(arguments, len(standings), 100)
	shown := standings
	if len(shown) > limit {
		shown = shown[:limit]
	}
	result := standingsResult{Competition: normalizeCompetition(competition), Season: season, Total: len(standings), Standings: shown}
	return toolSuccess(formatStandings(result), result)
}

func (s *MCPServer) competitionStatistics(arguments map[string]any) toolResult {
	filter, err := s.parseMatchFilter(arguments)
	if err != nil {
		return toolFailure(err.Error())
	}
	summary, biggest := s.data.CompetitionStatistics(filter)
	if summary.Matches == 0 {
		return toolFailure("No scored matches found with the supplied filters.")
	}
	mode := normalizeText(stringArg(arguments, "stat"))
	result := statisticsResult{Summary: summary}
	if mode == "" || mode == "summary" || mode == "biggest wins" || mode == "biggest_wins" {
		limit := limitArg(arguments, 10, 100)
		if len(biggest) > limit {
			biggest = biggest[:limit]
		}
		result.BiggestWins = biggest
	}
	if mode == "best home record" || mode == "best_home_record" || mode == "best records" {
		if best, ok := s.data.BestTeamRecord(filter, "home"); ok {
			result.BestHomeRecord = &best
		}
	}
	if mode == "best away record" || mode == "best_away_record" || mode == "best records" {
		if best, ok := s.data.BestTeamRecord(filter, "away"); ok {
			result.BestAwayRecord = &best
		}
	}
	if mode == "most goals" || mode == "most_goals" || mode == "highest scoring" {
		if best, ok := s.data.MostGoalsScorer(filter); ok {
			result.MostGoalsScorer = &best
		}
	}
	return toolSuccess(formatCompetitionStatistics(result), result)
}

func (s *MCPServer) teamCompetitions(arguments map[string]any) toolResult {
	team := stringArg(arguments, "team")
	if team == "" {
		return toolFailure("team is required")
	}
	competitions := s.data.TeamCompetitions(team, stringArg(arguments, "source"))
	if len(competitions) == 0 {
		return toolFailure("No matches found for " + team + ".")
	}
	result := map[string]any{"team": s.data.DisplayTeam(team), "competitions": competitions}
	return toolSuccess(formatTeamCompetitions(s.data.DisplayTeam(team), competitions), result)
}

func (s *MCPServer) compareSeasons(arguments map[string]any) toolResult {
	seasons := intSliceArg(arguments, "seasons")
	if len(seasons) < 2 {
		return toolFailure("at least two seasons are required")
	}
	competition := stringArg(arguments, "competition")
	if competition == "" {
		competition = "Brasileirão Série A"
	}
	result := s.data.CompareSeasons(competition, seasons, stringArg(arguments, "source"))
	return toolSuccess(formatSeasonComparison(result), result)
}

func (s *MCPServer) competitionBracket(arguments map[string]any) toolResult {
	competition := normalizeCompetition(stringArg(arguments, "competition"))
	if competition == "" {
		competition = "Copa Libertadores"
	}
	if competition != "Copa Libertadores" {
		return toolFailure("bracket reconstruction is available for Copa Libertadores, whose source includes tournament stages")
	}
	season := intArg(arguments, "season")
	if season <= 0 {
		return toolFailure("season is required for a bracket")
	}
	matches := s.data.SearchMatches(MatchFilter{Competition: competition, Season: season, Source: stringArg(arguments, "source"), Descending: false})
	byStage := make(map[string][]Match)
	total := 0
	for _, match := range matches {
		stage := normalizeStage(match.Stage)
		if stage == "" || stage == "group stage" {
			continue
		}
		byStage[stage] = append(byStage[stage], match)
		total++
	}
	if total == 0 {
		return toolFailure(fmt.Sprintf("No Copa Libertadores knockout-stage matches found for %d.", season))
	}
	stageOrder := map[string]int{"round of 16": 1, "quarterfinals": 2, "semifinals": 3, "final": 4}
	stages := make([]bracketStage, 0, len(byStage))
	for stage, stageMatches := range byStage {
		sortMatches(stageMatches, false)
		stages = append(stages, bracketStage{Stage: stage, Matches: stageMatches})
	}
	sort.Slice(stages, func(i, j int) bool {
		left, right := stageOrder[stages[i].Stage], stageOrder[stages[j].Stage]
		if left != right {
			return left < right
		}
		return stages[i].Stage < stages[j].Stage
	})
	limit := limitArg(arguments, 50, 100)
	shown := 0
	for stageIndex := range stages {
		remaining := limit - shown
		if remaining <= 0 {
			stages[stageIndex].Matches = nil
			continue
		}
		if len(stages[stageIndex].Matches) > remaining {
			stages[stageIndex].Matches = stages[stageIndex].Matches[:remaining]
		}
		shown += len(stages[stageIndex].Matches)
	}
	visibleStages := stages[:0]
	for _, stage := range stages {
		if len(stage.Matches) > 0 {
			visibleStages = append(visibleStages, stage)
		}
	}
	result := bracketResult{Competition: competition, Season: season, Total: total, Stages: visibleStages}
	return toolSuccess(formatBracket(result, shown), result)
}

func (s *MCPServer) listDataSources() toolResult {
	return toolSuccess(formatDataSources(s.data.Sources), map[string]any{"sources": s.data.Sources, "match_records": len(s.data.Matches), "player_records": len(s.data.Players)})
}

func formatMatch(match Match) string {
	score := "score unavailable"
	if match.HasScore {
		score = fmt.Sprintf("%d-%d", match.HomeGoals, match.AwayGoals)
	}
	details := match.Competition
	if match.Round != "" {
		details += " round " + match.Round
	}
	if match.Stage != "" {
		details += " " + match.Stage
	}
	if match.Venue != "" {
		details += " at " + match.Venue
	}
	return fmt.Sprintf("%s: %s %s %s (%s; %s)", match.DateText, match.HomeTeam, score, match.AwayTeam, details, match.Source)
}

func formatMatches(all, shown []Match) string {
	if len(all) == 0 {
		return "No matches found."
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d match(es) found", len(all))
	if len(shown) < len(all) {
		fmt.Fprintf(&b, " (showing %d)", len(shown))
	}
	for _, match := range shown {
		fmt.Fprintf(&b, "\n- %s", formatMatch(match))
	}
	return b.String()
}

func formatTeamStatistics(stats TeamStatistics) string {
	scope := stats.Scope
	if scope == "all" {
		scope = "overall"
	}
	filters := ""
	if stats.Competition != "" {
		filters += " " + stats.Competition
	}
	if stats.Season != 0 {
		filters += fmt.Sprintf(" %d", stats.Season)
	}
	return fmt.Sprintf("%s %s record%s:\n- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d, Difference: %+d\n- Points: %d\n- Win rate: %.1f%%\n- Goals per match: %.1f",
		stats.Team, scope, filters, stats.Matches, stats.Wins, stats.Draws, stats.Losses, stats.GoalsFor, stats.GoalsAgainst, stats.GoalDifference, stats.Points, stats.WinRate, stats.GoalsPerMatch)
}

func formatHeadToHead(record HeadToHeadRecord) string {
	return fmt.Sprintf("%s vs %s head-to-head:\n- Matches: %d\n- %s wins: %d\n- %s wins: %d\n- Draws: %d\n- Goals: %s %d, %s %d\n- %s win rate: %.1f%%",
		record.Team, record.Opponent, record.Matches, record.Team, record.TeamWins, record.Opponent, record.OpponentWins,
		record.Draws, record.Team, record.TeamGoals, record.Opponent, record.OpponentGoals, record.Team, record.TeamWinRate)
}

func formatPlayers(result PlayerSearchResult) string {
	if result.Total == 0 {
		return "No players found."
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d player(s) found", result.Total)
	if len(result.Players) < result.Total {
		fmt.Fprintf(&b, " (showing %d)", len(result.Players))
	}
	for index, player := range result.Players {
		fmt.Fprintf(&b, "\n%d. %s — Overall %d, %s, %s, %s", index+1, player.Name, player.Overall, player.Position, player.Club, player.Nationality)
	}
	return b.String()
}

func formatStandings(result standingsResult) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s %d standings (calculated from %d teams):", result.Competition, result.Season, result.Total)
	for _, standing := range result.Standings {
		fmt.Fprintf(&b, "\n%d. %s — %d pts (%dW, %dD, %dL), GF %d, GA %d, GD %+d", standing.Rank, standing.Team, standing.Points, standing.Wins, standing.Draws, standing.Losses, standing.GoalsFor, standing.GoalsAgainst, standing.GoalDifference)
	}
	return b.String()
}

func formatCompetitionStatistics(result statisticsResult) string {
	summary := result.Summary
	var b strings.Builder
	label := summary.Competition
	if label == "" {
		label = "Selected matches"
	}
	if summary.Season != 0 {
		label += " " + strconv.Itoa(summary.Season)
	}
	fmt.Fprintf(&b, "%s statistics:\n- Matches: %d\n- Goals: %d (%.2f per match)\n- Home wins: %d (%.1f%%), Draws: %d (%.1f%%), Away wins: %d (%.1f%%)", label, summary.Matches, summary.TotalGoals, summary.AverageGoals, summary.HomeWins, summary.HomeWinRate, summary.Draws, summary.DrawRate, summary.AwayWins, summary.AwayWinRate)
	if result.BestHomeRecord != nil {
		fmt.Fprintf(&b, "\n- Best home record: %s (%dW-%dD-%dL, %.1f%% wins)", result.BestHomeRecord.Team, result.BestHomeRecord.Wins, result.BestHomeRecord.Draws, result.BestHomeRecord.Losses, result.BestHomeRecord.WinRate)
	}
	if result.BestAwayRecord != nil {
		fmt.Fprintf(&b, "\n- Best away record: %s (%dW-%dD-%dL, %.1f%% wins)", result.BestAwayRecord.Team, result.BestAwayRecord.Wins, result.BestAwayRecord.Draws, result.BestAwayRecord.Losses, result.BestAwayRecord.WinRate)
	}
	if result.MostGoalsScorer != nil {
		fmt.Fprintf(&b, "\n- Most goals: %s (%d in %d matches, %.1f per match)", result.MostGoalsScorer.Team, result.MostGoalsScorer.GoalsFor, result.MostGoalsScorer.Matches, result.MostGoalsScorer.GoalsPerMatch)
	}
	if len(result.BiggestWins) > 0 {
		b.WriteString("\nBiggest wins:")
		for index, win := range result.BiggestWins {
			fmt.Fprintf(&b, "\n%d. %s (%s, +%d)", index+1, formatMatch(win.Match), win.Winner, win.Margin)
		}
	}
	return b.String()
}

func formatTeamCompetitions(team string, competitions []TeamCompetition) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s appears in %d competition(s):", team, len(competitions))
	for _, competition := range competitions {
		years := ""
		if competition.FirstSeason != 0 {
			years = fmt.Sprintf(", %d–%d", competition.FirstSeason, competition.LastSeason)
		}
		fmt.Fprintf(&b, "\n- %s: %d matches%s", competition.Competition, competition.Matches, years)
	}
	return b.String()
}

func formatSeasonComparison(result SeasonComparison) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s season comparison:", result.Competition)
	for _, summary := range result.Seasons {
		fmt.Fprintf(&b, "\n- %d: %d matches, %d goals, %.2f goals/match, home-win rate %.1f%%", summary.Season, summary.Matches, summary.TotalGoals, summary.AverageGoals, summary.HomeWinRate)
	}
	return b.String()
}

func formatBracket(result bracketResult, shown int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s %d knockout bracket (match results; the source does not provide aggregate tie metadata)", result.Competition, result.Season)
	if shown < result.Total {
		fmt.Fprintf(&b, " — showing %d of %d matches", shown, result.Total)
	}
	for _, stage := range result.Stages {
		label := stage.Stage
		if label != "" {
			label = strings.ToUpper(label[:1]) + label[1:]
		}
		fmt.Fprintf(&b, "\n%s:", label)
		for _, match := range stage.Matches {
			fmt.Fprintf(&b, "\n- %s", formatMatch(match))
		}
	}
	return b.String()
}

func formatDataSources(sources []DataSource) string {
	var b strings.Builder
	b.WriteString("Loaded datasets:")
	for _, source := range sources {
		fmt.Fprintf(&b, "\n- %s: %d %s records — %s", source.File, source.RecordCount, source.Kind, source.Description)
	}
	return b.String()
}

var yearExpression = regexp.MustCompile(`\b(?:19|20)\d{2}\b`)
var dateRangeExpression = regexp.MustCompile(`(?i)(?:between|from|entre|de)\s+(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{4})\s+(?:and|to|e|a)\s+(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{4})`)

func yearsInQuestion(question string) []int {
	values := yearExpression.FindAllString(question, -1)
	years := make([]int, 0, len(values))
	seen := make(map[int]bool)
	for _, value := range values {
		year, _ := strconv.Atoi(value)
		if !seen[year] {
			seen[year] = true
			years = append(years, year)
		}
	}
	return years
}

func dateRangeInQuestion(question string) (string, string) {
	parts := dateRangeExpression.FindStringSubmatch(question)
	if len(parts) != 3 {
		return "", ""
	}
	return parts[1], parts[2]
}

func inferCompetition(question string) string {
	q := normalizeText(question)
	switch {
	case strings.Contains(q, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(q, "copa do brasil") || strings.Contains(q, "brazilian cup"):
		return "Copa do Brasil"
	case strings.Contains(q, "brasileirao") || strings.Contains(q, "serie a") || strings.Contains(q, "seriea"):
		return "Brasileirão Série A"
	default:
		return ""
	}
}

func hasAny(question string, phrases ...string) bool {
	for _, phrase := range phrases {
		if strings.Contains(question, phrase) {
			return true
		}
	}
	return false
}

type detectedTeam struct {
	key   string
	index int
}

func (s *MCPServer) teamsInQuestion(question string) []string {
	normalized := " " + normalizeText(question) + " "
	// Do not mistake the club Brasil de Pelotas for the word in the competition
	// name "Copa do Brasil".
	normalized = strings.ReplaceAll(normalized, " copa do brasil ", " ")
	positions := make(map[string]int)
	for key := range s.data.teamName {
		if key == "" {
			continue
		}
		phrase := " " + key + " "
		if index := strings.Index(normalized, phrase); index >= 0 {
			positions[key] = index
		}
	}
	for alias, key := range teamAliases {
		phrase := " " + alias + " "
		if index := strings.Index(normalized, phrase); index >= 0 {
			if previous, exists := positions[key]; !exists || index < previous {
				positions[key] = index
			}
		}
	}
	found := make([]detectedTeam, 0, len(positions))
	for key, index := range positions {
		found = append(found, detectedTeam{key: key, index: index})
	}
	sort.Slice(found, func(i, j int) bool {
		if found[i].index != found[j].index {
			return found[i].index < found[j].index
		}
		return found[i].key < found[j].key
	})
	result := make([]string, 0, len(found))
	for _, team := range found {
		result = append(result, team.key)
	}
	return result
}

func playerNameFromQuestion(question string) string {
	trimmed := strings.TrimSpace(question)
	lower := normalizeText(trimmed)
	prefixes := []string{"who is ", "quem e ", "tell me about ", "player ", "jogador "}
	for _, prefix := range prefixes {
		if strings.HasPrefix(lower, prefix) {
			// Work with the original text after locating the same number of words.
			words := strings.Fields(trimmed)
			prefixWords := len(strings.Fields(prefix))
			if len(words) > prefixWords {
				return strings.Trim(strings.Join(words[prefixWords:], " "), "?.! ")
			}
		}
	}
	return ""
}

// naturalLanguageQuery routes the sample question styles in the specification
// to deterministic data operations. It is a convenience tool; callers who
// already know the desired operation should prefer the focused tools.
func (s *MCPServer) naturalLanguageQuery(arguments map[string]any) toolResult {
	question := stringArg(arguments, "question")
	if question == "" {
		question = stringArg(arguments, "query")
	}
	if question == "" {
		return toolFailure("question is required")
	}
	q := normalizeText(question)
	years := yearsInQuestion(question)
	competition := inferCompetition(question)
	teams := s.teamsInQuestion(question)
	limit := limitArg(arguments, 20, 100)
	startDate, endDate := dateRangeInQuestion(question)
	if len(teams) == 0 && competition == "" && len(years) == 0 && hasAny(q, "what was the score", "what was score", "the score") {
		if match, ok := s.mostRecentRememberedMatch(); ok {
			return toolSuccess("The most recent match returned was "+formatMatch(match), match)
		}
		return toolFailure("Please name the teams or date for the score; no prior match result is available in this server session.")
	}

	// Player lookups take precedence for a direct "Who is ...?" or an explicit
	// player request. Club/nationality/position filters are inferred where safe.
	playerQuestion := hasAny(q, "player", "players", "jogador", "jogadores", "who is", "quem e", "highest rated", "top rated", "top brazilian", "forward", "forwards", "striker", "strikers", "goalkeeper", "midfielder", "defender")
	if playerQuestion && !hasAny(q, "record", "standings", "match", "matches") {
		playerArgs := map[string]any{"limit": limit}
		if name := playerNameFromQuestion(question); name != "" {
			playerArgs["name"] = name
		}
		if hasAny(q, "brazilian", "brazilian players", "brasileiro", "brasileira") {
			playerArgs["nationality"] = "Brazil"
		}
		if len(teams) > 0 {
			playerArgs["club"] = teams[0]
		}
		if hasAny(q, "forward", "forwards", "striker", "strikers", "atacante") {
			playerArgs["position"] = "forward"
		}
		return s.searchPlayers(playerArgs)
	}

	if len(teams) >= 2 && hasAny(q, "head to head", "head-to-head", "compare", "versus", " vs ") {
		arguments := map[string]any{"team": teams[0], "opponent": teams[1], "limit": limit, "competition": competition}
		if len(years) == 1 {
			arguments["season"] = years[0]
		}
		return s.headToHead(arguments)
	}

	if len(years) >= 2 && hasAny(q, "compare", "comparison", "trend", "trends") && len(teams) == 0 {
		return s.compareSeasons(map[string]any{"competition": competition, "seasons": years})
	}

	if hasAny(q, "standings", "table", "who won", "champion", "winner", "relegated", "relegation") {
		if len(years) == 0 {
			return toolFailure("Please include a season for a standings, champion, or relegation question.")
		}
		standings, err := s.data.Standings(firstNonEmpty(competition, "Brasileirão Série A"), years[0], "")
		if err != nil {
			return toolFailure(err.Error())
		}
		if hasAny(q, "who won", "champion", "winner") {
			champion := standings[0]
			text := fmt.Sprintf("%s won the %d %s in the calculated table with %d points (%dW, %dD, %dL).", champion.Team, years[0], firstNonEmpty(competition, "Brasileirão Série A"), champion.Points, champion.Wins, champion.Draws, champion.Losses)
			return toolSuccess(text, map[string]any{"champion": champion, "competition": firstNonEmpty(competition, "Brasileirão Série A"), "season": years[0]})
		}
		if hasAny(q, "relegated", "relegation") {
			count := 4
			if len(standings) < count {
				count = len(standings)
			}
			relegated := standings[len(standings)-count:]
			text := fmt.Sprintf("Bottom %d in the calculated %d %s table (the usual relegation places):", count, years[0], firstNonEmpty(competition, "Brasileirão Série A"))
			for _, standing := range relegated {
				text += fmt.Sprintf("\n- %d. %s — %d pts", standing.Rank, standing.Team, standing.Points)
			}
			return toolSuccess(text, map[string]any{"relegation_candidates": relegated, "competition": firstNonEmpty(competition, "Brasileirão Série A"), "season": years[0]})
		}
		shown := standings
		if len(shown) > limit {
			shown = shown[:limit]
		}
		result := standingsResult{Competition: firstNonEmpty(competition, "Brasileirão Série A"), Season: years[0], Total: len(standings), Standings: shown}
		return toolSuccess(formatStandings(result), result)
	}

	if hasAny(q, "bracket") && competition == "Copa Libertadores" {
		if len(years) == 0 {
			return toolFailure("Please include a season for a Copa Libertadores bracket.")
		}
		bracketLimit := intArg(arguments, "limit")
		if bracketLimit <= 0 {
			bracketLimit = 50
		}
		return s.competitionBracket(map[string]any{"competition": competition, "season": years[0], "limit": bracketLimit})
	}

	if len(teams) > 0 && hasAny(q, "what competitions", "which competitions", "competitions has", "competitions did") {
		return s.teamCompetitions(map[string]any{"team": teams[0]})
	}

	if len(teams) > 0 && hasAny(q, "record", "win rate", "goals scored", "goals conceded", "performance") {
		scope := "all"
		if hasAny(q, "home record", "at home") {
			scope = "home"
		} else if hasAny(q, "away record", "on the road") {
			scope = "away"
		}
		statsCompetition := competition
		// A season-specific record without a competition is ordinarily asking for
		// a league record (as in the specification's Corinthians example), not a
		// mix of league, cup, and continental fixtures.
		if statsCompetition == "" && len(years) > 0 {
			statsCompetition = "Brasileirão Série A"
		}
		statsArgs := map[string]any{"team": teams[0], "competition": statsCompetition, "scope": scope}
		if len(years) > 0 {
			statsArgs["season"] = years[0]
		}
		if startDate != "" {
			statsArgs["start_date"], statsArgs["end_date"] = startDate, endDate
		}
		return s.teamStatistics(statsArgs)
	}

	if hasAny(q, "top scorer", "top scorers", "golden boot") {
		return toolFailure("The supplied datasets contain team match scores but no player-level goal events, so player top scorers cannot be calculated reliably.")
	}

	if hasAny(q, "average goals", "goals per match", "biggest win", "biggest victory", "best away record", "best home record", "most goals", "scored the most", "highest scoring") {
		statsArgs := map[string]any{"competition": competition, "limit": limit}
		if len(years) > 0 {
			statsArgs["season"] = years[0]
		}
		if startDate != "" {
			statsArgs["start_date"], statsArgs["end_date"] = startDate, endDate
		}
		if hasAny(q, "best away record") {
			statsArgs["stat"] = "best_away_record"
		} else if hasAny(q, "best home record") {
			statsArgs["stat"] = "best_home_record"
		} else if hasAny(q, "biggest") {
			statsArgs["stat"] = "biggest_wins"
		} else if hasAny(q, "most goals", "scored the most", "highest scoring") {
			statsArgs["stat"] = "most_goals"
		}
		return s.competitionStatistics(statsArgs)
	}

	matchArgs := map[string]any{"competition": competition, "limit": limit}
	if len(teams) > 0 {
		matchArgs["team"] = teams[0]
	}
	if len(teams) > 1 {
		matchArgs["opponent"] = teams[1]
	}
	if len(years) > 0 {
		matchArgs["season"] = years[0]
	}
	if startDate != "" {
		matchArgs["start_date"], matchArgs["end_date"] = startDate, endDate
	}
	if hasAny(q, "derby", "derbies", "classico", "clasico") {
		matchArgs["derbies_only"] = true
	}
	if hasAny(q, "final", "finals") {
		matchArgs["finals_only"] = true
	}
	if hasAny(q, "last play", "last played", "most recent") {
		matchArgs["limit"] = 1
	}
	return s.searchMatches(matchArgs)
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}

func (s *MCPServer) resources() []map[string]any {
	resources := []map[string]any{{
		"uri": "brazilian-soccer://overview", "name": "Brazilian soccer dataset overview", "mimeType": "application/json",
		"description": "Loaded dataset inventory and query guidance.",
	}}
	for _, source := range s.data.Sources {
		resources = append(resources, map[string]any{
			"uri": "brazilian-soccer://source/" + source.File, "name": source.File, "mimeType": "application/json",
			"description": source.Description,
		})
	}
	return resources
}

func (s *MCPServer) readResource(raw json.RawMessage) (any, *rpcError) {
	var arguments struct {
		URI string `json:"uri"`
	}
	if err := json.Unmarshal(raw, &arguments); err != nil {
		return nil, &rpcError{Code: -32602, Message: "invalid resources/read parameters"}
	}
	if arguments.URI == "brazilian-soccer://overview" {
		payload := map[string]any{"sources": s.data.Sources, "match_records": len(s.data.Matches), "player_records": len(s.data.Players), "hint": "Use tools/list for query operations; source resources describe loaded files rather than streaming full CSV contents."}
		encoded, _ := json.Marshal(payload)
		return map[string]any{"contents": []map[string]any{{"uri": arguments.URI, "mimeType": "application/json", "text": string(encoded)}}}, nil
	}
	const prefix = "brazilian-soccer://source/"
	if strings.HasPrefix(arguments.URI, prefix) {
		file := strings.TrimPrefix(arguments.URI, prefix)
		for _, source := range s.data.Sources {
			if source.File == file {
				encoded, _ := json.Marshal(source)
				return map[string]any{"contents": []map[string]any{{"uri": arguments.URI, "mimeType": "application/json", "text": string(encoded)}}}, nil
			}
		}
	}
	return nil, &rpcError{Code: -32002, Message: "resource not found"}
}

func (s *MCPServer) prompts() []map[string]any {
	return []map[string]any{{
		"name": "brazilian_soccer_question", "description": "Ask a natural-language question about the loaded Brazilian soccer data.",
		"arguments": []map[string]any{{"name": "question", "description": "For example: What was Flamengo's home record in 2022?", "required": true}},
	}}
}

func (s *MCPServer) getPrompt(raw json.RawMessage) (any, *rpcError) {
	var arguments struct {
		Name      string         `json:"name"`
		Arguments map[string]any `json:"arguments"`
	}
	if err := json.Unmarshal(raw, &arguments); err != nil {
		return nil, &rpcError{Code: -32602, Message: "invalid prompts/get parameters"}
	}
	if arguments.Name != "brazilian_soccer_question" {
		return nil, &rpcError{Code: -32002, Message: "prompt not found"}
	}
	question := stringArg(arguments.Arguments, "question")
	if question == "" {
		return nil, &rpcError{Code: -32602, Message: "question is required"}
	}
	return map[string]any{"description": "Brazilian soccer data question", "messages": []map[string]any{{"role": "user", "content": map[string]any{"type": "text", "text": question}}}}, nil
}

func schema(properties map[string]any, required ...string) map[string]any {
	result := map[string]any{"type": "object", "properties": properties, "additionalProperties": false}
	if len(required) > 0 {
		result["required"] = required
	}
	return result
}

func property(description, valueType string) map[string]any {
	return map[string]any{"type": valueType, "description": description}
}

func (s *MCPServer) toolDefinitions() []map[string]any {
	matchProperties := map[string]any{
		"team":      property("Team in either home or away position; accents and state suffixes are normalized.", "string"),
		"opponent":  property("Second team for an unordered head-to-head match search.", "string"),
		"home_team": property("Require this home team.", "string"), "away_team": property("Require this away team.", "string"),
		"competition": property("Brasileirão, Copa do Brasil, Copa Libertadores, Série B, or Série C.", "string"),
		"season":      property("Four-digit season year.", "integer"), "start_date": property("Inclusive YYYY-MM-DD, DD/MM/YYYY, or year.", "string"),
		"end_date": property("Inclusive YYYY-MM-DD, DD/MM/YYYY, or year.", "string"), "round": property("Round value or fragment.", "string"),
		"stage": property("Tournament stage value or fragment.", "string"), "source": property("Optional source file or source alias (historical, extended).", "string"),
		"derbies_only": property("Only return recognized traditional derbies.", "boolean"), "finals_only": property("Only return final matches (stage-labelled finals or the terminal Copa do Brasil round).", "boolean"),
		"include_duplicates": property("Keep duplicate physical matches from different source files.", "boolean"),
		"order":              property("Date order: desc (default) or asc.", "string"), "limit": property("Maximum returned rows, 1–100 (default 20).", "integer"),
	}
	return []map[string]any{
		{
			"name": "query_brazilian_soccer", "description": "Answer a natural-language Brazilian soccer question by routing it to match, player, standings, or statistics data.",
			"inputSchema": schema(map[string]any{"question": property("Natural-language question in English or Portuguese.", "string"), "limit": property("Maximum listed rows, 1–100.", "integer")}, "question"),
		},
		{
			"name": "search_matches", "description": "Find match results across all supplied match datasets. Duplicate physical matches are collapsed by default.",
			"inputSchema": schema(matchProperties),
		},
		{
			"name": "team_statistics", "description": "Calculate wins, draws, losses, goals, points, and win rate for one team.",
			"inputSchema": schema(map[string]any{"team": property("Team name.", "string"), "competition": property("Optional competition.", "string"), "season": property("Optional season.", "integer"), "start_date": property("Inclusive YYYY-MM-DD, DD/MM/YYYY, or year.", "string"), "end_date": property("Inclusive YYYY-MM-DD, DD/MM/YYYY, or year.", "string"), "scope": property("all (default), home, or away.", "string"), "source": property("Optional source file/alias.", "string")}, "team"),
		},
		{
			"name": "head_to_head", "description": "Compare two teams' results, goals, and recent meetings.",
			"inputSchema": schema(map[string]any{"team": property("First team.", "string"), "opponent": property("Second team.", "string"), "competition": property("Optional competition.", "string"), "season": property("Optional season.", "integer"), "start_date": property("Inclusive YYYY-MM-DD, DD/MM/YYYY, or year.", "string"), "end_date": property("Inclusive YYYY-MM-DD, DD/MM/YYYY, or year.", "string"), "source": property("Optional source file/alias.", "string"), "limit": property("Maximum listed meetings, 1–100.", "integer")}, "team", "opponent"),
		},
		{
			"name": "search_players", "description": "Search FIFA players by name, nationality, club, position, and overall rating.",
			"inputSchema": schema(map[string]any{"name": property("Player name fragment.", "string"), "nationality": property("Nationality; Brazilian maps to Brazil.", "string"), "club": property("Club-name fragment.", "string"), "position": property("Position code (ST, GK) or group (forward, midfielder, defender).", "string"), "min_overall": property("Minimum FIFA overall rating.", "integer"), "limit": property("Maximum returned players, 1–100 (default 25).", "integer")}),
		},
		{
			"name": "competition_standings", "description": "Calculate a league table from scored match results for one competition and season.",
			"inputSchema": schema(map[string]any{"competition": property("Competition; defaults to Brasileirão Série A.", "string"), "season": property("Season year.", "integer"), "source": property("Optional source file/alias.", "string"), "limit": property("Number of table rows.", "integer")}, "season"),
		},
		{
			"name": "competition_statistics", "description": "Calculate goals-per-match, result rates, biggest wins, most goals, and best home/away records.",
			"inputSchema": schema(map[string]any{"competition": property("Optional competition.", "string"), "season": property("Optional season.", "integer"), "start_date": property("Inclusive YYYY-MM-DD, DD/MM/YYYY, or year.", "string"), "end_date": property("Inclusive YYYY-MM-DD, DD/MM/YYYY, or year.", "string"), "source": property("Optional source file/alias.", "string"), "stat": property("summary, biggest_wins, most_goals, best_home_record, best_away_record, or best_records.", "string"), "limit": property("Maximum biggest-win rows.", "integer")}),
		},
		{
			"name": "team_competitions", "description": "List competitions and season ranges in which a team appears across the datasets.",
			"inputSchema": schema(map[string]any{"team": property("Team name.", "string"), "source": property("Optional source file/alias.", "string")}, "team"),
		},
		{
			"name": "compare_seasons", "description": "Compare aggregate match and goal statistics across two or more seasons.",
			"inputSchema": schema(map[string]any{"competition": property("Competition; defaults to Brasileirão Série A.", "string"), "seasons": map[string]any{"type": "array", "items": map[string]any{"type": "integer"}, "description": "At least two season years."}, "source": property("Optional source file/alias.", "string")}, "seasons"),
		},
		{
			"name": "competition_bracket", "description": "Group Copa Libertadores knockout match results by round for a season. The source does not contain aggregate tie metadata.",
			"inputSchema": schema(map[string]any{"competition": property("Copa Libertadores (default).", "string"), "season": property("Season year.", "integer"), "source": property("Optional source file/alias.", "string"), "limit": property("Maximum listed knockout matches, 1–100 (default 50).", "integer")}, "season"),
		},
		{
			"name": "list_data_sources", "description": "List all six loaded CSV datasets and record counts.",
			"inputSchema": schema(map[string]any{}),
		},
	}
}
