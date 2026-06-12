package main

import (
	"strings"
	"testing"
)

const brasileiraoCSV = `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2012-05-19 18:30:00,"Palmeiras-SP","SP","Portuguesa-SP","SP",1,1,2012,1
2019-11-27 21:30:00,"Flamengo-RJ","RJ","Corinthians-SP","SP",3,1,2019,38
`

const cupCSV = `"round","datetime","home_team","away_team","home_goal","away_goal","season"
"1",2012-03-07 16:00:00,"Boavista - RJ","América - MG",0,0,2012
"Final",2023-10-01 20:00:00,"São Paulo","Flamengo",2,1,2023
`

const libertadoresCSV = `"datetime","home_team","away_team","home_goal","away_goal","season","stage"
2013-02-12 20:15:00,"Nacional (URU)","Barcelona-EQU","2","2",2013,"group stage"
2019-11-23 17:00:00,"Flamengo","River Plate","2","1",2019,"final"
`

const brFootballCSV = `tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,2.0,4.0,75.0,104.0,8.0,13.0,20:00:00,2023-09-24,0.0,0.0,DRAW,DRAW,6.0
Brasileirao,Palmeiras,2.0,0.0,Santos,5.0,3.0,90.0,80.0,10.0,6.0,16:00:00,2023-06-10,1.0,-1.0,WON,LOST,8.0
`

const historicalCSV = `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,
2003.01.0002,29/03/2003,2003,1,Athletico-PR,Grêmio,2,0,PR,RS,Mandante,Arena da Baixada,
`

const fifaCSV = "\xef\xbb\xbf" + `,ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number,Joined,Loaned From,Contract Valid Until,Height,Weight
0,158023,L. Messi,31,http://example.com/messi.png,Argentina,http://example.com/arg.png,94,94,FC Barcelona,http://example.com/barca.png,€110.5M,€565K,2202,Left,5,4,4,Medium/ Medium,Messi,Yes,RF,10,"Jul 1, 2004",,2021,5'7,159lbs
1,212198,Neymar Jr,26,http://example.com/neymar.png,Brazil,http://example.com/bra.png,92,92,Paris Saint-Germain,http://example.com/psg.png,€123M,€280K,2154,Right,5,5,5,High/ Medium,Neymar,Yes,LW,10,"Jul 10, 2013",,2022,5'9,150lbs
2,200389,Alisson,25,http://example.com/alisson.png,Brazil,http://example.com/bra.png,89,91,Liverpool,http://example.com/liv.png,€62M,€175K,1845,Right,4,3,1,Medium/ Low,Generic,Yes,GK,1,"Jul 1, 2018",,2023,6'3,198lbs
`

func TestParseBrasileiraoCSV(t *testing.T) {
	matches, err := parseBrasileiraoCSV(strings.NewReader(brasileiraoCSV))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(matches) != 2 {
		t.Fatalf("expected 2 matches, got %d", len(matches))
	}

	m := matches[0]
	if m.Competition != "Brasileirao" {
		t.Errorf("Competition = %q, want %q", m.Competition, "Brasileirao")
	}
	// Raw team names are kept (with state suffix) for disambiguation in standings.
	if m.HomeTeam != "Palmeiras-SP" {
		t.Errorf("HomeTeam = %q, want %q", m.HomeTeam, "Palmeiras-SP")
	}
	if m.AwayTeam != "Portuguesa-SP" {
		t.Errorf("AwayTeam = %q, want %q", m.AwayTeam, "Portuguesa-SP")
	}
	if m.HomeGoal != 1 || m.AwayGoal != 1 {
		t.Errorf("goals = %d-%d, want 1-1", m.HomeGoal, m.AwayGoal)
	}
	if m.Season != 2012 {
		t.Errorf("Season = %d, want 2012", m.Season)
	}
	if m.Date != "2012-05-19" {
		t.Errorf("Date = %q, want %q", m.Date, "2012-05-19")
	}
	// teamContains normalizes for search
	if !teamContains(m.HomeTeam, "Palmeiras") {
		t.Errorf("expected teamContains(Palmeiras-SP, Palmeiras)=true")
	}

	m2 := matches[1]
	if !teamContains(m2.HomeTeam, "Flamengo") {
		t.Errorf("HomeTeam %q should match 'Flamengo'", m2.HomeTeam)
	}
	if m2.AwayGoal != 1 {
		t.Errorf("AwayGoal = %d, want 1", m2.AwayGoal)
	}
}

func TestParseCupCSV(t *testing.T) {
	matches, err := parseCupCSV(strings.NewReader(cupCSV))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(matches) != 2 {
		t.Fatalf("expected 2 matches, got %d", len(matches))
	}

	m := matches[0]
	if m.Competition != "Copa do Brasil" {
		t.Errorf("Competition = %q, want %q", m.Competition, "Copa do Brasil")
	}
	if m.HomeGoal != 0 || m.AwayGoal != 0 {
		t.Errorf("goals = %d-%d, want 0-0", m.HomeGoal, m.AwayGoal)
	}
	if m.Season != 2012 {
		t.Errorf("Season = %d, want 2012", m.Season)
	}

	m2 := matches[1]
	if m2.HomeTeam != "São Paulo" {
		t.Errorf("HomeTeam = %q, want %q", m2.HomeTeam, "São Paulo")
	}
	if m2.Round != "Final" {
		t.Errorf("Round = %q, want Final", m2.Round)
	}
}

func TestParseLibertadoresCSV(t *testing.T) {
	matches, err := parseLibertadoresCSV(strings.NewReader(libertadoresCSV))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(matches) != 2 {
		t.Fatalf("expected 2 matches, got %d", len(matches))
	}

	m := matches[0]
	if m.Competition != "Libertadores" {
		t.Errorf("Competition = %q, want %q", m.Competition, "Libertadores")
	}
	if m.HomeGoal != 2 || m.AwayGoal != 2 {
		t.Errorf("goals = %d-%d, want 2-2", m.HomeGoal, m.AwayGoal)
	}
	if m.Stage != "group stage" {
		t.Errorf("Stage = %q, want %q", m.Stage, "group stage")
	}
}

func TestParseBRFootballCSV(t *testing.T) {
	matches, err := parseBRFootballCSV(strings.NewReader(brFootballCSV))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(matches) != 2 {
		t.Fatalf("expected 2 matches, got %d", len(matches))
	}

	m := matches[0]
	if m.Competition != "Copa do Brasil" {
		t.Errorf("Competition = %q, want %q", m.Competition, "Copa do Brasil")
	}
	if m.HomeTeam != "Sao Paulo" {
		t.Errorf("HomeTeam = %q, want %q", m.HomeTeam, "Sao Paulo")
	}
	if m.HomeGoal != 1 || m.AwayGoal != 1 {
		t.Errorf("goals = %d-%d, want 1-1", m.HomeGoal, m.AwayGoal)
	}
	if m.Date != "2023-09-24" {
		t.Errorf("Date = %q, want 2023-09-24", m.Date)
	}
	if m.Season != 2023 {
		t.Errorf("Season = %d, want 2023", m.Season)
	}
	if m.HomeCorner != 2.0 {
		t.Errorf("HomeCorner = %f, want 2.0", m.HomeCorner)
	}
}

func TestParseHistoricalCSV(t *testing.T) {
	matches, err := parseHistoricalCSV(strings.NewReader(historicalCSV))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(matches) != 2 {
		t.Fatalf("expected 2 matches, got %d", len(matches))
	}

	m := matches[0]
	if m.Competition != "Brasileirao" {
		t.Errorf("Competition = %q, want %q", m.Competition, "Brasileirao")
	}
	if m.HomeTeam != "Guarani" {
		t.Errorf("HomeTeam = %q, want %q", m.HomeTeam, "Guarani")
	}
	if m.HomeGoal != 4 || m.AwayGoal != 2 {
		t.Errorf("goals = %d-%d, want 4-2", m.HomeGoal, m.AwayGoal)
	}
	if m.Date != "2003-03-29" {
		t.Errorf("Date = %q, want 2003-03-29", m.Date)
	}
	if m.Arena != "Brinco de Ouro" {
		t.Errorf("Arena = %q, want Brinco de Ouro", m.Arena)
	}
}

func TestParseFIFACSV(t *testing.T) {
	players, err := parseFIFACSV(strings.NewReader(fifaCSV))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(players) != 3 {
		t.Fatalf("expected 3 players, got %d", len(players))
	}

	p := players[0]
	if p.Name != "L. Messi" {
		t.Errorf("Name = %q, want L. Messi", p.Name)
	}
	if p.Nationality != "Argentina" {
		t.Errorf("Nationality = %q, want Argentina", p.Nationality)
	}
	if p.Overall != 94 {
		t.Errorf("Overall = %d, want 94", p.Overall)
	}
	if p.Club != "FC Barcelona" {
		t.Errorf("Club = %q, want FC Barcelona", p.Club)
	}

	p2 := players[1]
	if p2.Nationality != "Brazil" {
		t.Errorf("Nationality = %q, want Brazil", p2.Nationality)
	}
	if p2.Overall != 92 {
		t.Errorf("Overall = %d, want 92", p2.Overall)
	}
}
