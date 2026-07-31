// format.go renders query results as the compact, human-readable text blocks
// shown in the specification's "Example answer format" sections. Every tool
// returns both this text (for the LLM to read directly) and the equivalent
// structured JSON.
package mcpsrv

import (
	"fmt"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

func writeMatches(b *strings.Builder, ms []soccer.MatchView) {
	for _, m := range ms {
		fmt.Fprintf(b, "- %s\n", m.Summary)
	}
}

func formatMatchSearch(r *soccer.MatchSearchResult) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", capitalize(r.Description))
	if r.Rivalry != "" {
		fmt.Fprintf(&b, "Derby: %s\n", r.Rivalry)
	}
	fmt.Fprintf(&b, "Matches found: %d\n\n", r.Total)
	writeMatches(&b, r.Matches)
	if r.HeadToHead != nil {
		fmt.Fprintf(&b, "\nHead-to-head in dataset: %s\n", r.HeadToHead.Line)
	} else if r.Record != nil {
		fmt.Fprintf(&b, "\nRecord: %s\n", recordLine(*r.Record))
	}
	if r.Note != "" {
		fmt.Fprintf(&b, "\nNote: %s\n", r.Note)
	}
	return b.String()
}

func recordLine(r soccer.Record) string {
	return fmt.Sprintf("%d played, %dW %dD %dL, GF %d, GA %d, %d pts, win rate %.1f%%",
		r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.Points, r.WinRate)
}

func formatHeadToHead(r *soccer.HeadToHeadResult) string {
	var b strings.Builder
	title := fmt.Sprintf("%s vs %s", r.Summary.TeamA, r.Summary.TeamB)
	if r.Rivalry != "" {
		title += fmt.Sprintf(" (%s)", r.Rivalry)
	}
	fmt.Fprintf(&b, "%s\n%s\n\n", title, strings.Repeat("-", len(title)))
	if r.Summary.Played == 0 {
		fmt.Fprintf(&b, "%s\n", r.Note)
		return b.String()
	}
	fmt.Fprintf(&b, "Head-to-head in dataset: %s\n", r.Summary.Line)
	if len(r.ByCompetition) > 0 {
		b.WriteString("\nBy competition:\n")
		for _, c := range r.ByCompetition {
			fmt.Fprintf(&b, "- %s: %d played, %s %d wins, %s %d wins, %d draws\n",
				c.Competition, c.Played, r.Summary.TeamA, c.TeamAWins, r.Summary.TeamB, c.TeamBWins, c.Draws)
		}
	}
	if r.FirstMeeting != nil {
		fmt.Fprintf(&b, "\nFirst meeting: %s\n", r.FirstMeeting.Summary)
	}
	if r.LastMeeting != nil {
		fmt.Fprintf(&b, "Most recent:   %s\n", r.LastMeeting.Summary)
	}
	if r.BiggestTeamAWin != nil {
		fmt.Fprintf(&b, "Biggest %s win: %s\n", r.Summary.TeamA, r.BiggestTeamAWin.Summary)
	}
	if r.BiggestTeamBWin != nil {
		fmt.Fprintf(&b, "Biggest %s win: %s\n", r.Summary.TeamB, r.BiggestTeamBWin.Summary)
	}
	if len(r.Matches) > 0 {
		b.WriteString("\nMeetings (most recent first):\n")
		writeMatches(&b, r.Matches)
	}
	if r.Note != "" {
		fmt.Fprintf(&b, "\nNote: %s\n", r.Note)
	}
	return b.String()
}

func formatTeamStats(r *soccer.TeamStatsResult) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s (%s)\n", r.Team.Name, r.Scope)
	if r.Note != "" && r.Overall.Played == 0 {
		fmt.Fprintf(&b, "%s\n", r.Note)
		return b.String()
	}
	fmt.Fprintf(&b, "- Matches: %d\n", r.Overall.Played)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", r.Overall.Wins, r.Overall.Draws, r.Overall.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (diff %+d)\n", r.Overall.GoalsFor, r.Overall.GoalsAgainst, r.Overall.GoalDiff)
	fmt.Fprintf(&b, "- Points: %d (%.2f per game)\n", r.Overall.Points, r.Overall.PointsPerGame)
	fmt.Fprintf(&b, "- Win rate: %.1f%%\n", r.Overall.WinRate)
	if r.Home.Played > 0 {
		fmt.Fprintf(&b, "- Home: %s\n", recordLine(r.Home))
	}
	if r.Away.Played > 0 {
		fmt.Fprintf(&b, "- Away: %s\n", recordLine(r.Away))
	}
	if len(r.RecentForm) > 0 {
		fmt.Fprintf(&b, "- Recent form (newest first): %s\n", strings.Join(r.RecentForm, " "))
	}
	if len(r.ByCompetition) > 1 {
		b.WriteString("\nBy competition:\n")
		for _, c := range r.ByCompetition {
			fmt.Fprintf(&b, "- %s (%d-%d): %s\n", c.Competition, c.FirstSeason, c.LastSeason, recordLine(c.Record))
		}
	}
	if r.BiggestWin != nil {
		fmt.Fprintf(&b, "\nBiggest win:  %s\n", r.BiggestWin.Summary)
	}
	if r.BiggestLoss != nil {
		fmt.Fprintf(&b, "Biggest loss: %s\n", r.BiggestLoss.Summary)
	}
	return b.String()
}

func formatStandings(r *soccer.StandingsResult) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s — table calculated from match results\n\n", r.Season, r.Competition)
	fmt.Fprintf(&b, "%-3s %-24s %3s %3s %3s %3s %4s %4s %4s %4s  %s\n",
		"#", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts", "")
	for _, row := range r.Table {
		fmt.Fprintf(&b, "%-3d %-24s %3d %3d %3d %3d %4d %4d %+4d %4d  %s\n",
			row.Position, row.Team, row.Played, row.Wins, row.Draws, row.Losses,
			row.GoalsFor, row.GoalsAgainst, row.GoalDiff, row.Points, row.Note)
	}
	if r.Champion != "" {
		fmt.Fprintf(&b, "\nChampion: %s\n", r.Champion)
	}
	if len(r.RelegatedTeams) > 0 {
		fmt.Fprintf(&b, "Relegated: %s\n", strings.Join(r.RelegatedTeams, ", "))
	}
	fmt.Fprintf(&b, "Matches used: %d of %d expected. Tie-breakers: %s.\n", r.MatchesUsed, r.ExpectedMatches, r.TieBreakers)
	if r.Note != "" {
		fmt.Fprintf(&b, "Note: %s\n", r.Note)
	}
	return b.String()
}

func formatBracket(r *soccer.BracketResult) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s\n\n", r.Season, r.Competition)
	for _, s := range r.Stages {
		fmt.Fprintf(&b, "%s (%d matches)\n", s.Stage, len(s.Matches))
		if len(s.Ties) > 0 {
			for _, t := range s.Ties {
				winner := t.Winner
				if winner == "" {
					winner = "decided on penalties/away goals"
				}
				fmt.Fprintf(&b, "  - %s %s %s (%d leg(s)) → %s\n", t.TeamA, t.Aggregate, t.TeamB, t.Legs, winner)
			}
		} else {
			// The group stage runs to ~100 matches; list a sample and point at
			// search_matches for the rest rather than flooding the context.
			const maxListed = 12
			for i, m := range s.Matches {
				if i == maxListed {
					fmt.Fprintf(&b, "  ... and %d more (use search_matches with stage=\"group stage\" for the full list)\n",
						len(s.Matches)-maxListed)
					break
				}
				fmt.Fprintf(&b, "  - %s\n", m.Summary)
			}
		}
		b.WriteString("\n")
	}
	if r.Champion != "" {
		fmt.Fprintf(&b, "Champion: %s\n", r.Champion)
	}
	if r.Note != "" {
		fmt.Fprintf(&b, "Note: %s\n", r.Note)
	}
	return b.String()
}

func formatAggregate(r *soccer.AggregateStatsResult) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Statistics for %s\n\n", r.Scope)
	if r.Matches == 0 {
		fmt.Fprintf(&b, "%s\n", r.Note)
		return b.String()
	}
	fmt.Fprintf(&b, "Matches: %d, goals: %d\n", r.Matches, r.Goals)
	fmt.Fprintf(&b, "Average goals per match: %.2f (home %.2f, away %.2f)\n", r.GoalsPerMatch, r.AvgHomeGoals, r.AvgAwayGoals)
	fmt.Fprintf(&b, "Home win rate: %.1f%%, draw rate: %.1f%%, away win rate: %.1f%%\n", r.HomeWinPct, r.DrawPct, r.AwayWinPct)

	if len(r.BiggestWins) > 0 {
		b.WriteString("\nBiggest victories:\n")
		writeMatches(&b, r.BiggestWins)
	}
	if len(r.HighestScoring) > 0 {
		b.WriteString("\nHighest scoring matches:\n")
		writeMatches(&b, r.HighestScoring)
	}
	writeLeaders(&b, "Top scoring teams (goals for)", r.TopScoringTeams, "%.0f goals")
	writeLeaders(&b, "Best defences (goals against per match)", r.BestDefences, "%.2f conceded/match")
	writeLeaders(&b, "Best home records (points per game)", r.BestHomeRecords, "%.2f pts/game")
	writeLeaders(&b, "Best away records (points per game)", r.BestAwayRecords, "%.2f pts/game")
	return b.String()
}

func writeLeaders(b *strings.Builder, title string, rows []soccer.TeamLeaderRow, valueFmt string) {
	if len(rows) == 0 {
		return
	}
	fmt.Fprintf(b, "\n%s:\n", title)
	for _, row := range rows {
		fmt.Fprintf(b, "%d. %s — "+valueFmt+" (%dW %dD %dL in %d)\n",
			row.Position, row.Team, row.Value, row.Record.Wins, row.Record.Draws, row.Record.Losses, row.Record.Played)
	}
}

func formatPlayers(r *soccer.PlayerSearchResult) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Players matching: %s\n", r.Description)
	fmt.Fprintf(&b, "Found: %d\n", r.Total)
	if r.AvgOverall > 0 {
		fmt.Fprintf(&b, "Average overall rating: %.1f\n", r.AvgOverall)
	}
	b.WriteString("\n")
	for i, p := range r.Players {
		fmt.Fprintf(&b, "%d. %s\n", i+1, p.Summary)
	}
	if len(r.Groups) > 0 {
		b.WriteString("\nBreakdown:\n")
		for _, gr := range r.Groups {
			fmt.Fprintf(&b, "- %s: %d players (avg rating: %.1f, best: %s %d)\n",
				gr.Key, gr.Players, gr.AvgOverall, gr.TopPlayer, gr.TopOverall)
		}
	}
	if r.Note != "" {
		fmt.Fprintf(&b, "\nNote: %s\n", r.Note)
	}
	return b.String()
}

func formatPlayerProfile(p *soccer.PlayerProfileView) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", p.Summary)
	fmt.Fprintf(&b, "- FIFA ID: %d, jersey %d\n", p.ID, p.JerseyNumber)
	if p.Height != "" || p.Weight != "" {
		fmt.Fprintf(&b, "- Height: %s, weight: %s, preferred foot: %s\n", p.Height, p.Weight, p.PreferredFoot)
	}
	if p.Value != "" {
		fmt.Fprintf(&b, "- Value: %s, wage: %s, release clause: %s\n", p.Value, p.Wage, p.ReleaseClause)
	}
	if p.Joined != "" || p.ContractUntil != "" {
		fmt.Fprintf(&b, "- Joined: %s, contract until: %s\n", p.Joined, p.ContractUntil)
	}
	fmt.Fprintf(&b, "- Work rate: %s, skill moves: %d, weak foot: %d, international reputation: %d\n",
		p.WorkRate, p.SkillMoves, p.WeakFoot, p.IntlReputation)
	if len(p.TopSkills) > 0 {
		var parts []string
		for _, s := range p.TopSkills {
			parts = append(parts, fmt.Sprintf("%s %d", s.Skill, s.Value))
		}
		fmt.Fprintf(&b, "- Best attributes: %s\n", strings.Join(parts, ", "))
	}
	if p.LinkedClubTeamID != "" {
		fmt.Fprintf(&b, "- Club is linked to team %q in the match data (%d matches on record)\n",
			p.LinkedClubTeamID, p.LinkedClubMatches)
	}
	return b.String()
}

func formatSquad(r *soccer.ClubSquadResult) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Squad for %q\n", r.Query)
	if r.LinkedTeam != nil {
		fmt.Fprintf(&b, "Linked club in match data: %s (%d matches on record)\n", r.LinkedTeam.Name, r.LinkedTeam.MatchCount)
	}
	if r.SquadSize == 0 {
		fmt.Fprintf(&b, "\n%s\n", r.Note)
		return b.String()
	}
	fmt.Fprintf(&b, "FIFA club: %s — %d players, average rating %.1f, average age %.1f\n\n",
		r.FIFAClub, r.SquadSize, r.AvgOverall, r.AvgAge)
	for i, p := range r.Squad {
		fmt.Fprintf(&b, "%d. %s\n", i+1, p.Summary)
	}
	if len(r.ByNationality) > 0 {
		b.WriteString("\nBy nationality:\n")
		for _, gr := range r.ByNationality {
			fmt.Fprintf(&b, "- %s: %d (avg %.1f)\n", gr.Key, gr.Players, gr.AvgOverall)
		}
	}
	if r.Note != "" {
		fmt.Fprintf(&b, "\nNote: %s\n", r.Note)
	}
	return b.String()
}

func capitalize(s string) string {
	if s == "" {
		return s
	}
	return strings.ToUpper(s[:1]) + s[1:]
}
