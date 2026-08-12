package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"strconv"
	"strings"
	"time"
)

const serverVersion = "1.0.0"

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
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
	Content    []toolContent `json:"content"`
	Structured any           `json:"structuredContent,omitempty"`
	IsError    bool          `json:"isError,omitempty"`
}
type toolDefinition struct {
	Name, Description string
	InputSchema       map[string]any `json:"inputSchema"`
}

type MCPServer struct{ db *Database }

func NewMCPServer(db *Database) *MCPServer { return &MCPServer{db: db} }

func (s *MCPServer) Serve(r io.Reader, w io.Writer) error {
	decoder, encoder := json.NewDecoder(bufio.NewReader(r)), json.NewEncoder(w)
	for {
		var req rpcRequest
		if err := decoder.Decode(&req); err != nil {
			if err == io.EOF {
				return nil
			}
			return fmt.Errorf("decode JSON-RPC request: %w", err)
		}
		if len(req.ID) == 0 {
			continue
		}
		resp := s.handle(req)
		if err := encoder.Encode(resp); err != nil {
			return fmt.Errorf("encode JSON-RPC response: %w", err)
		}
	}
}

func (s *MCPServer) handle(req rpcRequest) rpcResponse {
	resp := rpcResponse{JSONRPC: "2.0", ID: req.ID}
	switch req.Method {
	case "initialize":
		resp.Result = map[string]any{"protocolVersion": "2025-06-18", "capabilities": map[string]any{"tools": map[string]any{"listChanged": false}, "resources": map[string]any{"subscribe": false, "listChanged": false}}, "serverInfo": map[string]string{"name": "brazilian-soccer-mcp", "version": serverVersion}, "instructions": "Use ask for natural-language soccer questions or the specialized tools for exact filters. Standings and statistics are calculated only from the provided datasets."}
	case "ping":
		resp.Result = map[string]any{}
	case "tools/list":
		resp.Result = map[string]any{"tools": toolDefinitions()}
	case "tools/call":
		var params struct {
			Name      string         `json:"name"`
			Arguments map[string]any `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &params); err != nil || params.Name == "" {
			resp.Error = &rpcError{-32602, "invalid tools/call parameters", nil}
			break
		}
		result, err := s.callTool(params.Name, params.Arguments)
		if err != nil {
			result = toolResult{Content: []toolContent{{"text", err.Error()}}, IsError: true}
		}
		resp.Result = result
	case "resources/list":
		resp.Result = map[string]any{"resources": []map[string]any{{"uri": "soccer://dataset/summary", "name": "Brazilian soccer dataset summary", "description": "Counts and coverage for the loaded Kaggle CSV files", "mimeType": "application/json"}}}
	case "resources/read":
		var params struct {
			URI string `json:"uri"`
		}
		_ = json.Unmarshal(req.Params, &params)
		if params.URI != "soccer://dataset/summary" {
			resp.Error = &rpcError{-32602, "unknown resource URI", params.URI}
			break
		}
		payload, _ := json.MarshalIndent(map[string]any{"matches": len(s.db.Matches), "players": len(s.db.Players), "sources": 6, "note": "Counts are loaded rows; cross-source duplicate matches are removed from query results."}, "", "  ")
		resp.Result = map[string]any{"contents": []map[string]string{{"uri": params.URI, "mimeType": "application/json", "text": string(payload)}}}
	default:
		resp.Error = &rpcError{-32601, "method not found", req.Method}
	}
	return resp
}

func objectSchema(properties map[string]any, required ...string) map[string]any {
	s := map[string]any{"type": "object", "properties": properties, "additionalProperties": false}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

func prop(t, description string) map[string]any {
	return map[string]any{"type": t, "description": description}
}

func commonMatchProperties() map[string]any {
	return map[string]any{
		"team":     prop("string", "Team in either home or away position; accents and state suffixes are optional"),
		"opponent": prop("string", "Optional opposing team"), "competition": prop("string", "Brasileirão/Serie A, Copa do Brasil, Libertadores, Serie B, or Serie C"),
		"season": prop("integer", "Four-digit season"), "start_date": prop("string", "Inclusive date in YYYY-MM-DD format"), "end_date": prop("string", "Inclusive date in YYYY-MM-DD format"),
		"stage": prop("string", "Round or stage text, for example final or group stage"), "limit": prop("integer", "Maximum records to return (default 100)"),
	}
}

func toolDefinitions() []toolDefinition {
	matchProps := commonMatchProperties()
	return []toolDefinition{
		{"ask", "Answer a natural-language question about matches, teams, players, competitions, standings, derbies, or aggregate statistics in the provided Brazilian soccer datasets.", objectSchema(map[string]any{"question": prop("string", "Natural-language question")}, "question")},
		{"search_matches", "Find matches across all five match CSV files by team, opponent, date range, competition, season, stage, and home/away role.", objectSchema(matchProps)},
		{"team_statistics", "Calculate a team's wins, draws, losses, goals, points, and home/away record using matching games.", objectSchema(map[string]any{"team": matchProps["team"], "competition": matchProps["competition"], "season": matchProps["season"], "home_only": prop("boolean", "Only home matches"), "away_only": prop("boolean", "Only away matches")}, "team")},
		{"head_to_head", "Compare two teams and return meetings, win/draw counts, and goals.", objectSchema(map[string]any{"team1": prop("string", "First team"), "team2": prop("string", "Second team"), "competition": matchProps["competition"], "season": matchProps["season"], "limit": matchProps["limit"]}, "team1", "team2")},
		{"search_players", "Search FIFA players by partial name, nationality, club, position group, and minimum rating; results are ordered by overall rating.", objectSchema(map[string]any{"name": prop("string", "Partial player name"), "nationality": prop("string", "Nationality such as Brazil"), "club": prop("string", "Partial club name"), "position": prop("string", "Exact code or forward/midfielder/defender/goalkeeper"), "min_overall": prop("integer", "Minimum FIFA overall rating"), "limit": prop("integer", "Maximum players (default 100)")})},
		{"standings", "Calculate a competition table from match results using points, wins, goal difference, and goals scored as tie-breakers.", objectSchema(map[string]any{"competition": matchProps["competition"], "season": matchProps["season"], "limit": prop("integer", "Maximum table rows (default all)")}, "competition", "season")},
		{"competition_statistics", "Calculate goals per match and home-win, away-win, and draw rates.", objectSchema(map[string]any{"competition": matchProps["competition"], "season": matchProps["season"]})},
		{"biggest_wins", "Return matches ordered by largest goal margin.", objectSchema(map[string]any{"competition": matchProps["competition"], "season": matchProps["season"], "team": matchProps["team"], "limit": prop("integer", "Maximum matches (default 10)")})},
		{"team_competitions", "List every competition in which a team appears across the match datasets.", objectSchema(map[string]any{"team": matchProps["team"]}, "team")},
		{"club_overview", "Cross-file view combining a club's match statistics and competitions with FIFA players whose club name matches.", objectSchema(map[string]any{"team": matchProps["team"], "competition": matchProps["competition"], "season": matchProps["season"], "player_limit": prop("integer", "Maximum matching FIFA players (default 20)")}, "team")},
	}
}

func (s *MCPServer) callTool(name string, a map[string]any) (toolResult, error) {
	switch name {
	case "ask":
		q := stringArg(a, "question")
		if q == "" {
			return toolResult{}, fmt.Errorf("question is required")
		}
		answer := s.db.Answer(q)
		return result(answer, map[string]any{"question": q, "answer": answer}), nil
	case "search_matches":
		f, err := matchFilterFromArgs(a)
		if err != nil {
			return toolResult{}, err
		}
		matches := s.db.SearchMatches(f)
		return result(formatMatches("Matching matches", matches, f.Limit), map[string]any{"count": len(matches), "matches": matches}), nil
	case "team_statistics":
		team := stringArg(a, "team")
		if team == "" {
			return toolResult{}, fmt.Errorf("team is required")
		}
		stats := s.db.TeamStatistics(team, MatchFilter{Competition: stringArg(a, "competition"), Season: intArg(a, "season"), HomeOnly: boolArg(a, "home_only"), AwayOnly: boolArg(a, "away_only")})
		return result(formatTeamStats(stats), stats), nil
	case "head_to_head":
		t1, t2 := stringArg(a, "team1"), stringArg(a, "team2")
		if t1 == "" || t2 == "" {
			return toolResult{}, fmt.Errorf("team1 and team2 are required")
		}
		h := s.db.HeadToHead(t1, t2, MatchFilter{Competition: stringArg(a, "competition"), Season: intArg(a, "season"), Limit: boundedLimit(a, 100, 500)})
		return result(formatHeadToHead(h, boundedLimit(a, 20, 100)), h), nil
	case "search_players":
		f := PlayerFilter{Name: stringArg(a, "name"), Nationality: stringArg(a, "nationality"), Club: stringArg(a, "club"), Position: stringArg(a, "position"), MinOverall: intArg(a, "min_overall"), Limit: boundedLimit(a, 100, 1000)}
		players := s.db.SearchPlayers(f)
		return result(formatPlayers("Matching players", players, f.Limit), map[string]any{"count": len(players), "players": players}), nil
	case "standings":
		competition := stringArg(a, "competition")
		season := intArg(a, "season")
		if competition == "" || season == 0 {
			return toolResult{}, fmt.Errorf("competition and season are required")
		}
		table := s.db.Standings(competition, season)
		limit := boundedLimit(a, len(table), len(table))
		if len(table) > limit {
			table = table[:limit]
		}
		return result(formatStandings(fmt.Sprintf("%d %s standings", season, displayCompetition(competition)), table, limit), map[string]any{"competition": competition, "season": season, "standings": table}), nil
	case "competition_statistics":
		stats := s.db.AggregateStats(MatchFilter{Competition: stringArg(a, "competition"), Season: intArg(a, "season")})
		return result(formatCompetitionStats(stats), stats), nil
	case "biggest_wins":
		limit := boundedLimit(a, 10, 100)
		matches := s.db.BiggestWins(MatchFilter{Competition: stringArg(a, "competition"), Season: intArg(a, "season"), Team: stringArg(a, "team")}, limit)
		return result(formatMatches("Biggest victories", matches, limit), map[string]any{"count": len(matches), "matches": matches}), nil
	case "team_competitions":
		team := stringArg(a, "team")
		if team == "" {
			return toolResult{}, fmt.Errorf("team is required")
		}
		competitions := s.db.CompetitionsForTeam(team)
		return result(fmt.Sprintf("%s appears in: %s.", cleanTeamName(team), strings.Join(competitions, ", ")), map[string]any{"team": team, "competitions": competitions}), nil
	case "club_overview":
		team := stringArg(a, "team")
		if team == "" {
			return toolResult{}, fmt.Errorf("team is required")
		}
		stats := s.db.TeamStatistics(team, MatchFilter{Competition: stringArg(a, "competition"), Season: intArg(a, "season")})
		playerLimit := intArg(a, "player_limit")
		if playerLimit <= 0 {
			playerLimit = 20
		}
		if playerLimit > 100 {
			playerLimit = 100
		}
		players := s.db.SearchPlayers(PlayerFilter{Club: team, Limit: playerLimit})
		competitions := s.db.CompetitionsForTeam(team)
		text := formatTeamStats(stats) + "\n\n" + formatPlayers("FIFA players at "+displayTeam(team), players, playerLimit) + "\n\nCompetitions: " + strings.Join(competitions, ", ")
		return result(text, map[string]any{"team": team, "statistics": stats, "players": players, "competitions": competitions}), nil
	default:
		return toolResult{}, fmt.Errorf("unknown tool %q", name)
	}
}

func result(text string, structured any) toolResult {
	return toolResult{Content: []toolContent{{"text", text}}, Structured: structured}
}
func stringArg(a map[string]any, k string) string { v, _ := a[k].(string); return strings.TrimSpace(v) }
func intArg(a map[string]any, k string) int {
	switch v := a[k].(type) {
	case float64:
		return int(v)
	case int:
		return v
	case string:
		i, _ := strconv.Atoi(v)
		return i
	}
	return 0
}
func boolArg(a map[string]any, k string) bool { v, _ := a[k].(bool); return v }
func boundedLimit(a map[string]any, def, max int) int {
	n := intArg(a, "limit")
	if n <= 0 {
		return def
	}
	if max > 0 && n > max {
		return max
	}
	return n
}
func matchFilterFromArgs(a map[string]any) (MatchFilter, error) {
	f := MatchFilter{Team: stringArg(a, "team"), Opponent: stringArg(a, "opponent"), Competition: stringArg(a, "competition"), Season: intArg(a, "season"), Stage: stringArg(a, "stage"), Limit: boundedLimit(a, 100, 1000)}
	var err error
	if v := stringArg(a, "start_date"); v != "" {
		f.StartDate, err = time.Parse("2006-01-02", v)
		if err != nil {
			return f, fmt.Errorf("start_date must be YYYY-MM-DD")
		}
	}
	if v := stringArg(a, "end_date"); v != "" {
		f.EndDate, err = time.Parse("2006-01-02", v)
		if err != nil {
			return f, fmt.Errorf("end_date must be YYYY-MM-DD")
		}
	}
	return f, nil
}
