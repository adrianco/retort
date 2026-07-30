package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestNormalizesBrazilianTeamNames(t *testing.T) {
	if !teamMatches("São Paulo FC", "Sao Paulo-SP") {
		t.Fatal("expected accent, suffix, and FC variation to match")
	}
	if !teamMatches("Flamengo", "Flamengo-RJ") {
		t.Fatal("expected state suffix to match")
	}
}
func TestDatabaseLoadsAllSources(t *testing.T) {
	d := t.TempDir()
	files := map[string]string{"Brasileirao_Matches.csv": "datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round\n2023-01-01,Flamengo-RJ,RJ,Palmeiras-SP,SP,2,1,2023,1\n", "Brazilian_Cup_Matches.csv": "round,datetime,home_team,away_team,home_goal,away_goal,season\nFinal,2023-02-01,Flamengo,Fluminense,1,0,2023\n", "Libertadores_Matches.csv": "datetime,home_team,away_team,home_goal,away_goal,season,stage\n2023-03-01,Palmeiras,Boca Juniors,3,0,2023,group stage\n", "BR-Football-Dataset.csv": "tournament,home,home_goal,away_goal,away,time,date\nCopa do Brasil,Sao Paulo,1,1,Flamengo,20:00,2023-04-01\n", "novo_campeonato_brasileiro.csv": "ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante\n1,02/05/2023,2023,2,Corinthians,Santos,2,2\n", "fifa_data.csv": "ID,Name,Age,Nationality,Overall,Potential,Club,Position\n1,Neymar Jr,31,Brazil,92,92,Paris Saint-Germain,LW\n"}
	for n, v := range files {
		if err := os.WriteFile(filepath.Join(d, n), []byte(v), 0644); err != nil {
			t.Fatal(err)
		}
	}
	db, err := LoadDatabase(d)
	if err != nil {
		t.Fatal(err)
	}
	if len(db.Matches) != 5 || len(db.Players) != 1 {
		t.Fatalf("loaded matches=%d players=%d", len(db.Matches), len(db.Players))
	}
	s := NewServer(db)
	got, err := s.teamStats(map[string]any{"team": "Flamengo", "season": float64(2023)})
	if err != nil || !strings.Contains(got, "3 matches") {
		t.Fatalf("unexpected stats %q: %v", got, err)
	}
	players := s.players(map[string]any{"nationality": "Brazil"})
	if !strings.Contains(players, "Neymar") {
		t.Fatal(players)
	}
}
func TestMCPToolsCall(t *testing.T) {
	s := NewServer(&Database{Matches: []Match{{Home: "Flamengo-RJ", Away: "Fluminense-RJ", HomeGoals: 2, AwayGoals: 1, Competition: "Brasileirao", Season: 2023}}})
	r := s.Handle(nil, rpcRequest{Method: "tools/call", ID: []byte("1"), Params: []byte(`{"name":"head_to_head","arguments":{"team1":"Flamengo","team2":"Fluminense"}}`)})
	raw, _ := jsonMarshal(r.Result)
	if !strings.Contains(string(raw), "Flamengo 1 wins") {
		t.Fatal(string(raw))
	}
}

func TestStandingsAvoidsOverlappingHistoricalRows(t *testing.T) {
	db := &Database{Matches: []Match{
		{Home: "Flamengo-RJ", Away: "Palmeiras-SP", HomeGoals: 1, AwayGoals: 0, Competition: "Brasileirao", Season: 2019, Source: "Brasileirao_Matches.csv"},
		{Home: "Flamengo", Away: "Palmeiras", HomeGoals: 1, AwayGoals: 0, Competition: "Brasileirao", Season: 2019, Source: "novo_campeonato_brasileiro.csv"},
	}}
	got, err := NewServer(db).standings(map[string]any{"season": float64(2019), "competition": "Brasileirao"})
	if err != nil || !strings.Contains(got, "Flamengo-RJ — 3 pts") {
		t.Fatalf("standings must use the canonical source once: %q (%v)", got, err)
	}
}
func jsonMarshal(v any) ([]byte, error) { return json.Marshal(v) }
