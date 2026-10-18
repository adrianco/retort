package mcp

import (
	"encoding/json"
	"fmt"
	"strings"

	"brazilian-soccer-mcp/internal/data"
	"brazilian-soccer-mcp/internal/names"
)

const (
	defaultMatchLimit  = 25
	defaultPlayerLimit = 20
	headToHeadRecent   = 5
	profileTopPlayers  = 3
)

// NewServer returns an MCP server exposing the soccer tools over store.
func NewServer(store *data.Store) *Server {
	s := newServer("brazilian-soccer-mcp", "0.1.0")
	h := &handlers{store: store}

	s.register(tool("search_matches",
		"Find Brazilian soccer matches by team, head-to-head pair, competition, season, date range or venue. "+
			"Examples: 'Flamengo vs Fluminense matches', 'Palmeiras matches in 2023', 'Copa do Brasil finals' (competition 'Copa do Brasil', stage 'Final').",
		schema(map[string]any{
			"team":        prop("string", "Club on either side, e.g. 'Palmeiras' or 'Flamengo-RJ'"),
			"team_a":      prop("string", "First club of a head-to-head pair"),
			"team_b":      prop("string", "Second club of a head-to-head pair"),
			"competition": prop("string", "Competition, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'"),
			"season":      prop("integer", "Season year, e.g. 2023"),
			"from":        prop("string", "Earliest match date (YYYY-MM-DD or DD/MM/YYYY)"),
			"to":          prop("string", "Latest match date (YYYY-MM-DD or DD/MM/YYYY)"),
			"venue":       prop("string", "With 'team': 'home' or 'away'"),
			"limit":       prop("integer", fmt.Sprintf("Maximum matches to list (default %d)", defaultMatchLimit)),
		}),
		h.searchMatches))

	s.register(tool("team_record",
		"Win/draw/loss record, goals for and against, and win rate for a team, optionally filtered by season, competition or venue. "+
			"Example: 'Corinthians home record in 2022 Brasileirão'.",
		schema(map[string]any{
			"team":        prop("string", "Club name"),
			"season":      prop("integer", "Season year"),
			"competition": prop("string", "Competition filter"),
			"venue":       prop("string", "'home' or 'away'"),
		}),
		h.teamRecord))

	s.register(tool("head_to_head",
		"Head-to-head record between two clubs across the dataset: wins, draws, goals and recent meetings. "+
			"Example: 'Compare Palmeiras and Santos head-to-head'.",
		schema(map[string]any{
			"team_a":      prop("string", "First club"),
			"team_b":      prop("string", "Second club"),
			"competition": prop("string", "Optional competition filter"),
			"season":      prop("integer", "Optional season filter"),
		}, "team_a", "team_b"),
		h.headToHead))

	s.register(tool("standings",
		"League table for one competition and season, calculated from match results (3 points for a win, 1 for a draw). "+
			"Example: 'Who won the 2019 Brasileirão?'.",
		schema(map[string]any{
			"competition": prop("string", "Competition, e.g. 'Brasileirão' (Serie A)"),
			"season":      prop("integer", "Season year, e.g. 2019"),
		}, "competition", "season"),
		h.standings))

	s.register(tool("league_stats",
		"Aggregate statistics for a competition: goals per match, home/draw/away rates and the biggest wins. "+
			"Omit season to cover all seasons. Example: 'Average goals per match in the Brasileirão'.",
		schema(map[string]any{
			"competition": prop("string", "Competition, e.g. 'Brasileirão'"),
			"season":      prop("integer", "Optional season year"),
		}, "competition"),
		h.leagueStats))

	s.register(tool("search_players",
		"Search the FIFA player dataset by name, nationality, club, position or rating. "+
			"Positions can be codes (ST, GK) or groups (forward, midfielder, defender, goalkeeper). "+
			"Examples: 'Brazilian players', 'forwards from São Paulo FC', 'Who is Gabriel Barbosa?'.",
		schema(map[string]any{
			"name":        prop("string", "Part of the player name"),
			"nationality": prop("string", "Country, e.g. 'Brazil' or 'Brazilian'"),
			"club":        prop("string", "Part of the club name, e.g. 'Flamengo'"),
			"position":    prop("string", "Position code or group"),
			"min_overall": prop("integer", "Minimum FIFA overall rating"),
			"limit":       prop("integer", fmt.Sprintf("Maximum players to list (default %d)", defaultPlayerLimit)),
		}),
		h.searchPlayers))

	s.register(tool("team_profile",
		"Cross-dataset view of a club: its match record from the match files and its squad from the FIFA dataset "+
			"(player count, average rating, top players). Example: 'Which players play for Flamengo?'.",
		schema(map[string]any{
			"team":   prop("string", "Club name"),
			"season": prop("integer", "Optional season year for the match record"),
		}, "team"),
		h.teamProfile))

	return s
}

type handlers struct {
	store *data.Store
}

type matchArgs struct {
	Team        string `json:"team"`
	TeamA       string `json:"team_a"`
	TeamB       string `json:"team_b"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	From        string `json:"from"`
	To          string `json:"to"`
	Venue       string `json:"venue"`
	Limit       int    `json:"limit"`
}

func (a matchArgs) filter() (data.MatchFilter, error) {
	f := data.MatchFilter{
		Team:        a.Team,
		TeamA:       a.TeamA,
		TeamB:       a.TeamB,
		Competition: a.Competition,
		Season:      a.Season,
		Venue:       strings.ToLower(a.Venue),
	}
	if f.Venue != "" && f.Venue != "home" && f.Venue != "away" {
		return f, fmt.Errorf("venue must be 'home' or 'away'")
	}
	var err error
	if a.From != "" {
		if f.From, err = data.ParseDate(a.From); err != nil {
			return f, err
		}
	}
	if a.To != "" {
		if f.To, err = data.ParseDate(a.To); err != nil {
			return f, err
		}
	}
	return f, nil
}

func (h *handlers) searchMatches(raw json.RawMessage) (string, error) {
	var a matchArgs
	if err := decode(raw, &a); err != nil {
		return "", err
	}
	f, err := a.filter()
	if err != nil {
		return "", err
	}
	ms := h.store.FindMatches(f)
	if len(ms) == 0 {
		return "No matches found for these criteria.", nil
	}
	limit := a.Limit
	if limit <= 0 {
		limit = defaultMatchLimit
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%d matches found:\n", len(ms))
	shown := ms
	if len(shown) > limit {
		shown = shown[:limit]
	}
	for _, m := range shown {
		b.WriteString("- " + formatMatch(m) + "\n")
	}
	if len(ms) > limit {
		fmt.Fprintf(&b, "... (%d more matches in dataset)\n", len(ms)-limit)
	}
	return b.String(), nil
}

type teamArgs struct {
	Team        string `json:"team"`
	Season      int    `json:"season"`
	Competition string `json:"competition"`
	Venue       string `json:"venue"`
}

func (h *handlers) teamRecord(raw json.RawMessage) (string, error) {
	var a teamArgs
	if err := decode(raw, &a); err != nil {
		return "", err
	}
	if strings.TrimSpace(a.Team) == "" {
		return "", fmt.Errorf("team is required")
	}
	ma := matchArgs{Team: a.Team, Season: a.Season, Competition: a.Competition, Venue: a.Venue}
	f, err := ma.filter()
	if err != nil {
		return "", err
	}
	rec, err := h.store.TeamRecord(f)
	if err != nil {
		return "", err
	}
	display := names.Parse(a.Team).Display
	if rec.Played == 0 {
		return fmt.Sprintf("No matches found for %s (%s).", display, scopeLabel(a.Season, a.Competition, a.Venue)), nil
	}
	return fmt.Sprintf("%s record (%s):\n- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Win rate: %.1f%%\n",
		display, scopeLabel(a.Season, a.Competition, a.Venue),
		rec.Played, rec.Wins, rec.Draws, rec.Losses, rec.GoalsFor, rec.GoalsAgainst, rec.WinRate()), nil
}

type headToHeadArgs struct {
	TeamA       string `json:"team_a"`
	TeamB       string `json:"team_b"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
}

func (h *handlers) headToHead(raw json.RawMessage) (string, error) {
	var a headToHeadArgs
	if err := decode(raw, &a); err != nil {
		return "", err
	}
	rec, ms, err := h.store.HeadToHead(data.MatchFilter{
		TeamA: a.TeamA, TeamB: a.TeamB, Competition: a.Competition, Season: a.Season,
	})
	if err != nil {
		return "", err
	}
	a1, b1 := names.Parse(a.TeamA).Display, names.Parse(a.TeamB).Display
	if rec.Matches == 0 {
		return fmt.Sprintf("No matches between %s and %s in the dataset.", a1, b1), nil
	}

	var b strings.Builder
	fmt.Fprintf(&b, "Head-to-head: %s vs %s (%d matches in dataset)\n", a1, b1, rec.Matches)
	fmt.Fprintf(&b, "Wins: %s %d, %s %d, draws %d\n", a1, rec.WinsA, b1, rec.WinsB, rec.Draws)
	fmt.Fprintf(&b, "Goals: %s %d - %d %s\n", a1, rec.GoalsA, rec.GoalsB, b1)
	b.WriteString("Most recent:\n")
	for i := len(ms) - 1; i >= 0 && i >= len(ms)-headToHeadRecent; i-- {
		b.WriteString("- " + formatMatch(ms[i]) + "\n")
	}
	return b.String(), nil
}

type standingsArgs struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
}

func (h *handlers) standings(raw json.RawMessage) (string, error) {
	var a standingsArgs
	if err := decode(raw, &a); err != nil {
		return "", err
	}
	label, err := data.ResolveCompetition(a.Competition)
	if err != nil {
		return "", err
	}
	table, err := h.store.Standings(a.Competition, a.Season)
	if err != nil {
		return "", err
	}
	if len(table) == 0 {
		return fmt.Sprintf("No results for %s in %d.", label, a.Season), nil
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%d %s standings (calculated from matches):\n", a.Season, label)
	for i, st := range table {
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL) GF %d, GA %d, GD %+d\n",
			i+1, st.Team, st.Points, st.Wins, st.Draws, st.Losses, st.GoalsFor, st.GoalsAgainst, st.GoalDifference())
	}
	return b.String(), nil
}

type leagueArgs struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
}

func (h *handlers) leagueStats(raw json.RawMessage) (string, error) {
	var a leagueArgs
	if err := decode(raw, &a); err != nil {
		return "", err
	}
	sum, err := h.store.LeagueSummary(a.Competition, a.Season)
	if err != nil {
		return "", err
	}
	if sum.Matches == 0 {
		return fmt.Sprintf("No matches for %s.", sum.Competition), nil
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%s, %s (%d matches):\n", sum.Competition, seasonText(a.Season), sum.Matches)
	fmt.Fprintf(&b, "Average goals per match: %.2f\n", sum.GoalsPerMatch())
	fmt.Fprintf(&b, "Home win rate: %.1f%%, draw rate: %.1f%%, away win rate: %.1f%%\n",
		sum.HomeWinRate(), sum.DrawRate(), sum.AwayWinRate())
	b.WriteString("Biggest wins:\n")
	for _, m := range sum.BiggestWins {
		b.WriteString("- " + formatMatch(m) + "\n")
	}
	return b.String(), nil
}

type playerArgs struct {
	Name        string `json:"name"`
	Nationality string `json:"nationality"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	MinOverall  int    `json:"min_overall"`
	Limit       int    `json:"limit"`
}

func (h *handlers) searchPlayers(raw json.RawMessage) (string, error) {
	var a playerArgs
	if err := decode(raw, &a); err != nil {
		return "", err
	}
	limit := a.Limit
	if limit <= 0 {
		limit = defaultPlayerLimit
	}
	ps := h.store.FindPlayers(data.PlayerFilter{
		Name: a.Name, Nationality: a.Nationality, Club: a.Club, Position: a.Position,
		MinOverall: a.MinOverall, Limit: limit,
	})
	if len(ps) == 0 {
		return "No players found for these criteria.", nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d players:\n", len(ps))
	for i, p := range ps {
		fmt.Fprintf(&b, "%d. %s\n", i+1, formatPlayer(p))
	}
	return b.String(), nil
}

type profileArgs struct {
	Team   string `json:"team"`
	Season int    `json:"season"`
}

func (h *handlers) teamProfile(raw json.RawMessage) (string, error) {
	var a profileArgs
	if err := decode(raw, &a); err != nil {
		return "", err
	}
	if strings.TrimSpace(a.Team) == "" {
		return "", fmt.Errorf("team is required")
	}
	display := names.Parse(a.Team).Display

	var b strings.Builder
	fmt.Fprintf(&b, "%s profile\n", display)

	rec, err := h.store.TeamRecord(data.MatchFilter{Team: a.Team, Season: a.Season})
	if err != nil {
		return "", err
	}
	if rec.Played == 0 {
		fmt.Fprintf(&b, "Match record (%s): no matches in dataset\n", scopeLabel(a.Season, "", ""))
	} else {
		fmt.Fprintf(&b, "Match record (%s): %d played, %d W, %d D, %d L, GF %d, GA %d, win rate %.1f%%\n",
			scopeLabel(a.Season, "", ""), rec.Played, rec.Wins, rec.Draws, rec.Losses,
			rec.GoalsFor, rec.GoalsAgainst, rec.WinRate())
	}

	squad := h.store.FindPlayers(data.PlayerFilter{Club: a.Team})
	if len(squad) == 0 {
		b.WriteString("Squad in FIFA dataset: no players found\n")
		return b.String(), nil
	}
	fmt.Fprintf(&b, "Squad in FIFA dataset: %d players, average overall %.1f\n", len(squad), data.AverageOverall(squad))
	top := squad
	if len(top) > profileTopPlayers {
		top = top[:profileTopPlayers]
	}
	b.WriteString("Top players:\n")
	for _, p := range top {
		b.WriteString("- " + formatPlayer(p) + "\n")
	}
	return b.String(), nil
}

func tool(name, description string, input map[string]any, h func(json.RawMessage) (string, error)) Tool {
	return Tool{Name: name, Description: description, InputSchema: input, handler: h}
}

func prop(typ, description string) map[string]any {
	return map[string]any{"type": typ, "description": description}
}

func schema(properties map[string]any, required ...string) map[string]any {
	s := map[string]any{"type": "object", "properties": properties}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

// decode unmarshals tool arguments, treating missing arguments as an empty object.
func decode(raw json.RawMessage, into any) error {
	if len(raw) == 0 || string(raw) == "null" {
		return nil
	}
	if err := json.Unmarshal(raw, into); err != nil {
		return fmt.Errorf("invalid arguments: %w", err)
	}
	return nil
}
