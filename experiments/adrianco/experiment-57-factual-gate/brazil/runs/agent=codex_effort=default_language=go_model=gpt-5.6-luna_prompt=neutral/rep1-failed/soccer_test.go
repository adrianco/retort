package soccer

import (
	"bytes"
	"encoding/json"
	"path/filepath"
	"testing"
)

func fixtureStore() *Store {
	return &Store{Matches: []Match{
		{Competition: "Brasileirão", Date: "2023-09-03", Home: "Flamengo-RJ", Away: "Fluminense-RJ", Season: 2023, HomeGoals: 2, AwayGoals: 1, Round: "22"},
		{Competition: "Brasileirão", Date: "2023-05-28", Home: "Fluminense-RJ", Away: "Flamengo-RJ", Season: 2023, HomeGoals: 1, AwayGoals: 0, Round: "8"},
		{Competition: "Brasileirão", Date: "2023-07-01", Home: "Palmeiras-SP", Away: "Santos-SP", Season: 2023, HomeGoals: 3, AwayGoals: 0},
	}, Players: []Player{{Name: "Neymar Jr", Nationality: "Brazil", Club: "Paris Saint-Germain", Position: "LW", Overall: 92}, {Name: "Gabriel Barbosa", Nationality: "Brazil", Club: "Flamengo", Position: "ST", Overall: 84}}}
}

func TestTeamNormalizationAndMatchSearch(t *testing.T) {
	got := fixtureStore().SearchMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense", Season: 2023})
	if len(got) != 2 {
		t.Fatalf("got %d matches", len(got))
	}
}
func TestStatsAndStandings(t *testing.T) {
	s := fixtureStore()
	st := s.Stats("Flamengo", "Brasileirao", 2023, false)
	if st.Matches != 2 || st.Wins != 1 || st.Losses != 1 || st.GoalsFor != 2 {
		t.Fatalf("unexpected stats: %+v", st)
	}
	tab := s.Standings("Brasileirão", 2023)
	if len(tab) != 4 || tab[0].Team != "Palmeiras-SP" || tab[0].Points != 3 {
		t.Fatalf("unexpected standings: %+v", tab)
	}
}
func TestPlayerSearch(t *testing.T) {
	got := fixtureStore().SearchPlayers(PlayerFilter{Nationality: "brasil", MinOverall: 85})
	if len(got) != 1 || got[0].Name != "Neymar Jr" {
		t.Fatalf("unexpected players: %+v", got)
	}
}
func TestLoadProvidedData(t *testing.T) {
	s, e := Load(filepath.Join("data", "kaggle"))
	if e != nil {
		t.Fatal(e)
	}
	if len(s.Matches) < 10000 || len(s.Players) < 10000 {
		t.Fatalf("incomplete data: %d matches, %d players", len(s.Matches), len(s.Players))
	}
}
func TestMCPProtocol(t *testing.T) {
	srv := NewServer(fixtureStore())
	req := rpcReq{JSONRPC: "2.0", ID: 1, Method: "tools/call"}
	req.Params, _ = json.Marshal(map[string]any{"name": "team_stats", "arguments": map[string]any{"team": "Flamengo", "season": 2023}})
	var out bytes.Buffer
	if e := srv.Serve(bytes.NewBufferString(mustJSON(req)+"\n"), &out); e != nil {
		t.Fatal(e)
	}
	if !bytes.Contains(out.Bytes(), []byte(`Wins`)) {
		t.Fatalf("unexpected MCP response: %s", out.String())
	}
}
func mustJSON(v any) string { b, _ := json.Marshal(v); return string(b) }
