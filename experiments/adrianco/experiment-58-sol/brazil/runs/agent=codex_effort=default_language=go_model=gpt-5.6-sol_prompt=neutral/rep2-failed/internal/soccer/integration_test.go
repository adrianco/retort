package soccer

import (
	"path/filepath"
	"testing"
	"time"
)

func loadTestCatalog(t *testing.T) *Catalog {
	t.Helper()
	start := time.Now()
	c, err := LoadDir(filepath.Join("..", "..", "data", "kaggle"))
	if err != nil {
		t.Fatalf("LoadDir: %v", err)
	}
	if elapsed := time.Since(start); elapsed > 2*time.Second {
		t.Fatalf("loading took %v, expected under 2 seconds", elapsed)
	}
	return c
}

func TestLoadAllRequiredSources(t *testing.T) {
	c := loadTestCatalog(t)
	if len(c.Sources) != 6 {
		t.Fatalf("loaded %d sources, want 6", len(c.Sources))
	}
	for _, name := range []string{sourceBrasileirao, sourceCup, sourceLibertadores, sourceExtended, sourceHistorical, sourceFIFA} {
		if c.Sources[name].Records == 0 {
			t.Errorf("source %s has no records", name)
		}
	}
	if len(c.Matches) < 20_000 || len(c.Players) < 18_000 {
		t.Fatalf("unexpected coverage: %d matches, %d players", len(c.Matches), len(c.Players))
	}
}

func TestMatchTeamAndHeadToHeadQueries(t *testing.T) {
	c := loadTestCatalog(t)
	result, err := c.SearchMatches(MatchQuery{Team: "Flamengo", Opponent: "Fluminense", Limit: 500})
	if err != nil {
		t.Fatal(err)
	}
	if result.Total == 0 {
		t.Fatal("expected Flamengo vs Fluminense matches")
	}
	for _, match := range result.Matches {
		if !((match.homeKey == "flamengo" && match.awayKey == "fluminense") || (match.homeKey == "fluminense" && match.awayKey == "flamengo")) {
			t.Fatalf("unexpected match: %+v", match)
		}
	}
	h2h, err := c.HeadToHead("Flamengo-RJ", "Fluminense", 0, "", 5)
	if err != nil {
		t.Fatal(err)
	}
	if h2h.TeamAWins+h2h.TeamBWins+h2h.Draws != h2h.Matches || len(h2h.Recent) != 5 {
		t.Fatalf("inconsistent head-to-head: %+v", h2h)
	}
}

func TestTeamStatisticsAndStandings(t *testing.T) {
	c := loadTestCatalog(t)
	record, err := c.TeamStatistics("Corinthians", 2022, "Brasileirão", "home")
	if err != nil {
		t.Fatal(err)
	}
	if record.Matches != 19 || record.Wins+record.Draws+record.Losses != 19 {
		t.Fatalf("unexpected Corinthians home record: %+v", record)
	}
	standings, err := c.Standings("Brasileirão Série A", 2019)
	if err != nil {
		t.Fatal(err)
	}
	if NormalizeTeam(standings.Champion) != "flamengo" {
		t.Fatalf("champion = %q, want Flamengo", standings.Champion)
	}
	if standings.Standings[0].Points != 90 {
		t.Fatalf("Flamengo points = %d, want 90", standings.Standings[0].Points)
	}
}

func TestPlayerAndCrossFileQueries(t *testing.T) {
	c := loadTestCatalog(t)
	players := c.SearchPlayers(PlayerQuery{Nationality: "Brazil", MinOverall: 85, Limit: 10})
	if players.Total == 0 || players.Players[0].Nationality != "Brazil" {
		t.Fatalf("unexpected player search: %+v", players)
	}
	neymar := c.SearchPlayers(PlayerQuery{Name: "Neymar", Limit: 1})
	if neymar.Returned != 1 || neymar.Players[0].Overall != 92 {
		t.Fatalf("unexpected Neymar result: %+v", neymar)
	}
	overview, err := c.ClubOverview("Grêmio", 2018, "Brasileirão")
	if err != nil {
		t.Fatal(err)
	}
	if overview.Record.Matches == 0 || overview.PlayerCount == 0 {
		t.Fatalf("cross-file overview missing data: %+v", overview)
	}
}

func TestAggregatePerformanceAndValidation(t *testing.T) {
	c := loadTestCatalog(t)
	start := time.Now()
	agg, err := c.Aggregate("Brasileirão", 2023, 5)
	if err != nil {
		t.Fatal(err)
	}
	if time.Since(start) > 5*time.Second {
		t.Fatal("aggregate query exceeded five seconds")
	}
	if agg.Matches == 0 || agg.GoalsPerMatch <= 0 || len(agg.BiggestVictories) != 5 {
		t.Fatalf("unexpected aggregate: %+v", agg)
	}
	if _, err := c.SearchMatches(MatchQuery{From: "2023-02-01", To: "2023-01-01"}); err == nil {
		t.Fatal("expected invalid date range error")
	}
}
