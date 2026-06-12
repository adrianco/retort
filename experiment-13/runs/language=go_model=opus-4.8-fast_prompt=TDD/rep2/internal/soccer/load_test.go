package soccer

import (
	"strings"
	"testing"
)

func TestLoadBrasileirao(t *testing.T) {
	csv := `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2012-05-19 18:30:00,"Palmeiras-SP","SP","Portuguesa-SP","SP",1,1,2012,1
2019-10-27 16:00:00,"Flamengo-RJ","RJ","Gremio-RS","RS",5,0,2019,28
`
	ms, err := loadBrasileirao(strings.NewReader(csv))
	if err != nil {
		t.Fatal(err)
	}
	if len(ms) != 2 {
		t.Fatalf("got %d matches, want 2", len(ms))
	}
	m := ms[0]
	if m.HomeTeam != "Palmeiras-SP" || m.AwayTeam != "Portuguesa-SP" {
		t.Errorf("teams = %q vs %q", m.HomeTeam, m.AwayTeam)
	}
	if m.HomeGoals != 1 || m.AwayGoals != 1 || !m.HasScore {
		t.Errorf("score = %d-%d ok=%v", m.HomeGoals, m.AwayGoals, m.HasScore)
	}
	if m.Season != 2012 || m.Round != "1" {
		t.Errorf("season/round = %d/%q", m.Season, m.Round)
	}
	if m.Competition != CompBrasileirao {
		t.Errorf("competition = %q", m.Competition)
	}
	if !m.HasDate || m.Date.Year() != 2012 {
		t.Errorf("date = %v ok=%v", m.Date, m.HasDate)
	}
}

func TestLoadCup(t *testing.T) {
	csv := `"round","datetime","home_team","away_team","home_goal","away_goal","season"
"1",2012-03-07 16:00:00,"Boavista - RJ","América - MG",0,0,2012
`
	ms, err := loadCup(strings.NewReader(csv))
	if err != nil {
		t.Fatal(err)
	}
	if len(ms) != 1 {
		t.Fatalf("got %d", len(ms))
	}
	if ms[0].Competition != CompCopaDoBrasil {
		t.Errorf("competition = %q", ms[0].Competition)
	}
	if ms[0].HomeTeam != "Boavista - RJ" || ms[0].Round != "1" {
		t.Errorf("unexpected %+v", ms[0])
	}
}

func TestLoadLibertadores(t *testing.T) {
	csv := `"datetime","home_team","away_team","home_goal","away_goal","season","stage"
2013-02-12 20:15:00,"Nacional (URU)","Barcelona-EQU","2","2",2013,"group stage"
`
	ms, err := loadLibertadores(strings.NewReader(csv))
	if err != nil {
		t.Fatal(err)
	}
	if len(ms) != 1 || ms[0].Competition != CompLibertadores {
		t.Fatalf("unexpected %+v", ms)
	}
	if ms[0].Stage != "group stage" || ms[0].HomeGoals != 2 {
		t.Errorf("unexpected %+v", ms[0])
	}
}

func TestLoadBRFootball(t *testing.T) {
	csv := `tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,2.0,4.0,75.0,104.0,8.0,13.0,20:00:00,2023-09-24,0.0,0.0,DRAW,DRAW,6.0
`
	ms, err := loadBRFootball(strings.NewReader(csv))
	if err != nil {
		t.Fatal(err)
	}
	if len(ms) != 1 {
		t.Fatalf("got %d", len(ms))
	}
	m := ms[0]
	if m.HomeGoals != 1 || m.AwayGoals != 1 {
		t.Errorf("score = %d-%d", m.HomeGoals, m.AwayGoals)
	}
	if m.HomeShots != 8 || m.AwayShots != 13 {
		t.Errorf("shots = %d/%d", m.HomeShots, m.AwayShots)
	}
	if m.Season != 2023 {
		t.Errorf("season derived from date = %d", m.Season)
	}
	if m.Competition != "Copa do Brasil" {
		t.Errorf("competition = %q", m.Competition)
	}
}

func TestLoadNovo(t *testing.T) {
	csv := `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,
`
	ms, err := loadNovo(strings.NewReader(csv))
	if err != nil {
		t.Fatal(err)
	}
	if len(ms) != 1 {
		t.Fatalf("got %d", len(ms))
	}
	m := ms[0]
	if m.HomeTeam != "Guarani" || m.AwayTeam != "Vasco" {
		t.Errorf("teams %q/%q", m.HomeTeam, m.AwayTeam)
	}
	if m.HomeGoals != 4 || m.AwayGoals != 2 || m.Season != 2003 {
		t.Errorf("unexpected %+v", m)
	}
	if m.Stadium != "Brinco de Ouro" {
		t.Errorf("stadium = %q", m.Stadium)
	}
	if !m.HasDate || m.Date.Day() != 29 {
		t.Errorf("date = %v", m.Date)
	}
}

func TestLoadFIFA(t *testing.T) {
	// Note the UTF-8 BOM before the leading empty header column.
	csv := "\uFEFF,ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number,Joined,Loaned From,Contract Valid Until,Height,Weight\n" +
		"0,158023,L. Messi,31,photo,Argentina,flag,94,94,FC Barcelona,logo,€110.5M,€565K,2202,Left,5,4,4,Medium/ Medium,Messi,Yes,RF,10,\"Jul 1, 2004\",,2021,5'7,159lbs\n"
	ps, err := loadFIFA(strings.NewReader(csv))
	if err != nil {
		t.Fatal(err)
	}
	if len(ps) != 1 {
		t.Fatalf("got %d", len(ps))
	}
	p := ps[0]
	if p.Name != "L. Messi" || p.Nationality != "Argentina" {
		t.Errorf("unexpected %+v", p)
	}
	if p.Overall != 94 || p.Club != "FC Barcelona" || p.Position != "RF" {
		t.Errorf("unexpected %+v", p)
	}
	if p.Age != 31 || p.ID != 158023 {
		t.Errorf("unexpected %+v", p)
	}
}
