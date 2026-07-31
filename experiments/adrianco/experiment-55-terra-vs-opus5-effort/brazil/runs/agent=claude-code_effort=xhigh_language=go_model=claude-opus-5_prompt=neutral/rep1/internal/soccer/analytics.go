// analytics.go answers statistics-shaped questions: "what is the average goals
// per match in the Brasileirão", "which team has the best away record", "show me
// the biggest wins in the dataset", "how do home and away performance compare".
//
// Everything here runs over the de-duplicated match view produced by graph.go, so
// a fixture that appears in three source files is still counted once.
package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// Metric names a team leaderboard.
type Metric string

// Supported leaderboard metrics.
const (
	MetricMostWins        Metric = "most_wins"
	MetricMostPoints      Metric = "most_points"
	MetricBestWinRate     Metric = "best_win_rate"
	MetricMostGoals       Metric = "most_goals_scored"
	MetricBestDefence     Metric = "best_defence"
	MetricMostCleanSheets Metric = "most_clean_sheets"
	MetricMostDraws       Metric = "most_draws"
	MetricBestGoalDiff    Metric = "best_goal_difference"
	MetricMostMatches     Metric = "most_matches"
)

// AllMetrics lists every supported leaderboard metric.
var AllMetrics = []Metric{
	MetricMostWins, MetricMostPoints, MetricBestWinRate, MetricMostGoals,
	MetricBestDefence, MetricMostCleanSheets, MetricMostDraws,
	MetricBestGoalDiff, MetricMostMatches,
}

// ParseMetric resolves a metric name, accepting a few natural spellings.
func ParseMetric(s string) (Metric, error) {
	key := strings.ReplaceAll(foldKey(s), " ", "_")
	if key == "" {
		return MetricMostPoints, nil
	}
	aliases := map[string]Metric{
		"wins": MetricMostWins, "most_wins": MetricMostWins,
		"points": MetricMostPoints, "most_points": MetricMostPoints,
		"win_rate": MetricBestWinRate, "best_win_rate": MetricBestWinRate,
		"goals": MetricMostGoals, "most_goals": MetricMostGoals,
		"most_goals_scored": MetricMostGoals, "goals_scored": MetricMostGoals,
		"defence": MetricBestDefence, "defense": MetricBestDefence,
		"best_defence": MetricBestDefence, "best_defense": MetricBestDefence,
		"fewest_conceded": MetricBestDefence,
		"clean_sheets":    MetricMostCleanSheets, "most_clean_sheets": MetricMostCleanSheets,
		"draws": MetricMostDraws, "most_draws": MetricMostDraws,
		"goal_difference": MetricBestGoalDiff, "best_goal_difference": MetricBestGoalDiff,
		"matches": MetricMostMatches, "most_matches": MetricMostMatches,
	}
	if m, ok := aliases[key]; ok {
		return m, nil
	}
	return "", fmt.Errorf("unknown metric %q (supported: %s)", s, joinMetrics(AllMetrics))
}

func joinMetrics(ms []Metric) string {
	parts := make([]string, len(ms))
	for i, m := range ms {
		parts[i] = string(m)
	}
	return strings.Join(parts, ", ")
}

// LeaderboardRow is one club's entry in a ranking.
type LeaderboardRow struct {
	Position int     `json:"position"`
	Team     string  `json:"team"`
	TeamID   string  `json:"team_id"`
	Value    float64 `json:"value"`
	Record   Record  `json:"record"`
	Detail   string  `json:"detail"`
}

// LeaderboardResult is the payload of the team_rankings tool.
type LeaderboardResult struct {
	Metric    string           `json:"metric"`
	Scope     string           `json:"scope"`
	MinPlayed int              `json:"minimum_matches_required"`
	Rows      []LeaderboardRow `json:"rankings"`
	Note      string           `json:"note,omitempty"`
}

// Leaderboard ranks clubs by a metric under a match filter, optionally
// restricted to home or away matches.
func (g *Graph) Leaderboard(metric Metric, f MatchFilter, venue Venue, minPlayed, limit int) (*LeaderboardResult, error) {
	rf, err := g.resolve(f)
	if err != nil {
		return nil, err
	}
	records := map[string]*Record{}
	get := func(id string) *Record {
		r := records[id]
		if r == nil {
			r = &Record{}
			records[id] = r
		}
		return r
	}
	total := 0
	for _, m := range g.matches {
		if !rf.matches(m) {
			continue
		}
		total++
		if venue != VenueAway {
			get(m.HomeID).add(m.HomeGoals, m.AwayGoals)
		}
		if venue != VenueHome {
			get(m.AwayID).add(m.AwayGoals, m.HomeGoals)
		}
	}
	scope := rf.scope
	if venue != VenueAll {
		scope += fmt.Sprintf(" (%s matches only)", venue)
	}
	res := &LeaderboardResult{Metric: string(metric), Scope: scope, MinPlayed: minPlayed}
	for id, rec := range records {
		rec.finish()
		if rec.Played < minPlayed {
			continue
		}
		t, ok := g.Team(id)
		if !ok {
			continue
		}
		row := LeaderboardRow{Team: t.Display, TeamID: id, Record: *rec}
		switch metric {
		case MetricMostWins:
			row.Value = float64(rec.Wins)
			row.Detail = fmt.Sprintf("%d wins in %d matches", rec.Wins, rec.Played)
		case MetricMostPoints:
			row.Value = float64(rec.Points)
			row.Detail = fmt.Sprintf("%d pts from %d matches (%.2f per game)", rec.Points, rec.Played, rec.PointsPerGame)
		case MetricBestWinRate:
			row.Value = rec.WinRate
			row.Detail = fmt.Sprintf("%.1f%% wins (%dW %dD %dL)", rec.WinRate, rec.Wins, rec.Draws, rec.Losses)
		case MetricMostGoals:
			row.Value = float64(rec.GoalsFor)
			row.Detail = fmt.Sprintf("%d goals in %d matches (%.2f per game)", rec.GoalsFor, rec.Played, round2(float64(rec.GoalsFor)/float64(rec.Played)))
		case MetricBestDefence:
			row.Value = -float64(rec.GoalsAgainst)
			row.Detail = fmt.Sprintf("%d conceded in %d matches (%.2f per game)", rec.GoalsAgainst, rec.Played, round2(float64(rec.GoalsAgainst)/float64(rec.Played)))
		case MetricMostCleanSheets:
			row.Value = float64(rec.CleanSheets)
			row.Detail = fmt.Sprintf("%d clean sheets in %d matches", rec.CleanSheets, rec.Played)
		case MetricMostDraws:
			row.Value = float64(rec.Draws)
			row.Detail = fmt.Sprintf("%d draws in %d matches", rec.Draws, rec.Played)
		case MetricBestGoalDiff:
			row.Value = float64(rec.GoalDiff)
			row.Detail = fmt.Sprintf("%+d goal difference (%d for, %d against)", rec.GoalDiff, rec.GoalsFor, rec.GoalsAgainst)
		case MetricMostMatches:
			row.Value = float64(rec.Played)
			row.Detail = fmt.Sprintf("%d matches", rec.Played)
		default:
			return nil, fmt.Errorf("unknown metric %q", metric)
		}
		res.Rows = append(res.Rows, row)
	}
	sort.Slice(res.Rows, func(i, j int) bool {
		if res.Rows[i].Value != res.Rows[j].Value {
			return res.Rows[i].Value > res.Rows[j].Value
		}
		if res.Rows[i].Record.Points != res.Rows[j].Record.Points {
			return res.Rows[i].Record.Points > res.Rows[j].Record.Points
		}
		return res.Rows[i].Team < res.Rows[j].Team
	})
	if limit > 0 && len(res.Rows) > limit {
		res.Rows = res.Rows[:limit]
	}
	for i := range res.Rows {
		res.Rows[i].Position = i + 1
	}
	if total == 0 {
		res.Note = "No matches under this filter. " + g.coverageHint(f)
	} else if metric == MetricBestWinRate || metric == MetricBestDefence {
		res.Note = fmt.Sprintf("Ranked over %d matches; clubs with fewer than %d appearances are excluded to keep rate based metrics meaningful.", total, minPlayed)
	}
	return res, nil
}

// AggregateStats is the payload of the aggregate_stats tool: the dataset-wide
// numbers behind questions such as "what is the average goals per match".
type AggregateStats struct {
	Scope          string      `json:"scope"`
	Matches        int         `json:"matches"`
	Goals          int         `json:"goals"`
	GoalsPerMatch  float64     `json:"goals_per_match"`
	HomeGoals      int         `json:"home_goals"`
	AwayGoals      int         `json:"away_goals"`
	HomeWins       int         `json:"home_wins"`
	Draws          int         `json:"draws"`
	AwayWins       int         `json:"away_wins"`
	HomeWinPercent float64     `json:"home_win_percent"`
	DrawPercent    float64     `json:"draw_percent"`
	AwayWinPercent float64     `json:"away_win_percent"`
	HomeAdvantage  string      `json:"home_advantage"`
	CleanSheets    int         `json:"matches_with_a_clean_sheet"`
	GoallessDraws  int         `json:"goalless_draws"`
	BiggestWins    []MatchView `json:"biggest_wins,omitempty"`
	HighestScoring []MatchView `json:"highest_scoring_matches,omitempty"`
	BySeason       []string    `json:"goals_per_match_by_season,omitempty"`
	ByCompetition  []string    `json:"goals_per_match_by_competition,omitempty"`
	Note           string      `json:"note,omitempty"`
}

// Aggregate computes headline statistics over any subset of matches.
func (g *Graph) Aggregate(f MatchFilter, topN int) (*AggregateStats, error) {
	ms, rf, err := g.FindMatches(f)
	if err != nil {
		return nil, err
	}
	res := &AggregateStats{Scope: rf.scope, Matches: len(ms)}
	if len(ms) == 0 {
		res.Note = "No matches under this filter. " + g.coverageHint(f)
		return res, nil
	}
	type acc struct{ matches, goals int }
	bySeason := map[int]*acc{}
	byComp := map[Competition]*acc{}
	for _, m := range ms {
		res.Goals += m.TotalGoals()
		res.HomeGoals += m.HomeGoals
		res.AwayGoals += m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			res.HomeWins++
		case m.HomeGoals == m.AwayGoals:
			res.Draws++
			if m.TotalGoals() == 0 {
				res.GoallessDraws++
			}
		default:
			res.AwayWins++
		}
		if m.HomeGoals == 0 || m.AwayGoals == 0 {
			res.CleanSheets++
		}
		a := bySeason[m.Season]
		if a == nil {
			a = &acc{}
			bySeason[m.Season] = a
		}
		a.matches++
		a.goals += m.TotalGoals()
		c := byComp[m.Competition]
		if c == nil {
			c = &acc{}
			byComp[m.Competition] = c
		}
		c.matches++
		c.goals += m.TotalGoals()
	}
	n := float64(len(ms))
	res.GoalsPerMatch = round2(float64(res.Goals) / n)
	res.HomeWinPercent = round1(float64(res.HomeWins) * 100 / n)
	res.DrawPercent = round1(float64(res.Draws) * 100 / n)
	res.AwayWinPercent = round1(float64(res.AwayWins) * 100 / n)
	res.HomeAdvantage = fmt.Sprintf("home teams win %.1f%% of matches and score %.2f goals per game versus %.2f away",
		res.HomeWinPercent, round2(float64(res.HomeGoals)/n), round2(float64(res.AwayGoals)/n))

	byMargin := append([]*Match(nil), ms...)
	sort.SliceStable(byMargin, func(i, j int) bool {
		if byMargin[i].GoalDifference() != byMargin[j].GoalDifference() {
			return byMargin[i].GoalDifference() > byMargin[j].GoalDifference()
		}
		return byMargin[i].TotalGoals() > byMargin[j].TotalGoals()
	})
	res.BiggestWins = g.Views(byMargin, topN)

	byTotal := append([]*Match(nil), ms...)
	sort.SliceStable(byTotal, func(i, j int) bool { return byTotal[i].TotalGoals() > byTotal[j].TotalGoals() })
	res.HighestScoring = g.Views(byTotal, topN)

	seasons := make([]int, 0, len(bySeason))
	for s := range bySeason {
		seasons = append(seasons, s)
	}
	sort.Ints(seasons)
	for _, s := range seasons {
		a := bySeason[s]
		res.BySeason = append(res.BySeason, fmt.Sprintf("%d: %.2f goals per match (%d matches)", s, round2(float64(a.goals)/float64(a.matches)), a.matches))
	}
	for _, c := range AllCompetitions {
		if a, ok := byComp[c]; ok {
			res.ByCompetition = append(res.ByCompetition, fmt.Sprintf("%s: %.2f goals per match (%d matches)", c, round2(float64(a.goals)/float64(a.matches)), a.matches))
		}
	}
	return res, nil
}

// rivalry names a traditional derby.
type rivalry struct {
	Name  string
	TeamA string
	TeamB string
}

// rivalries is the curated derby table used by list_derbies and by team
// profiles. IDs are canonical team IDs from the graph.
var rivalries = []rivalry{
	{"Fla-Flu", "flamengo-rj", "fluminense-rj"},
	{"Clássico dos Milhões", "flamengo-rj", "vasco-da-gama-rj"},
	{"Clássico Vovô", "botafogo-rj", "fluminense-rj"},
	{"Clássico da Rivalidade", "botafogo-rj", "flamengo-rj"},
	{"Clássico dos Gigantes", "botafogo-rj", "vasco-da-gama-rj"},
	{"Derby Paulista", "corinthians-sp", "palmeiras-sp"},
	{"Majestoso", "corinthians-sp", "sao-paulo-sp"},
	{"Choque-Rei", "palmeiras-sp", "sao-paulo-sp"},
	{"Clássico da Saudade", "corinthians-sp", "santos-sp"},
	{"Clássico Alvinegro", "palmeiras-sp", "santos-sp"},
	{"San-São", "santos-sp", "sao-paulo-sp"},
	{"Grenal", "gremio-rs", "internacional-rs"},
	{"Clássico Mineiro", "atletico-mg", "cruzeiro-mg"},
	{"Atletiba", "atletico-pr", "coritiba-pr"},
	{"Ba-Vi (Clássico dos Clássicos)", "bahia-ba", "vitoria-ba"},
	{"Clássico dos Clássicos (PE)", "nautico-pe", "sport-pe"},
	{"Clássico das Multidões", "santa-cruz-pe", "sport-pe"},
	{"Clássico-Rei", "ceara-ce", "fortaleza-ce"},
	{"Clássico da Paz", "goias-go", "vila-nova-go"},
	{"Clássico dos Milhões catarinense", "avai-sc", "figueirense-sc"},
}

// rivalryFor returns the derby between two clubs, if there is one.
func rivalryFor(a, b string) *rivalry {
	for i := range rivalries {
		r := &rivalries[i]
		if (r.TeamA == a && r.TeamB == b) || (r.TeamA == b && r.TeamB == a) {
			return r
		}
	}
	return nil
}

// rivalriesFor returns every derby a club takes part in.
func rivalriesFor(id string) []rivalry {
	var out []rivalry
	for _, r := range rivalries {
		if r.TeamA == id || r.TeamB == id {
			out = append(out, r)
		}
	}
	return out
}

// DerbyEntry is one rivalry with its record in the data.
type DerbyEntry struct {
	Name        string      `json:"name"`
	TeamA       string      `json:"team_a"`
	TeamB       string      `json:"team_b"`
	Matches     int         `json:"matches"`
	Record      string      `json:"record,omitempty"`
	LastMeeting *MatchView  `json:"last_meeting,omitempty"`
	Recent      []MatchView `json:"matches_in_scope,omitempty"`
}

// DerbiesResult is the payload of the list_derbies tool.
type DerbiesResult struct {
	Scope   string       `json:"scope"`
	Derbies []DerbyEntry `json:"derbies"`
	Note    string       `json:"note,omitempty"`
}

// Derbies reports the traditional rivalries, optionally restricted to a season
// or competition, which is what "show me all derbies in 2023" needs.
func (g *Graph) Derbies(f MatchFilter, includeMatches bool) (*DerbiesResult, error) {
	rf, err := g.resolve(f)
	if err != nil {
		return nil, err
	}
	res := &DerbiesResult{Scope: rf.scope}
	for _, r := range rivalries {
		ta, okA := g.Team(r.TeamA)
		tb, okB := g.Team(r.TeamB)
		if !okA || !okB {
			continue
		}
		var ms []*Match
		for _, m := range g.teamMatches(ta) {
			if m.OpponentOf(ta.ID) == tb.ID && rf.matches(m) {
				ms = append(ms, m)
			}
		}
		sortMatchesNewestFirst(ms)
		entry := DerbyEntry{Name: r.Name, TeamA: ta.Display, TeamB: tb.Display, Matches: len(ms)}
		if len(ms) > 0 {
			h2h := summariseH2H(ta, tb, ms)
			entry.Record = h2h.Summary
			v := g.View(ms[0])
			entry.LastMeeting = &v
			if includeMatches {
				entry.Recent = g.Views(ms, 20)
			}
		}
		res.Derbies = append(res.Derbies, entry)
	}
	sort.SliceStable(res.Derbies, func(i, j int) bool { return res.Derbies[i].Matches > res.Derbies[j].Matches })
	res.Note = "Rivalries are a curated list of Brazil's traditional derbies; records are computed from the matches present in the datasets."
	return res, nil
}
