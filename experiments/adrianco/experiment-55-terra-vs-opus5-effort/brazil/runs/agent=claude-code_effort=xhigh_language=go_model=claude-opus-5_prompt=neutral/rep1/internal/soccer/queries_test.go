// queries_test.go verifies the query layer against facts that can be checked
// independently of this code: the real Brasileirão tables, the real Copa do
// Brasil and Libertadores winners, and the real relegations. If the loader, the
// name normaliser or the de-duplication were wrong, these numbers would move.
package soccer

import (
	"strings"
	"testing"
	"time"
)

func TestStandings2019MatchesHistory(t *testing.T) {
	g := testGraph(t)
	table, err := g.Standings(SerieA, 2019, VenueAll)
	if err != nil {
		t.Fatal(err)
	}
	if !table.Complete {
		t.Fatal("2019 Série A should be a complete season in the data")
	}
	if len(table.Rows) != 20 {
		t.Fatalf("table has %d rows, want 20", len(table.Rows))
	}
	top := table.Rows[0]
	if top.Team != "Flamengo" || top.Points != 90 || top.Wins != 28 || top.Draws != 6 || top.Losses != 4 {
		t.Errorf("champion row = %+v, want Flamengo 90 pts (28W 6D 4L)", top)
	}
	// Brazil breaks ties on wins before goal difference, which is what put
	// Santos above Palmeiras in 2019 despite the worse goal difference.
	if table.Rows[1].Team != "Santos" || table.Rows[2].Team != "Palmeiras" {
		t.Errorf("places 2 and 3 = %s, %s; want Santos, Palmeiras", table.Rows[1].Team, table.Rows[2].Team)
	}
	if table.Rows[1].Points != 74 || table.Rows[2].Points != 74 {
		t.Errorf("Santos and Palmeiras should both have 74 points, got %d and %d", table.Rows[1].Points, table.Rows[2].Points)
	}
	wantRelegated := []string{"Cruzeiro", "CSA", "Chapecoense", "Avaí"}
	for _, club := range wantRelegated {
		if !contains(table.Relegated, club) {
			t.Errorf("%s should have been relegated in 2019, got %v", club, table.Relegated)
		}
	}
	// Every club plays 38 matches in a 20 club double round-robin.
	for _, row := range table.Rows {
		if row.Played != 38 {
			t.Errorf("%s played %d matches, want 38", row.Team, row.Played)
		}
	}
}

func TestStandings2020Relegation(t *testing.T) {
	g := testGraph(t)
	table, err := g.Standings(SerieA, 2020, VenueAll)
	if err != nil {
		t.Fatal(err)
	}
	if table.Champion != "Flamengo" {
		t.Errorf("2020 champion = %q, want Flamengo", table.Champion)
	}
	for _, club := range []string{"Vasco da Gama", "Goiás", "Coritiba", "Botafogo-RJ"} {
		if !contains(table.Relegated, club) {
			t.Errorf("%s should have been relegated in 2020, got %v", club, table.Relegated)
		}
	}
}

func TestHomeOnlyStandings(t *testing.T) {
	g := testGraph(t)
	table, err := g.Standings(SerieA, 2022, VenueHome)
	if err != nil {
		t.Fatal(err)
	}
	for _, row := range table.Rows {
		if row.Played != 19 {
			t.Fatalf("%s played %d home matches, want 19", row.Team, row.Played)
		}
	}
	if table.Champion != "" {
		t.Error("a home-only table must not declare a champion")
	}
}

func TestLeagueChampionsMatchHistory(t *testing.T) {
	g := testGraph(t)
	want := map[int]string{
		2009: "Flamengo", 2010: "Fluminense", 2011: "Corinthians", 2012: "Fluminense",
		2013: "Cruzeiro", 2014: "Cruzeiro", 2015: "Corinthians", 2016: "Palmeiras",
		2017: "Corinthians", 2018: "Palmeiras", 2019: "Flamengo", 2020: "Flamengo",
		2021: "Atlético-MG", 2022: "Palmeiras",
	}
	res := g.Champions(SerieA, 2009, 2022)
	got := map[int]string{}
	for _, c := range res.Champions {
		if !c.Decided {
			t.Errorf("%d Série A should be decided in the data: %s", c.Season, c.Detail)
		}
		got[c.Season] = c.Champion
	}
	for season, club := range want {
		if got[season] != club {
			t.Errorf("%d Série A champion = %q, want %q", season, got[season], club)
		}
	}
}

func TestCupChampionsMatchHistory(t *testing.T) {
	g := testGraph(t)
	cases := []struct {
		comp     Competition
		season   int
		champion string
		// Finals settled on penalties cannot be resolved from scores alone.
		undecided bool
	}{
		{Libertadores, 2014, "San Lorenzo", false},
		{Libertadores, 2015, "River Plate", false},
		{Libertadores, 2016, "Atlético Nacional", false},
		{Libertadores, 2017, "Grêmio", false},
		{Libertadores, 2018, "River Plate", false},
		{Libertadores, 2019, "Flamengo", false},
		{Libertadores, 2020, "Palmeiras", false},
		{Libertadores, 2013, "", true}, // Atlético-MG won on penalties
		{CopaDoBrasil, 2012, "Palmeiras", false},
		{CopaDoBrasil, 2013, "Flamengo", false},
		{CopaDoBrasil, 2014, "Atlético-MG", false},
		{CopaDoBrasil, 2016, "Grêmio", false},
		{CopaDoBrasil, 2018, "Cruzeiro", false},
		{CopaDoBrasil, 2019, "Athletico-PR", false},
		{CopaDoBrasil, 2020, "Palmeiras", false},
		{CopaDoBrasil, 2017, "", true}, // Cruzeiro won on penalties
	}
	for _, c := range cases {
		entry := g.championOf(c.comp, c.season)
		if entry == nil {
			t.Errorf("no champion entry for %s %d", c.comp, c.season)
			continue
		}
		if c.undecided {
			if entry.Decided {
				t.Errorf("%s %d was decided on penalties and must not name a champion, got %q", c.comp, c.season, entry.Champion)
			}
			if !strings.Contains(entry.Detail, "penalties") {
				t.Errorf("%s %d detail should mention penalties, got %q", c.comp, c.season, entry.Detail)
			}
			continue
		}
		if entry.Champion != c.champion {
			t.Errorf("%s %d champion = %q, want %q (%s)", c.comp, c.season, entry.Champion, c.champion, entry.Detail)
		}
	}
}

func TestTitlesForClub(t *testing.T) {
	g := testGraph(t)
	team, _, err := g.ResolveTeam("Palmeiras")
	if err != nil {
		t.Fatal(err)
	}
	titles := g.TitlesFor(team)
	if len(titles) < 5 {
		t.Errorf("Palmeiras should have several titles in the data, got %v", titles)
	}
	var league, liberta int
	for _, ti := range titles {
		switch ti.Competition {
		case string(SerieA):
			league++
		case string(Libertadores):
			liberta++
		}
	}
	if league < 3 {
		t.Errorf("Palmeiras won Série A in 2016, 2018 and 2022; found %d league titles", league)
	}
	if liberta < 1 {
		t.Errorf("Palmeiras won the 2020 Libertadores; found %d", liberta)
	}
}

func TestHeadToHeadFlaFlu(t *testing.T) {
	g := testGraph(t)
	res, err := g.HeadToHead("Flamengo", "Fluminense", MatchFilter{}, 10)
	if err != nil {
		t.Fatal(err)
	}
	s := res.Summary
	if s.Matches == 0 {
		t.Fatal("no Fla-Flu matches found")
	}
	if s.TeamAWins+s.TeamBWins+s.Draws != s.Matches {
		t.Errorf("wins %d + %d + draws %d != %d matches", s.TeamAWins, s.TeamBWins, s.Draws, s.Matches)
	}
	if res.Rivalry != "Fla-Flu" {
		t.Errorf("rivalry = %q, want Fla-Flu", res.Rivalry)
	}
	if res.BiggestWinA == nil || res.BiggestWinB == nil {
		t.Error("expected a biggest win for both clubs")
	}
	// Every returned match must actually be between these two clubs.
	for _, m := range res.Matches {
		ids := map[string]bool{m.HomeTeamID: true, m.AwayTeamID: true}
		if !ids["flamengo-rj"] || !ids["fluminense-rj"] {
			t.Errorf("match %s is not a Fla-Flu", m.Line)
		}
	}
	// Reversing the arguments must mirror the record.
	rev, err := g.HeadToHead("Fluminense", "Flamengo", MatchFilter{}, 0)
	if err != nil {
		t.Fatal(err)
	}
	if rev.Summary.TeamAWins != s.TeamBWins || rev.Summary.TeamBWins != s.TeamAWins || rev.Summary.Draws != s.Draws {
		t.Errorf("reversed head-to-head is inconsistent: %+v vs %+v", rev.Summary, s)
	}
}

func TestTeamStatsHomeRecord(t *testing.T) {
	g := testGraph(t)
	res, err := g.TeamStats("Corinthians", MatchFilter{Competition: SerieA, Season: 2022}, VenueHome)
	if err != nil {
		t.Fatal(err)
	}
	if res.Overall.Played != 19 {
		t.Errorf("Corinthians played %d home league matches in 2022, want 19", res.Overall.Played)
	}
	if res.Overall.Wins+res.Overall.Draws+res.Overall.Losses != res.Overall.Played {
		t.Error("wins, draws and losses do not add up")
	}
	if res.Overall.Points != res.Overall.Wins*3+res.Overall.Draws {
		t.Error("points are not three for a win, one for a draw")
	}
	if res.Away.Played != 0 {
		t.Error("a home-only query must not include away matches")
	}
	// The same query without a venue filter must cover twice as many matches.
	all, err := g.TeamStats("Corinthians", MatchFilter{Competition: SerieA, Season: 2022}, VenueAll)
	if err != nil {
		t.Fatal(err)
	}
	if all.Overall.Played != 38 {
		t.Errorf("Corinthians played %d league matches in 2022, want 38", all.Overall.Played)
	}
	if all.Home.Played != 19 || all.Away.Played != 19 {
		t.Errorf("home/away split = %d/%d, want 19/19", all.Home.Played, all.Away.Played)
	}
}

func TestTeamStatsAgreeWithStandings(t *testing.T) {
	g := testGraph(t)
	table, err := g.Standings(SerieA, 2018, VenueAll)
	if err != nil {
		t.Fatal(err)
	}
	for _, row := range table.Rows[:5] {
		stats, err := g.TeamStats(row.TeamID, MatchFilter{Competition: SerieA, Season: 2018}, VenueAll)
		if err != nil {
			t.Fatal(err)
		}
		if stats.Overall.Points != row.Points || stats.Overall.GoalsFor != row.GoalsFor {
			t.Errorf("%s: team_stats says %d pts / %d goals, standings say %d / %d",
				row.Team, stats.Overall.Points, stats.Overall.GoalsFor, row.Points, row.GoalsFor)
		}
	}
}

func TestSearchMatchesFilters(t *testing.T) {
	g := testGraph(t)
	// By club and season.
	res, err := g.SearchMatches(MatchFilter{Team: "Palmeiras", Season: 2023}, 500)
	if err != nil {
		t.Fatal(err)
	}
	if res.TotalMatches == 0 {
		t.Fatal("Palmeiras played no matches in 2023?")
	}
	for _, m := range res.Matches {
		if m.Season != 2023 {
			t.Errorf("match %s is not from 2023", m.Line)
		}
		if m.HomeTeamID != "palmeiras-sp" && m.AwayTeamID != "palmeiras-sp" {
			t.Errorf("match %s does not involve Palmeiras", m.Line)
		}
		if m.Date == "" || m.Competition == "" {
			t.Errorf("match %s is missing a date or competition", m.Line)
		}
	}

	// By date range.
	from := time.Date(2023, 9, 1, 0, 0, 0, 0, time.UTC)
	to := time.Date(2023, 9, 30, 0, 0, 0, 0, time.UTC)
	res, err = g.SearchMatches(MatchFilter{Competition: SerieA, DateFrom: from, DateTo: to}, 500)
	if err != nil {
		t.Fatal(err)
	}
	if res.TotalMatches == 0 {
		t.Fatal("no Série A matches in September 2023")
	}
	for _, m := range res.Matches {
		if m.Date < "2023-09-01" || m.Date > "2023-09-30" {
			t.Errorf("match %s falls outside the requested date range", m.Line)
		}
	}

	// By stage: the Copa do Brasil finals.
	res, err = g.SearchMatches(MatchFilter{Competition: CopaDoBrasil, Stage: "final"}, 100)
	if err != nil {
		t.Fatal(err)
	}
	if res.TotalMatches < 15 {
		t.Errorf("found %d Copa do Brasil final legs, expected around two per season", res.TotalMatches)
	}
	for _, m := range res.Matches {
		if !strings.Contains(strings.ToLower(m.Stage), "final") {
			t.Errorf("match %s is not a final", m.Line)
		}
	}

	// An unknown club must produce a helpful error, not an empty list.
	if _, err := g.SearchMatches(MatchFilter{Team: "Real Madrid"}, 10); err == nil {
		t.Error("expected an error for a club that is not in the data")
	}
}

func TestSearchMatchesDeduplication(t *testing.T) {
	g := testGraph(t)
	deduped, err := g.SearchMatches(MatchFilter{Team: "Flamengo", Competition: SerieA, Season: 2018}, 500)
	if err != nil {
		t.Fatal(err)
	}
	if deduped.TotalMatches != 38 {
		t.Errorf("Flamengo played %d Série A matches in 2018, want 38", deduped.TotalMatches)
	}
	raw, err := g.SearchMatches(MatchFilter{Team: "Flamengo", Competition: SerieA, Season: 2018, IncludeDuplicates: true}, 500)
	if err != nil {
		t.Fatal(err)
	}
	if raw.TotalMatches <= deduped.TotalMatches {
		t.Errorf("2018 is present in three files, so the raw view (%d) should exceed the de-duplicated one (%d)",
			raw.TotalMatches, deduped.TotalMatches)
	}
}

func TestPlayerQueries(t *testing.T) {
	g := testGraph(t)
	brazilians, err := g.SearchPlayers(PlayerFilter{Nationality: "Brazil"}, 10, true)
	if err != nil {
		t.Fatal(err)
	}
	if brazilians.Total != 827 {
		t.Errorf("found %d Brazilian players, want 827", brazilians.Total)
	}
	if len(brazilians.Players) != 10 {
		t.Errorf("returned %d players, want the requested 10", len(brazilians.Players))
	}
	if brazilians.Players[0].Name != "Neymar Jr" {
		t.Errorf("highest rated Brazilian is %q, want Neymar Jr", brazilians.Players[0].Name)
	}
	for i := 1; i < len(brazilians.Players); i++ {
		if brazilians.Players[i].Overall > brazilians.Players[i-1].Overall {
			t.Error("players are not sorted by overall rating")
		}
		if brazilians.Players[i].Nationality != "Brazil" {
			t.Errorf("player %s is not Brazilian", brazilians.Players[i].Name)
		}
	}
	if len(brazilians.ByClub) == 0 {
		t.Error("group_by_club produced no breakdown")
	}

	// Club filter, resolved through the match graph.
	club, err := g.SearchPlayers(PlayerFilter{Club: "Grêmio"}, 50, false)
	if err != nil {
		t.Fatal(err)
	}
	if club.Total != 20 {
		t.Errorf("Grêmio has %d players in the FIFA data, want 20", club.Total)
	}

	// Position group filter.
	forwards, err := g.SearchPlayers(PlayerFilter{Club: "Santos", Position: "forward"}, 50, false)
	if err != nil {
		t.Fatal(err)
	}
	if forwards.Total == 0 {
		t.Error("Santos has no forwards?")
	}
	for _, p := range forwards.Players {
		if p.PositionGroup != "forward" {
			t.Errorf("%s plays %s, which is not a forward position", p.Name, p.Position)
		}
	}

	// A club FIFA 19 does not license must explain itself rather than return an
	// unexplained empty list.
	missing, err := g.SearchPlayers(PlayerFilter{Club: "Flamengo"}, 10, false)
	if err != nil {
		t.Fatal(err)
	}
	if missing.Total == 0 && !strings.Contains(missing.Note, "FIFA 19") {
		t.Errorf("an empty club result should explain the gap, got %q", missing.Note)
	}
}

func TestPlayerProfile(t *testing.T) {
	g := testGraph(t)
	res, err := g.PlayerProfile("Neymar")
	if err != nil {
		t.Fatal(err)
	}
	if res.Player.Overall < 90 {
		t.Errorf("Neymar's rating is %d, expected above 90", res.Player.Overall)
	}
	if len(res.TopSkills) == 0 {
		t.Error("expected the profile to list top attributes")
	}
	if _, err := g.PlayerProfile("Zinedine Zidane"); err == nil {
		t.Error("expected an error for a player who is not in the FIFA 19 export")
	}
}

func TestAggregateStats(t *testing.T) {
	g := testGraph(t)
	res, err := g.Aggregate(MatchFilter{Competition: SerieA}, 5)
	if err != nil {
		t.Fatal(err)
	}
	if res.Matches < 8000 {
		t.Errorf("only %d Série A matches, expected more than 8000", res.Matches)
	}
	if res.GoalsPerMatch < 2.0 || res.GoalsPerMatch > 3.2 {
		t.Errorf("goals per match = %.2f, which is outside any plausible range", res.GoalsPerMatch)
	}
	if res.HomeWins+res.Draws+res.AwayWins != res.Matches {
		t.Error("results do not add up to the match count")
	}
	if res.HomeWinPercent <= res.AwayWinPercent {
		t.Error("expected a home advantage in Brazilian league football")
	}
	if len(res.BiggestWins) != 5 {
		t.Errorf("asked for the top 5 biggest wins, got %d", len(res.BiggestWins))
	}
	for i := 1; i < len(res.BiggestWins); i++ {
		a := res.BiggestWins[i-1]
		b := res.BiggestWins[i]
		if abs(a.HomeGoals-a.AwayGoals) < abs(b.HomeGoals-b.AwayGoals) {
			t.Error("biggest wins are not ordered by margin")
		}
	}
	if len(res.BySeason) == 0 {
		t.Error("expected a per-season breakdown")
	}
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}

func TestLeaderboards(t *testing.T) {
	g := testGraph(t)
	for _, metric := range AllMetrics {
		res, err := g.Leaderboard(metric, MatchFilter{Competition: SerieA, Season: 2019}, VenueAll, 10, 5)
		if err != nil {
			t.Fatalf("%s: %v", metric, err)
		}
		if len(res.Rows) != 5 {
			t.Errorf("%s returned %d rows, want 5", metric, len(res.Rows))
		}
		for i, row := range res.Rows {
			if row.Position != i+1 {
				t.Errorf("%s row %d has position %d", metric, i, row.Position)
			}
			if row.Detail == "" {
				t.Errorf("%s row %d has no explanation", metric, i)
			}
		}
	}
	// The 2019 top scorer and champion were the same club.
	goals, err := g.Leaderboard(MetricMostGoals, MatchFilter{Competition: SerieA, Season: 2019}, VenueAll, 10, 1)
	if err != nil {
		t.Fatal(err)
	}
	if goals.Rows[0].Team != "Flamengo" {
		t.Errorf("top scoring club of 2019 = %q, want Flamengo", goals.Rows[0].Team)
	}
	// Away-only ranking must halve the match counts.
	away, err := g.Leaderboard(MetricMostWins, MatchFilter{Competition: SerieA, Season: 2019}, VenueAway, 10, 3)
	if err != nil {
		t.Fatal(err)
	}
	for _, row := range away.Rows {
		if row.Record.Played != 19 {
			t.Errorf("%s played %d away matches in 2019, want 19", row.Team, row.Record.Played)
		}
	}
}

func TestCompetitionSummaryAndComparison(t *testing.T) {
	g := testGraph(t)
	res, err := g.CompetitionSummary(SerieA, []int{2018, 2019})
	if err != nil {
		t.Fatal(err)
	}
	if len(res.Seasons) != 2 {
		t.Fatalf("asked for two seasons, got %d", len(res.Seasons))
	}
	for _, s := range res.Seasons {
		if s.Teams != 20 || s.Matches != 380 {
			t.Errorf("%d season has %d teams and %d matches, want 20 and 380", s.Season, s.Teams, s.Matches)
		}
		if s.Champion == "" {
			t.Errorf("%d season has no champion", s.Season)
		}
	}
	if len(res.Comparison) == 0 {
		t.Error("two seasons should produce a comparison")
	}
	// Individual scorers are not in the data and the tool must say so.
	joined := strings.Join(res.Notes, " ")
	if !strings.Contains(joined, "goalscorer") {
		t.Errorf("expected a note about missing goalscorer data, got %v", res.Notes)
	}
}

func TestBracket(t *testing.T) {
	g := testGraph(t)
	res, err := g.Bracket(Libertadores, 2018)
	if err != nil {
		t.Fatal(err)
	}
	if res.Champion != "River Plate" {
		t.Errorf("2018 Libertadores champion = %q, want River Plate", res.Champion)
	}
	var final *Stage
	for i := range res.Stages {
		if res.Stages[i].Name == "final" {
			final = &res.Stages[i]
		}
	}
	if final == nil {
		t.Fatal("no final stage in the 2018 bracket")
	}
	if len(final.Ties) != 1 {
		t.Fatalf("the final should be a single tie, got %d", len(final.Ties))
	}
	tie := final.Ties[0]
	if tie.Winner != "River Plate" || tie.AggregateA+tie.AggregateB != 8 {
		t.Errorf("2018 final = %s %d-%d %s, want River Plate winning 5-3 on aggregate",
			tie.TeamA, tie.AggregateA, tie.AggregateB, tie.TeamB)
	}
	// A league has no bracket.
	if _, err := g.Bracket(SerieA, 2019); err == nil {
		t.Error("expected an error when asking for a league bracket")
	}
}

func TestDerbies(t *testing.T) {
	g := testGraph(t)
	res, err := g.Derbies(MatchFilter{Season: 2023}, false)
	if err != nil {
		t.Fatal(err)
	}
	found := 0
	for _, d := range res.Derbies {
		if d.Matches > 0 {
			found++
		}
	}
	if found < 5 {
		t.Errorf("only %d derbies were played in 2023 according to the data", found)
	}
	if res.Derbies[0].Name == "" || res.Derbies[0].Record == "" {
		t.Error("the top derby has no name or record")
	}
}

func TestTeamProfile(t *testing.T) {
	g := testGraph(t)
	res, err := g.TeamProfile("Palmeiras", 5)
	if err != nil {
		t.Fatal(err)
	}
	if res.TotalMatches < 500 {
		t.Errorf("Palmeiras has %d matches, expected many more", res.TotalMatches)
	}
	if len(res.Competitions) < 3 {
		t.Errorf("Palmeiras should appear in several competitions, got %v", res.Competitions)
	}
	if len(res.Titles) == 0 {
		t.Error("Palmeiras should have titles computed from the data")
	}
	if len(res.Rivalries) == 0 {
		t.Error("Palmeiras should have rivalries")
	}
	if res.FirstMatch == nil || res.LastMatch == nil {
		t.Error("expected a first and last match")
	}
	// A club FIFA does not license explains the empty squad.
	if res.SquadSize == 0 && res.SquadNote == "" {
		t.Error("an empty squad needs an explanation")
	}
}

func TestListTeams(t *testing.T) {
	g := testGraph(t)
	all := g.ListTeams("", 0)
	if len(all) < 300 {
		t.Errorf("only %d clubs in the directory", len(all))
	}
	atleticos := g.ListTeams("atletico", 0)
	if len(atleticos) < 3 {
		t.Errorf("expected several clubs called Atlético, got %d", len(atleticos))
	}
	byNickname := g.ListTeams("timao", 0)
	if len(byNickname) != 1 || byNickname[0].ID != "corinthians-sp" {
		t.Errorf("searching for a nickname returned %v", byNickname)
	}
}

// TestQueryPerformance covers the specification's response time requirements:
// simple lookups under two seconds, aggregates under five.
func TestQueryPerformance(t *testing.T) {
	g := testGraph(t)
	simple := []struct {
		name string
		run  func() error
	}{
		{"match search", func() error {
			_, err := g.SearchMatches(MatchFilter{Team: "Flamengo", Opponent: "Corinthians"}, 20)
			return err
		}},
		{"team stats", func() error {
			_, err := g.TeamStats("Palmeiras", MatchFilter{Season: 2022}, VenueAll)
			return err
		}},
		{"player search", func() error {
			_, err := g.SearchPlayers(PlayerFilter{Nationality: "Brazil"}, 20, false)
			return err
		}},
		{"standings", func() error {
			_, err := g.Standings(SerieA, 2019, VenueAll)
			return err
		}},
	}
	for _, c := range simple {
		start := time.Now()
		if err := c.run(); err != nil {
			t.Fatalf("%s: %v", c.name, err)
		}
		if elapsed := time.Since(start); elapsed > 2*time.Second {
			t.Errorf("%s took %v, the budget is 2s", c.name, elapsed)
		}
	}
	aggregates := []struct {
		name string
		run  func() error
	}{
		{"whole dataset statistics", func() error {
			_, err := g.Aggregate(MatchFilter{}, 10)
			return err
		}},
		{"all-time rankings", func() error {
			_, err := g.Leaderboard(MetricMostPoints, MatchFilter{}, VenueAll, 50, 20)
			return err
		}},
		{"all derbies", func() error {
			_, err := g.Derbies(MatchFilter{}, true)
			return err
		}},
		{"champions of every competition", func() error {
			g.Champions("", 0, 0)
			return nil
		}},
	}
	for _, c := range aggregates {
		start := time.Now()
		if err := c.run(); err != nil {
			t.Fatalf("%s: %v", c.name, err)
		}
		if elapsed := time.Since(start); elapsed > 5*time.Second {
			t.Errorf("%s took %v, the budget is 5s", c.name, elapsed)
		}
	}
}

// TestFormattersProduceReadableText checks the human-facing half of every tool
// result, which is what the model quotes back to the user.
func TestFormattersProduceReadableText(t *testing.T) {
	g := testGraph(t)
	matches, err := g.SearchMatches(MatchFilter{Team: "Santos", Season: 2019}, 5)
	if err != nil {
		t.Fatal(err)
	}
	h2h, err := g.HeadToHead("Palmeiras", "Santos", MatchFilter{}, 3)
	if err != nil {
		t.Fatal(err)
	}
	stats, err := g.TeamStats("Santos", MatchFilter{Season: 2019}, VenueAll)
	if err != nil {
		t.Fatal(err)
	}
	profile, err := g.TeamProfile("Santos", 3)
	if err != nil {
		t.Fatal(err)
	}
	table, err := g.Standings(SerieA, 2019, VenueAll)
	if err != nil {
		t.Fatal(err)
	}
	bracket, err := g.Bracket(CopaDoBrasil, 2019)
	if err != nil {
		t.Fatal(err)
	}
	summary, err := g.CompetitionSummary(SerieA, []int{2019})
	if err != nil {
		t.Fatal(err)
	}
	players, err := g.SearchPlayers(PlayerFilter{Nationality: "Brazil"}, 3, true)
	if err != nil {
		t.Fatal(err)
	}
	player, err := g.PlayerProfile("Neymar")
	if err != nil {
		t.Fatal(err)
	}
	ranking, err := g.Leaderboard(MetricMostWins, MatchFilter{Competition: SerieA, Season: 2019}, VenueAll, 10, 3)
	if err != nil {
		t.Fatal(err)
	}
	agg, err := g.Aggregate(MatchFilter{Competition: SerieA, Season: 2019}, 3)
	if err != nil {
		t.Fatal(err)
	}
	derbies, err := g.Derbies(MatchFilter{Season: 2019}, false)
	if err != nil {
		t.Fatal(err)
	}

	renders := map[string]string{
		"match search":        FormatMatchSearch(matches),
		"head to head":        FormatHeadToHead(h2h),
		"team stats":          FormatTeamStats(stats),
		"team profile":        FormatTeamProfile(profile),
		"standings":           FormatStandings(table),
		"champions":           FormatChampions(g.Champions(SerieA, 2019, 2019)),
		"bracket":             FormatBracket(bracket),
		"competition summary": FormatCompetitionSummary(summary),
		"player search":       FormatPlayerSearch(players),
		"player profile":      FormatPlayerProfile(player),
		"leaderboard":         FormatLeaderboard(ranking),
		"aggregate":           FormatAggregate(agg),
		"derbies":             FormatDerbies(derbies),
		"team list":           FormatTeamList(g.ListTeams("santos", 5), 5),
		"dataset info":        FormatDatasetInfo(g.DatasetInfo()),
	}
	for name, text := range renders {
		if len(text) < 40 {
			t.Errorf("%s rendered only %d characters: %q", name, len(text), text)
		}
		if strings.Contains(text, "%!") {
			t.Errorf("%s has a formatting error: %s", name, text)
		}
	}
	if !strings.Contains(renders["standings"], "Flamengo") {
		t.Error("the 2019 table should mention the champion")
	}
	if !strings.Contains(renders["head to head"], "wins") {
		t.Error("the head-to-head rendering should report wins")
	}
}
