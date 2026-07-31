package soccer

import (
	"math"
	"sort"
	"strconv"
	"strings"
)

// CompetitionStats aggregates match outcomes over a scope.
type CompetitionStats struct {
	Scope          string   `json:"scope"`
	Matches        int      `json:"matches"`
	Goals          int      `json:"total_goals"`
	AvgGoals       float64  `json:"avg_goals_per_match"`
	HomeWins       int      `json:"home_wins"`
	AwayWins       int      `json:"away_wins"`
	Draws          int      `json:"draws"`
	HomeWinPct     float64  `json:"home_win_pct"`
	AwayWinPct     float64  `json:"away_win_pct"`
	DrawPct        float64  `json:"draw_pct"`
	HomeGoals      int      `json:"home_goals"`
	AwayGoals      int      `json:"away_goals"`
	CleanSheets    int      `json:"clean_sheets"`
	GoallessDraws  int      `json:"goalless_draws"`
	BiggestWins    []string `json:"biggest_wins,omitempty"`
	HighestScoring []string `json:"highest_scoring,omitempty"`
	Seasons        []int    `json:"seasons_covered,omitempty"`
	Summary        string   `json:"summary"`
}

// StatsFilter scopes an aggregate statistics query.
type StatsFilter struct {
	Competition string
	Season      int
	SeasonFrom  int
	SeasonTo    int
	Team        string
	TopN        int
}

// AggregateStats computes league-wide averages and the notable results.
func (g *Graph) AggregateStats(f StatsFilter) (*CompetitionStats, error) {
	comp := ""
	if f.Competition != "" {
		comp = g.resolveCompetition(f.Competition)
		if comp == "" {
			return nil, &ErrNoData{What: "competition " + strconv.Quote(f.Competition)}
		}
	}
	var teamID string
	if f.Team != "" {
		t, err := g.ResolveTeam(f.Team)
		if err != nil {
			return nil, err
		}
		teamID = t.ID
	}

	topN := f.TopN
	if topN <= 0 {
		topN = 5
	}
	st := &CompetitionStats{}
	seasons := map[int]bool{}
	var byMargin, byGoals []int

	for i := range g.Matches {
		m := &g.Matches[i]
		if comp != "" && m.Competition != comp {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.SeasonFrom != 0 && m.Season < f.SeasonFrom {
			continue
		}
		if f.SeasonTo != 0 && m.Season > f.SeasonTo {
			continue
		}
		if teamID != "" && !m.Involves(teamID) {
			continue
		}
		st.Matches++
		seasons[m.Season] = true
		st.Goals += m.TotalGoals()
		st.HomeGoals += m.HomeGoals
		st.AwayGoals += m.AwayGoals
		switch m.Result() {
		case "home":
			st.HomeWins++
		case "away":
			st.AwayWins++
		default:
			st.Draws++
			if m.TotalGoals() == 0 {
				st.GoallessDraws++
			}
		}
		if m.HomeGoals == 0 || m.AwayGoals == 0 {
			st.CleanSheets++
		}
		byMargin = append(byMargin, i)
		byGoals = append(byGoals, i)
	}
	if st.Matches == 0 {
		return nil, &ErrNoData{What: statsScope(f)}
	}

	n := float64(st.Matches)
	st.AvgGoals = round2(float64(st.Goals) / n)
	st.HomeWinPct = round2(100 * float64(st.HomeWins) / n)
	st.AwayWinPct = round2(100 * float64(st.AwayWins) / n)
	st.DrawPct = round2(100 * float64(st.Draws) / n)
	st.Seasons = sortedInts(seasons)

	sort.SliceStable(byMargin, func(a, b int) bool {
		ma := abs(g.Matches[byMargin[a]].HomeGoals - g.Matches[byMargin[a]].AwayGoals)
		mb := abs(g.Matches[byMargin[b]].HomeGoals - g.Matches[byMargin[b]].AwayGoals)
		if ma != mb {
			return ma > mb
		}
		return g.Matches[byMargin[a]].TotalGoals() > g.Matches[byMargin[b]].TotalGoals()
	})
	sort.SliceStable(byGoals, func(a, b int) bool {
		return g.Matches[byGoals[a]].TotalGoals() > g.Matches[byGoals[b]].TotalGoals()
	})
	for i := 0; i < topN && i < len(byMargin); i++ {
		st.BiggestWins = append(st.BiggestWins, describeMatch(g.Matches[byMargin[i]]))
	}
	for i := 0; i < topN && i < len(byGoals); i++ {
		st.HighestScoring = append(st.HighestScoring, describeMatch(g.Matches[byGoals[i]]))
	}

	st.Scope = statsScope(f)
	st.Summary = st.Scope + ": " + itoa(st.Matches) + " matches, " +
		ftoa(st.AvgGoals) + " goals per match, home win rate " + ftoa(st.HomeWinPct) +
		"%, away " + ftoa(st.AwayWinPct) + "%, draws " + ftoa(st.DrawPct) + "%"
	return st, nil
}

func statsScope(f StatsFilter) string {
	var parts []string
	if f.Competition != "" {
		parts = append(parts, f.Competition)
	} else {
		parts = append(parts, "all competitions")
	}
	if f.Team != "" {
		parts = append(parts, "team "+f.Team)
	}
	switch {
	case f.Season != 0:
		parts = append(parts, strconv.Itoa(f.Season))
	case f.SeasonFrom != 0 || f.SeasonTo != 0:
		parts = append(parts, strconv.Itoa(f.SeasonFrom)+"-"+strconv.Itoa(f.SeasonTo))
	}
	return strings.Join(parts, ", ")
}

// LeaderboardEntry is one row of a ranked team list.
type LeaderboardEntry struct {
	Rank   int     `json:"rank"`
	Team   string  `json:"team"`
	TeamID string  `json:"team_id"`
	Value  float64 `json:"value"`
	Detail string  `json:"detail"`
}

// Leaderboard ranks clubs by a metric over a scope. Supported metrics:
// goals_for, goals_against, wins, points, win_rate, home_win_rate,
// away_win_rate, points_per_game, goal_difference, matches.
type LeaderboardFilter struct {
	Metric      string
	Competition string
	Season      int
	SeasonFrom  int
	SeasonTo    int
	Venue       string // "home", "away" or ""
	MinMatches  int
	Limit       int
	Ascending   bool
}

// Leaderboard answers "which team has the best/most X" questions.
func (g *Graph) Leaderboard(f LeaderboardFilter) ([]LeaderboardEntry, error) {
	metric := strings.ToLower(strings.TrimSpace(f.Metric))
	if metric == "" {
		metric = "points"
	}
	comp := ""
	if f.Competition != "" {
		comp = g.resolveCompetition(f.Competition)
		if comp == "" {
			return nil, &ErrNoData{What: "competition " + strconv.Quote(f.Competition)}
		}
	}

	recs := map[string]*Record{}
	names := map[string]string{}
	for i := range g.Matches {
		m := &g.Matches[i]
		if comp != "" && m.Competition != comp {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.SeasonFrom != 0 && m.Season < f.SeasonFrom {
			continue
		}
		if f.SeasonTo != 0 && m.Season > f.SeasonTo {
			continue
		}
		sides := []struct {
			ref    TeamRef
			gf, ga int
			home   bool
		}{
			{m.Home, m.HomeGoals, m.AwayGoals, true},
			{m.Away, m.AwayGoals, m.HomeGoals, false},
		}
		for _, s := range sides {
			if f.Venue == "home" && !s.home {
				continue
			}
			if f.Venue == "away" && s.home {
				continue
			}
			r := recs[s.ref.ID]
			if r == nil {
				r = &Record{}
				recs[s.ref.ID] = r
				names[s.ref.ID] = s.ref.Name
			}
			r.add(s.gf, s.ga)
		}
	}
	if len(recs) == 0 {
		return nil, &ErrNoData{What: "matches for the requested scope"}
	}

	// Rate metrics are meaningless for a club with two fixtures, so apply a
	// default floor unless the caller set one.
	minMatches := f.MinMatches
	if minMatches <= 0 && (strings.Contains(metric, "rate") || strings.Contains(metric, "per_game")) {
		minMatches = 10
	}

	var out []LeaderboardEntry
	for id, r := range recs {
		r.finish()
		if r.Matches < minMatches {
			continue
		}
		var v float64
		switch metric {
		case "goals_for", "goals", "goals_scored":
			v = float64(r.GoalsFor)
		case "goals_against", "goals_conceded":
			v = float64(r.GoalsAgainst)
		case "wins":
			v = float64(r.Wins)
		case "draws":
			v = float64(r.Draws)
		case "losses":
			v = float64(r.Losses)
		case "matches":
			v = float64(r.Matches)
		case "goal_difference":
			v = float64(r.GoalDiff)
		case "win_rate", "home_win_rate", "away_win_rate":
			v = r.WinRate
		case "points_per_game":
			v = r.PointsPerGame
		case "points":
			v = float64(r.Points)
		default:
			return nil, &ErrNoData{What: "unknown metric " + strconv.Quote(f.Metric)}
		}
		out = append(out, LeaderboardEntry{
			Team: names[id], TeamID: id, Value: v,
			Detail: itoa(r.Matches) + " matches, " + itoa(r.Wins) + "W " + itoa(r.Draws) +
				"D " + itoa(r.Losses) + "L, GF " + itoa(r.GoalsFor) + " GA " + itoa(r.GoalsAgainst) +
				", " + itoa(r.Points) + " pts",
		})
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Value != out[j].Value {
			if f.Ascending {
				return out[i].Value < out[j].Value
			}
			return out[i].Value > out[j].Value
		}
		return out[i].Team < out[j].Team
	})
	limit := f.Limit
	if limit <= 0 {
		limit = 10
	}
	if len(out) > limit {
		out = out[:limit]
	}
	for i := range out {
		out[i].Rank = i + 1
	}
	return out, nil
}

// SeasonComparison contrasts two seasons of the same competition.
type SeasonComparison struct {
	Competition string                       `json:"competition"`
	Seasons     map[string]*CompetitionStats `json:"seasons"`
	Deltas      map[string]float64           `json:"deltas"`
	Summary     string                       `json:"summary"`
}

// CompareSeasons answers "compare the 2018 and 2019 seasons".
func (g *Graph) CompareSeasons(competition string, a, b int) (*SeasonComparison, error) {
	sa, err := g.AggregateStats(StatsFilter{Competition: competition, Season: a})
	if err != nil {
		return nil, err
	}
	sb, err := g.AggregateStats(StatsFilter{Competition: competition, Season: b})
	if err != nil {
		return nil, err
	}
	comp := g.resolveCompetition(competition)
	out := &SeasonComparison{
		Competition: comp,
		Seasons:     map[string]*CompetitionStats{strconv.Itoa(a): sa, strconv.Itoa(b): sb},
		Deltas: map[string]float64{
			"matches":             float64(sb.Matches - sa.Matches),
			"avg_goals_per_match": round2(sb.AvgGoals - sa.AvgGoals),
			"home_win_pct":        round2(sb.HomeWinPct - sa.HomeWinPct),
			"draw_pct":            round2(sb.DrawPct - sa.DrawPct),
		},
	}
	out.Summary = comp + " " + strconv.Itoa(a) + " vs " + strconv.Itoa(b) + ": goals/match " +
		ftoa(sa.AvgGoals) + " -> " + ftoa(sb.AvgGoals) + ", home win% " +
		ftoa(sa.HomeWinPct) + " -> " + ftoa(sb.HomeWinPct)
	return out, nil
}

// Derby lists traditional rivalries the datasets can resolve.
type Derby struct {
	Name  string   `json:"name"`
	Teams []string `json:"teams"`
}

// knownDerbies are the classic Brazilian rivalries, by canonical team ID.
var knownDerbies = []struct {
	name string
	a, b string
}{
	{"Fla-Flu", "flamengo", "fluminense"},
	{"Clássico dos Milhões", "flamengo", "vasco-da-gama"},
	{"Clássico Vovô", "botafogo", "fluminense"},
	{"Clássico da Rivalidade", "botafogo", "flamengo"},
	{"Derby Paulista", "corinthians", "palmeiras"},
	{"Majestoso", "corinthians", "sao-paulo"},
	{"Clássico Alvinegro", "corinthians", "santos"},
	{"San-São", "santos", "sao-paulo"},
	{"Choque-Rei", "palmeiras", "sao-paulo"},
	{"Clássico da Saudade", "palmeiras", "santos"},
	{"Grenal", "gremio", "internacional"},
	{"Clássico Mineiro", "atletico-mineiro", "cruzeiro"},
	{"Atletiba", "athletico-paranaense", "coritiba"},
	{"Clássico dos Clássicos", "nautico", "sport-recife"},
	{"Ba-Vi", "bahia", "vitoria"},
	{"Clássico-Rei", "ceara", "fortaleza"},
}

// DerbyMatches finds fixtures between traditional rivals, optionally scoped to
// a season.
func (g *Graph) DerbyMatches(season int, limit int) (map[string][]string, error) {
	if limit <= 0 {
		limit = 10
	}
	out := map[string][]string{}
	for _, d := range knownDerbies {
		ta, okA := g.teams[d.a]
		tb, okB := g.teams[d.b]
		if !okA || !okB {
			continue
		}
		var lines []string
		for _, i := range ta.matchIdx {
			m := &g.Matches[i]
			if !m.Involves(tb.ID) {
				continue
			}
			if season != 0 && m.Season != season {
				continue
			}
			lines = append(lines, describeMatch(*m))
		}
		if len(lines) == 0 {
			continue
		}
		sort.Sort(sort.Reverse(sort.StringSlice(lines)))
		if len(lines) > limit {
			lines = lines[:limit]
		}
		out[d.name] = lines
	}
	if len(out) == 0 {
		return nil, &ErrNoData{What: "derby matches in the requested scope"}
	}
	return out, nil
}

// --- small helpers -------------------------------------------------------

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

func round2(f float64) float64 { return math.Round(f*100) / 100 }

func itoa(n int) string { return strconv.Itoa(n) }

func ftoa(f float64) string { return strconv.FormatFloat(f, 'f', -1, 64) }

func plural(n int, one, many string) string {
	if n == 1 {
		return "1 " + one
	}
	return strconv.Itoa(n) + " " + many
}
