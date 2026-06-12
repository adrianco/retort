package soccer

import (
	"os"
	"path/filepath"
	"testing"
)

// writeFixture creates a small, deterministic dataset in a temp dir and loads
// it. It deliberately includes the same Série A 2019 fixtures in two sources
// (with different name spellings) to exercise cross-source coverage selection.
func writeFixture(t *testing.T) *DB {
	t.Helper()
	dir := t.TempDir()

	files := map[string]string{
		// Série A 2019 — authoritative source (priority 0).
		"novo_campeonato_brasileiro.csv": `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2019.01,01/05/2019,2019,1,Flamengo,Vasco,3,0,RJ,RJ,Mandante,Maracanã,
2019.02,02/05/2019,2019,1,Palmeiras,Santos,1,1,SP,SP,Empate,Allianz,
2019.03,08/05/2019,2019,2,Vasco,Flamengo,1,2,RJ,RJ,Visitante,São Januário,
`,
		// Série A — same 2019 fixtures (duplicate, with -RJ/-SP suffixes) plus a
		// 2020 fixture the authoritative source does not cover (priority 1).
		"Brasileirao_Matches.csv": `datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round
2019-05-01 16:00:00,Flamengo-RJ,RJ,Vasco-RJ,RJ,3,0,2019,1
2019-05-02 16:00:00,Palmeiras-SP,SP,Santos-SP,SP,1,1,2019,1
2020-08-15 16:00:00,Flamengo-RJ,RJ,Palmeiras-SP,SP,2,1,2020,1
`,
		"Libertadores_Matches.csv": `datetime,home_team,away_team,home_goal,away_goal,season,stage
2019-11-23 17:00:00,Flamengo,River Plate (ARG),2,1,2019,final
`,
		"Brazilian_Cup_Matches.csv": `round,datetime,home_team,away_team,home_goal,away_goal,season
final,2019-09-18 21:30:00,Athletico - PR,Internacional - RS,1,0,2019
`,
		// Broad fallback (priority 5): a Série B fixture only this file has, plus
		// a duplicate of the Série A 2019 final-round game (must be dropped).
		"BR-Football-Dataset.csv": `tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
Serie B,Guarani,2.0,0.0,Cruzeiro,5.0,3.0,80.0,60.0,12.0,7.0,16:00:00,2019-06-01,0,0,WIN,LOSS,8.0
Serie A,Vasco,1.0,2.0,Flamengo,4.0,6.0,70.0,90.0,9.0,14.0,18:00:00,2019-05-08,0,0,LOSS,WIN,10.0
`,
		// Minimal FIFA player rows (only the columns the loader reads).
		"fifa_data.csv": `ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Height,Weight,Preferred Foot
1,Neymar Jr,27,Brazil,92,93,Paris Saint-Germain,LW,10,5'9,150lbs,Right
2,Gabriel Jesus,22,Brazil,83,90,Manchester City,ST,33,5'9,161lbs,Right
3,L. Messi,32,Argentina,94,94,FC Barcelona,RW,10,5'7,159lbs,Left
4,Bruno,28,Brazil,75,76,Santos,GK,1,6'3,180lbs,Right
`,
	}
	for name, content := range files {
		if err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0o644); err != nil {
			t.Fatalf("writing %s: %v", name, err)
		}
	}

	db, err := Load(dir)
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	return db
}

func TestLoadCounts(t *testing.T) {
	db := writeFixture(t)
	if len(db.Players) != 4 {
		t.Errorf("players = %d, want 4", len(db.Players))
	}
	// Competitions present: Série A, Série B, Libertadores, Copa do Brasil.
	comps := db.Competitions()
	if len(comps) != 4 {
		t.Errorf("competitions = %v, want 4", comps)
	}
}

func TestCoverageDeduplication(t *testing.T) {
	db := writeFixture(t)

	// Série A 2019 must come solely from the authoritative source: 3 matches,
	// not 3+2 (Brasileirao file) +1 (BR-Football). The 2020 fixture (only in
	// the Brasileirao file) is additionally kept.
	var seriesA2019, seriesA2020 int
	for _, m := range db.Matches {
		if m.Competition == CompBrasileiraoA && m.Season == 2019 {
			seriesA2019++
		}
		if m.Competition == CompBrasileiraoA && m.Season == 2020 {
			seriesA2020++
		}
	}
	if seriesA2019 != 3 {
		t.Errorf("Série A 2019 matches = %d, want 3 (no cross-source duplicates)", seriesA2019)
	}
	if seriesA2020 != 1 {
		t.Errorf("Série A 2020 matches = %d, want 1", seriesA2020)
	}

	// The Série B fixture (only in BR-Football) must survive.
	var seriesB int
	for _, m := range db.Matches {
		if m.Competition == CompBrasileiraoB {
			seriesB++
		}
	}
	if seriesB != 1 {
		t.Errorf("Série B matches = %d, want 1", seriesB)
	}
}

func TestStandings(t *testing.T) {
	db := writeFixture(t)
	table := db.Standings(CompBrasileiraoA, 2019)
	if len(table) == 0 {
		t.Fatal("empty standings")
	}
	// Flamengo: beat Vasco 3-0 (home) and 2-1 (away) => 2 wins, 6 pts, top.
	top := table[0]
	if top.Team != "Flamengo" {
		t.Errorf("leader = %q, want Flamengo", top.Team)
	}
	if top.Points() != 6 || top.Wins != 2 {
		t.Errorf("Flamengo: %d pts %dW, want 6 pts 2W", top.Points(), top.Wins)
	}
}

func TestHeadToHead(t *testing.T) {
	db := writeFixture(t)
	h := db.HeadToHead("Flamengo", "Vasco")
	if got := h.AWins + h.BWins + h.Draws; got != 2 {
		t.Fatalf("Flamengo-Vasco played = %d, want 2", got)
	}
	if h.AWins != 2 || h.BWins != 0 {
		t.Errorf("Flamengo %dW Vasco %dW, want 2-0", h.AWins, h.BWins)
	}
	if h.AGoals != 5 || h.BGoals != 1 {
		t.Errorf("goals Flamengo %d Vasco %d, want 5-1", h.AGoals, h.BGoals)
	}
}

func TestTeamRecordHomeOnly(t *testing.T) {
	db := writeFixture(t)
	// Flamengo home in 2019 Série A: only the 3-0 vs Vasco (Libertadores final
	// excluded by competition filter).
	rec := db.TeamRecord(MatchFilter{Team: "Flamengo", Season: 2019, Competition: "Brasileirão", HomeOnly: true})
	if rec.Played != 1 || rec.Wins != 1 || rec.GoalsFor != 3 {
		t.Errorf("Flamengo 2019 home: played=%d wins=%d GF=%d, want 1/1/3", rec.Played, rec.Wins, rec.GoalsFor)
	}
}

func TestSearchPlayers(t *testing.T) {
	db := writeFixture(t)

	brazilians := db.SearchPlayers(PlayerFilter{Nationality: "Brazil"})
	if len(brazilians) != 3 {
		t.Errorf("Brazilian players = %d, want 3", len(brazilians))
	}
	if brazilians[0].Name != "Neymar Jr" {
		t.Errorf("top Brazilian = %q, want Neymar Jr (sorted by Overall)", brazilians[0].Name)
	}

	// Club filter + position.
	gk := db.SearchPlayers(PlayerFilter{Club: "Santos", Position: "GK"})
	if len(gk) != 1 || gk[0].Name != "Bruno" {
		t.Errorf("Santos GK search = %+v, want single 'Bruno'", gk)
	}

	highRated := db.SearchPlayers(PlayerFilter{MinOverall: 90})
	if len(highRated) != 2 { // Messi 94, Neymar 92
		t.Errorf("players >=90 = %d, want 2", len(highRated))
	}
}

func TestCompetitionStats(t *testing.T) {
	db := writeFixture(t)
	s := db.CompetitionStats(CompBrasileiraoA, 2019, 5)
	// 3 matches: 3-0, 1-1, 1-2 => goals 3+2+3 = 8.
	if s.Matches != 3 || s.TotalGoals != 8 {
		t.Errorf("stats: matches=%d goals=%d, want 3/8", s.Matches, s.TotalGoals)
	}
	if got := s.AvgGoals(); got < 2.66 || got > 2.67 {
		t.Errorf("avg goals = %.3f, want ~2.667", got)
	}
	// Biggest win first should be the 3-0.
	if len(s.BiggestWins) == 0 || absInt(s.BiggestWins[0].HomeGoals-s.BiggestWins[0].AwayGoals) != 3 {
		t.Errorf("biggest win margin not 3: %+v", s.BiggestWins)
	}
}

func TestDateAndGoalParsing(t *testing.T) {
	if _, ok := parseDate("29/03/2003"); !ok {
		t.Error("failed to parse DD/MM/YYYY")
	}
	if _, ok := parseDate("2012-05-19 18:30:00"); !ok {
		t.Error("failed to parse datetime")
	}
	if _, ok := parseDate(""); ok {
		t.Error("empty date should fail")
	}
	if g, ok := parseGoals("2.0"); !ok || g != 2 {
		t.Errorf("parseGoals(2.0) = %d,%v want 2,true", g, ok)
	}
	if _, ok := parseGoals(""); ok {
		t.Error("empty goals should report not-present")
	}
}
