// Package tools wires the soccer query layer onto the MCP server: it declares
// the tool schemas an LLM sees, decodes their arguments, runs the query and
// returns both a human readable text rendering (what the model reads) and the
// structured JSON result (what a programmatic client can consume).
package tools

import (
	"fmt"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/soccer"
)

// Instructions is the server level guidance sent during the MCP handshake.
const Instructions = `Knowledge graph over Brazilian football datasets (Brasileirão Série A/B/C,
Copa do Brasil, Copa Libertadores match results plus the FIFA player database).

Use search_matches / head_to_head for fixtures and rivalries, team_stats and
rank_teams for club performance, standings for league tables computed from
results, search_players / get_player / club_squads for the FIFA player data, and
competition_stats / biggest_wins for aggregate analysis. Team names may be given
loosely ("Flamengo", "Flamengo-RJ", "Sao Paulo") - they are normalised
internally. All answers come only from the loaded CSV datasets.`

const defaultLimit = 20

// Register adds every soccer tool to the MCP server.
func Register(s *mcp.Server, store *soccer.Store) {
	for _, t := range allTools(store) {
		s.Register(t.tool, t.handler)
	}
}

type binding struct {
	tool    mcp.Tool
	handler mcp.Handler
}

// prop is a small helper for declaring input schema properties.
func prop(typ, desc string) *mcp.Prop { return &mcp.Prop{Type: typ, Description: desc} }

func schema(required []string, props map[string]*mcp.Prop) mcp.Schema {
	return mcp.Schema{Type: "object", Properties: props, Required: required}
}

// matchFilterProps are the shared filtering arguments accepted by the
// match-oriented tools.
func matchFilterProps(extra map[string]*mcp.Prop) map[string]*mcp.Prop {
	p := map[string]*mcp.Prop{
		"competition": prop("string", "Competition name: Brasileirão / Série A, Série B, Série C, Copa do Brasil or Libertadores."),
		"season":      prop("integer", "Season year, e.g. 2019."),
		"from":        prop("string", "Inclusive start date (YYYY-MM-DD or DD/MM/YYYY)."),
		"to":          prop("string", "Inclusive end date (YYYY-MM-DD or DD/MM/YYYY)."),
		"stage":       prop("string", "Tournament stage substring, e.g. 'final', 'semifinals', 'group stage'."),
		"round":       prop("string", "Round number, e.g. '22'."),
	}
	for k, v := range extra {
		p[k] = v
	}
	return p
}

// filterFrom builds a soccer.MatchFilter from tool arguments.
func filterFrom(a mcp.Args) soccer.MatchFilter {
	return soccer.MatchFilter{
		Team:        a.String("team"),
		Opponent:    a.String("opponent"),
		HomeTeam:    a.String("home_team"),
		AwayTeam:    a.String("away_team"),
		Competition: a.String("competition"),
		Season:      a.Int("season", 0),
		From:        a.String("from"),
		To:          a.String("to"),
		Stage:       a.String("stage"),
		Round:       a.String("round"),
		Venue:       a.String("venue"),
		Limit:       a.Int("limit", 0),
	}
}

// text builds a successful tool result carrying both renderings.
func text(s string, structured any) (*mcp.CallToolResult, error) {
	return &mcp.CallToolResult{
		Content:           []mcp.Content{mcp.TextContent(s)},
		StructuredContent: structured,
	}, nil
}

func allTools(st *soccer.Store) []binding {
	return []binding{
		searchMatches(st),
		headToHead(st),
		teamStats(st),
		standings(st),
		rankTeams(st),
		competitionStats(st),
		biggestWins(st),
		searchPlayers(st),
		getPlayer(st),
		clubSquads(st),
		listTeams(st),
		listCompetitions(st),
		datasetInfo(st),
	}
}

func searchMatches(st *soccer.Store) binding {
	return binding{
		tool: mcp.Tool{
			Name:        "search_matches",
			Title:       "Search matches",
			Description: "Find matches by team, opponent, competition, season, date range, stage or round. Returns the most recent matches first.",
			InputSchema: schema(nil, matchFilterProps(map[string]*mcp.Prop{
				"team":      prop("string", "Club that played in the match (home or away)."),
				"opponent":  prop("string", "Restrict to matches against this club."),
				"home_team": prop("string", "Club that played at home."),
				"away_team": prop("string", "Club that played away."),
				"venue":     {Type: "string", Description: "Restrict 'team' to home or away matches.", Enum: []string{"home", "away", "any"}},
				"limit":     prop("integer", "Maximum matches to return (default 20)."),
			})),
		},
		handler: func(a mcp.Args) (*mcp.CallToolResult, error) {
			f := filterFrom(a)
			limit := f.Limit
			if limit <= 0 {
				limit = defaultLimit
			}
			f.Limit = 0
			all := st.SearchMatches(f)
			shown := all
			if len(shown) > limit {
				shown = shown[:limit]
			}
			title := "Matches: " + scopeTitle(f)
			return text(soccer.FormatMatches(title, shown, len(all)),
				map[string]any{"total": len(all), "matches": shown})
		},
	}
}

func headToHead(st *soccer.Store) binding {
	return binding{
		tool: mcp.Tool{
			Name:        "head_to_head",
			Title:       "Head-to-head record",
			Description: "Compare two clubs: wins, draws, goals and the list of meetings across all loaded competitions.",
			InputSchema: schema([]string{"team_a", "team_b"}, matchFilterProps(map[string]*mcp.Prop{
				"team_a": prop("string", "First club."),
				"team_b": prop("string", "Second club."),
				"limit":  prop("integer", "Maximum meetings to list (default 20)."),
			})),
		},
		handler: func(a mcp.Args) (*mcp.CallToolResult, error) {
			ta, err := a.RequireString("team_a")
			if err != nil {
				return nil, err
			}
			tb, err := a.RequireString("team_b")
			if err != nil {
				return nil, err
			}
			f := filterFrom(a)
			if f.Limit <= 0 {
				f.Limit = defaultLimit
			}
			h, err := st.HeadToHead(ta, tb, f)
			if err != nil {
				return nil, err
			}
			return text(soccer.FormatH2H(h), h)
		},
	}
}

func teamStats(st *soccer.Store) binding {
	return binding{
		tool: mcp.Tool{
			Name:        "team_stats",
			Title:       "Team statistics",
			Description: "Win/draw/loss record, goals for and against, home and away splits, per-competition and per-season breakdown for one club.",
			InputSchema: schema([]string{"team"}, matchFilterProps(map[string]*mcp.Prop{
				"team":  prop("string", "Club to report on."),
				"venue": {Type: "string", Description: "Restrict to home or away matches.", Enum: []string{"home", "away", "any"}},
			})),
		},
		handler: func(a mcp.Args) (*mcp.CallToolResult, error) {
			if _, err := a.RequireString("team"); err != nil {
				return nil, err
			}
			rep, err := st.TeamStats(filterFrom(a))
			if err != nil {
				return nil, err
			}
			return text(soccer.FormatTeamReport(rep), rep)
		},
	}
}

func standings(st *soccer.Store) binding {
	return binding{
		tool: mcp.Tool{
			Name:        "standings",
			Title:       "League table",
			Description: "Compute the final league table for a competition and season from the match results (3 points per win, goal difference tie-break). Use it to answer 'who won the 2019 Brasileirão?' or 'who was relegated?'.",
			InputSchema: schema([]string{"season"}, map[string]*mcp.Prop{
				"season":      prop("integer", "Season year, e.g. 2019."),
				"competition": prop("string", "Competition, default Brasileirão Série A."),
				"top":         prop("integer", "Only return the first N places (0 = all)."),
				"bottom":      prop("integer", "Only return the last N places (relegation zone)."),
			}),
		},
		handler: func(a mcp.Args) (*mcp.CallToolResult, error) {
			season := a.Int("season", 0)
			if season == 0 {
				return nil, fmt.Errorf("missing required argument \"season\"")
			}
			comp := a.String("competition")
			rows, err := st.Standings(comp, season)
			if err != nil {
				return nil, err
			}
			name := soccer.ResolveCompetition(comp)
			if name == "" {
				name = soccer.CompSerieA
			}
			shown := rows
			if n := a.Int("top", 0); n > 0 && n < len(shown) {
				shown = shown[:n]
			}
			if n := a.Int("bottom", 0); n > 0 && n < len(shown) {
				shown = shown[len(shown)-n:]
			}
			return text(soccer.FormatStandings(name, season, shown),
				map[string]any{"competition": name, "season": season, "table": shown})
		},
	}
}

func rankTeams(st *soccer.Store) binding {
	return binding{
		tool: mcp.Tool{
			Name:        "rank_teams",
			Title:       "Rank teams by metric",
			Description: "Rank every club in a scope by points, wins, win rate, goals scored, goals conceded or goal difference. Set venue=home or away to answer 'which team has the best home/away record?'.",
			InputSchema: schema(nil, matchFilterProps(map[string]*mcp.Prop{
				"metric":      {Type: "string", Description: "Ranking metric (default points).", Enum: []string{"points", "wins", "win_rate", "goals_for", "goals_against", "goal_diff"}},
				"venue":       {Type: "string", Description: "Count only home or only away matches.", Enum: []string{"home", "away", "any"}},
				"min_matches": prop("integer", "Ignore clubs with fewer than this many matches (default 10)."),
				"limit":       prop("integer", "How many clubs to return (default 10)."),
			})),
		},
		handler: func(a mcp.Args) (*mcp.CallToolResult, error) {
			f := filterFrom(a)
			metric := a.String("metric")
			rows, err := st.RankTeams(f, metric, a.Int("min_matches", 10))
			if err != nil {
				return nil, err
			}
			limit := a.Int("limit", 10)
			if limit > 0 && len(rows) > limit {
				rows = rows[:limit]
			}
			if metric == "" {
				metric = "points"
			}
			title := fmt.Sprintf("Teams ranked by %s: %s", metric, scopeTitle(f))
			return text(soccer.FormatRankings(title, rows), rows)
		},
	}
}

func competitionStats(st *soccer.Store) binding {
	return binding{
		tool: mcp.Tool{
			Name:        "competition_stats",
			Title:       "Aggregate statistics",
			Description: "Aggregate statistics over any slice of the match data: goals per match, home/away/draw rates, clean sheets, seasons covered and the highest scoring match.",
			InputSchema: schema(nil, matchFilterProps(map[string]*mcp.Prop{
				"team": prop("string", "Restrict to matches involving this club."),
			})),
		},
		handler: func(a mcp.Args) (*mcp.CallToolResult, error) {
			s, err := st.Stats(filterFrom(a))
			if err != nil {
				return nil, err
			}
			return text(soccer.FormatStats(s), s)
		},
	}
}

func biggestWins(st *soccer.Store) binding {
	return binding{
		tool: mcp.Tool{
			Name:        "biggest_wins",
			Title:       "Biggest victories",
			Description: "List the matches with the largest goal margins in any slice of the data.",
			InputSchema: schema(nil, matchFilterProps(map[string]*mcp.Prop{
				"team":  prop("string", "Restrict to matches involving this club."),
				"limit": prop("integer", "How many matches to return (default 10)."),
			})),
		},
		handler: func(a mcp.Args) (*mcp.CallToolResult, error) {
			f := filterFrom(a)
			if f.Limit <= 0 {
				f.Limit = 10
			}
			matches := st.BiggestWins(f)
			title := "Biggest victories: " + scopeTitle(f)
			return text(soccer.FormatMatches(title, matches, len(matches)),
				map[string]any{"matches": matches})
		},
	}
}

func playerFilterFrom(a mcp.Args) soccer.PlayerFilter {
	return soccer.PlayerFilter{
		Name:        a.String("name"),
		Nationality: a.String("nationality"),
		Club:        a.String("club"),
		Position:    a.String("position"),
		MinOverall:  a.Int("min_overall", 0),
		MinAge:      a.Int("min_age", 0),
		MaxAge:      a.Int("max_age", 0),
		SortBy:      a.String("sort_by"),
		Limit:       a.Int("limit", 0),
	}
}

func searchPlayers(st *soccer.Store) binding {
	return binding{
		tool: mcp.Tool{
			Name:        "search_players",
			Title:       "Search players",
			Description: "Search the FIFA player database by name, nationality, club, position, rating or age. Highest rated first by default.",
			InputSchema: schema(nil, map[string]*mcp.Prop{
				"name":        prop("string", "Player name fragment (accent insensitive)."),
				"nationality": prop("string", "Nationality, e.g. 'Brazil'."),
				"club":        prop("string", "Club name fragment, e.g. 'Flamengo'."),
				"position":    prop("string", "Position code (ST, GK, LW...) or group (goalkeeper, defender, midfielder, forward)."),
				"min_overall": prop("integer", "Minimum FIFA overall rating."),
				"min_age":     prop("integer", "Minimum age."),
				"max_age":     prop("integer", "Maximum age."),
				"sort_by":     {Type: "string", Description: "Sort order (default overall).", Enum: []string{"overall", "potential", "age", "name"}},
				"limit":       prop("integer", "How many players to return (default 20)."),
			}),
		},
		handler: func(a mcp.Args) (*mcp.CallToolResult, error) {
			f := playerFilterFrom(a)
			limit := f.Limit
			if limit <= 0 {
				limit = defaultLimit
			}
			f.Limit = 0
			all := st.SearchPlayers(f)
			shown := all
			if len(shown) > limit {
				shown = shown[:limit]
			}
			title := "Players matching " + playerScope(f)
			return text(soccer.FormatPlayers(title, shown, len(all)),
				map[string]any{"total": len(all), "players": shown})
		},
	}
}

func getPlayer(st *soccer.Store) binding {
	return binding{
		tool: mcp.Tool{
			Name:        "get_player",
			Title:       "Player profile",
			Description: "Full FIFA profile for one player: ratings, club, physical data and key attributes.",
			InputSchema: schema([]string{"name"}, map[string]*mcp.Prop{
				"name": prop("string", "Player name, e.g. 'Gabriel Barbosa' or 'Neymar'."),
			}),
		},
		handler: func(a mcp.Args) (*mcp.CallToolResult, error) {
			name, err := a.RequireString("name")
			if err != nil {
				return nil, err
			}
			found := st.SearchPlayers(soccer.PlayerFilter{Name: name, Limit: 5})
			if len(found) == 0 {
				// Fall back to the individual name parts: the FIFA data
				// abbreviates many names ("L. Messi", "Gabriel Jesus").
				for _, part := range strings.Fields(name) {
					if len(part) < 4 {
						continue
					}
					if found = st.SearchPlayers(soccer.PlayerFilter{Name: part, Limit: 5}); len(found) > 0 {
						break
					}
				}
			}
			if len(found) == 0 {
				return nil, fmt.Errorf("no player matching %q in the FIFA dataset", name)
			}
			out := soccer.FormatPlayerProfile(found[0])
			if len(found) > 1 {
				var others []string
				for _, p := range found[1:] {
					others = append(others, p.Name)
				}
				out += "\nOther matches for this name: " + strings.Join(others, ", ")
			}
			return text(out, found[0])
		},
	}
}

func clubSquads(st *soccer.Store) binding {
	return binding{
		tool: mcp.Tool{
			Name:        "club_squads",
			Title:       "Squads of clubs in the match data",
			Description: "Cross-dataset query: for every club that appears in the match data, summarise its FIFA players (count, average rating, top rated). Optionally filter the players by nationality.",
			InputSchema: schema(nil, map[string]*mcp.Prop{
				"nationality": prop("string", "Only count players of this nationality, e.g. 'Brazil'."),
				"limit":       prop("integer", "How many clubs to return (default 20)."),
			}),
		},
		handler: func(a mcp.Args) (*mcp.CallToolResult, error) {
			nat := a.String("nationality")
			limit := a.Int("limit", defaultLimit)
			squads := st.ClubSquads(nat, limit)
			title := "Clubs in the match data with FIFA squad information"
			if nat != "" {
				title += " (" + nat + " players only)"
			}
			return text(soccer.FormatSquads(title, squads), squads)
		},
	}
}

func listTeams(st *soccer.Store) binding {
	return binding{
		tool: mcp.Tool{
			Name:        "list_teams",
			Title:       "List clubs",
			Description: "List the clubs present in the match data, with match counts, seasons covered and competitions played. Useful for resolving how a club is named in the data.",
			InputSchema: schema(nil, map[string]*mcp.Prop{
				"query": prop("string", "Optional name fragment to filter by."),
				"limit": prop("integer", "How many clubs to return (default 30)."),
			}),
		},
		handler: func(a mcp.Args) (*mcp.CallToolResult, error) {
			teams := st.ListTeams(a.String("query"), a.Int("limit", 30))
			return text(soccer.FormatTeams("Clubs in the match data", teams), teams)
		},
	}
}

func listCompetitions(st *soccer.Store) binding {
	return binding{
		tool: mcp.Tool{
			Name:        "list_competitions",
			Title:       "List competitions",
			Description: "List the competitions in the loaded data with match counts, team counts and season coverage.",
			InputSchema: schema(nil, map[string]*mcp.Prop{}),
		},
		handler: func(a mcp.Args) (*mcp.CallToolResult, error) {
			comps := st.ListCompetitions()
			return text(soccer.FormatCompetitions(comps), comps)
		},
	}
}

func datasetInfo(st *soccer.Store) binding {
	return binding{
		tool: mcp.Tool{
			Name:        "dataset_info",
			Title:       "Dataset coverage",
			Description: "Describe what data is loaded: number of matches, players and competitions, and any files that failed to load.",
			InputSchema: schema(nil, map[string]*mcp.Prop{}),
		},
		handler: func(a mcp.Args) (*mcp.CallToolResult, error) {
			comps := st.ListCompetitions()
			var b strings.Builder
			fmt.Fprintf(&b, "Loaded %d unique matches and %d players.\n", len(st.Matches), len(st.Players))
			b.WriteString(soccer.FormatCompetitions(comps))
			if errs := st.LoadErrors(); len(errs) > 0 {
				fmt.Fprintf(&b, "\nLoad warnings: %s", strings.Join(errs, "; "))
			}
			return text(b.String(), map[string]any{
				"matches":      len(st.Matches),
				"players":      len(st.Players),
				"competitions": comps,
				"warnings":     st.LoadErrors(),
			})
		},
	}
}

// scopeTitle describes a match filter for use in result headings.
func scopeTitle(f soccer.MatchFilter) string {
	var parts []string
	if f.Team != "" {
		parts = append(parts, f.Team)
	}
	if f.Opponent != "" {
		parts = append(parts, "vs "+f.Opponent)
	}
	if f.HomeTeam != "" {
		parts = append(parts, f.HomeTeam+" at home")
	}
	if f.AwayTeam != "" {
		parts = append(parts, f.AwayTeam+" away")
	}
	if f.Competition != "" {
		c := soccer.ResolveCompetition(f.Competition)
		if c == "" {
			c = f.Competition
		}
		parts = append(parts, c)
	}
	if f.Season != 0 {
		parts = append(parts, fmt.Sprintf("season %d", f.Season))
	}
	if f.From != "" || f.To != "" {
		parts = append(parts, fmt.Sprintf("%s..%s", f.From, f.To))
	}
	if f.Stage != "" {
		parts = append(parts, f.Stage)
	}
	if f.Round != "" {
		parts = append(parts, "round "+f.Round)
	}
	if f.Venue != "" {
		parts = append(parts, f.Venue)
	}
	if len(parts) == 0 {
		return "all competitions and seasons"
	}
	return strings.Join(parts, ", ")
}

// playerScope describes a player filter for use in result headings.
func playerScope(f soccer.PlayerFilter) string {
	var parts []string
	if f.Name != "" {
		parts = append(parts, "name~"+f.Name)
	}
	if f.Nationality != "" {
		parts = append(parts, f.Nationality)
	}
	if f.Club != "" {
		parts = append(parts, "club "+f.Club)
	}
	if f.Position != "" {
		parts = append(parts, f.Position)
	}
	if f.MinOverall > 0 {
		parts = append(parts, fmt.Sprintf("overall>=%d", f.MinOverall))
	}
	if f.MinAge > 0 {
		parts = append(parts, fmt.Sprintf("age>=%d", f.MinAge))
	}
	if f.MaxAge > 0 {
		parts = append(parts, fmt.Sprintf("age<=%d", f.MaxAge))
	}
	if len(parts) == 0 {
		return "any criteria"
	}
	return strings.Join(parts, ", ")
}
