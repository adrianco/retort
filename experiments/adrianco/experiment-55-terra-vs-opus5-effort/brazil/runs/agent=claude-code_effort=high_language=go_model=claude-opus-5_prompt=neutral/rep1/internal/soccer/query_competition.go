// query_competition.go implements the "Competition Queries" section: league
// tables computed from raw match results, and knockout brackets.
package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// StandingRow is one line of a computed league table.
type StandingRow struct {
	Position int    `json:"position"`
	Team     string `json:"team"`
	TeamID   string `json:"team_id"`
	Record
	Note string `json:"note,omitempty"`
}

// StandingsResult is a season's league table, derived purely from match results.
type StandingsResult struct {
	Competition     string        `json:"competition"`
	Season          int           `json:"season"`
	Table           []StandingRow `json:"table"`
	Champion        string        `json:"champion,omitempty"`
	RelegatedTeams  []string      `json:"relegated,omitempty"`
	MatchesUsed     int           `json:"matches_used"`
	ExpectedMatches int           `json:"expected_matches"`
	Complete        bool          `json:"season_complete"`
	Note            string        `json:"note,omitempty"`
	TieBreakers     string        `json:"tie_breakers"`
}

// Standings computes the final table for a league season. Points are 3 for a
// win and 1 for a draw; ties are broken by wins, then goal difference, then
// goals scored, matching the Brazilian federation's criteria.
func (g *Graph) Standings(competition string, season int) (*StandingsResult, error) {
	compID, err := ResolveCompetition(competition)
	if err != nil {
		return nil, err
	}
	if compID == "" {
		compID = CompSerieA
	}
	if competitionCatalog[compID].Kind != "league" {
		return nil, fmt.Errorf("%s is a knockout competition — use competition_bracket instead of standings",
			CompetitionName(compID))
	}
	if season == 0 {
		return nil, fmt.Errorf("a season is required, e.g. 2019")
	}

	var seasonMatches []*Match
	appearances := map[string]int{}
	for _, m := range g.byComp[compID] {
		if m.Season != season {
			continue
		}
		seasonMatches = append(seasonMatches, m)
		appearances[m.HomeTeamID]++
		appearances[m.AwayTeamID]++
	}
	if len(seasonMatches) == 0 {
		return nil, fmt.Errorf("no %s matches for season %d in the datasets", CompetitionName(compID), season)
	}

	// The source data occasionally mislabels a regional-championship fixture as
	// Série A (for example Brasília FC vs CA Taguatinga on 2016-01-30). Such
	// rows introduce clubs that played once in a 38-round season, so clubs with
	// fewer than a quarter of the busiest club's matches are treated as noise
	// and excluded from the table, with a note.
	maxPlayed := 0
	for _, n := range appearances {
		if n > maxPlayed {
			maxPlayed = n
		}
	}
	core := map[string]bool{}
	var excluded []string
	for _, id := range sortedKeys(appearances) {
		if appearances[id]*4 >= maxPlayed {
			core[id] = true
		} else {
			excluded = append(excluded, fmt.Sprintf("%s (%d match(es))", g.teamName(id), appearances[id]))
		}
	}

	recs := map[string]*Record{}
	used := 0
	for _, m := range seasonMatches {
		if !core[m.HomeTeamID] || !core[m.AwayTeamID] {
			continue
		}
		used++
		if recs[m.HomeTeamID] == nil {
			recs[m.HomeTeamID] = &Record{}
		}
		if recs[m.AwayTeamID] == nil {
			recs[m.AwayTeamID] = &Record{}
		}
		recs[m.HomeTeamID].add(m.HomeGoals, m.AwayGoals)
		recs[m.AwayTeamID].add(m.AwayGoals, m.HomeGoals)
	}

	res := &StandingsResult{
		Competition:     CompetitionName(compID),
		Season:          season,
		MatchesUsed:     used,
		ExpectedMatches: len(recs) * (len(recs) - 1),
		TieBreakers:     "points, then wins, then goal difference, then goals scored",
	}
	if len(excluded) > 0 {
		res.Note = "excluded as mislabelled source rows: " + strings.Join(excluded, ", ")
	}
	// A champion is only declared when every fixture of the double round-robin
	// is present; otherwise the table is a partial view and saying who "won"
	// would be a guess.
	res.Complete = res.ExpectedMatches > 0 && used >= res.ExpectedMatches

	for id := range recs {
		recs[id].finalize()
		res.Table = append(res.Table, StandingRow{Team: g.teamName(id), TeamID: id, Record: *recs[id]})
	}
	sort.SliceStable(res.Table, func(i, j int) bool {
		a, b := res.Table[i], res.Table[j]
		switch {
		case a.Points != b.Points:
			return a.Points > b.Points
		case a.Wins != b.Wins:
			return a.Wins > b.Wins
		case a.GoalDiff != b.GoalDiff:
			return a.GoalDiff > b.GoalDiff
		case a.GoalsFor != b.GoalsFor:
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	for i := range res.Table {
		res.Table[i].Position = i + 1
	}

	if res.Complete {
		res.Table[0].Note = "Champion"
		res.Champion = res.Table[0].Team
		n := len(res.Table)
		relegationSlots := 4
		if compID == CompSerieC {
			relegationSlots = 0
		}
		for i := n - relegationSlots; i < n && i >= 0; i++ {
			res.Table[i].Note = "Relegated"
			res.RelegatedTeams = append(res.RelegatedTeams, res.Table[i].Team)
		}
	} else {
		partial := fmt.Sprintf("only %d of the expected %d matches are present, so this table is partial and no champion is declared",
			used, res.ExpectedMatches)
		if res.Note == "" {
			res.Note = partial
		} else {
			res.Note += "; " + partial
		}
	}
	return res, nil
}

// BracketStage groups a knockout competition's matches by stage.
type BracketStage struct {
	Stage   string       `json:"stage"`
	Matches []MatchView  `json:"matches"`
	Ties    []BracketTie `json:"ties,omitempty"`
}

// BracketTie aggregates a two-legged tie into a single line.
type BracketTie struct {
	TeamA      string `json:"team_a"`
	TeamB      string `json:"team_b"`
	Legs       int    `json:"legs"`
	TeamAGoals int    `json:"team_a_goals"`
	TeamBGoals int    `json:"team_b_goals"`
	Aggregate  string `json:"aggregate"`
	Winner     string `json:"winner,omitempty"`
}

// BracketResult is a knockout competition's season, stage by stage.
type BracketResult struct {
	Competition string         `json:"competition"`
	Season      int            `json:"season"`
	Stages      []BracketStage `json:"stages"`
	Champion    string         `json:"champion,omitempty"`
	Note        string         `json:"note,omitempty"`
}

var stageOrder = map[string]int{
	"group stage": 0, "round of 16": 1, "quarterfinals": 2, "semifinals": 3, "final": 4,
}

func stageRank(s string) int {
	if v, ok := stageOrder[strings.ToLower(s)]; ok {
		return v
	}
	// "Round 3" etc. sort before the named knockout stages.
	var n int
	if _, err := fmt.Sscanf(strings.ToLower(s), "round %d", &n); err == nil {
		return -100 + n
	}
	return -1
}

// Bracket renders a knockout season stage by stage, collapsing two-legged ties.
func (g *Graph) Bracket(competition string, season int) (*BracketResult, error) {
	compID, err := ResolveCompetition(competition)
	if err != nil {
		return nil, err
	}
	if compID == "" {
		return nil, fmt.Errorf("a competition is required, e.g. libertadores or copa-do-brasil")
	}
	if competitionCatalog[compID].Kind != "knockout" {
		return nil, fmt.Errorf("%s is a league — use standings instead of competition_bracket",
			CompetitionName(compID))
	}
	if season == 0 {
		return nil, fmt.Errorf("a season is required, e.g. 2018")
	}

	byStage := map[string][]*Match{}
	for _, m := range g.byComp[compID] {
		if m.Season != season {
			continue
		}
		stage := m.Stage
		if stage == "" {
			stage = "Unclassified"
		}
		byStage[stage] = append(byStage[stage], m)
	}
	if len(byStage) == 0 {
		return nil, fmt.Errorf("no %s matches for season %d in the datasets", CompetitionName(compID), season)
	}

	res := &BracketResult{Competition: CompetitionName(compID), Season: season}
	for _, stage := range sortedKeys(byStage) {
		ms := byStage[stage]
		sort.SliceStable(ms, func(i, j int) bool { return ms[i].Date.Before(ms[j].Date) })
		bs := BracketStage{Stage: stage, Matches: g.ToViews(ms)}
		if !strings.EqualFold(stage, "Group Stage") {
			bs.Ties = g.collapseTies(ms)
		}
		res.Stages = append(res.Stages, bs)
	}
	sort.SliceStable(res.Stages, func(i, j int) bool {
		return stageRank(res.Stages[i].Stage) < stageRank(res.Stages[j].Stage)
	})

	// The winner of the final tie is the champion.
	for _, s := range res.Stages {
		if strings.EqualFold(s.Stage, "Final") && len(s.Ties) > 0 {
			res.Champion = s.Ties[0].Winner
		}
	}
	if res.Champion == "" {
		res.Note = "the champion could not be determined from the match data alone " +
			"(the final may have been decided on penalties or away goals)"
	}
	return res, nil
}

// collapseTies folds home-and-away legs between the same pair into one tie.
func (g *Graph) collapseTies(ms []*Match) []BracketTie {
	type acc struct {
		aID, bID string
		aGoals   int
		bGoals   int
		legs     int
	}
	order := []string{}
	seen := map[string]*acc{}
	for _, m := range ms {
		k := pairKey(m.HomeTeamID, m.AwayTeamID)
		a, ok := seen[k]
		if !ok {
			a = &acc{aID: m.HomeTeamID, bID: m.AwayTeamID}
			seen[k] = a
			order = append(order, k)
		}
		a.legs++
		if m.HomeTeamID == a.aID {
			a.aGoals += m.HomeGoals
			a.bGoals += m.AwayGoals
		} else {
			a.aGoals += m.AwayGoals
			a.bGoals += m.HomeGoals
		}
	}
	out := make([]BracketTie, 0, len(order))
	for _, k := range order {
		a := seen[k]
		t := BracketTie{
			TeamA: g.teamName(a.aID), TeamB: g.teamName(a.bID),
			Legs: a.legs, TeamAGoals: a.aGoals, TeamBGoals: a.bGoals,
			Aggregate: fmt.Sprintf("%d-%d", a.aGoals, a.bGoals),
		}
		switch {
		case a.aGoals > a.bGoals:
			t.Winner = t.TeamA
		case a.bGoals > a.aGoals:
			t.Winner = t.TeamB
		}
		out = append(out, t)
	}
	return out
}
