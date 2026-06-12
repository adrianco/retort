// Context: Brazilian Soccer MCP Server.
// File: format.go
// Purpose: The tool handler implementations — each reads coerced arguments,
// runs the corresponding query, and renders a concise, human-readable answer
// in the style shown in the specification.
package mcpserver

import (
	"fmt"
	"strings"

	"brazilian-soccer-mcp/internal/soccer"
)

const defaultMatchLimit = 30

// formatMatchLine renders a single match as e.g.
// "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)".
func formatMatchLine(m soccer.Match) string {
	date := "date unknown"
	if m.HasDate {
		date = m.Date.Format("2006-01-02")
	}
	score := "vs"
	if m.HasScore {
		score = fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals)
	}
	ctx := m.Competition
	switch {
	case m.Round != "":
		ctx = fmt.Sprintf("%s Round %s", m.Competition, m.Round)
	case m.Stage != "":
		ctx = fmt.Sprintf("%s %s", m.Competition, m.Stage)
	}
	return fmt.Sprintf("%s: %s %s %s (%s)", date, m.HomeTeam, score, m.AwayTeam, ctx)
}

func (h *Handler) searchMatches(args map[string]any) (string, error) {
	f := soccer.MatchFilter{
		Team:        argString(args, "team"),
		Opponent:    argString(args, "opponent"),
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
	}
	if from := argString(args, "from"); from != "" {
		if t, ok := soccer.ParseDate(from); ok {
			f.From = t
		}
	}
	if to := argString(args, "to"); to != "" {
		if t, ok := soccer.ParseDate(to); ok {
			f.To = t
		}
	}
	limit := argInt(args, "limit")
	if limit <= 0 {
		limit = defaultMatchLimit
	}

	matches := h.DB.FindMatches(f)
	if len(matches) == 0 {
		return "No matches found for the given criteria.", nil
	}

	var b strings.Builder
	fmt.Fprintf(&b, "Found %d match(es):\n", len(matches))
	shown := matches
	if len(shown) > limit {
		shown = shown[:limit]
	}
	for _, m := range shown {
		fmt.Fprintf(&b, "- %s\n", formatMatchLine(m))
	}
	if len(matches) > limit {
		fmt.Fprintf(&b, "... (%d more not shown)\n", len(matches)-limit)
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

func (h *Handler) headToHead(args map[string]any) (string, error) {
	a, err := requireString(args, "team_a")
	if err != nil {
		return "", err
	}
	bTeam, err := requireString(args, "team_b")
	if err != nil {
		return "", err
	}
	h2h := h.DB.HeadToHead(a, bTeam)
	if len(h2h.Matches) == 0 {
		return fmt.Sprintf("No matches found between %s and %s in the dataset.", a, bTeam), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s — head-to-head (%d matches):\n", a, bTeam, len(h2h.Matches))
	fmt.Fprintf(&b, "%s: %d win(s), %s: %d win(s), Draws: %d\n", a, h2h.AWins, bTeam, h2h.BWins, h2h.Draws)
	fmt.Fprintf(&b, "Goals: %s %d - %d %s\n", a, h2h.AGoals, h2h.BGoals, bTeam)
	b.WriteString("\nMatches:\n")
	for _, m := range h2h.Matches {
		fmt.Fprintf(&b, "- %s\n", formatMatchLine(m))
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

func parseVenue(s string) soccer.Venue {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "home":
		return soccer.VenueHome
	case "away":
		return soccer.VenueAway
	default:
		return soccer.VenueAny
	}
}

func (h *Handler) teamRecord(args map[string]any) (string, error) {
	team, err := requireString(args, "team")
	if err != nil {
		return "", err
	}
	f := soccer.TeamFilter{
		Team:        team,
		Season:      argInt(args, "season"),
		Competition: argString(args, "competition"),
		Venue:       parseVenue(argString(args, "venue")),
	}
	r := h.DB.TeamRecord(f)

	scope := team
	var quals []string
	if f.Season != 0 {
		quals = append(quals, fmt.Sprintf("%d", f.Season))
	}
	if f.Competition != "" {
		quals = append(quals, f.Competition)
	}
	switch f.Venue {
	case soccer.VenueHome:
		quals = append(quals, "home")
	case soccer.VenueAway:
		quals = append(quals, "away")
	}
	if len(quals) > 0 {
		scope = fmt.Sprintf("%s (%s)", team, strings.Join(quals, " "))
	}

	if r.Matches == 0 {
		return fmt.Sprintf("No matches found for %s.", scope), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s record:\n", scope)
	fmt.Fprintf(&b, "- Matches: %d\n", r.Matches)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", r.Wins, r.Draws, r.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d\n", r.GoalsFor, r.GoalsAgainst)
	fmt.Fprintf(&b, "- Points: %d\n", r.Points())
	fmt.Fprintf(&b, "- Win rate: %.1f%%", r.WinRate()*100)
	return b.String(), nil
}

func (h *Handler) standings(args map[string]any) (string, error) {
	season := argInt(args, "season")
	if season == 0 {
		return "", fmt.Errorf("missing required argument %q", "season")
	}
	competition := argString(args, "competition")
	if competition == "" {
		competition = soccer.CompBrasileirao
	}
	table := h.DB.Standings(season, competition)
	if len(table) == 0 {
		return fmt.Sprintf("No standings available for %d %s.", season, competition), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s standings (calculated from matches):\n", season, competition)
	for i, r := range table {
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW %dD %dL, GF %d GA %d, GD %+d)\n",
			i+1, r.Team, r.Points(), r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDifference())
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

const defaultPlayerLimit = 20

func (h *Handler) searchPlayers(args map[string]any) (string, error) {
	limit := argInt(args, "limit")
	if limit <= 0 {
		limit = defaultPlayerLimit
	}
	f := soccer.PlayerFilter{
		Name:        argString(args, "name"),
		Nationality: argString(args, "nationality"),
		Club:        argString(args, "club"),
		Position:    argString(args, "position"),
		MinOverall:  argInt(args, "min_overall"),
		Limit:       limit,
	}
	players := h.DB.FindPlayers(f)
	if len(players) == 0 {
		return "No players found for the given criteria.", nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d player(s):\n", len(players))
	for i, p := range players {
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Position: %s, Club: %s, Nationality: %s\n",
			i+1, p.Name, p.Overall, p.Position, p.Club, p.Nationality)
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

func (h *Handler) matchStatistics(args map[string]any) (string, error) {
	f := soccer.MatchFilter{
		Team:        argString(args, "team"),
		Competition: argString(args, "competition"),
		Season:      argInt(args, "season"),
	}
	avg := h.DB.AverageGoals(f)
	homeRate := h.DB.HomeWinRate(f)
	biggest := h.DB.BiggestWins(f, 5)
	if len(biggest) == 0 && avg == 0 {
		return "No matches found for the given criteria.", nil
	}

	var scope []string
	if f.Competition != "" {
		scope = append(scope, f.Competition)
	}
	if f.Season != 0 {
		scope = append(scope, fmt.Sprintf("%d", f.Season))
	}
	if f.Team != "" {
		scope = append(scope, f.Team)
	}
	title := "Match statistics"
	if len(scope) > 0 {
		title = fmt.Sprintf("Match statistics (%s)", strings.Join(scope, " "))
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%s:\n", title)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", avg)
	fmt.Fprintf(&b, "- Home win rate: %.1f%%\n", homeRate*100)
	if len(biggest) > 0 {
		b.WriteString("- Biggest victories:\n")
		for _, m := range biggest {
			fmt.Fprintf(&b, "  - %s\n", formatMatchLine(m))
		}
	}
	return strings.TrimRight(b.String(), "\n"), nil
}
