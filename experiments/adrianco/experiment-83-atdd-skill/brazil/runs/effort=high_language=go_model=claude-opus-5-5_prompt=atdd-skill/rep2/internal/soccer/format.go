package soccer

import (
	"fmt"
	"strings"
)

// Text renderings of each answer, written for a language model (or a
// person) to read.

func MatchLine(m MatchView) string {
	where := m.Competition
	switch {
	case m.Stage != "" && m.Stage != "group stage":
		where += ", " + m.Stage
	case m.Round > 0 && m.Competition != Libertadores:
		where += fmt.Sprintf(" Round %d", m.Round)
	}
	line := fmt.Sprintf("%s: %s %d-%d %s (%s)", m.Date, m.Home, m.HomeGoals, m.AwayGoals, m.Away, where)
	if m.Arena != "" {
		line += " at " + m.Arena
	}
	if st := m.Statistics; st != nil {
		line += fmt.Sprintf(" [corners %d-%d, shots %d-%d]", st.HomeCorners, st.AwayCorners, st.HomeShots, st.AwayShots)
	}
	return line
}

func (a MatchesAnswer) Text() string {
	var b strings.Builder
	if a.Message != "" {
		b.WriteString(a.Message + ".\n")
	}
	q := a.criteria
	title := "Matches"
	switch {
	case q.Team != "" && q.Opponent != "" && a.HeadToHead != nil:
		title = a.HeadToHead.Team + " vs " + a.HeadToHead.Opponent
	case q.Team != "":
		title = "Matches involving " + q.Team
	}
	var filters []string
	if q.Competition != "" {
		filters = append(filters, q.Competition)
	}
	if q.Season != 0 {
		filters = append(filters, fmt.Sprint(q.Season))
	}
	if q.Venue == "home" || q.Venue == "away" {
		filters = append(filters, q.Venue+" only")
	}
	if q.Stage != "" {
		filters = append(filters, "stage: "+q.Stage)
	}
	if !q.From.IsZero() || !q.To.IsZero() {
		filters = append(filters, fmt.Sprintf("between %s and %s", dateOr(q.From.Format("2006-01-02"), q.From.IsZero()), dateOr(q.To.Format("2006-01-02"), q.To.IsZero())))
	}
	if len(filters) > 0 {
		title += " (" + strings.Join(filters, ", ") + ")"
	}
	if a.Total == 0 {
		b.WriteString(title + ": no matches found in the dataset.\n")
		return b.String()
	}
	fmt.Fprintf(&b, "%s: %d match(es) found", title, a.Total)
	if a.Shown < a.Total {
		fmt.Fprintf(&b, ", showing the %d most recent", a.Shown)
	}
	b.WriteString("\n")
	for _, m := range a.Matches {
		b.WriteString("- " + MatchLine(m) + "\n")
	}
	if a.Shown < a.Total {
		fmt.Fprintf(&b, "- ... (%d more matches in dataset)\n", a.Total-a.Shown)
	}
	if h := a.HeadToHead; h != nil {
		fmt.Fprintf(&b, "\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws (goals %d-%d)\n",
			h.Team, h.TeamWins, h.Opponent, h.OpponentWins, h.Draws, h.TeamGoals, h.OpponentGoals)
	}
	return b.String()
}

func dateOr(s string, zero bool) string {
	if zero {
		return "any date"
	}
	return s
}

func recordLines(b *strings.Builder, r Record) {
	fmt.Fprintf(b, "- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d (difference %+d)\n- Points: %d\n- Win rate: %.1f%%\n",
		r.Matches, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDifference, r.Points, r.WinRate)
}

func (a TeamRecordAnswer) Text() string {
	var b strings.Builder
	scope := []string{}
	if a.Season != 0 {
		scope = append(scope, fmt.Sprint(a.Season))
	}
	if a.Competition != "" {
		scope = append(scope, a.Competition)
	} else {
		scope = append(scope, "all competitions")
	}
	kind := "record"
	if a.Venue == "home" || a.Venue == "away" {
		kind = a.Venue + " record"
	}
	fmt.Fprintf(&b, "%s %s (%s):\n", a.Team, kind, strings.Join(scope, " "))
	recordLines(&b, a.Record)
	return b.String()
}

func (a HeadToHeadAnswer) Text() string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s head-to-head", a.TeamA, a.TeamB)
	if a.Competition != "" || a.Season != 0 {
		fmt.Fprintf(&b, " (%s)", strings.TrimSpace(a.Competition+" "+seasonText(a.Season)))
	}
	fmt.Fprintf(&b, ":\n- Matches: %d\n- %s wins: %d\n- %s wins: %d\n- Draws: %d\n- Goals: %s %d, %s %d\n",
		a.Matches, a.TeamA, a.TeamAWins, a.TeamB, a.TeamBWins, a.Draws, a.TeamA, a.TeamAGoals, a.TeamB, a.TeamBGoals)
	if len(a.RecentMatches) > 0 {
		b.WriteString("\nMost recent meetings:\n")
		for _, m := range a.RecentMatches {
			b.WriteString("- " + MatchLine(m) + "\n")
		}
	}
	if len(a.BiggestWins) > 0 {
		b.WriteString("\nBiggest wins in this fixture:\n")
		for _, m := range a.BiggestWins {
			b.WriteString("- " + MatchLine(m) + "\n")
		}
	}
	return b.String()
}

func seasonText(y int) string {
	if y == 0 {
		return ""
	}
	return fmt.Sprint(y)
}

var metricNames = map[string]string{
	"goals_for": "goals scored", "goals_against": "goals conceded (fewest first)", "win_rate": "win rate",
	"points": "points", "wins": "wins", "goal_difference": "goal difference", "points_per_game": "points per game",
}

func (a RankingAnswer) Text() string {
	var b strings.Builder
	fmt.Fprintf(&b, "Teams ranked by %s", metricNames[a.Metric])
	var scope []string
	if a.Competition != "" {
		scope = append(scope, a.Competition)
	}
	if a.Season != 0 {
		scope = append(scope, fmt.Sprint(a.Season))
	}
	if a.Venue != "all" {
		scope = append(scope, a.Venue+" matches")
	}
	if a.MinMatches > 1 {
		scope = append(scope, fmt.Sprintf("minimum %d matches", a.MinMatches))
	}
	if len(scope) > 0 {
		b.WriteString(" (" + strings.Join(scope, ", ") + ")")
	}
	b.WriteString(":\n")
	if len(a.Ranking) == 0 {
		b.WriteString("No teams match.\n")
	}
	for _, e := range a.Ranking {
		value := fmt.Sprintf("%g", e.Value)
		if a.Metric == "win_rate" {
			value = fmt.Sprintf("%.1f%%", e.Value)
		}
		fmt.Fprintf(&b, "%d. %s - %s (%d matches: %dW %dD %dL, goals %d-%d)\n",
			e.Position, e.Team, value, e.Matches, e.Wins, e.Draws, e.Losses, e.GoalsFor, e.GoalsAgainst)
	}
	return b.String()
}

func (a TeamCompetitionsAnswer) Text() string {
	var b strings.Builder
	fmt.Fprintf(&b, "Competitions %s has played in (provided data):\n", a.Team)
	for _, c := range a.Competitions {
		fmt.Fprintf(&b, "- %s: %d matches (%dW %dD %dL), seasons %s\n", c.Competition, c.Matches, c.Wins, c.Draws, c.Losses, yearsText(c.Seasons))
	}
	if len(a.Competitions) == 0 {
		b.WriteString("- none found\n")
	}
	return b.String()
}

func yearsText(ys []int) string {
	if len(ys) == 0 {
		return ""
	}
	parts := []string{}
	start, prev := ys[0], ys[0]
	flush := func() {
		if start == prev {
			parts = append(parts, fmt.Sprint(start))
		} else {
			parts = append(parts, fmt.Sprintf("%d-%d", start, prev))
		}
	}
	for _, y := range ys[1:] {
		if y == prev+1 {
			prev = y
			continue
		}
		flush()
		start, prev = y, y
	}
	flush()
	return strings.Join(parts, ", ")
}

func (a TeamOverviewAnswer) Text() string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s overview (all competitions in the provided data):\n", a.Team)
	recordLines(&b, a.Record)
	fmt.Fprintf(&b, "- Home: %dW %dD %dL (win rate %.1f%%); Away: %dW %dD %dL (win rate %.1f%%)\n",
		a.HomeRecord.Wins, a.HomeRecord.Draws, a.HomeRecord.Losses, a.HomeRecord.WinRate,
		a.AwayRecord.Wins, a.AwayRecord.Draws, a.AwayRecord.Losses, a.AwayRecord.WinRate)
	if len(a.Competitions) > 0 {
		b.WriteString("\nBy competition:\n")
		for _, c := range a.Competitions {
			fmt.Fprintf(&b, "- %s: %d matches, %dW %dD %dL, seasons %s\n", c.Competition, c.Matches, c.Wins, c.Draws, c.Losses, yearsText(c.Seasons))
		}
	}
	if len(a.RecentMatches) > 0 {
		b.WriteString("\nMost recent matches:\n")
		for _, m := range a.RecentMatches {
			b.WriteString("- " + MatchLine(m) + "\n")
		}
	}
	if a.Squad.Players > 0 {
		fmt.Fprintf(&b, "\nSquad in FIFA ratings (%s): %d players, average rating %.1f\n", a.Squad.FIFAClub, a.Squad.Players, a.Squad.AverageOverall)
		for i, p := range a.Squad.TopPlayers {
			fmt.Fprintf(&b, "%d. %s\n", i+1, PlayerLine(p))
		}
	} else {
		b.WriteString("\nNo players for this club in the FIFA ratings.\n")
	}
	return b.String()
}

func (a StandingsAnswer) Text() string {
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s Final Standings (calculated from %d matches):\n", a.Season, a.Competition, a.Matches)
	for _, r := range a.Table {
		note := ""
		if r.Position == 1 {
			note = " - Champion"
		}
		for _, t := range a.Relegated {
			if t == r.Team {
				note = " - Relegated"
			}
		}
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL, GF %d, GA %d, GD %+d)%s\n",
			r.Position, r.Team, r.Points, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDifference, note)
	}
	if len(a.Relegated) > 0 {
		fmt.Fprintf(&b, "\nRelegation zone (bottom four): %s\n", strings.Join(a.Relegated, ", "))
	}
	return b.String()
}

func (a BracketAnswer) Text() string {
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s knockout bracket (aggregate scores):\n", a.Season, a.Competition)
	for _, st := range a.Stages {
		fmt.Fprintf(&b, "\n%s:\n", strings.ToUpper(st.Stage[:1])+st.Stage[1:])
		for _, t := range st.Ties {
			winner := "level on aggregate (decided by penalties or away goals)"
			if t.Winner != "" {
				winner = t.Winner + " advance"
				if st.Stage == "final" {
					winner = t.Winner + " win the title"
				}
			}
			fmt.Fprintf(&b, "- %s %d-%d %s: %s\n", t.TeamA, t.TeamAGoals, t.TeamBGoals, t.TeamB, winner)
			for _, l := range t.Legs {
				fmt.Fprintf(&b, "    %s: %s %d-%d %s\n", l.Date, l.Home, l.HomeGoals, l.AwayGoals, l.Away)
			}
		}
	}
	return b.String()
}

func statsLines(b *strings.Builder, s CompetitionStats) {
	fmt.Fprintf(b, "- Matches: %d, Goals: %d\n- Average goals per match: %.2f\n- Home win rate: %.1f%%, Draw rate: %.1f%%, Away win rate: %.1f%%\n",
		s.Matches, s.Goals, s.AverageGoalsPerMatch, s.HomeWinRate, s.DrawRate, s.AwayWinRate)
}

func (s CompetitionStats) Text() string {
	var b strings.Builder
	scope := strings.TrimSpace(s.Competition + " " + seasonText(s.Season))
	if scope == "" {
		scope = "all competitions"
	}
	fmt.Fprintf(&b, "Statistics for %s (provided data):\n", scope)
	statsLines(&b, s)
	return b.String()
}

func (a SeasonComparison) Text() string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s season comparison:\n", a.Competition)
	for _, s := range a.Seasons {
		fmt.Fprintf(&b, "\n%d:\n", s.Season)
		if s.Matches == 0 {
			b.WriteString("- no matches in the data\n")
			continue
		}
		statsLines(&b, s)
		if s.Champion != "" {
			fmt.Fprintf(&b, "- Champion: %s (%d pts)\n- Top scoring team: %s (%d goals)\n", s.Champion, s.ChampionPoints, s.TopScoringTeam, s.TopScoringTeamGoals)
		}
	}
	return b.String()
}

func (a BiggestWinsAnswer) Text() string {
	var b strings.Builder
	scope := strings.TrimSpace(strings.Join([]string{a.Team, a.Competition, seasonText(a.Season)}, " "))
	if scope == "" {
		scope = "all competitions"
	}
	fmt.Fprintf(&b, "Biggest victories (%s, provided data):\n", scope)
	for i, m := range a.Matches {
		fmt.Fprintf(&b, "%d. %s\n", i+1, MatchLine(m))
	}
	if len(a.Matches) == 0 {
		b.WriteString("No wins found.\n")
	}
	return b.String()
}

func (a DerbiesAnswer) Text() string {
	var b strings.Builder
	scope := strings.TrimSpace(a.Competition + " " + seasonText(a.Season))
	if scope == "" {
		scope = "all seasons"
	}
	fmt.Fprintf(&b, "Derbies (%s): %d found\n", scope, a.Total)
	for _, d := range a.Derbies {
		fmt.Fprintf(&b, "- %s: %s\n", d.Derby, MatchLine(d.Match))
	}
	return b.String()
}

func PlayerLine(p Player) string {
	club := p.Club
	if club == "" {
		club = "no club"
	}
	return fmt.Sprintf("%s - Overall: %d, Potential: %d, Position: %s, Age: %d, Nationality: %s, Club: %s",
		p.Name, p.Overall, p.Potential, dash(p.Position), p.Age, p.Nationality, club)
}

func dash(s string) string {
	if s == "" {
		return "-"
	}
	return s
}

func (a PlayersAnswer) Text() string {
	var b strings.Builder
	if a.Total == 0 {
		msg := a.Message
		if msg == "" {
			msg = "no players match"
		}
		b.WriteString(strings.ToUpper(msg[:1]) + msg[1:] + ".\n")
		if len(a.Suggestions) > 0 {
			b.WriteString("Did you mean:\n")
			for _, p := range a.Suggestions {
				b.WriteString("- " + PlayerLine(p) + "\n")
			}
		}
		return b.String()
	}
	fmt.Fprintf(&b, "%d player(s) found", a.Total)
	if len(a.Players) < a.Total {
		fmt.Fprintf(&b, ", top %d by rating", len(a.Players))
	}
	b.WriteString(":\n")
	for i, p := range a.Players {
		fmt.Fprintf(&b, "%d. %s", i+1, PlayerLine(p))
		if p.Height != "" || p.Weight != "" {
			fmt.Fprintf(&b, ", Height: %s, Weight: %s", dash(p.Height), dash(p.Weight))
		}
		if p.Value != "" {
			fmt.Fprintf(&b, ", Value: %s", p.Value)
		}
		b.WriteString("\n")
	}
	return b.String()
}

func (a ClubsAnswer) Text() string {
	var b strings.Builder
	who := "Players"
	if a.Nationality != "" {
		who = "Players from " + a.Nationality
	}
	where := "by club"
	if a.BrazilianClubsOnly {
		where = "at Brazilian clubs (clubs that have played in the Brasileirão Série A)"
	}
	fmt.Fprintf(&b, "%s %s: %d players at %d clubs\n", who, where, a.TotalPlayers, a.TotalClubs)
	if len(a.Clubs) < a.TotalClubs {
		fmt.Fprintf(&b, "(showing the top %d clubs)\n", len(a.Clubs))
	}
	for _, c := range a.Clubs {
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %.1f, best: %s %d)\n", c.Club, c.Players, c.AverageOverall, c.BestPlayer, c.BestOverall)
	}
	return b.String()
}

func DatasetsText(ds []Dataset, matches, unplayed, players int) string {
	var b strings.Builder
	b.WriteString("Datasets loaded:\n")
	for _, d := range ds {
		status := fmt.Sprintf("%d records", d.Records)
		if !d.Loaded {
			status = "NOT LOADED: " + d.Error
		}
		fmt.Fprintf(&b, "- %s (%s): %s - %s\n", d.Name, d.File, status, d.Description)
	}
	fmt.Fprintf(&b, "\nAfter merging records of the same match across datasets: %d matches with results (%d fixtures without a recorded score excluded); %d players.\n",
		matches, unplayed, players)
	return b.String()
}
