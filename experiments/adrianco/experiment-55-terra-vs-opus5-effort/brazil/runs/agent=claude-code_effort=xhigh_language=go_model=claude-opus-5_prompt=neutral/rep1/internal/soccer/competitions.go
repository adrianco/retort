// competitions.go answers competition-shaped questions: "who won the 2019
// Brasileirão", "which teams were relegated in 2020", "show the 2018 Libertadores
// bracket", "compare the 2018 and 2019 seasons".
//
// No dataset ships a standings table, so tables are recomputed from match
// results using the CBF tie-break order (points, wins, goal difference, goals
// for). Cup winners are derived from the final, aggregating two legged ties.
// Whenever the underlying data is incomplete the result says so rather than
// quietly reporting a wrong champion.
package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// StandingRow is one line of a league table.
type StandingRow struct {
	Position     int     `json:"position"`
	Team         string  `json:"team"`
	TeamID       string  `json:"team_id"`
	Played       int     `json:"played"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	GoalDiff     int     `json:"goal_difference"`
	Points       int     `json:"points"`
	WinRate      float64 `json:"win_rate_percent"`
	Zone         string  `json:"zone,omitempty"`
}

// StandingsResult is the payload of the standings tool.
type StandingsResult struct {
	Competition string        `json:"competition"`
	Season      int           `json:"season"`
	Scope       string        `json:"scope"`
	Complete    bool          `json:"season_complete"`
	Rows        []StandingRow `json:"table"`
	Champion    string        `json:"champion,omitempty"`
	Relegated   []string      `json:"relegated,omitempty"`
	Excluded    []string      `json:"excluded_teams,omitempty"`
	Notes       []string      `json:"notes,omitempty"`
}

// Standings computes a league table from match results. venue restricts the
// table to home or away matches, which is what "best home record" questions
// need.
func (g *Graph) Standings(comp Competition, season int, venue Venue) (*StandingsResult, error) {
	if !comp.IsLeague() {
		return nil, fmt.Errorf("%s is a knockout competition; use competition_bracket or champions instead", comp)
	}
	ms := g.SeasonMatches(comp, season)
	if len(ms) == 0 {
		seasons := g.Seasons(comp)
		return nil, fmt.Errorf("no %s matches for season %d (available: %s)", comp, season, formatSeasons(seasons))
	}
	res := &StandingsResult{Competition: string(comp), Season: season, Scope: fmt.Sprintf("%d %s", season, comp)}
	if venue != VenueAll {
		res.Scope += fmt.Sprintf(" (%s matches only)", venue)
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
	played := map[string]int{}
	for _, m := range ms {
		played[m.HomeID]++
		played[m.AwayID]++
		if venue != VenueAway {
			get(m.HomeID).add(m.HomeGoals, m.AwayGoals)
		}
		if venue != VenueHome {
			get(m.AwayID).add(m.AwayGoals, m.HomeGoals)
		}
	}

	// A handful of rows in BR-Football carry a competition label that does not
	// match the fixture (a state-championship game filed under Serie A). Clubs
	// with a token number of matches are dropped from the table and reported.
	maxPlayed := 0
	for _, n := range played {
		if n > maxPlayed {
			maxPlayed = n
		}
	}
	threshold := maxPlayed / 3
	for id, rec := range records {
		if played[id] < threshold {
			if t, ok := g.Team(id); ok {
				res.Excluded = append(res.Excluded, fmt.Sprintf("%s (%d matches)", t.Display, played[id]))
			}
			delete(records, id)
			continue
		}
		rec.finish()
	}
	sort.Strings(res.Excluded)

	for id, rec := range records {
		t, ok := g.Team(id)
		if !ok {
			continue
		}
		res.Rows = append(res.Rows, StandingRow{
			Team: t.Display, TeamID: id,
			Played: rec.Played, Wins: rec.Wins, Draws: rec.Draws, Losses: rec.Losses,
			GoalsFor: rec.GoalsFor, GoalsAgainst: rec.GoalsAgainst,
			GoalDiff: rec.GoalDiff, Points: rec.Points, WinRate: rec.WinRate,
		})
	}
	sortStandings(res.Rows)
	for i := range res.Rows {
		res.Rows[i].Position = i + 1
	}

	// A season is complete when every club played the full double round-robin:
	// teams*(teams-1) fixtures, i.e. twice that many team-appearances.
	teams := len(res.Rows)
	expected := teams * (teams - 1)
	total := 0
	for _, r := range res.Rows {
		total += r.Played
	}
	if venue == VenueAll {
		res.Complete = teams > 1 && total == 2*expected
	} else {
		res.Complete = teams > 1 && total == expected
	}

	if res.Complete && venue == VenueAll {
		res.Champion = res.Rows[0].Team
		res.Rows[0].Zone = "champion"
		if teams >= 16 {
			for i := teams - 4; i < teams; i++ {
				res.Rows[i].Zone = "relegation"
				res.Relegated = append(res.Relegated, res.Rows[i].Team)
			}
		}
	} else if venue == VenueAll {
		res.Notes = append(res.Notes, fmt.Sprintf(
			"The %d %s data in this repository is incomplete (%d of the %d fixtures a %d-club double round-robin needs), so this is a partial standing rather than a final classification.",
			season, comp, total/2, expected, teams))
	}
	res.Notes = append(res.Notes, "Table computed from match results; tie-break order is points, wins, goal difference, goals scored (CBF rules).")
	return res, nil
}

// sortStandings applies the CBF tie-break order.
func sortStandings(rows []StandingRow) {
	sort.SliceStable(rows, func(i, j int) bool {
		a, b := rows[i], rows[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		if a.GoalDiff != b.GoalDiff {
			return a.GoalDiff > b.GoalDiff
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
}

func formatSeasons(seasons []int) string {
	if len(seasons) == 0 {
		return "none"
	}
	parts := make([]string, len(seasons))
	for i, s := range seasons {
		parts[i] = fmt.Sprintf("%d", s)
	}
	return strings.Join(parts, ", ")
}

// ChampionEntry is one competition winner.
type ChampionEntry struct {
	Competition string      `json:"competition"`
	Season      int         `json:"season"`
	Champion    string      `json:"champion,omitempty"`
	ChampionID  string      `json:"champion_id,omitempty"`
	RunnerUp    string      `json:"runner_up,omitempty"`
	Detail      string      `json:"detail,omitempty"`
	Decided     bool        `json:"decided"`
	Final       []MatchView `json:"final,omitempty"`
}

// buildChampions precomputes every competition winner once at load time, so that
// team profiles and champion queries are instant.
func (g *Graph) buildChampions() {
	g.titles = map[string][]Title{}
	for _, comp := range AllCompetitions {
		for _, season := range g.Seasons(comp) {
			entry := g.computeChampion(comp, season)
			g.champions = append(g.champions, entry)
			if entry.Decided && entry.ChampionID != "" {
				g.titles[entry.ChampionID] = append(g.titles[entry.ChampionID], Title{
					Competition: entry.Competition, Season: entry.Season, Detail: entry.Detail,
				})
			}
		}
	}
	sort.Slice(g.champions, func(i, j int) bool {
		if g.champions[i].Competition != g.champions[j].Competition {
			return g.champions[i].Competition < g.champions[j].Competition
		}
		return g.champions[i].Season < g.champions[j].Season
	})
}

// computeChampion derives the winner of one competition season.
func (g *Graph) computeChampion(comp Competition, season int) ChampionEntry {
	entry := ChampionEntry{Competition: string(comp), Season: season}
	if comp.IsLeague() {
		table, err := g.Standings(comp, season, VenueAll)
		if err != nil || len(table.Rows) == 0 {
			entry.Detail = "no data"
			return entry
		}
		top := table.Rows[0]
		entry.Champion, entry.ChampionID = top.Team, top.TeamID
		if len(table.Rows) > 1 {
			entry.RunnerUp = table.Rows[1].Team
		}
		entry.Decided = table.Complete
		if table.Complete {
			entry.Detail = fmt.Sprintf("%d pts (%dW %dD %dL)", top.Points, top.Wins, top.Draws, top.Losses)
		} else {
			entry.Detail = "season incomplete in the provided data; this is the leader, not a confirmed champion"
		}
		return entry
	}
	return g.cupWinner(comp, season, entry)
}

// cupWinner resolves a knockout competition by aggregating the final.
func (g *Graph) cupWinner(comp Competition, season int, entry ChampionEntry) ChampionEntry {
	var finals []*Match
	for _, m := range g.SeasonMatches(comp, season) {
		if strings.EqualFold(m.Stage, "final") {
			finals = append(finals, m)
		}
	}
	if len(finals) == 0 {
		entry.Detail = "the final is not present in the provided data"
		return entry
	}
	agg := map[string]int{}
	for _, m := range finals {
		agg[m.HomeID] += m.HomeGoals
		agg[m.AwayID] += m.AwayGoals
		entry.Final = append(entry.Final, g.View(m))
	}
	type pair struct {
		id    string
		goals int
	}
	var sides []pair
	for id, goals := range agg {
		sides = append(sides, pair{id, goals})
	}
	sort.Slice(sides, func(i, j int) bool {
		if sides[i].goals != sides[j].goals {
			return sides[i].goals > sides[j].goals
		}
		return sides[i].id < sides[j].id
	})
	if len(sides) < 2 {
		entry.Detail = "the final is only partially present in the provided data"
		return entry
	}
	winner, loser := sides[0], sides[1]
	wt, _ := g.Team(winner.id)
	lt, _ := g.Team(loser.id)
	if winner.goals == loser.goals {
		entry.Detail = fmt.Sprintf("final aggregate %d-%d between %s and %s: decided on penalties, which the datasets do not record",
			winner.goals, loser.goals, wt.Display, lt.Display)
		entry.RunnerUp = ""
		return entry
	}
	entry.Champion, entry.ChampionID = wt.Display, wt.ID
	entry.RunnerUp = lt.Display
	entry.Decided = true
	if len(finals) == 1 {
		entry.Detail = fmt.Sprintf("won the final %d-%d", winner.goals, loser.goals)
	} else {
		entry.Detail = fmt.Sprintf("won the two legged final %d-%d on aggregate", winner.goals, loser.goals)
	}
	return entry
}

// ChampionsResult is the payload of the champions tool.
type ChampionsResult struct {
	Scope     string          `json:"scope"`
	Champions []ChampionEntry `json:"champions"`
	Titles    []string        `json:"titles_by_club,omitempty"`
	Note      string          `json:"note,omitempty"`
}

// Champions lists winners for a competition and season range. An empty
// competition covers all of them.
func (g *Graph) Champions(comp Competition, from, to int) *ChampionsResult {
	res := &ChampionsResult{Scope: "all competitions"}
	if comp != "" {
		res.Scope = string(comp)
	}
	if from != 0 || to != 0 {
		res.Scope += fmt.Sprintf(", seasons %d-%d", from, to)
	}
	counts := map[string]int{}
	for _, c := range g.champions {
		if comp != "" && c.Competition != string(comp) {
			continue
		}
		if from != 0 && c.Season < from {
			continue
		}
		if to != 0 && c.Season > to {
			continue
		}
		res.Champions = append(res.Champions, c)
		if c.Decided && c.Champion != "" {
			counts[c.Champion]++
		}
	}
	res.Titles = topKeys(counts, 10)
	if len(res.Champions) == 0 {
		res.Note = "No seasons match this query. " + g.coverageHint(MatchFilter{Competition: comp})
	}
	return res
}

// TitlesFor returns the competitions a club won, newest first.
func (g *Graph) TitlesFor(t *Team) []Title {
	titles := append([]Title(nil), g.titles[t.ID]...)
	sort.Slice(titles, func(i, j int) bool {
		if titles[i].Season != titles[j].Season {
			return titles[i].Season > titles[j].Season
		}
		return titles[i].Competition < titles[j].Competition
	})
	return titles
}

// Tie is a knockout pairing, aggregated over its legs.
type Tie struct {
	Stage      string      `json:"stage"`
	TeamA      string      `json:"team_a"`
	TeamB      string      `json:"team_b"`
	AggregateA int         `json:"aggregate_a"`
	AggregateB int         `json:"aggregate_b"`
	Winner     string      `json:"winner,omitempty"`
	Legs       []MatchView `json:"legs"`
}

// BracketResult is the payload of the competition_bracket tool.
type BracketResult struct {
	Competition string   `json:"competition"`
	Season      int      `json:"season"`
	Stages      []Stage  `json:"stages"`
	Champion    string   `json:"champion,omitempty"`
	Notes       []string `json:"notes,omitempty"`
}

// Stage groups the ties played at one point of a knockout competition.
type Stage struct {
	Name    string `json:"name"`
	Matches int    `json:"matches"`
	Ties    []Tie  `json:"ties,omitempty"`
}

// stageOrder sorts knockout stages from earliest to the final.
var stageOrder = map[string]int{
	"group stage": 0, "round of 128": 1, "round of 64": 2, "round of 32": 3,
	"round of 16": 4, "quarterfinals": 5, "semifinals": 6, "final": 7,
}

// Bracket reconstructs the knockout path of a cup season.
func (g *Graph) Bracket(comp Competition, season int) (*BracketResult, error) {
	if comp.IsLeague() {
		return nil, fmt.Errorf("%s is a league; use standings instead", comp)
	}
	ms := g.SeasonMatches(comp, season)
	if len(ms) == 0 {
		return nil, fmt.Errorf("no %s matches for season %d (available: %s)", comp, season, formatSeasons(g.Seasons(comp)))
	}
	byStage := map[string][]*Match{}
	for _, m := range ms {
		stage := m.StageLabel()
		if stage == "" {
			stage = "unlabelled"
		}
		byStage[strings.ToLower(stage)] = append(byStage[strings.ToLower(stage)], m)
	}
	res := &BracketResult{Competition: string(comp), Season: season}
	names := make([]string, 0, len(byStage))
	for name := range byStage {
		names = append(names, name)
	}
	sort.Slice(names, func(i, j int) bool {
		oi, oki := stageOrder[names[i]]
		oj, okj := stageOrder[names[j]]
		if oki && okj {
			return oi < oj
		}
		if oki != okj {
			return okj
		}
		return names[i] < names[j]
	})
	for _, name := range names {
		stage := Stage{Name: name, Matches: len(byStage[name])}
		if name != "group stage" {
			stage.Ties = g.buildTies(name, byStage[name])
		}
		res.Stages = append(res.Stages, stage)
	}
	champ := g.championOf(comp, season)
	if champ != nil {
		res.Champion = champ.Champion
		if champ.Detail != "" {
			res.Notes = append(res.Notes, champ.Detail)
		}
	}
	if comp == CopaDoBrasil {
		res.Notes = append(res.Notes, "Copa do Brasil rounds are numbered in the source file; stage names are derived by counting back from the last round played that season.")
	}
	return res, nil
}

// buildTies pairs up the legs of a knockout round.
func (g *Graph) buildTies(stage string, ms []*Match) []Tie {
	groups := map[string][]*Match{}
	var order []string
	for _, m := range ms {
		a, b := m.HomeID, m.AwayID
		if a > b {
			a, b = b, a
		}
		key := a + "|" + b
		if _, ok := groups[key]; !ok {
			order = append(order, key)
		}
		groups[key] = append(groups[key], m)
	}
	sort.Strings(order)
	ties := make([]Tie, 0, len(order))
	for _, key := range order {
		legs := groups[key]
		sort.SliceStable(legs, func(i, j int) bool { return legs[i].Date.Before(legs[j].Date) })
		ids := strings.SplitN(key, "|", 2)
		ta, _ := g.Team(ids[0])
		tb, _ := g.Team(ids[1])
		tie := Tie{Stage: stage, TeamA: ta.Display, TeamB: tb.Display}
		for _, m := range legs {
			if m.HomeID == ta.ID {
				tie.AggregateA += m.HomeGoals
				tie.AggregateB += m.AwayGoals
			} else {
				tie.AggregateA += m.AwayGoals
				tie.AggregateB += m.HomeGoals
			}
			tie.Legs = append(tie.Legs, g.View(m))
		}
		switch {
		case tie.AggregateA > tie.AggregateB:
			tie.Winner = tie.TeamA
		case tie.AggregateB > tie.AggregateA:
			tie.Winner = tie.TeamB
		default:
			tie.Winner = "decided on penalties (not in the data)"
		}
		ties = append(ties, tie)
	}
	return ties
}

// championOf looks up a precomputed champion entry.
func (g *Graph) championOf(comp Competition, season int) *ChampionEntry {
	for i := range g.champions {
		if g.champions[i].Competition == string(comp) && g.champions[i].Season == season {
			return &g.champions[i]
		}
	}
	return nil
}

// SeasonSummary aggregates one competition season.
type SeasonSummary struct {
	Competition     string     `json:"competition"`
	Season          int        `json:"season"`
	Matches         int        `json:"matches"`
	Teams           int        `json:"teams"`
	Goals           int        `json:"goals"`
	GoalsPerMatch   float64    `json:"goals_per_match"`
	HomeWinPercent  float64    `json:"home_win_percent"`
	DrawPercent     float64    `json:"draw_percent"`
	AwayWinPercent  float64    `json:"away_win_percent"`
	Champion        string     `json:"champion,omitempty"`
	ChampionDetail  string     `json:"champion_detail,omitempty"`
	TopScoringTeams []string   `json:"top_scoring_teams,omitempty"`
	BestDefences    []string   `json:"best_defences,omitempty"`
	BiggestWin      *MatchView `json:"biggest_win,omitempty"`
	HighestScoring  *MatchView `json:"highest_scoring_match,omitempty"`
	Stages          []string   `json:"stages,omitempty"`
	DataSources     []string   `json:"data_sources,omitempty"`
}

// CompetitionSummaryResult is the payload of the competition_summary tool; it
// holds one entry per requested season plus a comparison when several are asked
// for.
type CompetitionSummaryResult struct {
	Scope      string          `json:"scope"`
	Seasons    []SeasonSummary `json:"seasons"`
	Comparison []string        `json:"comparison,omitempty"`
	Notes      []string        `json:"notes,omitempty"`
}

// CompetitionSummary aggregates one or more seasons of a competition.
func (g *Graph) CompetitionSummary(comp Competition, seasons []int) (*CompetitionSummaryResult, error) {
	if comp == "" {
		return nil, fmt.Errorf("a competition is required")
	}
	if len(seasons) == 0 {
		seasons = g.Seasons(comp)
		if len(seasons) > 0 {
			seasons = seasons[len(seasons)-1:]
		}
	}
	res := &CompetitionSummaryResult{Scope: string(comp)}
	for _, season := range seasons {
		ms := g.SeasonMatches(comp, season)
		if len(ms) == 0 {
			return nil, fmt.Errorf("no %s matches for season %d (available: %s)", comp, season, formatSeasons(g.Seasons(comp)))
		}
		sum := SeasonSummary{Competition: string(comp), Season: season, Matches: len(ms)}
		teams := map[string]bool{}
		scored := map[string]int{}
		conceded := map[string]int{}
		stages := map[string]bool{}
		sources := map[string]bool{}
		var biggest, highest *Match
		homeWins, draws := 0, 0
		for _, m := range ms {
			teams[m.HomeID], teams[m.AwayID] = true, true
			sum.Goals += m.TotalGoals()
			scored[m.HomeID] += m.HomeGoals
			scored[m.AwayID] += m.AwayGoals
			conceded[m.HomeID] += m.AwayGoals
			conceded[m.AwayID] += m.HomeGoals
			if s := m.StageLabel(); s != "" {
				stages[s] = true
			}
			for _, src := range m.SourceList() {
				sources[src] = true
			}
			switch {
			case m.HomeGoals > m.AwayGoals:
				homeWins++
			case m.HomeGoals == m.AwayGoals:
				draws++
			}
			if biggest == nil || m.GoalDifference() > biggest.GoalDifference() {
				biggest = m
			}
			if highest == nil || m.TotalGoals() > highest.TotalGoals() {
				highest = m
			}
		}
		sum.Teams = len(teams)
		sum.GoalsPerMatch = round2(float64(sum.Goals) / float64(len(ms)))
		sum.HomeWinPercent = round1(float64(homeWins) * 100 / float64(len(ms)))
		sum.DrawPercent = round1(float64(draws) * 100 / float64(len(ms)))
		sum.AwayWinPercent = round1(float64(len(ms)-homeWins-draws) * 100 / float64(len(ms)))
		sum.TopScoringTeams = g.topTeamCounts(scored, 5, "goals")
		sum.BestDefences = g.bottomTeamCounts(conceded, 5, "conceded")
		if biggest != nil {
			v := g.View(biggest)
			sum.BiggestWin = &v
		}
		if highest != nil {
			v := g.View(highest)
			sum.HighestScoring = &v
		}
		for s := range stages {
			sum.Stages = append(sum.Stages, s)
		}
		sort.Strings(sum.Stages)
		for s := range sources {
			sum.DataSources = append(sum.DataSources, s)
		}
		sort.Strings(sum.DataSources)
		if champ := g.championOf(comp, season); champ != nil {
			sum.Champion, sum.ChampionDetail = champ.Champion, champ.Detail
		}
		res.Seasons = append(res.Seasons, sum)
	}
	if len(res.Seasons) > 1 {
		res.Comparison = compareSeasons(res.Seasons)
	}
	res.Notes = append(res.Notes,
		"Individual goalscorer data is not present in any of the provided datasets, so top scorers are reported per team rather than per player.")
	return res, nil
}

// compareSeasons renders the deltas between the first and last season asked for.
func compareSeasons(seasons []SeasonSummary) []string {
	first, last := seasons[0], seasons[len(seasons)-1]
	return []string{
		fmt.Sprintf("Matches: %d in %d vs %d in %d", first.Matches, first.Season, last.Matches, last.Season),
		fmt.Sprintf("Goals per match: %.2f in %d vs %.2f in %d (%+.2f)", first.GoalsPerMatch, first.Season, last.GoalsPerMatch, last.Season, last.GoalsPerMatch-first.GoalsPerMatch),
		fmt.Sprintf("Home win rate: %.1f%% in %d vs %.1f%% in %d (%+.1f points)", first.HomeWinPercent, first.Season, last.HomeWinPercent, last.Season, last.HomeWinPercent-first.HomeWinPercent),
		fmt.Sprintf("Draw rate: %.1f%% in %d vs %.1f%% in %d", first.DrawPercent, first.Season, last.DrawPercent, last.Season),
		fmt.Sprintf("Champion: %s in %d, %s in %d", orNone(first.Champion), first.Season, orNone(last.Champion), last.Season),
	}
}

func orNone(s string) string {
	if s == "" {
		return "not determined from the data"
	}
	return s
}

// topTeamCounts renders the highest values of a per-team counter.
func (g *Graph) topTeamCounts(counts map[string]int, n int, unit string) []string {
	return g.rankTeamCounts(counts, n, unit, true)
}

// bottomTeamCounts renders the lowest values of a per-team counter.
func (g *Graph) bottomTeamCounts(counts map[string]int, n int, unit string) []string {
	return g.rankTeamCounts(counts, n, unit, false)
}

func (g *Graph) rankTeamCounts(counts map[string]int, n int, unit string, desc bool) []string {
	type kv struct {
		id string
		n  int
	}
	var list []kv
	for id, c := range counts {
		list = append(list, kv{id, c})
	}
	sort.Slice(list, func(i, j int) bool {
		if list[i].n != list[j].n {
			if desc {
				return list[i].n > list[j].n
			}
			return list[i].n < list[j].n
		}
		return list[i].id < list[j].id
	})
	var out []string
	for i := 0; i < len(list) && i < n; i++ {
		t, ok := g.Team(list[i].id)
		if !ok {
			continue
		}
		out = append(out, fmt.Sprintf("%s (%d %s)", t.Display, list[i].n, unit))
	}
	return out
}
