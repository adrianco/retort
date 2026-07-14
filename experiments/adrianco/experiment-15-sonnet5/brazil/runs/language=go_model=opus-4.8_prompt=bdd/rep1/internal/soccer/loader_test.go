package soccer

import (
	"strings"
	"testing"
)

// Behaviour: each source CSV is parsed into normalised Match/Player values,
// tolerating the format quirks (float goals, DD/MM/YYYY dates, BOM headers).

func Test_given_brasileirao_csv_when_loaded_then_match_is_parsed(t *testing.T) {
	// Given one Brasileirão row
	csv := `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2019-04-27 21:00:00,"Flamengo-RJ","RJ","Cruzeiro-MG","MG",3,1,2019,1`
	// When it is loaded
	got, err := loadSimpleMatches(strings.NewReader(csv), CompBrasileirao, FileBrasileirao)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// Then one match with the expected fields is produced
	if len(got) != 1 {
		t.Fatalf("expected 1 match, got %d", len(got))
	}
	m := got[0]
	if m.HomeTeam != "Flamengo" || m.AwayTeam != "Cruzeiro" {
		t.Errorf("unexpected teams: %q vs %q", m.HomeTeam, m.AwayTeam)
	}
	if m.HomeGoals != 3 || m.AwayGoals != 1 {
		t.Errorf("unexpected score: %d-%d", m.HomeGoals, m.AwayGoals)
	}
	if m.Season != 2019 {
		t.Errorf("unexpected season: %d", m.Season)
	}
	if m.Date.Format("2006-01-02") != "2019-04-27" {
		t.Errorf("unexpected date: %v", m.Date)
	}
}

func Test_given_br_football_float_goals_when_loaded_then_goals_are_rounded_ints(t *testing.T) {
	// Given a BR-Football row whose goals are floats
	csv := `tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_shots,away_shots,date
Serie A,Santos,4.0,0.0,Flamengo,3.0,5.0,23.0,5.0,2019-12-08`
	// When it is loaded
	got, err := loadBRFootball(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// Then the float goals become integers and the competition is canonicalised
	if len(got) != 1 {
		t.Fatalf("expected 1 match, got %d", len(got))
	}
	m := got[0]
	if m.HomeGoals != 4 || m.AwayGoals != 0 {
		t.Errorf("expected 4-0, got %d-%d", m.HomeGoals, m.AwayGoals)
	}
	if m.Competition != CompBrasileirao {
		t.Errorf("expected Serie A mapped to %q, got %q", CompBrasileirao, m.Competition)
	}
	if m.HomeShots != 23 {
		t.Errorf("expected extended stat home_shots=23, got %d", m.HomeShots)
	}
}

func Test_given_novo_brazilian_date_when_loaded_then_date_is_parsed(t *testing.T) {
	// Given a historical row with a DD/MM/YYYY date and Portuguese columns
	csv := `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,`
	// When it is loaded
	got, err := loadNovoBR(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// Then the Brazilian-format date is parsed correctly
	if len(got) != 1 {
		t.Fatalf("expected 1 match, got %d", len(got))
	}
	if got[0].Date.Format("2006-01-02") != "2003-03-29" {
		t.Errorf("expected 2003-03-29, got %v", got[0].Date)
	}
}

func Test_given_fifa_csv_with_bom_when_loaded_then_player_is_parsed(t *testing.T) {
	// Given a FIFA row whose header carries a UTF-8 BOM
	csv := "\uFEFF,ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Height,Weight\n" +
		"0,158023,L. Messi,31,Argentina,94,94,FC Barcelona,RF,10,5'7,159lbs"
	// When it is loaded
	got, err := loadPlayers(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// Then the BOM is ignored and the player fields are populated
	if len(got) != 1 {
		t.Fatalf("expected 1 player, got %d", len(got))
	}
	p := got[0]
	if p.Name != "L. Messi" || p.Overall != 94 || p.Nationality != "Argentina" {
		t.Errorf("unexpected player: %+v", p)
	}
}

func Test_given_blank_goal_when_parsed_then_marked_unknown(t *testing.T) {
	// Given a blank goal cell
	// When parsed
	// Then it is reported as -1 (unknown) rather than 0
	if got := parseGoals("  "); got != -1 {
		t.Fatalf("expected -1 for blank goals, got %d", got)
	}
}
