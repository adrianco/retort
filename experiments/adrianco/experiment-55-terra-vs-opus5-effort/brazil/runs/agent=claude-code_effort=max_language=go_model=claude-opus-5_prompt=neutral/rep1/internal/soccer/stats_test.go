package soccer

import (
	"fmt"
	"testing"
	"time"
)

// TestKnownChampions checks the computed tables against seasons whose outcome
// is a matter of record. If normalisation, deduplication or the points
// calculation break, these are the first things to go wrong.
func TestKnownChampions(t *testing.T) {
	s := testStore(t)
	cases := []struct {
		comp     string
		season   int
		champion string
		points   int
	}{
		{CompBrasileirao, 2003, "Cruzeiro", 100},
		{CompBrasileirao, 2009, "Flamengo", 67},
		{CompBrasileirao, 2012, "Fluminense", 77},
		{CompBrasileirao, 2013, "Cruzeiro", 76},
		{CompBrasileirao, 2015, "Corinthians", 81},
		{CompBrasileirao, 2016, "Palmeiras", 80},
		{CompBrasileirao, 2017, "Corinthians", 72},
		{CompBrasileirao, 2018, "Palmeiras", 80},
		{CompBrasileirao, 2019, "Flamengo", 90},
		{CompBrasileirao, 2020, "Flamengo", 71},
		{CompBrasileirao, 2021, "Atlético-MG", 84},
		{CompBrasileirao, 2022, "Palmeiras", 81},
	}
	for _, c := range cases {
		table := s.Standings(c.comp, c.season, StandingsOptions{})
		if table.Champion != c.champion {
			t.Errorf("%s %d champion = %q, want %q", c.comp, c.season, table.Champion, c.champion)
			continue
		}
		if got := table.Rows[0].Points; got != c.points {
			t.Errorf("%s %d: %s finished on %d points, want %d", c.comp, c.season, c.champion, got, c.points)
		}
	}
}

// The 2019 table is the example in the specification.
func TestStandings2019MatchesTheSpecification(t *testing.T) {
	s := testStore(t)
	table := s.Standings(CompBrasileirao, 2019, StandingsOptions{})
	if len(table.Rows) != 20 {
		t.Fatalf("2019 table has %d clubs", len(table.Rows))
	}
	want := []struct {
		pos             int
		team            string
		points, w, d, l int
	}{
		{1, "Flamengo", 90, 28, 6, 4},
		{2, "Santos", 74, 22, 8, 8},
		{3, "Palmeiras", 74, 21, 11, 6},
	}
	for _, w := range want {
		row := table.Rows[w.pos-1]
		if row.TeamName != w.team || row.Points != w.points || row.Wins != w.w || row.Draws != w.d || row.Losses != w.l {
			t.Errorf("position %d = %s %d pts (%dW %dD %dL), want %s %d pts (%dW %dD %dL)",
				w.pos, row.TeamName, row.Points, row.Wins, row.Draws, row.Losses, w.team, w.points, w.w, w.d, w.l)
		}
	}
	if len(table.Relegated) != 4 {
		t.Errorf("2019 relegated %v, want four clubs", table.Relegated)
	}
	if !table.Complete {
		t.Error("2019 should be a complete season")
	}
}

// Where fixtures are missing, no champion may be declared: the 2023 Série A is
// three matches short and the leader of the partial table is not the club that
// actually won the title.
func TestIncompleteSeasonDeclaresNoChampion(t *testing.T) {
	s := testStore(t)
	table := s.Standings(CompBrasileirao, 2023, StandingsOptions{})
	if table.Complete {
		t.Fatal("2023 should be reported as incomplete")
	}
	if table.Champion != "" {
		t.Errorf("2023 declared %q champion from an incomplete season", table.Champion)
	}
	if table.Leader == "" {
		t.Error("2023 should still report who leads the partial table")
	}
	if table.Note == "" {
		t.Error("an incomplete season must explain itself")
	}
}

// Série C is played in groups and knockouts, so a single table is not a league
// standing and must not name a champion.
func TestGroupFormatHasNoChampion(t *testing.T) {
	s := testStore(t)
	table := s.Standings(CompSerieC, 2022, StandingsOptions{})
	if len(table.Rows) == 0 {
		t.Fatal("no Série C 2022 table")
	}
	if table.Champion != "" {
		t.Errorf("Série C 2022 declared %q champion", table.Champion)
	}
	if table.Note == "" {
		t.Error("Série C tables must carry the format caveat")
	}
}

func TestRelegation2020(t *testing.T) {
	s := testStore(t)
	table := s.Standings(CompBrasileirao, 2020, StandingsOptions{})
	want := map[string]bool{"Vasco da Gama": true, "Goiás": true, "Coritiba": true, "Botafogo": true}
	if len(table.Relegated) != 4 {
		t.Fatalf("relegated = %v", table.Relegated)
	}
	for _, name := range table.Relegated {
		if !want[name] {
			t.Errorf("%s was not relegated in 2020 (got %v)", name, table.Relegated)
		}
	}
}

func TestStandingsThroughRound(t *testing.T) {
	s := testStore(t)
	table := s.Standings(CompBrasileirao, 2019, StandingsOptions{ThroughRound: 10})
	if table.Matches != 100 {
		t.Errorf("ten rounds of a 20 club league is 100 matches, got %d", table.Matches)
	}
	if table.Champion != "" {
		t.Error("a partial table must not name a champion")
	}
	for _, row := range table.Rows {
		if row.Matches > 10 {
			t.Errorf("%s played %d matches in the first ten rounds", row.TeamName, row.Matches)
		}
	}
}

func TestHomeAndAwayTables(t *testing.T) {
	s := testStore(t)
	home := s.Standings(CompBrasileirao, 2019, StandingsOptions{Venue: VenueHome})
	away := s.Standings(CompBrasileirao, 2019, StandingsOptions{Venue: VenueAway})
	for _, table := range []*Standings{home, away} {
		for _, row := range table.Rows {
			if row.Matches != 19 {
				t.Errorf("%s played %d matches in a one-venue table, want 19", row.TeamName, row.Matches)
			}
		}
	}
	if home.Rows[0].Points <= 0 || away.Rows[0].Points <= 0 {
		t.Error("venue tables should still award points")
	}
}

func TestHeadToHead(t *testing.T) {
	s := testStore(t)
	h := s.HeadToHead("flamengo-rj", "fluminense-rj", MatchFilter{})
	if h == nil {
		t.Fatal("no head-to-head")
	}
	if h.Total < 40 {
		t.Errorf("Fla-Flu has only %d meetings in the data", h.Total)
	}
	if h.AWins+h.BWins+h.Draws != h.Total {
		t.Errorf("results do not add up: %d + %d + %d != %d", h.AWins, h.BWins, h.Draws, h.Total)
	}
	if h.Rivalry != "Fla-Flu" {
		t.Errorf("rivalry = %q, want Fla-Flu", h.Rivalry)
	}
	if h.FirstMeeting == nil || h.LastMeeting == nil {
		t.Error("first and last meeting should be reported")
	}
	if h.FirstMeeting.Date.After(h.LastMeeting.Date) {
		t.Error("first meeting is after the last")
	}
	// Reversing the clubs mirrors the record.
	rev := s.HeadToHead("fluminense-rj", "flamengo-rj", MatchFilter{})
	if rev.AWins != h.BWins || rev.BWins != h.AWins || rev.Draws != h.Draws {
		t.Errorf("mirrored head-to-head disagrees: %+v vs %+v", h, rev)
	}
	// Every match must involve both clubs.
	for _, m := range h.Matches {
		if !m.Involves("flamengo-rj") || !m.Involves("fluminense-rj") {
			t.Errorf("unrelated match in head-to-head: %s", m.Label())
		}
	}
}

func TestHeadToHeadWithFilter(t *testing.T) {
	s := testStore(t)
	h := s.HeadToHead("palmeiras-sp", "santos-sp", MatchFilter{CompetitionID: CompBrasileirao, SeasonFrom: 2015, SeasonTo: 2019})
	for _, m := range h.Matches {
		if m.CompetitionID != CompBrasileirao || m.Season < 2015 || m.Season > 2019 {
			t.Errorf("filter ignored: %s %d", m.CompetitionID, m.Season)
		}
	}
}

func TestTeamRecordMatchesStandings(t *testing.T) {
	s := testStore(t)
	table := s.Standings(CompBrasileirao, 2022, StandingsOptions{})
	for _, row := range table.Rows[:5] {
		rec := s.TeamRecord(row.TeamID, MatchFilter{CompetitionID: CompBrasileirao, Season: 2022})
		if rec.Matches != row.Matches || rec.Wins != row.Wins || rec.GoalsFor != row.GoalsFor {
			t.Errorf("%s: TeamRecord %+v disagrees with the table row %+v", row.TeamName, rec, row.Record)
		}
	}
}

func TestCorinthiansHomeRecord2022(t *testing.T) {
	s := testStore(t)
	rec := s.TeamRecord("corinthians-sp", MatchFilter{CompetitionID: CompBrasileirao, Season: 2022, Venue: VenueHome})
	if rec.Matches != 19 {
		t.Errorf("Corinthians played %d home matches in 2022, want 19", rec.Matches)
	}
	if rec.Wins+rec.Draws+rec.Losses != rec.Matches {
		t.Error("results do not add up")
	}
	if rec.WinRate() <= 0 || rec.WinRate() > 100 {
		t.Errorf("win rate %.1f is out of range", rec.WinRate())
	}
}

func TestAggregate(t *testing.T) {
	s := testStore(t)
	a := s.Aggregate(MatchFilter{CompetitionID: CompBrasileirao})
	if a.Matches < 8000 {
		t.Errorf("only %d Brasileirão matches", a.Matches)
	}
	if a.HomeWins+a.AwayWins+a.Draws != a.Matches {
		t.Error("outcomes do not add up")
	}
	if a.AvgGoals < 2.0 || a.AvgGoals > 3.5 {
		t.Errorf("average goals per match = %.2f, which is not plausible", a.AvgGoals)
	}
	if a.HomeWinRate < 40 || a.HomeWinRate > 60 {
		t.Errorf("home win rate = %.1f%%, which is not plausible", a.HomeWinRate)
	}
	if a.Goals != a.HomeGoals+a.AwayGoals {
		t.Error("goals do not add up")
	}
	if a.HomeGoals <= a.AwayGoals {
		t.Error("home teams should outscore away teams over 8000 matches")
	}
}

func TestTeamRecordsRanking(t *testing.T) {
	s := testStore(t)
	best := s.TeamRecords(MatchFilter{CompetitionID: CompBrasileirao, Season: 2019}, "points", 10, 5)
	if len(best) != 5 {
		t.Fatalf("got %d ranked clubs", len(best))
	}
	if best[0].TeamName != "Flamengo" {
		t.Errorf("best 2019 record = %s, want Flamengo", best[0].TeamName)
	}
	for i := 1; i < len(best); i++ {
		if best[i-1].Points() < best[i].Points() {
			t.Error("ranking is not sorted by points")
		}
	}
	scorers := s.TeamRecords(MatchFilter{CompetitionID: CompBrasileirao, Season: 2019}, "goals_for", 10, 3)
	for i := 1; i < len(scorers); i++ {
		if scorers[i-1].GoalsFor < scorers[i].GoalsFor {
			t.Error("goals_for ranking is not sorted")
		}
	}
	home := s.TeamRecords(MatchFilter{CompetitionID: CompBrasileirao, Season: 2019, Venue: VenueHome}, "win_rate", 10, 3)
	for _, r := range home {
		if r.Matches != 19 {
			t.Errorf("%s has %d home matches in 2019", r.TeamName, r.Matches)
		}
	}
}

func TestBiggestWins(t *testing.T) {
	s := testStore(t)
	ms := s.BiggestWins(MatchFilter{CompetitionID: CompBrasileirao}, 5)
	if len(ms) != 5 {
		t.Fatalf("got %d matches", len(ms))
	}
	for i := 1; i < len(ms); i++ {
		if ms[i-1].GoalMargin() < ms[i].GoalMargin() {
			t.Error("biggest wins are not sorted by margin")
		}
	}
	if ms[0].GoalMargin() < 6 {
		t.Errorf("the biggest Brasileirão win in the data is only %d goals", ms[0].GoalMargin())
	}
	high := s.HighestScoring(MatchFilter{CompetitionID: CompBrasileirao}, 3)
	if high[0].TotalGoals() < 9 {
		t.Errorf("highest scoring match has %d goals", high[0].TotalGoals())
	}
}

func TestCompareSeasons(t *testing.T) {
	s := testStore(t)
	cmp := s.CompareSeasons(CompBrasileirao, []int{2018, 2019, 1900})
	if len(cmp.Seasons) != 2 {
		t.Fatalf("compared %v, want only the two seasons that exist", cmp.Seasons)
	}
	if cmp.Champions[2019] != "Flamengo" || cmp.Champions[2018] != "Palmeiras" {
		t.Errorf("champions = %v", cmp.Champions)
	}
	if cmp.Aggregates[2019].Matches != 380 {
		t.Errorf("2019 aggregate covers %d matches", cmp.Aggregates[2019].Matches)
	}
	if cmp.TopScorers[2019].TeamName == "" {
		t.Error("no top scoring club for 2019")
	}
}

func TestDerbies(t *testing.T) {
	s := testStore(t)
	derbies := s.Derbies(MatchFilter{Season: 2019, CompetitionID: CompBrasileirao}, "", 0)
	if len(derbies) == 0 {
		t.Fatal("no derbies in the 2019 Brasileirão")
	}
	for _, d := range derbies {
		if _, ok := RivalryFor(d.Match.HomeTeamID, d.Match.AwayTeamID); !ok {
			t.Errorf("%s is not a derby", d.Match.Label())
		}
	}
	flaflu := s.Derbies(MatchFilter{}, "Fla-Flu", 0)
	for _, d := range flaflu {
		if d.Rivalry.Name != "Fla-Flu" {
			t.Errorf("rivalry filter leaked %q", d.Rivalry.Name)
		}
		if !d.Match.Involves("flamengo-rj") || !d.Match.Involves("fluminense-rj") {
			t.Errorf("%s is not a Fla-Flu", d.Match.Label())
		}
	}
}

func TestProfile(t *testing.T) {
	s := testStore(t)
	p := s.Profile("palmeiras-sp")
	if p == nil {
		t.Fatal("no profile for Palmeiras")
	}
	if p.Record.Matches == 0 {
		t.Error("empty record")
	}
	if p.Home.Matches+p.Away.Matches != p.Record.Matches {
		t.Error("home and away do not add up to the overall record")
	}
	comps := map[string]bool{}
	total := 0
	for _, c := range p.ByCompetition {
		comps[c.CompetitionID] = true
		total += c.Record.Matches
	}
	if total != p.Record.Matches {
		t.Error("per-competition records do not add up")
	}
	if !comps[CompBrasileirao] || !comps[CompLibertadores] || !comps[CompCopaDoBrasil] {
		t.Errorf("Palmeiras should appear in three competitions, got %v", comps)
	}
	titles := map[int]bool{}
	for _, title := range p.Titles {
		titles[title.Season] = true
	}
	for _, season := range []int{2016, 2018, 2022} {
		if !titles[season] {
			t.Errorf("Palmeiras' %d title is missing from the profile", season)
		}
	}
	if p.BiggestWin == nil || p.HeaviestLoss == nil {
		t.Error("profile should include the biggest win and heaviest defeat")
	}
	if len(p.Stadiums) == 0 {
		t.Error("profile should list home grounds")
	}
	if len(p.Rivals) == 0 {
		t.Error("Palmeiras has derbies")
	}
}

// Query performance: the specification asks for simple lookups under two
// seconds and aggregates under five.
func TestQueryPerformance(t *testing.T) {
	s := testStore(t)
	simple := []struct {
		name string
		run  func()
	}{
		{"team lookup", func() { s.Teams.Lookup("Flamengo") }},
		{"match search", func() { s.FindMatches(MatchFilter{TeamID: "flamengo-rj", Limit: 20}) }},
		{"head to head", func() { s.HeadToHead("flamengo-rj", "fluminense-rj", MatchFilter{}) }},
		{"player search", func() { s.FindPlayers(PlayerFilter{Nationality: "Brazil", Limit: 20}) }},
		{"player by name", func() { s.FindPlayers(PlayerFilter{Name: "Neymar", Limit: 5}) }},
		{"match details", func() { s.FindMatches(MatchFilter{TeamID: "flamengo-rj", OpponentID: "corinthians-sp", Limit: 1}) }},
	}
	for _, c := range simple {
		start := time.Now()
		c.run()
		if elapsed := time.Since(start); elapsed > 2*time.Second {
			t.Errorf("%s took %s, the budget is 2s", c.name, elapsed)
		}
	}
	aggregate := []struct {
		name string
		run  func()
	}{
		{"full standings", func() { s.Standings(CompBrasileirao, 2019, StandingsOptions{ThroughRound: 38}) }},
		{"all-time aggregate", func() { s.Aggregate(MatchFilter{}) }},
		{"records across everything", func() { s.TeamRecords(MatchFilter{}, "win_rate", 50, 20) }},
		{"club profile", func() { s.Profile("flamengo-rj") }},
		{"season comparison", func() { s.CompareSeasons(CompBrasileirao, s.Seasons(CompBrasileirao)) }},
	}
	for _, c := range aggregate {
		start := time.Now()
		c.run()
		if elapsed := time.Since(start); elapsed > 5*time.Second {
			t.Errorf("%s took %s, the budget is 5s", c.name, elapsed)
		}
	}
}

// The store is shared by every concurrent tool call, so a query must never
// reorder a slice that the store owns.
func TestProfileDoesNotMutateTheStore(t *testing.T) {
	s := testStore(t)
	for _, id := range []string{"gremio-rs", "cruzeiro-mg", "internacional-rs"} {
		squad := s.PlayersForTeam(id)
		if len(squad) < 3 {
			continue
		}
		before := append([]*Player(nil), squad...)
		p := s.Profile(id)
		after := s.PlayersForTeam(id)
		for i := range before {
			if before[i] != after[i] {
				t.Fatalf("Profile(%s) reordered the store's squad at index %d", id, i)
			}
		}
		if len(p.Squad) > 1 && p.Squad[0].Overall < p.Squad[1].Overall {
			t.Errorf("the profile squad is not sorted by rating")
		}
	}
}

// Results built by walking a map must not change between identical calls.
func TestQueriesAreDeterministic(t *testing.T) {
	s := testStore(t)
	checks := map[string]func() string{
		"profile competitions": func() string { return fmt.Sprint(s.Profile("flamengo-rj").ByCompetition) },
		"profile stadiums":     func() string { return fmt.Sprint(s.Profile("palmeiras-sp").Stadiums) },
		"head to head":         func() string { return fmt.Sprint(s.HeadToHead("flamengo-rj", "fluminense-rj", MatchFilter{}).ByComp) },
		"club summaries":       func() string { return fmt.Sprint(s.ClubSummaries(ClubFilter{Country: "BRA", MinPlayers: 1})) },
		"team records":         func() string { return fmt.Sprint(s.TeamRecords(MatchFilter{}, "wins", 10, 20)) },
		"standings": func() string {
			return fmt.Sprint(s.Standings(CompBrasileirao, 2019, StandingsOptions{Venue: VenueHome}).Rows)
		},
		"suggestions": func() string { return fmt.Sprint(s.SuggestPlayers("silva", 5)) },
	}
	for name, fn := range checks {
		first := fn()
		for i := 0; i < 50; i++ {
			if got := fn(); got != first {
				t.Errorf("%s is not deterministic:\n%s\n%s", name, first, got)
				break
			}
		}
	}
}

func TestCompareSeasonsIgnoresRepeats(t *testing.T) {
	s := testStore(t)
	cmp := s.CompareSeasons(CompBrasileirao, []int{2019, 2019, 2018, 2019})
	if len(cmp.Seasons) != 2 {
		t.Errorf("compared %v, want each season once", cmp.Seasons)
	}
}
