package soccer

import (
	"strings"
	"testing"
	"time"
)

func TestLoadBrasileiraoMatches(t *testing.T) {
	csv := `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2012-05-19 18:30:00,"Palmeiras-SP","SP","Portuguesa-SP","SP",1,1,2012,1
2023-09-03 20:00:00,"Flamengo-RJ","RJ","Fluminense-RJ","RJ",2,1,2023,22
`
	matches, err := LoadBrasileiraoMatches(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("LoadBrasileiraoMatches returned error: %v", err)
	}
	if len(matches) != 2 {
		t.Fatalf("got %d matches, want 2", len(matches))
	}

	m := matches[1]
	if m.HomeTeam != "Flamengo-RJ" || m.AwayTeam != "Fluminense-RJ" {
		t.Errorf("unexpected team names: %+v", m)
	}
	if m.HomeKey != "flamengo" || m.AwayKey != "fluminense" {
		t.Errorf("unexpected normalized keys: home=%q away=%q", m.HomeKey, m.AwayKey)
	}
	if m.HomeGoals != 2 || m.AwayGoals != 1 {
		t.Errorf("unexpected score: %d-%d", m.HomeGoals, m.AwayGoals)
	}
	if m.Season != 2023 {
		t.Errorf("unexpected season: %d", m.Season)
	}
	if m.Round != "22" {
		t.Errorf("unexpected round: %q", m.Round)
	}
	if !m.Date.Equal(time.Date(2023, 9, 3, 20, 0, 0, 0, time.UTC)) {
		t.Errorf("unexpected date: %v", m.Date)
	}
	if m.Competition != "Brasileirao" {
		t.Errorf("unexpected competition: %q", m.Competition)
	}
	if m.Outcome() != "home" {
		t.Errorf("unexpected outcome: %q", m.Outcome())
	}
}

func TestLoadCopaDoBrasilMatches(t *testing.T) {
	csv := `"round","datetime","home_team","away_team","home_goal","away_goal","season"
"1",2012-03-07 16:00:00,"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ","America - MG",0,0,2012
"Final",2019-11-13 21:30:00,"Cruzeiro-MG","Athletico-PR",1,1,2019
`
	matches, err := LoadCopaDoBrasilMatches(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("LoadCopaDoBrasilMatches returned error: %v", err)
	}
	if len(matches) != 2 {
		t.Fatalf("got %d matches, want 2", len(matches))
	}
	m := matches[1]
	if m.Competition != "Copa do Brasil" {
		t.Errorf("unexpected competition: %q", m.Competition)
	}
	if m.Round != "Final" {
		t.Errorf("unexpected round: %q", m.Round)
	}
	if m.HomeKey != "cruzeiro" || m.AwayKey != "athletico" {
		t.Errorf("unexpected keys: home=%q away=%q", m.HomeKey, m.AwayKey)
	}
	if m.Season != 2019 {
		t.Errorf("unexpected season: %d", m.Season)
	}
	if m.Outcome() != "draw" {
		t.Errorf("unexpected outcome: %q", m.Outcome())
	}
}

func TestLoadLibertadoresMatches(t *testing.T) {
	csv := `"datetime","home_team","away_team","home_goal","away_goal","season","stage"
2013-02-12 20:15:00,"Nacional (URU)","Barcelona-EQU","2","2",2013,"group stage"
2018-12-08 17:00:00,"River Plate","Boca Juniors","3","1",2018,"final"
`
	matches, err := LoadLibertadoresMatches(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("LoadLibertadoresMatches returned error: %v", err)
	}
	if len(matches) != 2 {
		t.Fatalf("got %d matches, want 2", len(matches))
	}
	m := matches[1]
	if m.Competition != "Libertadores" {
		t.Errorf("unexpected competition: %q", m.Competition)
	}
	if m.Stage != "final" {
		t.Errorf("unexpected stage: %q", m.Stage)
	}
	if m.HomeGoals != 3 || m.AwayGoals != 1 {
		t.Errorf("unexpected score: %d-%d", m.HomeGoals, m.AwayGoals)
	}
	if m.Season != 2018 {
		t.Errorf("unexpected season: %d", m.Season)
	}
}

func TestLoadLibertadoresMatchesSkipsUnparseableRows(t *testing.T) {
	csv := `"datetime","home_team","away_team","home_goal","away_goal","season","stage"
2013-02-12 20:15:00,"Nacional (URU)","Barcelona-EQU","2","2",2013,"group stage"
NA,"Flamengo","Athletico","-","-",NA,"final"
`
	matches, err := LoadLibertadoresMatches(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("LoadLibertadoresMatches returned error: %v", err)
	}
	if len(matches) != 1 {
		t.Fatalf("got %d matches, want 1 (malformed row should be skipped)", len(matches))
	}
}

func TestLoadBRFootballMatches(t *testing.T) {
	csv := `tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,2.0,4.0,75.0,104.0,8.0,13.0,20:00:00,2023-09-24,0.0,0.0,DRAW,DRAW,6.0
Serie A,Flamengo,2.0,1.0,Fluminense,5.0,3.0,110.0,90.0,12.0,9.0,16:00:00,2023-09-03,1.0,-1.0,WON,LOST,8.0
`
	matches, err := LoadBRFootballMatches(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("LoadBRFootballMatches returned error: %v", err)
	}
	if len(matches) != 2 {
		t.Fatalf("got %d matches, want 2", len(matches))
	}
	m0 := matches[0]
	if m0.Competition != "Copa do Brasil" {
		t.Errorf("unexpected competition: %q", m0.Competition)
	}
	if m0.HomeGoals != 1 || m0.AwayGoals != 1 {
		t.Errorf("unexpected score: %d-%d", m0.HomeGoals, m0.AwayGoals)
	}
	if m0.Season != 2023 {
		t.Errorf("unexpected season: %d", m0.Season)
	}
	if !m0.Date.Equal(time.Date(2023, 9, 24, 20, 0, 0, 0, time.UTC)) {
		t.Errorf("unexpected date: %v", m0.Date)
	}
	m1 := matches[1]
	if m1.Competition != "Serie A" {
		t.Errorf("unexpected competition: %q", m1.Competition)
	}
	if m1.HomeKey != "flamengo" || m1.AwayKey != "fluminense" {
		t.Errorf("unexpected keys: home=%q away=%q", m1.HomeKey, m1.AwayKey)
	}
}

func TestLoadHistoricalBrasileiraoMatches(t *testing.T) {
	csv := `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,
2003.01.0002,29/03/2003,2003,1,Athletico-PR,Grêmio,2,0,PR,RS,Mandante,Arena da Baixada,
`
	matches, err := LoadHistoricalBrasileiraoMatches(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("LoadHistoricalBrasileiraoMatches returned error: %v", err)
	}
	if len(matches) != 2 {
		t.Fatalf("got %d matches, want 2", len(matches))
	}
	m := matches[1]
	if m.Competition != "Brasileirao (Historical)" {
		t.Errorf("unexpected competition: %q", m.Competition)
	}
	if m.HomeKey != "athletico" || m.AwayKey != "gremio" {
		t.Errorf("unexpected keys: home=%q away=%q", m.HomeKey, m.AwayKey)
	}
	if m.Stadium != "Arena da Baixada" {
		t.Errorf("unexpected stadium: %q", m.Stadium)
	}
	if !m.Date.Equal(time.Date(2003, 3, 29, 0, 0, 0, 0, time.UTC)) {
		t.Errorf("unexpected date: %v", m.Date)
	}
	if m.Season != 2003 {
		t.Errorf("unexpected season: %d", m.Season)
	}
	if m.HomeGoals != 2 || m.AwayGoals != 0 {
		t.Errorf("unexpected score: %d-%d", m.HomeGoals, m.AwayGoals)
	}
}
