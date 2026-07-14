package main

import (
	"fmt"
	"strings"
	"testing"
)

func collectWarnings(t *testing.T) (warnFunc, *[]string) {
	t.Helper()
	var warnings []string
	return func(format string, args ...any) {
		warnings = append(warnings, fmt.Sprintf(format, args...))
	}, &warnings
}

func TestLoadBrasileirao(t *testing.T) {
	csv := `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2012-05-19 18:30:00,"Palmeiras-SP","SP","Portuguesa-SP","SP",1,1,2012,1
2013-06-01 16:00:00,"Flamengo-RJ","RJ","Corinthians-SP","SP",3,0,2013,5
`
	warn, warnings := collectWarnings(t)
	matches, err := loadBrasileirao(strings.NewReader(csv), warn)
	if err != nil {
		t.Fatalf("loadBrasileirao: %v", err)
	}
	if len(matches) != 2 {
		t.Fatalf("got %d matches, want 2", len(matches))
	}
	if len(*warnings) != 0 {
		t.Fatalf("unexpected warnings: %v", *warnings)
	}
	m := matches[0]
	if m.Competition != "Brasileirão" || m.Season != 2012 || m.HomeGoals != 1 || m.AwayGoals != 1 || !m.HasGoals {
		t.Fatalf("unexpected match: %+v", m)
	}
	if m.DateStr != "2012-05-19" {
		t.Fatalf("DateStr = %q, want 2012-05-19", m.DateStr)
	}
}

func TestLoadLibertadoresSkipsNA(t *testing.T) {
	csv := `"datetime","home_team","away_team","home_goal","away_goal","season","stage"
2013-02-12 20:15:00,"Nacional (URU)","Barcelona-EQU","2","2",2013,"group stage"
2022-11-30 00:00:00,"Palmeiras","Flamengo","0","1",NA,"final"
`
	warn, warnings := collectWarnings(t)
	matches, err := loadLibertadores(strings.NewReader(csv), warn)
	if err != nil {
		t.Fatalf("loadLibertadores: %v", err)
	}
	if len(matches) != 1 {
		t.Fatalf("got %d matches, want 1 (NA season row should be skipped)", len(matches))
	}
	if len(*warnings) != 1 {
		t.Fatalf("got %d warnings, want 1", len(*warnings))
	}
}

func TestLoadBRFootballCombinesDateAndTime(t *testing.T) {
	csv := `tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,2.0,4.0,75.0,104.0,8.0,13.0,20:00:00,2023-09-24,0.0,0.0,DRAW,DRAW,6.0
`
	warn, _ := collectWarnings(t)
	matches, err := loadBRFootball(strings.NewReader(csv), warn)
	if err != nil {
		t.Fatalf("loadBRFootball: %v", err)
	}
	if len(matches) != 1 {
		t.Fatalf("got %d matches, want 1", len(matches))
	}
	m := matches[0]
	if m.Competition != "Copa do Brasil (Extended Stats)" {
		t.Fatalf("Competition = %q", m.Competition)
	}
	if m.DateStr != "2023-09-24" || m.Season != 2023 {
		t.Fatalf("DateStr/Season = %q/%d", m.DateStr, m.Season)
	}
	if m.Extended == nil || m.Extended.HomeCorners != 2.0 || m.Extended.AwayShots != 13.0 {
		t.Fatalf("Extended = %+v", m.Extended)
	}
}

func TestLoadNovoCampeonatoBrazilianDate(t *testing.T) {
	csv := `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,
`
	warn, _ := collectWarnings(t)
	matches, err := loadNovoCampeonato(strings.NewReader(csv), warn)
	if err != nil {
		t.Fatalf("loadNovoCampeonato: %v", err)
	}
	if len(matches) != 1 {
		t.Fatalf("got %d matches, want 1", len(matches))
	}
	m := matches[0]
	if m.DateStr != "2003-03-29" {
		t.Fatalf("DateStr = %q, want 2003-03-29", m.DateStr)
	}
	if m.HomeGoals != 4 || m.AwayGoals != 2 || m.Arena != "Brinco de Ouro" {
		t.Fatalf("unexpected match: %+v", m)
	}
}

func TestLoadFIFA(t *testing.T) {
	csv := "\uFEFF,ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Height,Weight,Value,Wage\n" +
		"0,158023,L. Messi,31,Argentina,94,94,FC Barcelona,RF,10,5'7,159lbs,€110.5M,€565K\n"
	warn, _ := collectWarnings(t)
	players, err := loadFIFA(strings.NewReader(csv), warn)
	if err != nil {
		t.Fatalf("loadFIFA: %v", err)
	}
	if len(players) != 1 {
		t.Fatalf("got %d players, want 1", len(players))
	}
	p := players[0]
	if p.Name != "L. Messi" || p.Overall != 94 || p.Club != "FC Barcelona" || p.Nationality != "Argentina" {
		t.Fatalf("unexpected player: %+v", p)
	}
}
