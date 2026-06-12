// Context: Brazilian Soccer MCP Server.
// File: loader_test.go
// Purpose: Tests for parsing each of the six provided CSV layouts into the
// common Match / Player model, plus multi-format date handling.
package soccer

import (
	"strings"
	"testing"
)

func TestParseDate(t *testing.T) {
	cases := []struct {
		in    string
		ok    bool
		year  int
		month int
		day   int
	}{
		{"2012-05-19 18:30:00", true, 2012, 5, 19},
		{"2023-09-24", true, 2023, 9, 24},
		{"29/03/2003", true, 2003, 3, 29},
		{"", false, 0, 0, 0},
		{"not-a-date", false, 0, 0, 0},
	}
	for _, c := range cases {
		got, ok := parseDate(c.in)
		if ok != c.ok {
			t.Errorf("parseDate(%q) ok = %v, want %v", c.in, ok, c.ok)
			continue
		}
		if ok && (got.Year() != c.year || int(got.Month()) != c.month || got.Day() != c.day) {
			t.Errorf("parseDate(%q) = %v, want %d-%02d-%02d", c.in, got, c.year, c.month, c.day)
		}
	}
}

func TestParseBrasileirao(t *testing.T) {
	csv := `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2012-05-19 18:30:00,"Palmeiras-SP","SP","Portuguesa-SP","SP",1,1,2012,1
2012-05-20 16:00:00,"Flamengo-RJ","RJ","Santos-SP","SP",3,1,2012,1`
	matches, err := parseBrasileirao(strings.NewReader(csv))
	if err != nil {
		t.Fatal(err)
	}
	if len(matches) != 2 {
		t.Fatalf("got %d matches, want 2", len(matches))
	}
	m := matches[0]
	if m.HomeTeam != "Palmeiras" || m.AwayTeam != "Portuguesa" {
		t.Errorf("teams = %q vs %q", m.HomeTeam, m.AwayTeam)
	}
	if m.HomeGoals != 1 || m.AwayGoals != 1 || !m.HasScore {
		t.Errorf("score = %d-%d hasScore=%v", m.HomeGoals, m.AwayGoals, m.HasScore)
	}
	if m.Season != 2012 || m.Round != "1" {
		t.Errorf("season=%d round=%q", m.Season, m.Round)
	}
	// Brasileirão has no "stage" column; Stage must be empty.
	if m.Stage != "" {
		t.Errorf("stage = %q, want empty (no stage column in source)", m.Stage)
	}
	if m.Competition != CompBrasileirao {
		t.Errorf("competition = %q", m.Competition)
	}
	if !m.HasDate || m.Date.Year() != 2012 {
		t.Errorf("date not parsed: %v", m.Date)
	}
}

func TestParseCup(t *testing.T) {
	csv := `"round","datetime","home_team","away_team","home_goal","away_goal","season"
"1",2012-03-07 16:00:00,"Boavista Sport Club - RJ","América - MG",0,0,2012`
	matches, err := parseCup(strings.NewReader(csv))
	if err != nil {
		t.Fatal(err)
	}
	if len(matches) != 1 {
		t.Fatalf("got %d matches, want 1", len(matches))
	}
	m := matches[0]
	// "América - MG" canonicalizes to the well-known club name "América-MG";
	// the unknown "Boavista Sport Club - RJ" is just cleaned of its suffix.
	if m.HomeTeam != "Boavista Sport Club" || m.AwayTeam != "América-MG" {
		t.Errorf("teams = %q vs %q", m.HomeTeam, m.AwayTeam)
	}
	if m.Competition != CompCopaDoBrasil {
		t.Errorf("competition = %q", m.Competition)
	}
}

func TestParseLibertadores(t *testing.T) {
	csv := `"datetime","home_team","away_team","home_goal","away_goal","season","stage"
2013-02-12 20:15:00,"Nacional (URU)","Barcelona-EQU","2","2",2013,"group stage"`
	matches, err := parseLibertadores(strings.NewReader(csv))
	if err != nil {
		t.Fatal(err)
	}
	m := matches[0]
	if m.HomeTeam != "Nacional" || m.AwayTeam != "Barcelona" {
		t.Errorf("teams = %q vs %q", m.HomeTeam, m.AwayTeam)
	}
	if m.Stage != "group stage" {
		t.Errorf("stage = %q", m.Stage)
	}
	// Libertadores has no "round" column; Round must be empty, not the value
	// of some other (index-0) column.
	if m.Round != "" {
		t.Errorf("round = %q, want empty (no round column in source)", m.Round)
	}
	if m.Competition != CompLibertadores {
		t.Errorf("competition = %q", m.Competition)
	}
}

func TestParseBRFootball(t *testing.T) {
	csv := `tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,2.0,4.0,75.0,104.0,8.0,13.0,20:00:00,2023-09-24,0.0,0.0,DRAW,DRAW,6.0
Serie A,Palmeiras,3.0,0.0,Santos,5.0,2.0,90.0,40.0,12.0,4.0,16:00:00,2023-10-01,1.0,-1.0,WIN,LOSS,7.0`
	matches, err := parseBRFootball(strings.NewReader(csv))
	if err != nil {
		t.Fatal(err)
	}
	if len(matches) != 2 {
		t.Fatalf("got %d matches, want 2", len(matches))
	}
	m := matches[1]
	if m.HomeTeam != "Palmeiras" || m.AwayTeam != "Santos" {
		t.Errorf("teams = %q vs %q", m.HomeTeam, m.AwayTeam)
	}
	if m.HomeGoals != 3 || m.AwayGoals != 0 {
		t.Errorf("score = %d-%d", m.HomeGoals, m.AwayGoals)
	}
	// The extended dataset's "Serie A" is canonicalized to the Brasileirão so
	// it deduplicates against the dedicated Brasileirão files.
	if m.Competition != CompBrasileirao {
		t.Errorf("competition = %q, want %q", m.Competition, CompBrasileirao)
	}
	if m.Season != 2023 {
		t.Errorf("season = %d", m.Season)
	}
}

func TestParseNovo(t *testing.T) {
	csv := `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,`
	matches, err := parseNovo(strings.NewReader(csv))
	if err != nil {
		t.Fatal(err)
	}
	m := matches[0]
	if m.HomeTeam != "Guarani" || m.AwayTeam != "Vasco" {
		t.Errorf("teams = %q vs %q", m.HomeTeam, m.AwayTeam)
	}
	if m.HomeGoals != 4 || m.AwayGoals != 2 {
		t.Errorf("score = %d-%d", m.HomeGoals, m.AwayGoals)
	}
	if m.Season != 2003 || m.Competition != CompBrasileirao {
		t.Errorf("season=%d comp=%q", m.Season, m.Competition)
	}
	if m.Date.Day() != 29 || m.Date.Month() != 3 {
		t.Errorf("date = %v", m.Date)
	}
}

func TestParsePlayers(t *testing.T) {
	csv := `,ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number
0,158023,L. Messi,31,photo.png,Argentina,flag.png,94,94,FC Barcelona,logo.png,€110.5M,€565K,2202,Left,5,4,4,Medium/ Medium,Messi,Yes,RF,10
1,20801,Neymar Jr,27,photo.png,Brazil,flag.png,92,93,Paris Saint-Germain,logo.png,€118M,€290K,2143,Right,5,5,5,High/ Medium,Neymar,Yes,LW,10`
	players, err := parsePlayers(strings.NewReader(csv))
	if err != nil {
		t.Fatal(err)
	}
	if len(players) != 2 {
		t.Fatalf("got %d players, want 2", len(players))
	}
	p := players[1]
	if p.Name != "Neymar Jr" || p.Nationality != "Brazil" {
		t.Errorf("player = %q (%q)", p.Name, p.Nationality)
	}
	if p.Overall != 92 || p.Potential != 93 {
		t.Errorf("ratings = %d/%d", p.Overall, p.Potential)
	}
	if p.Club != "Paris Saint-Germain" || p.Position != "LW" {
		t.Errorf("club=%q pos=%q", p.Club, p.Position)
	}
	if p.ID != 20801 || p.Age != 27 {
		t.Errorf("id=%d age=%d", p.ID, p.Age)
	}
}
