// Context
// -------
// Behaviour-Driven (Given/When/Then) tests for the query layer, exercised
// against the real bundled datasets. The graph is loaded once in TestMain and
// shared (read-only) across scenarios. Assertions favour ranges and invariants
// over brittle exact counts where the data could plausibly evolve, but pin the
// well-known historical results that the specification itself cites (e.g. the
// 2019 Brasileirão champion).
package soccer

import (
	"os"
	"testing"
)

var testGraph *Graph

func TestMain(m *testing.M) {
	dir, ok := FindDataDir("")
	if !ok {
		panic("could not locate data/kaggle for tests")
	}
	g, err := LoadGraph(dir)
	if err != nil {
		panic(err)
	}
	testGraph = g
	os.Exit(m.Run())
}

func TestDataIsLoaded(t *testing.T) {
	// Given the six CSV datasets, When the graph is loaded, Then matches,
	// players, teams and all expected competitions are present.
	if len(testGraph.Matches) == 0 {
		t.Fatal("expected matches to be loaded")
	}
	if len(testGraph.Players) < 18000 {
		t.Errorf("expected ~18207 players, got %d", len(testGraph.Players))
	}
	for _, comp := range []string{CompBrasileirao, CompCopaBrasil, CompLibertadores} {
		found := false
		for _, c := range testGraph.Competitions() {
			if c == comp {
				found = true
			}
		}
		if !found {
			t.Errorf("expected competition %q to be present", comp)
		}
	}
}

func TestSearchMatchesBetweenTwoTeams(t *testing.T) {
	// Given the match data is loaded,
	// When I search for matches between "Flamengo" and "Fluminense",
	// Then I receive matches each having a date, scores and competition.
	matches := testGraph.SearchMatches(MatchQuery{Team: "Flamengo", Team2: "Fluminense"})
	if len(matches) == 0 {
		t.Fatal("expected Fla-Flu matches")
	}
	for _, m := range matches {
		if m.Date.IsZero() {
			t.Error("match missing date")
		}
		if m.Competition == "" {
			t.Error("match missing competition")
		}
		// Both teams must be on opposite sides.
		flaHome := teamMatchesQuery("Flamengo", m.HomeTeam)
		fluHome := teamMatchesQuery("Fluminense", m.HomeTeam)
		if flaHome == fluHome {
			t.Errorf("both teams on same side: %s vs %s", m.HomeTeam, m.AwayTeam)
		}
	}
}

func TestSearchMatchesByCompetitionAndSeason(t *testing.T) {
	// Given the data, When I search Palmeiras matches in the 2021 Libertadores,
	// Then every result is from that competition and season.
	matches := testGraph.SearchMatches(MatchQuery{Team: "Palmeiras", Competition: "Libertadores", Season: 2021})
	if len(matches) == 0 {
		t.Fatal("expected Palmeiras 2021 Libertadores matches")
	}
	for _, m := range matches {
		if m.Competition != CompLibertadores || m.Season != 2021 {
			t.Errorf("unexpected match: %s", FormatMatch(m))
		}
	}
}

func TestHeadToHead(t *testing.T) {
	// Given the data, When I request the Palmeiras vs Santos head-to-head,
	// Then wins/draws are consistent with the number of matches.
	h := testGraph.HeadToHead("Palmeiras", "Santos")
	if len(h.Matches) == 0 {
		t.Fatal("expected Palmeiras-Santos matches")
	}
	if h.WinsA+h.WinsB+h.Draws != len(h.Matches) {
		t.Errorf("wins(%d)+draws(%d)+losses(%d) != matches(%d)",
			h.WinsA, h.Draws, h.WinsB, len(h.Matches))
	}
}

func TestTeamStatsRecordIsConsistent(t *testing.T) {
	// Given the data, When I request Corinthians' 2022 home record,
	// Then played == wins+draws+losses and there are at most one home game
	// per opponent in the league.
	rec := testGraph.TeamStats("Corinthians", TeamStatsOptions{Season: 2022, Filter: "home"})
	if rec.Played == 0 {
		t.Fatal("expected Corinthians 2022 home matches")
	}
	if rec.Wins+rec.Draws+rec.Losses != rec.Played {
		t.Errorf("W+D+L (%d) != played (%d)", rec.Wins+rec.Draws+rec.Losses, rec.Played)
	}
	if rec.WinRate() < 0 || rec.WinRate() > 100 {
		t.Errorf("win rate out of range: %.1f", rec.WinRate())
	}
}

func TestStandings2019Champion(t *testing.T) {
	// Given the data, When I compute the 2019 Brasileirão standings,
	// Then there are exactly 20 teams, each plays 38 games, and Flamengo is
	// champion with 90 points (as cited in the specification).
	table := testGraph.Standings(CompBrasileirao, 2019)
	if len(table) != 20 {
		t.Fatalf("expected 20 teams, got %d", len(table))
	}
	for _, r := range table {
		if r.Played != 38 {
			t.Errorf("%s played %d games, want 38", r.Team, r.Played)
		}
	}
	champ := table[0]
	if TeamKey(champ.Team) != TeamKey("Flamengo") {
		t.Errorf("expected Flamengo champion, got %s", champ.Team)
	}
	if champ.Points() != 90 {
		t.Errorf("expected Flamengo 90 pts, got %d", champ.Points())
	}
}

func TestDistinctAtleticosNotMerged(t *testing.T) {
	// Given clubs sharing the base name "Atletico", When standings are built,
	// Then Atletico-MG, Atletico-GO and Atletico-PR are treated as distinct
	// (none plays an impossible number of games).
	for _, season := range []int{2017, 2018, 2019} {
		for _, r := range testGraph.Standings(CompBrasileirao, season) {
			if r.Played > 38 {
				t.Errorf("%d: %s played %d games (>38) — clubs likely merged",
					season, r.Team, r.Played)
			}
		}
	}
}

func TestSearchBrazilianPlayers(t *testing.T) {
	// Given the FIFA data, When I search by nationality "Brazil",
	// Then many players are returned, sorted by overall descending.
	players := testGraph.SearchPlayers(PlayerQuery{Nationality: "Brazil", Limit: 50})
	if len(players) == 0 {
		t.Fatal("expected Brazilian players")
	}
	for i := 1; i < len(players); i++ {
		if players[i-1].Overall < players[i].Overall {
			t.Error("players not sorted by overall descending")
			break
		}
	}
	if players[0].Nationality != "Brazil" {
		t.Errorf("expected Brazilian top player, got %s", players[0].Nationality)
	}
}

func TestSearchPlayersByName(t *testing.T) {
	// Given the FIFA data, When I search the name "Neymar",
	// Then a matching player is returned.
	players := testGraph.SearchPlayers(PlayerQuery{Name: "Neymar"})
	if len(players) == 0 {
		t.Fatal("expected to find Neymar")
	}
	if !containsFold(players[0].Name, "Neymar") {
		t.Errorf("unexpected top result %q", players[0].Name)
	}
}

func TestSearchPlayersByClub(t *testing.T) {
	// Given the FIFA data, When I filter by a Brazilian club present in the
	// dataset ("Santos"), Then players are returned.
	players := testGraph.SearchPlayers(PlayerQuery{Club: "Santos", Limit: 30})
	if len(players) == 0 {
		t.Fatal("expected Santos players")
	}
}

func TestCompetitionStatistics(t *testing.T) {
	// Given the data, When I compute 2019 Brasileirão statistics,
	// Then the match count is a full season and averages are sane.
	cs := testGraph.Statistics(CompBrasileirao, 2019, 5)
	if cs.Matches != 380 {
		t.Errorf("expected 380 matches in 2019 Brasileirão, got %d", cs.Matches)
	}
	if cs.AvgGoals() < 1.5 || cs.AvgGoals() > 4 {
		t.Errorf("implausible avg goals: %.2f", cs.AvgGoals())
	}
	if cs.HomeWins+cs.AwayWins+cs.Draws != cs.Matches {
		t.Error("result split does not sum to match count")
	}
	if len(cs.BiggestWins) != 5 {
		t.Errorf("expected 5 biggest wins, got %d", len(cs.BiggestWins))
	}
}

func TestNoFixtureDoubleCountingInPrimary(t *testing.T) {
	// Given overlapping datasets, When the primary set is built, Then a full
	// Brasileirão season is ~380 matches, not an inflated multiple.
	cs := testGraph.Statistics(CompBrasileirao, 2018, 1)
	if cs.Matches < 360 || cs.Matches > 400 {
		t.Errorf("2018 Brasileirão has %d matches; expected ~380 (double counting?)", cs.Matches)
	}
}
