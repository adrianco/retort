package main

import (
	"bytes"
	"encoding/json"
	"path/filepath"
	"strings"
	"testing"
)

func testRepository(t *testing.T) *Repository {
	t.Helper()
	r, err := NewRepository(filepath.Join("data", "kaggle"))
	if err != nil {
		t.Fatalf("Given the supplied CSV files, loading them failed: %v", err)
	}
	return r
}

func TestMatchQueries_GivenLoadedData_WhenSearchingDerby_ThenMatchesHaveCoreFields(t *testing.T) {
	r := testRepository(t)
	matches := r.SearchMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense", Limit: 100})
	if len(matches) == 0 {
		t.Fatal("When searching Flamengo versus Fluminense, expected one or more matches")
	}
	for _, m := range matches {
		if m.Home == "" || m.Away == "" || m.Competition == "" || m.Date.IsZero() {
			t.Fatalf("Then every match should be complete, got %#v", m)
		}
	}
}

func TestTeamStatistics_GivenTeamNameVariants_WhenCalculating_ThenResultsMatch(t *testing.T) {
	r := testRepository(t)
	a := r.TeamStatistics("Palmeiras", "Brasileirão", 2023, false)
	b := r.TeamStatistics("Palmeiras-SP", "Brasileirao", 2023, false)
	if a.Matches == 0 {
		t.Fatal("expected Palmeiras matches in 2023")
	}
	if a.Matches != b.Matches || a.Wins != b.Wins || a.Draws != b.Draws || a.Losses != b.Losses || a.GoalsFor != b.GoalsFor || a.GoalsAgainst != b.GoalsAgainst {
		t.Fatalf("Then state and accent variants should produce equal results: %#v != %#v", a, b)
	}
	if a.Wins+a.Draws+a.Losses != a.Matches {
		t.Fatalf("Then W+D+L must equal matches: %#v", a)
	}
}

func TestPlayerSearch_GivenFIFAData_WhenFilteringBrazilianPlayers_ThenRatingOrderIsDescending(t *testing.T) {
	r := testRepository(t)
	players := r.SearchPlayers(PlayerFilter{Nationality: "Brazil", Limit: 20})
	if len(players) == 0 {
		t.Fatal("expected Brazilian FIFA players")
	}
	for i, p := range players {
		if !containsName(p.Nationality, "Brazil") {
			t.Fatalf("unexpected nationality: %#v", p)
		}
		if i > 0 && players[i-1].Overall < p.Overall {
			t.Fatal("players were not sorted by overall rating")
		}
	}
}

func TestStandings_GivenBrasileiraoSeason_WhenCalculated_ThenPointsAreInternallyConsistent(t *testing.T) {
	r := testRepository(t)
	standings := r.Standings("Brasileirão", 2019)
	if len(standings) < 20 {
		t.Fatalf("expected a full 2019 table, got %d teams", len(standings))
	}
	for _, s := range standings {
		if s.Played != s.Wins+s.Draws+s.Losses || s.Points != 3*s.Wins+s.Draws {
			t.Fatalf("invalid standing: %#v", s)
		}
	}
	if !containsName(standings[0].Team, "Flamengo") || standings[0].Points != 90 {
		t.Fatalf("expected the calculated 2019 champion to be Flamengo on 90 points, got %#v", standings[0])
	}
}

func TestRankings_GivenSeason_WhenRequestingAwayResults_ThenEveryEntryUsesAwayMatches(t *testing.T) {
	r := testRepository(t)
	ranked := r.RankTeams("Brasileirão", 2019, "away")
	if len(ranked) != 20 {
		t.Fatalf("expected 20 ranked teams, got %d", len(ranked))
	}
	for _, team := range ranked {
		if team.Matches != 19 {
			t.Fatalf("expected 19 away matches per team, got %#v", team)
		}
	}
}

func TestMCP_GivenInitializeAndToolCall_WhenServed_ThenItReturnsToolContent(t *testing.T) {
	r := testRepository(t)
	input := strings.NewReader("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\"}\n" +
		"{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"search_players\",\"arguments\":{\"name\":\"Neymar\",\"limit\":1}}}\n")
	var output bytes.Buffer
	if err := Serve(r, input, &output); err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(output.String()), "\n")
	if len(lines) != 2 {
		t.Fatalf("expected two JSON-RPC responses, got %q", output.String())
	}
	var response struct {
		Result struct {
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
	}
	if err := json.Unmarshal([]byte(lines[1]), &response); err != nil {
		t.Fatal(err)
	}
	if len(response.Result.Content) != 1 || !strings.Contains(response.Result.Content[0].Text, "Neymar") {
		t.Fatalf("unexpected tool response: %s", lines[1])
	}
}
