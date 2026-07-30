package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestLoadDataAndQueriesWithNameVariations(t *testing.T) {
	dir := writeFixtureData(t)
	data, err := LoadData(dir)
	if err != nil {
		t.Fatalf("LoadData() error = %v", err)
	}
	if got, want := len(data.Matches), 6; got != want {
		t.Fatalf("loaded matches = %d, want %d", got, want)
	}
	if got, want := len(data.Players), 2; got != want {
		t.Fatalf("loaded players = %d, want %d", got, want)
	}

	// Flamengo-RJ, Flamengo, and Sport Club Corinthians Paulista should all
	// remain searchable with their common short forms.
	matches := data.SearchMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense", Limit: 10})
	if got, want := len(matches), 5; got != want {
		t.Fatalf("Fla-Flu matches = %d, want %d", got, want)
	}
	var serieAMatch Match
	for _, match := range matches {
		if match.Source == "Brasileirao_Matches.csv" {
			serieAMatch = match
			break
		}
	}
	if serieAMatch.HomeTeam != "Flamengo-RJ" {
		t.Fatalf("Serie A home team = %q, want Flamengo-RJ", serieAMatch.HomeTeam)
	}

	stats := data.TeamStatistics("Flamengo", 2023, "Brasileirão Série A", "home")
	if stats.Matches != 1 || stats.Wins != 1 || stats.GoalsFor != 2 || stats.GoalsAgainst != 1 {
		t.Fatalf("home stats = %#v, want one 2-1 win", stats)
	}
	standings := data.Standings("Brasileirao", 2023)
	if len(standings) != 2 || standings[0].Team != "Flamengo" || standings[0].Points != 3 {
		t.Fatalf("standings = %#v, want Flamengo first on 3 points", standings)
	}
	players := data.SearchPlayers("", "Brazilian", "Flamengo", "", 10)
	if len(players) != 1 || players[0].Name != "Gabriel Barbosa" {
		t.Fatalf("player search = %#v", players)
	}
	if forwards := data.SearchPlayers("", "", "São Paulo FC", "forwards", 10); len(forwards) != 1 || forwards[0].Name != "Alex" {
		t.Fatalf("club and forward aliases did not match: %#v", forwards)
	}
	if got := data.TeamCompetitions("Sport Club Corinthians Paulista"); len(got) != 1 || got[0] != "Brasileirão" {
		t.Fatalf("Corinthians competitions = %#v", got)
	}
}

func TestSearchAndAggregatesDeduplicateOverlappingSources(t *testing.T) {
	data, err := LoadData(writeFixtureData(t))
	if err != nil {
		t.Fatal(err)
	}
	// Search preserves the supplied datasets' individual rows and sources.
	if got := len(data.SearchMatches(MatchFilter{Team: "Flamengo", Competition: "Brasileirão", Limit: 10})); got != 3 {
		t.Fatalf("search result count = %d, want source-preserving 3", got)
	}
	// Calculated results describe one real fixture, not its duplicate record.
	h2h := data.HeadToHead("Flamengo", "Fluminense", "Brasileirão", 2023, 10)
	if h2h.Matches != 1 || h2h.TeamAWins != 1 || h2h.Draws != 0 {
		t.Fatalf("head-to-head = %#v", h2h)
	}
	competition := data.CompetitionStatistics("Brasileirão", 2023)
	if competition.Matches != 1 || competition.Goals != 3 || competition.HomeWinRate != 100 {
		t.Fatalf("competition statistics = %#v", competition)
	}
}

func TestMCPStdioProtocolAndToolCall(t *testing.T) {
	data, err := LoadData(writeFixtureData(t))
	if err != nil {
		t.Fatal(err)
	}
	input := strings.NewReader("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-03-26\"}}\n" +
		"{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"search_matches\",\"arguments\":{\"team\":\"Flamengo\",\"season\":2023}}}\n")
	var output bytes.Buffer
	if err := NewServer(data).RunServer(input, &output); err != nil {
		t.Fatalf("RunServer() error = %v", err)
	}
	lines := strings.Split(strings.TrimSpace(output.String()), "\n")
	if len(lines) != 2 {
		t.Fatalf("response lines = %d, output = %s", len(lines), output.String())
	}
	var initialized struct {
		Result struct {
			ProtocolVersion string                     `json:"protocolVersion"`
			Capabilities    map[string]json.RawMessage `json:"capabilities"`
		} `json:"result"`
	}
	if err := json.Unmarshal([]byte(lines[0]), &initialized); err != nil {
		t.Fatal(err)
	}
	if initialized.Result.ProtocolVersion != "2025-03-26" || initialized.Result.Capabilities["tools"] == nil {
		t.Fatalf("initialize response = %s", lines[0])
	}
	var called struct {
		Result struct {
			Structured []Match `json:"structuredContent"`
		} `json:"result"`
	}
	if err := json.Unmarshal([]byte(lines[1]), &called); err != nil {
		t.Fatal(err)
	}
	if len(called.Result.Structured) != 5 {
		t.Fatalf("tool result = %#v, want five Flamengo rows", called.Result.Structured)
	}
}

func TestBundledDatasetsAllLoad(t *testing.T) {
	data, err := LoadData("data/kaggle")
	if err != nil {
		t.Fatalf("bundled data failed to load: %v", err)
	}
	if len(data.Players) != 18207 {
		t.Fatalf("players = %d, want 18207", len(data.Players))
	}
	sources := map[string]bool{}
	for _, match := range data.Matches {
		sources[match.Source] = true
	}
	for _, source := range []string{"Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv"} {
		if !sources[source] {
			t.Errorf("no loaded matches from %s", source)
		}
	}
	standings := data.Standings("Brasileirão", 2019)
	if len(standings) != 20 || standings[0].Team != "Flamengo" || standings[0].Points != 90 || standings[0].Played != 38 {
		t.Fatalf("2019 standings did not use the authoritative Serie A season: first=%#v, teams=%d", standings[0], len(standings))
	}
}

func writeFixtureData(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	files := map[string]string{
		"Brasileirao_Matches.csv":        "datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round\n2023-09-03 18:30:00,Flamengo-RJ,RJ,Fluminense-RJ,RJ,2,1,2023,22\n",
		"Brazilian_Cup_Matches.csv":      "round,datetime,home_team,away_team,home_goal,away_goal,season\nfinal,2023-09-24 20:00:00,Fluminense,Flamengo,1,0,2023\n",
		"Libertadores_Matches.csv":       "datetime,home_team,away_team,home_goal,away_goal,season,stage\n2023-06-01 20:00:00,Flamengo,Fluminense,1,1,2023,group stage\n",
		"BR-Football-Dataset.csv":        "tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners\nSerie A,Flamengo,2.0,1.0,Fluminense,3.0,4.0,10.0,8.0,7.0,4.0,18:30:00,2023-09-03,0,0,WON,LOST,7\n",
		"novo_campeonato_brasileiro.csv": "ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS\n2023.01.1,03/09/2023,2023,22,Flamengo,Fluminense,2,1,RJ,RJ,Mandante,Maracana,\n2023.01.2,10/09/2023,2023,23,Sport Club Corinthians Paulista,Santos,0,0,SP,SP,Empate,Neo Quimica,\n",
		"fifa_data.csv":                  "\ufeff,ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Height,Weight\n0,1,Gabriel Barbosa,26,Brazilian,81,82,Flamengo,ST,9,5'10,165lbs\n1,2,Alex,25,Argentinian,80,84,São Paulo,ST,8,5'9,150lbs\n",
	}
	for name, contents := range files {
		if err := os.WriteFile(filepath.Join(dir, name), []byte(contents), 0o600); err != nil {
			t.Fatalf("write %s: %v", name, err)
		}
	}
	return dir
}
