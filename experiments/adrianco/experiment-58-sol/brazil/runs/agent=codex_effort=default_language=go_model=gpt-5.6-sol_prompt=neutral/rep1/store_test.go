package main

import (
	"testing"
	"time"
)

func testStore() *Store {
	d := func(v string) time.Time { t, _ := parseDate(v); return t }
	hc, ac := 8, 2
	return &Store{
		matches: []Match{
			{Date: d("2023-09-03"), HomeTeam: "Flamengo-RJ", AwayTeam: "Fluminense-RJ", HomeGoals: 2, AwayGoals: 1, Competition: "Brasileirão Serie A", Season: 2023, Round: "22", Source: "a.csv"},
			// Same event from another feed: analytics must count it once.
			{Date: d("2023-09-03"), HomeTeam: "Flamengo", AwayTeam: "Fluminense", HomeGoals: 2, AwayGoals: 1, Competition: "Serie A", Season: 2023, Source: "b.csv", HomeCorners: &hc, AwayCorners: &ac},
			{Date: d("2023-05-28"), HomeTeam: "Fluminense", AwayTeam: "Flamengo", HomeGoals: 1, AwayGoals: 0, Competition: "Brasileirão Serie A", Season: 2023, Source: "a.csv"},
			{Date: d("2023-04-01"), HomeTeam: "Clube de Regatas do Flamengo", AwayTeam: "São Paulo FC", HomeGoals: 0, AwayGoals: 0, Competition: "Copa do Brasil", Season: 2023, Stage: "Final", Source: "cup.csv"},
			{Date: d("2022-07-01"), HomeTeam: "Sport Club Corinthians Paulista", AwayTeam: "Palmeiras-SP", HomeGoals: 3, AwayGoals: 0, Competition: "Brasileirão Serie A", Season: 2022, Source: "a.csv"},
		},
		players: []Player{
			{ID: 1, Name: "Gabriel Barbosa", Nationality: "Brazil", Club: "Flamengo", Position: "ST", Overall: 83},
			{ID: 2, Name: "Example Keeper", Nationality: "Brazil", Club: "Flamengo-RJ", Position: "GK", Overall: 75},
			{ID: 3, Name: "Other Player", Nationality: "Argentina", Club: "River Plate", Position: "CM", Overall: 84},
		},
		teamNames: map[string]string{"flamengo": "Flamengo", "fluminense": "Fluminense", "sao paulo": "São Paulo", "corinthians": "Corinthians", "palmeiras": "Palmeiras"},
	}
}

func TestNormalizeTeamVariations(t *testing.T) {
	for _, tc := range []struct{ got, want string }{
		{normalizeTeam("Flamengo-RJ"), "flamengo"},
		{normalizeTeam("Flamengo - RJ"), "flamengo"},
		{normalizeTeam("São Paulo FC"), "sao paulo"},
		{normalizeTeam("Sport Club Corinthians Paulista"), "corinthians"},
		{normalizeTeam("Grêmio"), "gremio"},
	} {
		if tc.got != tc.want {
			t.Errorf("got %q, want %q", tc.got, tc.want)
		}
	}
}

func TestSearchMatchesDeduplicatesFeedsAndFilters(t *testing.T) {
	s := testStore()
	got := s.Matches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense", Season: 2023, Limit: 20})
	if len(got) != 2 {
		t.Fatalf("got %d matches, want 2", len(got))
	}
	if !got[0].Date.After(got[1].Date) {
		t.Fatal("matches are not newest first")
	}
	raw := s.Matches(MatchFilter{Source: "b.csv", Limit: 20})
	if len(raw) != 1 || raw[0].HomeCorners == nil {
		t.Fatalf("source-specific query lost raw extended data: %+v", raw)
	}
	finals := s.Matches(MatchFilter{Competition: "Brazilian Cup", Stage: "final", Limit: 20})
	if len(finals) != 1 || normalizeTeam(finals[0].AwayTeam) != "sao paulo" {
		t.Fatalf("final filter: %+v", finals)
	}
}

func TestTeamStatisticsAndHeadToHead(t *testing.T) {
	s := testStore()
	r := s.TeamStatistics("Flamengo", "Brasileirão", "", 2023)
	if r.Matches != 2 || r.Wins != 1 || r.Losses != 1 || r.GoalsFor != 2 || r.GoalsAgainst != 2 || r.Points != 3 {
		t.Fatalf("unexpected record: %+v", r)
	}
	home := s.TeamStatistics("Flamengo", "", "home", 2023)
	if home.Matches != 2 || home.Wins != 1 || home.Draws != 1 {
		t.Fatalf("unexpected home record: %+v", home)
	}
	h2h := s.HeadToHead("Flamengo", "Fluminense", "", 2023)
	if h2h["matches"] != 2 || h2h["team_1_wins"] != 1 || h2h["team_2_wins"] != 1 {
		t.Fatalf("unexpected h2h: %+v", h2h)
	}
}

func TestPlayersStandingsAndCrossFileProfile(t *testing.T) {
	s := testStore()
	players := s.Players(PlayerFilter{Nationality: "Brasil", Club: "Clube de Regatas do Flamengo", Position: "ST", MinOverall: 80})
	if len(players) != 1 || players[0].Name != "Gabriel Barbosa" {
		t.Fatalf("unexpected players: %+v", players)
	}
	standings := s.Standings("Brasileirão", 2023, 0)
	if len(standings) != 2 || standings[0].Points != 3 || standings[0].Position != 1 {
		t.Fatalf("unexpected standings: %+v", standings)
	}
	profile := s.TeamProfile("Flamengo-RJ", 2023)
	if len(profile["competitions"].([]string)) != 2 || len(profile["players_in_fifa_dataset"].([]Player)) != 2 {
		t.Fatalf("unexpected profile: %+v", profile)
	}
}

func TestCompetitionStatisticsAndBiggestWins(t *testing.T) {
	s := testStore()
	stats := s.CompetitionStatistics("Brasileirão", 2023)
	if stats["matches"] != 2 || stats["goals"] != 4 || stats["goals_per_match"] != 2.0 {
		t.Fatalf("unexpected stats: %+v", stats)
	}
	wins := s.BiggestWins("", "Brasileirão", 0, 1)
	if len(wins) != 1 || wins[0].HomeGoals-wins[0].AwayGoals != 3 {
		t.Fatalf("unexpected biggest win: %+v", wins)
	}
}

func TestDerbies(t *testing.T) {
	got := testStore().Derbies(2023, "Brasileirão", 20)
	if len(got) != 2 || got[0].Derby != "Fla-Flu" {
		t.Fatalf("unexpected derbies: %+v", got)
	}
}
