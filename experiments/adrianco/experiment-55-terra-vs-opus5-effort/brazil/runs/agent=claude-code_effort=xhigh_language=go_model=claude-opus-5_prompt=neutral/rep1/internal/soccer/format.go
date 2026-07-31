// format.go renders query results as the readable text an LLM can quote back to
// a user, mirroring the answer formats in the specification.
//
// Every MCP tool returns both a structured JSON payload and one of these
// renderings: the JSON so a client can compute with the answer, the text so the
// model does not have to invent a presentation for it.
package soccer

import (
	"fmt"
	"strings"
)

// report is a small line-oriented text builder.
type report struct{ b strings.Builder }

func (r *report) line(format string, args ...any) {
	fmt.Fprintf(&r.b, format, args...)
	r.b.WriteByte('\n')
}

func (r *report) blank() { r.b.WriteByte('\n') }

func (r *report) list(items []string, prefix string) {
	for _, it := range items {
		r.line("%s%s", prefix, it)
	}
}

func (r *report) String() string { return strings.TrimRight(r.b.String(), "\n") }

// FormatMatchSearch renders a match list with an optional head-to-head footer.
func FormatMatchSearch(res *MatchSearchResult) string {
	var r report
	r.line("Matches: %s", res.Query)
	r.line("Found %d match(es).", res.TotalMatches)
	if len(res.Matches) > 0 {
		r.blank()
		for _, m := range res.Matches {
			r.line("- %s", m.Line)
		}
	}
	if res.HeadToHead != nil {
		r.blank()
		r.line("Head-to-head in dataset: %s", res.HeadToHead.Summary)
		for comp, rec := range res.HeadToHead.ByCompetition {
			r.line("  %s: %s", comp, rec)
		}
	}
	if res.Note != "" {
		r.blank()
		r.line("%s", res.Note)
	}
	return r.String()
}

// FormatHeadToHead renders a two club comparison.
func FormatHeadToHead(res *HeadToHeadResult) string {
	var r report
	plain := fmt.Sprintf("%s vs %s", res.Summary.TeamA, res.Summary.TeamB)
	title := plain
	if res.Rivalry != "" {
		title += fmt.Sprintf(" (%s)", res.Rivalry)
	}
	if res.Scope != "" && res.Scope != plain {
		title += " - " + res.Scope
	}
	r.line("%s", title)
	r.line("Matches: %d", res.Summary.Matches)
	r.line("%s", res.Summary.Summary)
	if res.Summary.FirstMeeting != "" {
		r.line("First meeting: %s, last meeting: %s", res.Summary.FirstMeeting, res.Summary.LastMeeting)
	}
	if res.HomeRecordA != "" {
		r.line("%s", res.HomeRecordA)
		r.line("%s", res.HomeRecordB)
	}
	if res.RecentForm != "" {
		r.line("%s recent form (most recent first): %s", res.Summary.TeamA, res.RecentForm)
	}
	if len(res.Summary.ByCompetition) > 0 {
		r.blank()
		r.line("By competition:")
		for comp, rec := range res.Summary.ByCompetition {
			r.line("  %s - %s (wins-draws-losses for %s)", comp, rec, res.Summary.TeamA)
		}
	}
	if res.BiggestWinA != nil {
		r.blank()
		r.line("Biggest %s win: %s", res.Summary.TeamA, res.BiggestWinA.Line)
	}
	if res.BiggestWinB != nil {
		r.line("Biggest %s win: %s", res.Summary.TeamB, res.BiggestWinB.Line)
	}
	if len(res.Matches) > 0 {
		r.blank()
		r.line("Matches (%d of %d shown, newest first):", len(res.Matches), res.TotalMatches)
		for _, m := range res.Matches {
			r.line("- %s", m.Line)
		}
	}
	if res.Note != "" {
		r.blank()
		r.line("%s", res.Note)
	}
	return r.String()
}

// FormatTeamStats renders a club's record.
func FormatTeamStats(res *TeamStatsResult) string {
	var r report
	r.line("%s - %s", res.Team.Display, res.Scope)
	r.line("- Matches: %d", res.Overall.Played)
	r.line("- Wins: %d, Draws: %d, Losses: %d", res.Overall.Wins, res.Overall.Draws, res.Overall.Losses)
	r.line("- Goals For: %d, Goals Against: %d (%+d)", res.Overall.GoalsFor, res.Overall.GoalsAgainst, res.Overall.GoalDiff)
	r.line("- Points: %d (%.2f per game), Win rate: %.1f%%", res.Overall.Points, res.Overall.PointsPerGame, res.Overall.WinRate)
	r.line("- Clean sheets: %d, longest unbeaten run: %d", res.Overall.CleanSheets, res.LongestUnbeaten)
	if res.Home.Played > 0 && res.Away.Played > 0 {
		r.line("- Home: %s", res.Home.Summary())
		r.line("- Away: %s", res.Away.Summary())
	}
	if res.RecentForm != "" {
		r.line("- Recent form (newest first): %s", res.RecentForm)
	}
	if res.BiggestWin != nil {
		r.line("- Biggest win: %s", res.BiggestWin.Line)
	}
	if res.BiggestDefeat != nil {
		r.line("- Heaviest defeat: %s", res.BiggestDefeat.Line)
	}
	if len(res.ByCompetition) > 1 {
		r.blank()
		r.line("By competition:")
		for _, nr := range res.ByCompetition {
			r.line("  %s: %s", nr.Label, nr.Record.Summary())
		}
	}
	if len(res.BySeason) > 1 {
		r.blank()
		r.line("By season:")
		for _, nr := range res.BySeason {
			r.line("  %s: %s", nr.Label, nr.Record.Summary())
		}
	}
	if len(res.TopOpponents) > 0 {
		r.blank()
		r.line("Most played opponents: %s", strings.Join(res.TopOpponents, ", "))
	}
	if len(res.Alternatives) > 0 {
		r.line("Other clubs matching the name: %s", strings.Join(res.Alternatives, ", "))
	}
	if res.Note != "" {
		r.blank()
		r.line("%s", res.Note)
	}
	return r.String()
}

// FormatTeamProfile renders the cross dataset club overview.
func FormatTeamProfile(res *TeamProfileResult) string {
	var r report
	where := res.Team.StateName
	if res.Team.Country != "" {
		where = res.Team.Country
	}
	r.line("%s (%s)", res.Team.Display, where)
	if len(res.Team.Nicknames) > 0 {
		r.line("Known as: %s", strings.Join(res.Team.Nicknames, ", "))
	}
	r.line("Name variants in the datasets: %s", strings.Join(res.Team.Aliases, " | "))
	r.line("Total matches in the knowledge graph: %d", res.TotalMatches)
	r.line("Overall record: %s", res.Overall.Summary())
	if res.FirstMatch != nil {
		r.line("First match: %s", res.FirstMatch.Line)
		r.line("Most recent match: %s", res.LastMatch.Line)
	}
	if len(res.Competitions) > 0 {
		r.blank()
		r.line("Competitions:")
		for _, c := range res.Competitions {
			r.line("  %s: %d matches, seasons %s - %s", c.Competition, c.Matches, c.SeasonRange, c.Record.Summary())
		}
	}
	if len(res.Titles) > 0 {
		r.blank()
		r.line("Titles computed from the match data:")
		for _, t := range res.Titles {
			r.line("  %d %s (%s)", t.Season, t.Competition, t.Detail)
		}
	}
	if len(res.Rivalries) > 0 {
		r.blank()
		r.line("Rivalries: %s", strings.Join(res.Rivalries, ", "))
	}
	if len(res.Stadiums) > 0 {
		r.line("Home stadiums recorded: %s", strings.Join(res.Stadiums, ", "))
	}
	if len(res.Squad) > 0 {
		r.blank()
		r.line("Squad in the FIFA dataset (%d players, highest rated first):", res.SquadSize)
		for i, p := range res.Squad {
			r.line("  %d. %s", i+1, p.Line)
		}
	} else if res.SquadNote != "" {
		r.blank()
		r.line("%s", res.SquadNote)
	}
	if len(res.Alternatives) > 0 {
		r.blank()
		r.line("Other clubs matching the name: %s", strings.Join(res.Alternatives, ", "))
	}
	return r.String()
}

// FormatStandings renders a league table.
func FormatStandings(res *StandingsResult) string {
	var r report
	r.line("%s standings (calculated from matches)", res.Scope)
	if res.Champion != "" {
		r.line("Champion: %s", res.Champion)
	}
	r.blank()
	r.line("%-3s %-24s %3s %3s %3s %3s %4s %4s %5s %4s", "#", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts")
	for _, row := range res.Rows {
		marker := ""
		switch row.Zone {
		case "champion":
			marker = " - Champion"
		case "relegation":
			marker = " - Relegated"
		}
		r.line("%-3d %-24s %3d %3d %3d %3d %4d %4d %+5d %4d%s",
			row.Position, truncate(row.Team, 24), row.Played, row.Wins, row.Draws, row.Losses,
			row.GoalsFor, row.GoalsAgainst, row.GoalDiff, row.Points, marker)
	}
	if len(res.Relegated) > 0 {
		r.blank()
		r.line("Relegated: %s", strings.Join(res.Relegated, ", "))
	}
	if len(res.Excluded) > 0 {
		r.line("Excluded as data noise: %s", strings.Join(res.Excluded, ", "))
	}
	if len(res.Notes) > 0 {
		r.blank()
		r.list(res.Notes, "Note: ")
	}
	return r.String()
}

func truncate(s string, n int) string {
	runes := []rune(s)
	if len(runes) <= n {
		return s
	}
	return string(runes[:n-1]) + "…"
}

// FormatChampions renders a winners list.
func FormatChampions(res *ChampionsResult) string {
	var r report
	r.line("Champions: %s", res.Scope)
	r.blank()
	for _, c := range res.Champions {
		switch {
		case c.Champion == "":
			r.line("- %d %s: undetermined (%s)", c.Season, c.Competition, c.Detail)
		case c.Decided:
			runner := ""
			if c.RunnerUp != "" {
				runner = fmt.Sprintf(", runner-up %s", c.RunnerUp)
			}
			r.line("- %d %s: %s (%s%s)", c.Season, c.Competition, c.Champion, c.Detail, runner)
		default:
			r.line("- %d %s: %s [%s]", c.Season, c.Competition, c.Champion, c.Detail)
		}
	}
	if len(res.Titles) > 0 {
		r.blank()
		r.line("Most titles in scope: %s", strings.Join(res.Titles, ", "))
	}
	if res.Note != "" {
		r.blank()
		r.line("%s", res.Note)
	}
	return r.String()
}

// FormatBracket renders a knockout tournament.
func FormatBracket(res *BracketResult) string {
	var r report
	r.line("%d %s bracket", res.Season, res.Competition)
	if res.Champion != "" {
		r.line("Champion: %s", res.Champion)
	}
	for _, st := range res.Stages {
		r.blank()
		r.line("%s (%d matches):", strings.ToUpper(st.Name[:1])+st.Name[1:], st.Matches)
		for _, tie := range st.Ties {
			r.line("  %s %d-%d %s -> %s", tie.TeamA, tie.AggregateA, tie.AggregateB, tie.TeamB, tie.Winner)
			for _, leg := range tie.Legs {
				r.line("      %s", leg.Line)
			}
		}
	}
	if len(res.Notes) > 0 {
		r.blank()
		r.list(res.Notes, "Note: ")
	}
	return r.String()
}

// FormatCompetitionSummary renders one or more season summaries.
func FormatCompetitionSummary(res *CompetitionSummaryResult) string {
	var r report
	r.line("%s summary", res.Scope)
	for _, s := range res.Seasons {
		r.blank()
		r.line("%d season:", s.Season)
		r.line("- Matches: %d, Teams: %d", s.Matches, s.Teams)
		r.line("- Goals: %d (%.2f per match)", s.Goals, s.GoalsPerMatch)
		r.line("- Results: %.1f%% home wins, %.1f%% draws, %.1f%% away wins", s.HomeWinPercent, s.DrawPercent, s.AwayWinPercent)
		if s.Champion != "" {
			r.line("- Champion: %s (%s)", s.Champion, s.ChampionDetail)
		}
		if len(s.TopScoringTeams) > 0 {
			r.line("- Top scoring teams: %s", strings.Join(s.TopScoringTeams, ", "))
		}
		if len(s.BestDefences) > 0 {
			r.line("- Best defences: %s", strings.Join(s.BestDefences, ", "))
		}
		if s.BiggestWin != nil {
			r.line("- Biggest win: %s", s.BiggestWin.Line)
		}
		if s.HighestScoring != nil {
			r.line("- Highest scoring match: %s", s.HighestScoring.Line)
		}
		if len(s.Stages) > 0 {
			r.line("- Stages: %s", strings.Join(s.Stages, ", "))
		}
		if len(s.DataSources) > 0 {
			r.line("- Data sources: %s", strings.Join(s.DataSources, ", "))
		}
	}
	if len(res.Comparison) > 0 {
		r.blank()
		r.line("Comparison:")
		r.list(res.Comparison, "- ")
	}
	if len(res.Notes) > 0 {
		r.blank()
		r.list(res.Notes, "Note: ")
	}
	return r.String()
}

// FormatPlayerSearch renders a player list.
func FormatPlayerSearch(res *PlayerSearchResult) string {
	var r report
	r.line("Players: %s", res.Query)
	r.line("Matching players: %d", res.Total)
	if len(res.Players) > 0 {
		r.blank()
		for i, p := range res.Players {
			r.line("%d. %s", i+1, p.Line)
		}
	}
	if len(res.ByClub) > 0 {
		r.blank()
		r.line("By club:")
		for _, c := range res.ByClub {
			r.line("- %s: %d players (avg rating: %.1f, best: %s)", c.Club, c.Players, c.AverageRating, c.BestPlayer)
		}
	}
	if res.Note != "" {
		r.blank()
		r.line("%s", res.Note)
	}
	r.line("Source: %s", res.DataSource)
	return r.String()
}

// FormatPlayerProfile renders one player.
func FormatPlayerProfile(res *PlayerProfileResult) string {
	var r report
	p := res.Player
	r.line("%s", p.Name)
	r.line("- Overall: %d, Potential: %d", p.Overall, p.Potential)
	r.line("- Age: %d, Nationality: %s", p.Age, p.Nationality)
	r.line("- Club: %s, Position: %s (%s), Shirt: %d", orDash(p.Club), orDash(p.Position), orDash(p.PositionGroup), p.Jersey)
	r.line("- Physical: %s, %s, preferred foot %s", orDash(p.Height), orDash(p.Weight), orDash(p.Foot))
	if p.Value != "" {
		r.line("- Value: %s, Wage: %s, contract until %s", p.Value, orDash(p.Wage), orDash(p.Contract))
	}
	if len(res.TopSkills) > 0 {
		r.line("- Best attributes: %s", strings.Join(res.TopSkills, ", "))
	}
	if res.ClubTeam != nil {
		r.line("- Club in the match graph: %s (%s)", res.ClubTeam.Display, res.ClubTeam.StateName)
	}
	if len(res.Teammates) > 0 {
		r.line("- Team mates: %s", strings.Join(res.Teammates, ", "))
	}
	if len(res.SimilarNames) > 0 {
		r.line("- Other players matching the name: %s", strings.Join(res.SimilarNames, ", "))
	}
	if res.Note != "" {
		r.line("%s", res.Note)
	}
	return r.String()
}

// FormatLeaderboard renders a team ranking.
func FormatLeaderboard(res *LeaderboardResult) string {
	var r report
	r.line("Ranking by %s - %s", res.Metric, res.Scope)
	r.blank()
	for _, row := range res.Rows {
		r.line("%2d. %-26s %s", row.Position, truncate(row.Team, 26), row.Detail)
	}
	if res.Note != "" {
		r.blank()
		r.line("%s", res.Note)
	}
	return r.String()
}

// FormatAggregate renders dataset-wide statistics.
func FormatAggregate(res *AggregateStats) string {
	var r report
	r.line("Statistics: %s", res.Scope)
	r.line("- Matches: %d", res.Matches)
	if res.Matches == 0 {
		if res.Note != "" {
			r.line("%s", res.Note)
		}
		return r.String()
	}
	r.line("- Goals: %d", res.Goals)
	r.line("- Average goals per match: %.2f", res.GoalsPerMatch)
	r.line("- Home win rate: %.1f%% (draws %.1f%%, away wins %.1f%%)", res.HomeWinPercent, res.DrawPercent, res.AwayWinPercent)
	r.line("- Home advantage: %s", res.HomeAdvantage)
	r.line("- Matches with a clean sheet: %d, goalless draws: %d", res.CleanSheets, res.GoallessDraws)
	if len(res.BiggestWins) > 0 {
		r.blank()
		r.line("Biggest victories:")
		for i, m := range res.BiggestWins {
			r.line("%d. %s", i+1, m.Line)
		}
	}
	if len(res.HighestScoring) > 0 {
		r.blank()
		r.line("Highest scoring matches:")
		for i, m := range res.HighestScoring {
			r.line("%d. %s", i+1, m.Line)
		}
	}
	if len(res.ByCompetition) > 0 {
		r.blank()
		r.line("By competition:")
		r.list(res.ByCompetition, "- ")
	}
	if len(res.BySeason) > 0 {
		r.blank()
		r.line("By season:")
		r.list(res.BySeason, "- ")
	}
	if res.Note != "" {
		r.blank()
		r.line("%s", res.Note)
	}
	return r.String()
}

// FormatDerbies renders the rivalry table.
func FormatDerbies(res *DerbiesResult) string {
	var r report
	r.line("Traditional derbies - %s", res.Scope)
	r.blank()
	for _, d := range res.Derbies {
		if d.Matches == 0 {
			r.line("- %s (%s vs %s): no matches in scope", d.Name, d.TeamA, d.TeamB)
			continue
		}
		r.line("- %s (%s vs %s): %d matches. %s", d.Name, d.TeamA, d.TeamB, d.Matches, d.Record)
		if d.LastMeeting != nil {
			r.line("    last: %s", d.LastMeeting.Line)
		}
		for _, m := range d.Recent {
			r.line("      %s", m.Line)
		}
	}
	if res.Note != "" {
		r.blank()
		r.line("%s", res.Note)
	}
	return r.String()
}

// FormatTeamList renders the club directory.
func FormatTeamList(entries []TeamListEntry, total int) string {
	var r report
	r.line("Clubs in the knowledge graph: showing %d of %d", len(entries), total)
	r.blank()
	for _, e := range entries {
		line := fmt.Sprintf("- %s [%s]: %d matches", e.Display, e.ID, e.Matches)
		if len(e.Competitions) > 0 {
			line += " in " + strings.Join(e.Competitions, ", ")
		}
		if e.SquadSize > 0 {
			line += fmt.Sprintf("; %d FIFA player rows", e.SquadSize)
		}
		r.line("%s", line)
		if len(e.Nicknames) > 0 {
			r.line("    nicknames: %s", strings.Join(e.Nicknames, ", "))
		}
	}
	return r.String()
}

// FormatDatasetInfo renders the provenance report.
func FormatDatasetInfo(res *DatasetInfoResult) string {
	var r report
	r.line("Brazilian soccer knowledge graph")
	r.line("Data directory: %s", res.DataDir)
	r.line("Loaded in %d ms", res.LoadMillis)
	r.blank()
	r.line("Totals: %d clubs, %d unique matches (%d source rows), %d players",
		res.Stats.Teams, res.Stats.Matches, res.Stats.MatchRows, res.Stats.Players)
	r.line("Seasons: %s", res.Stats.SeasonRange)
	r.blank()
	r.line("Matches by competition:")
	for _, c := range AllCompetitions {
		if n, ok := res.Stats.Competitions[string(c)]; ok {
			r.line("- %s: %d", c, n)
		}
	}
	r.blank()
	r.line("Source files:")
	for _, s := range res.Sources {
		r.line("- %s (%s, %s)", s.File, s.Key, s.License)
		r.line("    %s", s.Description)
		r.line("    rows loaded: %d, rows skipped: %d", s.Rows, s.Skipped)
		if len(s.SkipReasons) > 0 {
			r.line("    skip reasons: %s", strings.Join(s.SkipReasons, "; "))
		}
		if s.SeasonMax > 0 {
			r.line("    seasons: %d-%d", s.SeasonMin, s.SeasonMax)
		}
		r.line("    source: %s", s.URL)
	}
	if len(res.Notes) > 0 {
		r.blank()
		r.list(res.Notes, "Note: ")
	}
	return r.String()
}

// DatasetInfoResult is the payload of the dataset_info tool.
type DatasetInfoResult struct {
	DataDir    string       `json:"data_directory"`
	LoadMillis int64        `json:"load_millis"`
	Stats      Stats        `json:"stats"`
	Sources    []SourceInfo `json:"sources"`
	Notes      []string     `json:"notes,omitempty"`
}

// DatasetInfo reports what was loaded and how the overlapping files were
// reconciled.
func (g *Graph) DatasetInfo() *DatasetInfoResult {
	res := &DatasetInfoResult{
		DataDir:    g.dataDir,
		LoadMillis: g.loadTime.Milliseconds(),
		Stats:      g.Stats(),
		Sources:    g.sources,
	}
	res.Notes = append(res.Notes,
		"Série A 2014-2019 appears in three of the source files. Each real fixture is stored once (the file with explicit season and round numbers wins) and the duplicate rows donate their extra columns, so BR-Football shots and corners and historic stadium names enrich the same match.",
		"Statistics, standings and head-to-head records are computed over the de-duplicated view; set include_duplicates on search_matches to see the raw per-file rows.",
		"The datasets contain no goalscorer, lineup or referee data, so questions about individual scorers cannot be answered from them.")
	if n := len(g.unresolved); n > 0 {
		res.Notes = append(res.Notes, fmt.Sprintf("%d source rows could not be attached to two distinct clubs and were left out (for example a Copa do Brasil row listing the same club as home and away).", n))
	}
	return res
}
