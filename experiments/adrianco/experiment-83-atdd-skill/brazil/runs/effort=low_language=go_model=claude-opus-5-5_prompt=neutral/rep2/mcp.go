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

const protocolVersion = "2024-11-05"

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

// Tool describes an MCP tool.
type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	handler     func(db *DB, a args) (string, error)
}

type args map[string]any

func (a args) str(k string) string {
	switch v := a[k].(type) {
	case string:
		return strings.TrimSpace(v)
	case float64:
		return strconv.FormatFloat(v, 'f', -1, 64)
	}
	return ""
}

func (a args) num(k string) int {
	switch v := a[k].(type) {
	case float64:
		return int(v)
	case string:
		n, _ := strconv.Atoi(strings.TrimSpace(v))
		return n
	}
	return 0
}

func (a args) boolean(k string) bool {
	switch v := a[k].(type) {
	case bool:
		return v
	case string:
		return v == "true"
	}
	return false
}

func (a args) date(k string) (time.Time, error) {
	s := a.str(k)
	if s == "" {
		return time.Time{}, nil
	}
	return ParseDate(s)
}

func prop(typ, desc string) map[string]any { return map[string]any{"type": typ, "description": desc} }

func schema(required []string, props map[string]any) map[string]any {
	s := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

var compDesc = "Competition: Brasileirão/Serie A, Serie B, Serie C, Copa do Brasil, Libertadores"

// Tools is the tool registry.
var Tools = []Tool{
	{
		Name:        "search_matches",
		Description: "Search matches across all datasets by team, opponent, home/away team, competition, season, date range or round/stage (e.g. 'final').",
		InputSchema: schema(nil, map[string]any{
			"team": prop("string", "Team playing either home or away"), "opponent": prop("string", "Opponent of team"),
			"home_team": prop("string", "Home team"), "away_team": prop("string", "Away team"),
			"competition": prop("string", compDesc), "season": prop("integer", "Season year"),
			"date_from": prop("string", "Start date (YYYY-MM-DD or DD/MM/YYYY)"), "date_to": prop("string", "End date"),
			"round": prop("string", "Round number or stage, e.g. 'final', 'semifinals'"), "limit": prop("integer", "Max matches listed (default 20)"),
		}),
		handler: func(db *DB, a args) (string, error) {
			from, err := a.date("date_from")
			if err != nil {
				return "", err
			}
			to, err := a.date("date_to")
			if err != nil {
				return "", err
			}
			return db.SearchMatches(MatchFilter{Team: a.str("team"), Opponent: a.str("opponent"), HomeTeam: a.str("home_team"),
				AwayTeam: a.str("away_team"), Competition: a.str("competition"), Season: a.num("season"),
				DateFrom: from, DateTo: to, Round: a.str("round")}, a.num("limit")), nil
		},
	},
	{
		Name:        "head_to_head",
		Description: "Head-to-head record and match list between two teams.",
		InputSchema: schema([]string{"team1", "team2"}, map[string]any{
			"team1": prop("string", "First team"), "team2": prop("string", "Second team"),
			"competition": prop("string", compDesc), "season": prop("integer", "Season year"), "limit": prop("integer", "Max matches listed"),
		}),
		handler: func(db *DB, a args) (string, error) {
			return db.HeadToHead(a.str("team1"), a.str("team2"), a.str("competition"), a.num("season"), a.num("limit")), nil
		},
	},
	{
		Name:        "team_record",
		Description: "Win/draw/loss record and goals for a team, optionally filtered by season, competition and venue (home/away).",
		InputSchema: schema([]string{"team"}, map[string]any{
			"team": prop("string", "Team name"), "season": prop("integer", "Season year"),
			"competition": prop("string", compDesc), "venue": prop("string", "home, away or all"),
		}),
		handler: func(db *DB, a args) (string, error) {
			return db.TeamRecordText(a.str("team"), a.num("season"), a.str("competition"), strings.ToLower(a.str("venue"))), nil
		},
	},
	{
		Name:        "standings",
		Description: "League table for a season calculated from match results, including champion and relegation zone.",
		InputSchema: schema([]string{"season"}, map[string]any{
			"season": prop("integer", "Season year"), "competition": prop("string", "Default Brasileirão Serie A"),
			"top": prop("integer", "Only show top N"),
		}),
		handler: func(db *DB, a args) (string, error) {
			return db.StandingsText(a.num("season"), a.str("competition"), a.num("top")), nil
		},
	},
	{
		Name:        "team_rankings",
		Description: "Rank teams by goals_for, goals_against (fewest), wins, win_rate or points; e.g. best home record or most goals in a season.",
		InputSchema: schema(nil, map[string]any{
			"metric": prop("string", "goals_for | goals_against | wins | win_rate | points"), "season": prop("integer", "Season year"),
			"competition": prop("string", compDesc), "venue": prop("string", "home, away or all"),
			"min_matches": prop("integer", "Minimum matches to qualify"), "limit": prop("integer", "Number of teams"),
		}),
		handler: func(db *DB, a args) (string, error) {
			return db.TeamRankings(a.str("metric"), a.num("season"), a.str("competition"), strings.ToLower(a.str("venue")), a.num("min_matches"), a.num("limit")), nil
		},
	},
	{
		Name:        "compare_seasons",
		Description: "Compare aggregate statistics (goals per match, home/away win rates, leader) across seasons.",
		InputSchema: schema([]string{"seasons"}, map[string]any{
			"seasons":     map[string]any{"type": "array", "items": map[string]any{"type": "integer"}, "description": "Season years"},
			"competition": prop("string", compDesc),
		}),
		handler: func(db *DB, a args) (string, error) {
			var ss []int
			switch v := a["seasons"].(type) {
			case []any:
				for _, x := range v {
					if f, ok := x.(float64); ok {
						ss = append(ss, int(f))
					}
				}
			case string:
				for _, p := range strings.FieldsFunc(v, func(r rune) bool { return r == ',' || r == ' ' }) {
					if n, err := strconv.Atoi(p); err == nil {
						ss = append(ss, n)
					}
				}
			}
			if len(ss) == 0 {
				return "", fmt.Errorf("seasons is required")
			}
			return db.CompareSeasons(ss, a.str("competition")), nil
		},
	},
	{
		Name:        "team_competitions",
		Description: "List the competitions and seasons a team has played in across all match files.",
		InputSchema: schema([]string{"team"}, map[string]any{"team": prop("string", "Team name")}),
		handler: func(db *DB, a args) (string, error) {
			return db.TeamCompetitions(a.str("team")), nil
		},
	},
	{
		Name:        "derbies",
		Description: "List traditional Brazilian derby (clássico) matches, optionally for a season.",
		InputSchema: schema(nil, map[string]any{"season": prop("integer", "Season year"), "limit": prop("integer", "Matches listed per derby")}),
		handler: func(db *DB, a args) (string, error) {
			l := a.num("limit")
			if l == 0 {
				l = 5
			}
			return db.ListDerbies(a.num("season"), l), nil
		},
	},
	{
		Name:        "search_players",
		Description: "Search FIFA player database by name, nationality, club, position (code or group: forward/midfielder/defender/goalkeeper) and minimum rating.",
		InputSchema: schema(nil, map[string]any{
			"name": prop("string", "Player name substring"), "nationality": prop("string", "Country, e.g. Brazil"),
			"club": prop("string", "Club name"), "position": prop("string", "Position code or group"),
			"min_overall": prop("integer", "Minimum overall rating"), "limit": prop("integer", "Max players listed (default 20)"),
		}),
		handler: func(db *DB, a args) (string, error) {
			return db.SearchPlayers(PlayerFilter{Name: a.str("name"), Nationality: a.str("nationality"), Club: a.str("club"),
				Position: a.str("position"), MinOverall: a.num("min_overall")}, a.num("limit")), nil
		},
	},
	{
		Name:        "player_details",
		Description: "Full attributes (skills, physicals, value) for a player by name.",
		InputSchema: schema([]string{"name"}, map[string]any{"name": prop("string", "Player name")}),
		handler: func(db *DB, a args) (string, error) {
			return db.PlayerDetails(a.str("name")), nil
		},
	},
	{
		Name:        "players_by_club",
		Description: "Count and average rating of players of a nationality grouped by club; optionally only Brazilian clubs.",
		InputSchema: schema(nil, map[string]any{
			"nationality": prop("string", "Country (default Brazil)"), "brazilian_clubs_only": prop("boolean", "Only clubs in Brazilian match data"),
			"limit": prop("integer", "Max clubs listed"),
		}),
		handler: func(db *DB, a args) (string, error) {
			nat := a.str("nationality")
			if nat == "" {
				nat = "Brazil"
			}
			return db.PlayersByClub(nat, a.boolean("brazilian_clubs_only"), a.num("limit")), nil
		},
	},
	{
		Name:        "team_profile",
		Description: "Cross-dataset team profile: overall match record, competitions, and FIFA players at the club.",
		InputSchema: schema([]string{"team"}, map[string]any{"team": prop("string", "Team name")}),
		handler: func(db *DB, a args) (string, error) {
			return db.TeamProfile(a.str("team")), nil
		},
	},
	{
		Name:        "dataset_overview",
		Description: "Describe loaded datasets and match counts per competition.",
		InputSchema: schema(nil, map[string]any{}),
		handler: func(db *DB, a args) (string, error) {
			return db.Overview(), nil
		},
	},
}

// CallTool invokes a tool by name.
func (db *DB) CallTool(name string, a args) (string, error) {
	for _, t := range Tools {
		if t.Name == name {
			return t.handler(db, a)
		}
	}
	return "", fmt.Errorf("unknown tool %q", name)
}

// Handle processes one JSON-RPC message; returns nil for notifications.
func (db *DB) Handle(line []byte) *rpcResponse {
	var req rpcRequest
	if err := json.Unmarshal(line, &req); err != nil {
		return &rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &rpcError{-32700, "parse error"}}
	}
	if len(req.ID) == 0 { // notification
		return nil
	}
	resp := &rpcResponse{JSONRPC: "2.0", ID: req.ID}
	switch req.Method {
	case "initialize":
		resp.Result = map[string]any{
			"protocolVersion": protocolVersion,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": "brazilian-soccer-mcp", "version": "1.0.0"},
		}
	case "ping":
		resp.Result = map[string]any{}
	case "tools/list":
		resp.Result = map[string]any{"tools": Tools}
	case "tools/call":
		var p struct {
			Name      string `json:"name"`
			Arguments args   `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			resp.Error = &rpcError{-32602, "invalid params"}
			break
		}
		text, err := db.CallTool(p.Name, p.Arguments)
		if err != nil {
			resp.Result = map[string]any{"content": []map[string]any{{"type": "text", "text": "Error: " + err.Error()}}, "isError": true}
		} else {
			resp.Result = map[string]any{"content": []map[string]any{{"type": "text", "text": text}}}
		}
	default:
		resp.Error = &rpcError{-32601, "method not found: " + req.Method}
	}
	return resp
}

// Serve runs the newline-delimited JSON-RPC stdio loop.
func (db *DB) Serve(in io.Reader, out io.Writer) error {
	sc := bufio.NewScanner(in)
	sc.Buffer(make([]byte, 1024*1024), 16*1024*1024)
	enc := json.NewEncoder(out)
	for sc.Scan() {
		line := sc.Bytes()
		if len(strings.TrimSpace(string(line))) == 0 {
			continue
		}
		if resp := db.Handle(line); resp != nil {
			if err := enc.Encode(resp); err != nil {
				return err
			}
		}
	}
	return sc.Err()
}
