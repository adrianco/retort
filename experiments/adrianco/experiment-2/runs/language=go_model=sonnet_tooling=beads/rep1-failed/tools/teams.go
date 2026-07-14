package tools

import (
	"context"
	"fmt"
	"sort"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"brazilian-soccer-mcp/data"
)

// RegisterTeamTools registers team statistics MCP tools.
func RegisterTeamTools(s *server.MCPServer, store *data.Store) {
	s.AddTool(mcp.NewTool("team_stats",
		mcp.WithDescription("Get win/loss/draw record and goals stats for a team. Optionally filter by season and competition."),
		mcp.WithString("team", mcp.Description("Team name"), mcp.Required()),
		mcp.WithNumber("season", mcp.Description("Season year (0 = all seasons)")),
		mcp.WithString("competition",
			mcp.Description("Filter competition: 'brasileirao', 'cup', 'libertadores', 'all' (default 'all')"),
			mcp.DefaultString("all"),
		),
		mcp.WithString("venue",
			mcp.Description("Filter by venue: 'home', 'away', 'all' (default 'all')"),
			mcp.DefaultString("all"),
		),
	), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return teamStats(store, req)
	})

	s.AddTool(mcp.NewTool("top_teams",
		mcp.WithDescription("Rank teams by wins, goals scored, or points in a season."),
		mcp.WithNumber("season", mcp.Description("Season year (0 = all seasons)")),
		mcp.WithString("competition",
			mcp.Description("Competition: 'brasileirao', 'cup', 'libertadores', 'all'"),
			mcp.DefaultString("brasileirao"),
		),
		mcp.WithString("rank_by",
			mcp.Description("Ranking metric: 'points', 'wins', 'goals_scored', 'goal_diff' (default 'points')"),
			mcp.DefaultString("points"),
		),
		mcp.WithNumber("limit", mcp.Description("Max teams to show (default 20)")),
	), func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		return topTeams(store, req)
	})
}

type teamRecord struct {
	team                               string
	played, wins, draws, losses        int
	goalsFor, goalsAgainst, goalsDiff  int
	homeWins, homeDraws, homeLosses    int
	awayWins, awayDraws, awayLosses    int
}

func (r *teamRecord) points() int { return r.wins*3 + r.draws }

func buildRecord(store *data.Store, teamQuery, competition string, season int) map[string]*teamRecord {
	records := make(map[string]*teamRecord)

	get := func(name string) *teamRecord {
		if _, ok := records[name]; !ok {
			records[name] = &teamRecord{team: name}
		}
		return records[name]
	}

	process := func(home, away string, hg, ag, s int, comp string) {
		if competition != "all" && comp != competition {
			return
		}
		if season != 0 && s != season {
			return
		}
		hn := data.NormalizeTeam(home)
		an := data.NormalizeTeam(away)

		if teamQuery != "" && !data.TeamMatches(home, teamQuery) && !data.TeamMatches(away, teamQuery) {
			return
		}

		hr := get(hn)
		ar := get(an)

		hr.played++
		ar.played++
		hr.goalsFor += hg
		hr.goalsAgainst += ag
		ar.goalsFor += ag
		ar.goalsAgainst += hg

		switch {
		case hg > ag:
			hr.wins++
			hr.homeWins++
			ar.losses++
			ar.awayLosses++
		case ag > hg:
			ar.wins++
			ar.awayWins++
			hr.losses++
			hr.homeLosses++
		default:
			hr.draws++
			hr.homeDraws++
			ar.draws++
			ar.awayDraws++
		}
	}

	if competition == "all" || competition == "brasileirao" {
		for _, m := range store.BrasileiraoMatches {
			process(m.HomeTeam, m.AwayTeam, m.HomeGoal, m.AwayGoal, m.Season, "brasileirao")
		}
		for _, m := range store.HistoricalMatches {
			process(m.HomeTeam, m.AwayTeam, m.HomeGoals, m.AwayGoals, m.Year, "brasileirao")
		}
	}
	if competition == "all" || competition == "cup" {
		for _, m := range store.CupMatches {
			process(m.HomeTeam, m.AwayTeam, m.HomeGoal, m.AwayGoal, m.Season, "cup")
		}
	}
	if competition == "all" || competition == "libertadores" {
		for _, m := range store.LibertadoresMatches {
			process(m.HomeTeam, m.AwayTeam, m.HomeGoal, m.AwayGoal, m.Season, "libertadores")
		}
	}

	for _, r := range records {
		r.goalsDiff = r.goalsFor - r.goalsAgainst
	}

	return records
}

func teamStats(store *data.Store, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	args := req.GetArguments()
	team, _ := args["team"].(string)
	seasonF, _ := args["season"].(float64)
	season := int(seasonF)
	competition, _ := args["competition"].(string)
	if competition == "" {
		competition = "all"
	}
	venue, _ := args["venue"].(string)
	if venue == "" {
		venue = "all"
	}

	if team == "" {
		return mcp.NewToolResultText("team parameter is required."), nil
	}

	records := buildRecord(store, team, competition, season)

	// Find the matching record
	var rec *teamRecord
	for name, r := range records {
		if data.TeamMatches(name, team) {
			if rec == nil || r.played > rec.played {
				rec = r
			}
		}
	}

	if rec == nil || rec.played == 0 {
		return mcp.NewToolResultText(fmt.Sprintf("No matches found for team '%s' with given filters.", team)), nil
	}

	var sb strings.Builder
	compDesc := competition
	if competition == "all" {
		compDesc = "all competitions"
	} else {
		compDesc = compLabel(competition)
	}
	seasonDesc := "all seasons"
	if season != 0 {
		seasonDesc = fmt.Sprintf("%d", season)
	}

	sb.WriteString(fmt.Sprintf("%s — %s, %s\n\n", rec.team, compDesc, seasonDesc))
	sb.WriteString(fmt.Sprintf("Overall:  P=%d  W=%d  D=%d  L=%d  GF=%d  GA=%d  GD=%+d  Pts=%d\n",
		rec.played, rec.wins, rec.draws, rec.losses,
		rec.goalsFor, rec.goalsAgainst, rec.goalsDiff, rec.points()))

	if venue == "all" || venue == "home" {
		hp := rec.homeWins + rec.homeDraws + rec.homeLosses
		sb.WriteString(fmt.Sprintf("Home:     P=%d  W=%d  D=%d  L=%d\n", hp, rec.homeWins, rec.homeDraws, rec.homeLosses))
	}
	if venue == "all" || venue == "away" {
		ap := rec.awayWins + rec.awayDraws + rec.awayLosses
		sb.WriteString(fmt.Sprintf("Away:     P=%d  W=%d  D=%d  L=%d\n", ap, rec.awayWins, rec.awayDraws, rec.awayLosses))
	}
	if rec.played > 0 {
		winRate := float64(rec.wins) / float64(rec.played) * 100
		sb.WriteString(fmt.Sprintf("Win rate: %.1f%%\n", winRate))
	}

	return mcp.NewToolResultText(sb.String()), nil
}

func topTeams(store *data.Store, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	args := req.GetArguments()
	seasonF, _ := args["season"].(float64)
	season := int(seasonF)
	competition, _ := args["competition"].(string)
	if competition == "" {
		competition = "brasileirao"
	}
	rankBy, _ := args["rank_by"].(string)
	if rankBy == "" {
		rankBy = "points"
	}
	limitF, _ := args["limit"].(float64)
	limit := int(limitF)
	if limit <= 0 {
		limit = 20
	}

	records := buildRecord(store, "", competition, season)

	type entry struct {
		r     *teamRecord
		score int
	}
	var list []entry
	for _, r := range records {
		var score int
		switch rankBy {
		case "wins":
			score = r.wins
		case "goals_scored":
			score = r.goalsFor
		case "goal_diff":
			score = r.goalsDiff
		default:
			score = r.points()
		}
		list = append(list, entry{r, score})
	}

	sort.Slice(list, func(i, j int) bool {
		if list[i].score != list[j].score {
			return list[i].score > list[j].score
		}
		return list[i].r.goalsDiff > list[j].r.goalsDiff
	})

	if len(list) > limit {
		list = list[:limit]
	}

	var sb strings.Builder
	compDesc := compLabel(competition)
	seasonDesc := "all seasons"
	if season != 0 {
		seasonDesc = fmt.Sprintf("%d", season)
	}
	sb.WriteString(fmt.Sprintf("Top teams — %s, %s (ranked by %s):\n\n", compDesc, seasonDesc, rankBy))
	sb.WriteString(fmt.Sprintf("%-3s  %-28s  %4s  %4s  %4s  %4s  %4s  %4s  %4s  %4s\n",
		"#", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"))
	sb.WriteString(strings.Repeat("-", 80) + "\n")

	for i, e := range list {
		r := e.r
		sb.WriteString(fmt.Sprintf("%-3d  %-28s  %4d  %4d  %4d  %4d  %4d  %4d  %+4d  %4d\n",
			i+1, truncate(r.team, 28),
			r.played, r.wins, r.draws, r.losses,
			r.goalsFor, r.goalsAgainst, r.goalsDiff, r.points()))
	}

	return mcp.NewToolResultText(sb.String()), nil
}

func truncate(s string, n int) string {
	runes := []rune(s)
	if len(runes) <= n {
		return s
	}
	return string(runes[:n-1]) + "…"
}
