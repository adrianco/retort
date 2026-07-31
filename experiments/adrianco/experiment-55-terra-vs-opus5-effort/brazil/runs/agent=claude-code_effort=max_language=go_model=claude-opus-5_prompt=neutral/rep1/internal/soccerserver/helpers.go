// Package soccerserver wires the Brazilian football knowledge graph into an
// MCP server: it declares the tools, resources and prompts, converts loosely
// typed tool arguments into typed queries and renders the answers.
//
// helpers.go holds the argument plumbing shared by every tool.
package soccerserver

import (
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// api is the receiver every tool handler hangs off.
type api struct {
	store *soccer.Store
}

// defaultLimit and maxLimit bound every list-returning tool so a single call
// cannot flood the model's context.
const (
	defaultLimit = 20
	maxLimit     = 200
)

// resolveTeam turns free text into a canonical club, or returns a tool result
// that explains the problem (ambiguity, or a "did you mean" list).
func (a *api) resolveTeam(value, argName string) (*soccer.Team, *mcp.ToolResult) {
	team, _, err := a.store.ResolveTeam(value)
	if err == nil {
		return team, nil
	}
	var amb *soccer.AmbiguousError
	if errors.As(err, &amb) {
		return nil, mcp.ErrorResult("%q could mean several clubs: %s. Pass one of those names (or its id) in %q.",
			value, strings.Join(teamNames(amb.Candidates), ", "), argName)
	}
	var nf *soccer.NotFoundError
	if errors.As(err, &nf) {
		if len(nf.Suggestions) > 0 {
			return nil, mcp.ErrorResult("no club called %q is in the data. Did you mean: %s?",
				value, strings.Join(nf.Suggestions, ", "))
		}
		return nil, mcp.ErrorResult("no club called %q is in the data; call list_teams to see what is available.", value)
	}
	return nil, mcp.ErrorResult("could not resolve %s=%q: %v", argName, value, err)
}

func teamNames(ts []*soccer.Team) []string {
	out := make([]string, 0, len(ts))
	for _, t := range ts {
		out = append(out, fmt.Sprintf("%s (%s)", t.Name, t.ID))
	}
	return out
}

// resolveCompetition maps free text to a competition id.
func (a *api) resolveCompetition(value string) (string, *mcp.ToolResult) {
	if strings.TrimSpace(value) == "" {
		return "", nil
	}
	id, ok := soccer.ResolveCompetition(value)
	if !ok {
		return "", mcp.ErrorResult("unknown competition %q; available: %s", value, strings.Join(a.competitionNames(), ", "))
	}
	if len(a.store.CompetitionMatches(id)) == 0 {
		return "", mcp.ErrorResult("competition %q has no matches in the provided data", value)
	}
	return id, nil
}

func (a *api) competitionNames() []string {
	var out []string
	for _, c := range a.store.CompetitionsWithData() {
		out = append(out, fmt.Sprintf("%s (%s)", c.Short, c.ID))
	}
	return out
}

// parseDateArg accepts ISO or Brazilian dates.
func parseDateArg(value, argName string) (time.Time, *mcp.ToolResult) {
	if strings.TrimSpace(value) == "" {
		return time.Time{}, nil
	}
	t, _, ok := soccer.ParseDate(value)
	if !ok {
		return time.Time{}, mcp.ErrorResult("%s=%q is not a date I understand; use YYYY-MM-DD", argName, value)
	}
	return t, nil
}

// parseEndOfDay parses an upper bound. A plain date means the whole of that
// day: matches carry a kick-off time, so date_to=2019-05-26 has to include the
// 16:00 fixture, not stop at midnight.
func parseEndOfDay(value, argName string) (time.Time, *mcp.ToolResult) {
	if strings.TrimSpace(value) == "" {
		return time.Time{}, nil
	}
	t, hasTime, ok := soccer.ParseDate(value)
	if !ok {
		return time.Time{}, mcp.ErrorResult("%s=%q is not a date I understand; use YYYY-MM-DD", argName, value)
	}
	if !hasTime {
		t = endOfDay(t)
	}
	return t, nil
}

// endOfDay returns the last instant of the day t falls in.
func endOfDay(t time.Time) time.Time {
	return t.AddDate(0, 0, 1).Add(-time.Second)
}

// commonFilterProps are the match filter arguments shared by several tools.
func commonFilterProps() map[string]*mcp.Prop {
	return map[string]*mcp.Prop{
		"competition": mcp.Str("Competition to restrict to: brasileirao, serie-b, serie-c, copa-do-brasil or libertadores. Free text such as \"Serie A\" is accepted."),
		"season":      mcp.Int("Single season (year), e.g. 2019."),
		"season_from": mcp.Int("First season of a range (inclusive)."),
		"season_to":   mcp.Int("Last season of a range (inclusive)."),
		"date_from":   mcp.Str("Earliest match date, YYYY-MM-DD."),
		"date_to":     mcp.Str("Latest match date, YYYY-MM-DD."),
	}
}

// applyCommonFilters fills the shared filter fields from the arguments.
func (a *api) applyCommonFilters(args mcp.Args, f *soccer.MatchFilter) *mcp.ToolResult {
	comp, errRes := a.resolveCompetition(args.String("competition"))
	if errRes != nil {
		return errRes
	}
	f.CompetitionID = comp

	season, err := args.Int("season", 0)
	if err != nil {
		return mcp.ErrorResult("%v", err)
	}
	f.Season = season
	if f.SeasonFrom, err = args.Int("season_from", 0); err != nil {
		return mcp.ErrorResult("%v", err)
	}
	if f.SeasonTo, err = args.Int("season_to", 0); err != nil {
		return mcp.ErrorResult("%v", err)
	}
	from, errRes := parseDateArg(args.String("date_from"), "date_from")
	if errRes != nil {
		return errRes
	}
	to, errRes := parseEndOfDay(args.String("date_to"), "date_to")
	if errRes != nil {
		return errRes
	}
	f.From, f.To = from, to
	if !f.From.IsZero() && !f.To.IsZero() && f.To.Before(f.From) {
		return mcp.ErrorResult("date_to (%s) is before date_from (%s)", args.String("date_to"), args.String("date_from"))
	}
	if f.SeasonFrom != 0 && f.SeasonTo != 0 && f.SeasonTo < f.SeasonFrom {
		return mcp.ErrorResult("season_to (%d) is before season_from (%d)", f.SeasonTo, f.SeasonFrom)
	}
	return nil
}

// limitArg reads a bounded limit argument.
func limitArg(args mcp.Args, def int) (int, *mcp.ToolResult) {
	limit, err := args.Int("limit", def)
	if err != nil {
		return 0, mcp.ErrorResult("%v", err)
	}
	if limit <= 0 {
		limit = def
	}
	if limit > maxLimit {
		limit = maxLimit
	}
	return limit, nil
}

// scopeLabel describes the active filters in prose, for answer headings.
func scopeLabel(f soccer.MatchFilter) string {
	var parts []string
	if f.CompetitionID != "" {
		parts = append(parts, soccer.CompetitionLabel(f.CompetitionID))
	}
	switch {
	case f.Season != 0:
		parts = append(parts, fmt.Sprint(f.Season))
	case f.SeasonFrom != 0 && f.SeasonTo != 0:
		parts = append(parts, fmt.Sprintf("%d-%d", f.SeasonFrom, f.SeasonTo))
	case f.SeasonFrom != 0:
		parts = append(parts, fmt.Sprintf("from %d", f.SeasonFrom))
	case f.SeasonTo != 0:
		parts = append(parts, fmt.Sprintf("until %d", f.SeasonTo))
	}
	if !f.From.IsZero() || !f.To.IsZero() {
		switch {
		case !f.From.IsZero() && !f.To.IsZero():
			parts = append(parts, fmt.Sprintf("%s to %s", f.From.Format("2006-01-02"), f.To.Format("2006-01-02")))
		case !f.From.IsZero():
			parts = append(parts, "since "+f.From.Format("2006-01-02"))
		default:
			parts = append(parts, "until "+f.To.Format("2006-01-02"))
		}
	}
	if f.Stage != "" {
		parts = append(parts, f.Stage)
	}
	if f.Round != 0 {
		parts = append(parts, fmt.Sprintf("round %d", f.Round))
	}
	if len(parts) == 0 {
		return "all competitions and seasons in the data"
	}
	return strings.Join(parts, ", ")
}

// matchesJSON renders matches for the structuredContent field.
func matchesJSON(ms []*soccer.Match) []map[string]any {
	out := make([]map[string]any, 0, len(ms))
	for _, m := range ms {
		item := map[string]any{
			"id":          m.ID,
			"date":        m.DateString(),
			"competition": m.CompetitionID,
			"season":      m.Season,
			"home_team":   m.HomeName,
			"away_team":   m.AwayName,
			"home_id":     m.HomeTeamID,
			"away_id":     m.AwayTeamID,
			"home_goals":  m.HomeGoals,
			"away_goals":  m.AwayGoals,
			"outcome":     string(m.Outcome()),
			"sources":     m.Sources,
		}
		if r := m.RoundLabel(); r != "" {
			item["round"] = r
		}
		if m.Venue != "" {
			item["venue"] = m.Venue
		}
		if m.Stats != nil {
			item["stats"] = m.Stats
		}
		out = append(out, item)
	}
	return out
}

func playersJSON(ps []*soccer.Player) []map[string]any {
	out := make([]map[string]any, 0, len(ps))
	for _, p := range ps {
		out = append(out, map[string]any{
			"id":          p.ID,
			"name":        p.Name,
			"overall":     p.Overall,
			"potential":   p.Potential,
			"position":    p.Position,
			"group":       p.PositionGroup(),
			"club":        p.Club,
			"team_id":     p.TeamID,
			"nationality": p.Nationality,
			"age":         p.Age,
			"value":       p.Value,
		})
	}
	return out
}
