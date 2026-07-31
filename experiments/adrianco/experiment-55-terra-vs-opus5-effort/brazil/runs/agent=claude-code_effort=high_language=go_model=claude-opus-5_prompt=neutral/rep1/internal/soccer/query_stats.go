// query_stats.go implements the "Statistical Analysis" section: corpus-wide and
// scoped aggregates, team leaderboards and season comparisons.
package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// TeamLeaderRow is one entry of a team leaderboard.
type TeamLeaderRow struct {
	Position int     `json:"position"`
	Team     string  `json:"team"`
	Value    float64 `json:"value"`
	Record   Record  `json:"record"`
}

// SeasonAggregate summarises one season within a scope.
type SeasonAggregate struct {
	Season        int     `json:"season"`
	Matches       int     `json:"matches"`
	Goals         int     `json:"goals"`
	GoalsPerMatch float64 `json:"goals_per_match"`
	HomeWinPct    float64 `json:"home_win_pct"`
	DrawPct       float64 `json:"draw_pct"`
	AwayWinPct    float64 `json:"away_win_pct"`
}

// AggregateStatsResult holds the computed statistics for a scope.
type AggregateStatsResult struct {
	Scope           string            `json:"scope"`
	Matches         int               `json:"matches"`
	Goals           int               `json:"goals"`
	GoalsPerMatch   float64           `json:"goals_per_match"`
	HomeWins        int               `json:"home_wins"`
	Draws           int               `json:"draws"`
	AwayWins        int               `json:"away_wins"`
	HomeWinPct      float64           `json:"home_win_pct"`
	DrawPct         float64           `json:"draw_pct"`
	AwayWinPct      float64           `json:"away_win_pct"`
	AvgHomeGoals    float64           `json:"avg_home_goals"`
	AvgAwayGoals    float64           `json:"avg_away_goals"`
	BiggestWins     []MatchView       `json:"biggest_wins"`
	HighestScoring  []MatchView       `json:"highest_scoring"`
	TopScoringTeams []TeamLeaderRow   `json:"top_scoring_teams"`
	BestDefences    []TeamLeaderRow   `json:"best_defences"`
	BestHomeRecords []TeamLeaderRow   `json:"best_home_records"`
	BestAwayRecords []TeamLeaderRow   `json:"best_away_records"`
	BySeason        []SeasonAggregate `json:"by_season,omitempty"`
	Note            string            `json:"note,omitempty"`
}

// StatsScope narrows an aggregate computation.
type StatsScope struct {
	Competition string
	Team        string
	Season      int
	SeasonFrom  int
	SeasonTo    int
	TopN        int
	MinMatches  int // minimum matches for a club to enter a leaderboard
}

// AggregateStats computes goals-per-match, home advantage, biggest wins and
// team leaderboards over a scope.
func (g *Graph) AggregateStats(s StatsScope) (*AggregateStatsResult, error) {
	compID := ""
	var err error
	if strings.TrimSpace(s.Competition) != "" {
		if compID, err = ResolveCompetition(s.Competition); err != nil {
			return nil, err
		}
	}
	teamID := ""
	if strings.TrimSpace(s.Team) != "" {
		t, err := g.ResolveTeam(s.Team)
		if err != nil {
			return nil, err
		}
		teamID = t.ID
	}

	pool := g.Matches
	switch {
	case teamID != "":
		pool = g.byTeam[teamID]
	case compID != "":
		pool = g.byComp[compID]
	}

	var ms []*Match
	for _, m := range pool {
		if compID != "" && m.Competition != compID {
			continue
		}
		if s.Season != 0 && m.Season != s.Season {
			continue
		}
		if s.SeasonFrom != 0 && m.Season < s.SeasonFrom {
			continue
		}
		if s.SeasonTo != 0 && m.Season > s.SeasonTo {
			continue
		}
		ms = append(ms, m)
	}

	scope := describeScope(compID, s.Season, s.SeasonFrom, s.SeasonTo, "")
	if teamID != "" {
		scope = g.teamName(teamID) + ", " + scope
	}
	res := &AggregateStatsResult{Scope: scope, Matches: len(ms)}
	if len(ms) == 0 {
		res.Note = "no matches in this scope"
		return res, nil
	}

	topN := s.TopN
	if topN <= 0 {
		topN = 5
	}
	minMatches := s.MinMatches
	if minMatches <= 0 {
		minMatches = 10
	}

	homeGoals, awayGoals := 0, 0
	overall := map[string]*Record{}
	home := map[string]*Record{}
	away := map[string]*Record{}
	seasons := map[int]*SeasonAggregate{}

	get := func(m map[string]*Record, id string) *Record {
		if m[id] == nil {
			m[id] = &Record{}
		}
		return m[id]
	}

	for _, m := range ms {
		homeGoals += m.HomeGoals
		awayGoals += m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			res.HomeWins++
		case m.AwayGoals > m.HomeGoals:
			res.AwayWins++
		default:
			res.Draws++
		}
		get(overall, m.HomeTeamID).add(m.HomeGoals, m.AwayGoals)
		get(overall, m.AwayTeamID).add(m.AwayGoals, m.HomeGoals)
		get(home, m.HomeTeamID).add(m.HomeGoals, m.AwayGoals)
		get(away, m.AwayTeamID).add(m.AwayGoals, m.HomeGoals)

		sa, ok := seasons[m.Season]
		if !ok {
			sa = &SeasonAggregate{Season: m.Season}
			seasons[m.Season] = sa
		}
		sa.Matches++
		sa.Goals += m.TotalGoals()
		switch {
		case m.HomeGoals > m.AwayGoals:
			sa.HomeWinPct++
		case m.AwayGoals > m.HomeGoals:
			sa.AwayWinPct++
		default:
			sa.DrawPct++
		}
	}

	n := float64(len(ms))
	res.Goals = homeGoals + awayGoals
	res.GoalsPerMatch = round2(float64(res.Goals) / n)
	res.HomeWinPct = round1(float64(res.HomeWins) * 100 / n)
	res.DrawPct = round1(float64(res.Draws) * 100 / n)
	res.AwayWinPct = round1(float64(res.AwayWins) * 100 / n)
	res.AvgHomeGoals = round2(float64(homeGoals) / n)
	res.AvgAwayGoals = round2(float64(awayGoals) / n)

	byMargin := append([]*Match(nil), ms...)
	sortMatches(byMargin, "goal_diff")
	res.BiggestWins = g.ToViews(head(byMargin, topN))

	byGoals := append([]*Match(nil), ms...)
	sortMatches(byGoals, "total_goals")
	res.HighestScoring = g.ToViews(head(byGoals, topN))

	res.TopScoringTeams = g.leaderboard(overall, minMatches, topN,
		func(r Record) float64 { return float64(r.GoalsFor) })
	res.BestDefences = g.leaderboardAsc(overall, minMatches, topN,
		func(r Record) float64 { return round2(float64(r.GoalsAgainst) / float64(r.Played)) })
	res.BestHomeRecords = g.leaderboard(home, minMatches, topN,
		func(r Record) float64 { return r.PointsPerGame })
	res.BestAwayRecords = g.leaderboard(away, minMatches, topN,
		func(r Record) float64 { return r.PointsPerGame })

	for _, sa := range seasons {
		f := float64(sa.Matches)
		sa.GoalsPerMatch = round2(float64(sa.Goals) / f)
		sa.HomeWinPct = round1(sa.HomeWinPct * 100 / f)
		sa.DrawPct = round1(sa.DrawPct * 100 / f)
		sa.AwayWinPct = round1(sa.AwayWinPct * 100 / f)
		res.BySeason = append(res.BySeason, *sa)
	}
	sort.SliceStable(res.BySeason, func(i, j int) bool { return res.BySeason[i].Season < res.BySeason[j].Season })
	return res, nil
}

func head(ms []*Match, n int) []*Match {
	if len(ms) > n {
		return ms[:n]
	}
	return ms
}

func (g *Graph) leaderboard(recs map[string]*Record, minMatches, topN int, value func(Record) float64) []TeamLeaderRow {
	return g.rankTeams(recs, minMatches, topN, value, true)
}

func (g *Graph) leaderboardAsc(recs map[string]*Record, minMatches, topN int, value func(Record) float64) []TeamLeaderRow {
	return g.rankTeams(recs, minMatches, topN, value, false)
}

func (g *Graph) rankTeams(recs map[string]*Record, minMatches, topN int, value func(Record) float64, desc bool) []TeamLeaderRow {
	rows := make([]TeamLeaderRow, 0, len(recs))
	for id, r := range recs {
		if r.Played < minMatches {
			continue
		}
		r.finalize()
		rows = append(rows, TeamLeaderRow{Team: g.teamName(id), Value: value(*r), Record: *r})
	}
	sort.SliceStable(rows, func(i, j int) bool {
		if rows[i].Value != rows[j].Value {
			if desc {
				return rows[i].Value > rows[j].Value
			}
			return rows[i].Value < rows[j].Value
		}
		return rows[i].Team < rows[j].Team
	})
	if len(rows) > topN {
		rows = rows[:topN]
	}
	for i := range rows {
		rows[i].Position = i + 1
	}
	return rows
}

// SeasonComparison compares aggregate statistics across seasons.
type SeasonComparison struct {
	Competition string            `json:"competition"`
	Seasons     []SeasonAggregate `json:"seasons"`
	Leaders     []SeasonLeader    `json:"leaders"`
	Commentary  string            `json:"commentary"`
}

// SeasonLeader records who topped the table in a compared season.
type SeasonLeader struct {
	Season    int    `json:"season"`
	Champion  string `json:"champion,omitempty"`
	Points    int    `json:"points,omitempty"`
	TopScorer string `json:"top_scoring_team,omitempty"`
	Goals     int    `json:"top_scoring_team_goals,omitempty"`
}

// CompareSeasons aggregates and contrasts several seasons of one competition.
func (g *Graph) CompareSeasons(competition string, seasons []int) (*SeasonComparison, error) {
	compID, err := ResolveCompetition(competition)
	if err != nil {
		return nil, err
	}
	if compID == "" {
		compID = CompSerieA
	}
	if len(seasons) == 0 {
		return nil, fmt.Errorf("at least one season is required")
	}
	out := &SeasonComparison{Competition: CompetitionName(compID)}
	for _, s := range seasons {
		agg, err := g.AggregateStats(StatsScope{Competition: compID, Season: s, TopN: 1, MinMatches: 5})
		if err != nil {
			return nil, err
		}
		if agg.Matches == 0 {
			continue
		}
		out.Seasons = append(out.Seasons, SeasonAggregate{
			Season: s, Matches: agg.Matches, Goals: agg.Goals,
			GoalsPerMatch: agg.GoalsPerMatch, HomeWinPct: agg.HomeWinPct,
			DrawPct: agg.DrawPct, AwayWinPct: agg.AwayWinPct,
		})
		leader := SeasonLeader{Season: s}
		if len(agg.TopScoringTeams) > 0 {
			leader.TopScorer = agg.TopScoringTeams[0].Team
			leader.Goals = agg.TopScoringTeams[0].Record.GoalsFor
		}
		if competitionCatalog[compID].Kind == "league" {
			if st, err := g.Standings(compID, s); err == nil && len(st.Table) > 0 {
				leader.Champion = st.Table[0].Team
				leader.Points = st.Table[0].Points
			}
		}
		out.Leaders = append(out.Leaders, leader)
	}
	if len(out.Seasons) == 0 {
		return nil, fmt.Errorf("none of the requested seasons are present for %s", CompetitionName(compID))
	}
	first, last := out.Seasons[0], out.Seasons[len(out.Seasons)-1]
	delta := round2(last.GoalsPerMatch - first.GoalsPerMatch)
	dir := "more"
	if delta < 0 {
		dir = "fewer"
		delta = -delta
	}
	out.Commentary = fmt.Sprintf("%d averaged %.2f goals per match versus %.2f in %d (%.2f %s goals per match); home win rate moved from %.1f%% to %.1f%%",
		last.Season, last.GoalsPerMatch, first.GoalsPerMatch, first.Season, delta, dir, first.HomeWinPct, last.HomeWinPct)
	return out, nil
}
