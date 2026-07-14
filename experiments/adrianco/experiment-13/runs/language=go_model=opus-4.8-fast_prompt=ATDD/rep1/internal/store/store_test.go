package store

import (
	"os"
	"path/filepath"
	"testing"
)

// loadStore writes the given named CSV files into a temp kaggle dir and loads them.
func loadStore(t *testing.T, files map[string]string) *Store {
	t.Helper()
	dir := t.TempDir()
	kaggle := filepath.Join(dir, "kaggle")
	if err := os.MkdirAll(kaggle, 0o755); err != nil {
		t.Fatal(err)
	}
	for name, content := range files {
		if err := os.WriteFile(filepath.Join(kaggle, name), []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	s, err := Load(dir)
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	return s
}

const brasHeader = `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"` + "\n"

func TestTeamStatsComputesRecord(t *testing.T) {
	s := loadStore(t, map[string]string{
		"Brasileirao_Matches.csv": brasHeader +
			`2022-01-01 16:00:00,"Corinthians-SP","SP","Santos-SP","SP",2,0,2022,1` + "\n" +
			`2022-01-08 16:00:00,"Corinthians-SP","SP","Palmeiras-SP","SP",1,1,2022,2` + "\n" +
			`2022-01-15 16:00:00,"Gremio-RS","RS","Corinthians-SP","SP",3,0,2022,3` + "\n",
	})
	ts := s.TeamStats(MatchFilter{Team: "Corinthians", Season: 2022})
	if ts.Matches != 3 || ts.Wins != 1 || ts.Draws != 1 || ts.Losses != 1 {
		t.Errorf("unexpected record: %+v", ts)
	}
	if ts.GoalsFor != 3 || ts.GoalsAgainst != 4 {
		t.Errorf("unexpected goals: GF=%d GA=%d", ts.GoalsFor, ts.GoalsAgainst)
	}
	if ts.Points != 4 {
		t.Errorf("expected 4 points, got %d", ts.Points)
	}
}

func TestStandingsOrdersByPointsThenGoalDifference(t *testing.T) {
	s := loadStore(t, map[string]string{
		"Brasileirao_Matches.csv": brasHeader +
			// A and B both beat C; A wins by more, so A tops on goal difference.
			`2020-01-01 16:00:00,"Alpha-SP","SP","Charlie-RJ","RJ",5,0,2020,1` + "\n" +
			`2020-01-08 16:00:00,"Bravo-MG","MG","Charlie-RJ","RJ",1,0,2020,2` + "\n",
	})
	table := s.Standings("Brasileirao", 2020)
	if len(table) != 3 {
		t.Fatalf("expected 3 teams, got %d", len(table))
	}
	if table[0].Team != "Alpha" || table[1].Team != "Bravo" {
		t.Errorf("expected Alpha then Bravo by goal difference, got %q then %q", table[0].Team, table[1].Team)
	}
	if table[0].Position != 1 {
		t.Errorf("expected positions to be assigned")
	}
}

func TestSeasonPrecedenceAvoidsDoubleCounting(t *testing.T) {
	// The same competition+season exists in two files; only the first wins.
	novoHeader := "ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS\n"
	s := loadStore(t, map[string]string{
		"Brasileirao_Matches.csv": brasHeader +
			`2019-01-01 16:00:00,"Flamengo-RJ","RJ","Santos-SP","SP",2,0,2019,1` + "\n",
		"novo_campeonato_brasileiro.csv": novoHeader +
			`2019.01.0001,01/01/2019,2019,1,Flamengo,Santos,2,0,RJ,SP,Mandante,X,` + "\n" +
			`2019.01.0002,08/01/2019,2019,2,Flamengo,Santos,3,0,RJ,SP,Mandante,X,` + "\n",
	})
	m, _ := s.Counts()
	if m != 1 {
		t.Fatalf("expected the secondary file's overlapping season to be ignored (1 match), got %d", m)
	}
}

func TestStateSuffixKeepsDistinctClubsSeparate(t *testing.T) {
	s := loadStore(t, map[string]string{
		"Brasileirao_Matches.csv": brasHeader +
			`2019-01-01 16:00:00,"Atletico-MG","MG","Flamengo-RJ","RJ",1,0,2019,1` + "\n" +
			`2019-01-08 16:00:00,"Atletico-GO","GO","Flamengo-RJ","RJ",0,1,2019,2` + "\n",
	})
	table := s.Standings("Brasileirao", 2019)
	// Atletico-MG, Atletico-GO and Flamengo => 3 distinct teams.
	if len(table) != 3 {
		t.Fatalf("expected 3 distinct teams, got %d: %+v", len(table), table)
	}
}

func TestHeadToHeadFromTeamPerspective(t *testing.T) {
	s := loadStore(t, map[string]string{
		"Brasileirao_Matches.csv": brasHeader +
			`2021-01-01 16:00:00,"Palmeiras-SP","SP","Santos-SP","SP",2,0,2021,1` + "\n" +
			`2021-06-01 16:00:00,"Santos-SP","SP","Palmeiras-SP","SP",1,1,2021,2` + "\n",
	})
	h := s.HeadToHead("Palmeiras", "Santos")
	if h.Matches != 2 || h.TeamWins != 1 || h.OpponentWins != 0 || h.Draws != 1 {
		t.Errorf("unexpected head-to-head: %+v", h)
	}
}
