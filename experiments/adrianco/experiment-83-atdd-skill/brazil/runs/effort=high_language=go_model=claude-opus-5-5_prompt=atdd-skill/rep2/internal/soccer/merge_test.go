package soccer

import (
	"os"
	"path/filepath"
	"testing"
)

func writeFile(t *testing.T, dir, name, content string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestOneDatasetListingAPairingTwiceInASeasonKeepsBoth(t *testing.T) {
	dir := t.TempDir()
	writeFile(t, dir, "novo_campeonato_brasileiro.csv", "ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS\n"+
		"1,19/07/2009,2009,12,Botafogo-RJ,Flamengo,2,2,RJ,RJ,Empate,Maracanã,\n"+
		"2,25/10/2009,2009,31,Botafogo-RJ,Flamengo,0,1,RJ,RJ,Visitante,Engenhão,\n")
	s := Load(dir)
	if len(s.Matches) != 2 {
		t.Fatalf("expected both matches, got %d", len(s.Matches))
	}
}

func TestDuplicateRowsWithinADatasetAreOneMatch(t *testing.T) {
	dir := t.TempDir()
	writeFile(t, dir, "BR-Football-Dataset.csv", "tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners\n"+
		"Serie A,Goias,2.0,3.0,Atletico Mineiro,5.0,2.0,,,,,23:30:00,2014-09-18,,,,,7.0\n"+
		"Serie A,Goias,2.0,3.0,Atletico Mineiro,5.0,2.0,,,,,20:00:00,2014-09-17,,,,,7.0\n")
	s := Load(dir)
	if len(s.Matches) != 1 {
		t.Fatalf("expected one match, got %d", len(s.Matches))
	}
}

func TestMissingFilesAreReportedNotFatal(t *testing.T) {
	s := Load(t.TempDir())
	if len(s.Datasets) != 6 {
		t.Fatalf("expected the six datasets to be described, got %d", len(s.Datasets))
	}
	for _, d := range s.Datasets {
		if d.Loaded || d.Error == "" {
			t.Errorf("%s should be reported as not loaded", d.File)
		}
	}
}
