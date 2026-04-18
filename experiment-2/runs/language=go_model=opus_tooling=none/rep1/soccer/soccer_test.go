package soccer

import (
	"os"
	"path/filepath"
	"testing"
)

func dataDir(t *testing.T) string {
	t.Helper()
	wd, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	d := filepath.Join(wd, "..", "data", "kaggle")
	if _, err := os.Stat(d); err != nil {
		t.Skipf("data dir not available: %v", err)
	}
	return d
}

var cached *DB

func loadDB(t *testing.T) *DB {
	t.Helper()
	if cached != nil {
		return cached
	}
	d, err := LoadAll(dataDir(t))
	if err != nil {
		t.Fatalf("load: %v", err)
	}
	cached = d
	return cached
}

func TestNormalizeTeam(t *testing.T) {
	cases := map[string]string{
		"Palmeiras-SP":                    "palmeiras-sp",
		"Flamengo-RJ":                     "flamengo-rj",
		"São Paulo":                       "sao paulo",
		"Grêmio":                          "gremio",
		"Nacional (URU)":                  "nacional",
		"Sport Club Corinthians Paulista": "corinthians paulista",
	}
	for in, want := range cases {
		if got := NormalizeTeam(in); got != want {
			t.Errorf("NormalizeTeam(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestParseDate(t *testing.T) {
	cases := []string{
		"2023-09-03",
		"2012-05-19 18:30:00",
		"29/03/2003",
	}
	for _, s := range cases {
		if parseDate(s).IsZero() {
			t.Errorf("parseDate(%q) returned zero", s)
		}
	}
}

func TestLoadAndCounts(t *testing.T) {
	db := loadDB(t)
	if len(db.Matches) < 20000 {
		t.Errorf("expected many matches loaded, got %d", len(db.Matches))
	}
	if len(db.Players) < 10000 {
		t.Errorf("expected many players loaded, got %d", len(db.Players))
	}
}

func TestMatchesBetween(t *testing.T) {
	db := loadDB(t)
	ms := db.MatchesBetween("Flamengo", "Fluminense")
	if len(ms) == 0 {
		t.Fatal("expected some Fla-Flu matches")
	}
	for _, m := range ms {
		ok1 := TeamMatches("Flamengo", m.HomeTeam) && TeamMatches("Fluminense", m.AwayTeam)
		ok2 := TeamMatches("Fluminense", m.HomeTeam) && TeamMatches("Flamengo", m.AwayTeam)
		if !ok1 && !ok2 {
			t.Fatalf("bad match pair: %s vs %s", m.HomeTeam, m.AwayTeam)
		}
	}
}

func TestH2H(t *testing.T) {
	db := loadDB(t)
	h := db.H2H("Palmeiras", "Santos")
	total := h.AWins + h.BWins + h.Draws
	if total == 0 || total != len(h.Matches) {
		t.Errorf("bad h2h totals: %+v", h)
	}
}

func TestTeamStats(t *testing.T) {
	db := loadDB(t)
	s := db.TeamStats("Flamengo", StatsFilter{Season: 2019, Competition: "Brasileirão"})
	if s.Matches == 0 {
		t.Fatal("expected Flamengo 2019 matches")
	}
	if s.Wins+s.Draws+s.Losses != s.Matches {
		t.Errorf("W+D+L != Matches: %+v", s)
	}
	if s.Points != 3*s.Wins+s.Draws {
		t.Errorf("points wrong: %+v", s)
	}
}

func TestStandings2019Flamengo(t *testing.T) {
	db := loadDB(t)
	table := db.Standings(2019, "Brasileirão Serie A")
	if len(table) == 0 {
		t.Fatal("empty table")
	}
	// Flamengo won the 2019 Brasileirão — top of the table.
	if !TeamMatches("Flamengo", table[0].Team) {
		t.Errorf("expected Flamengo champion 2019, got %q", table[0].Team)
	}
}

func TestAverageGoalsPerMatch(t *testing.T) {
	db := loadDB(t)
	avg := db.AverageGoalsPerMatch(0, "Brasileirão Serie A")
	if avg < 1.5 || avg > 4.0 {
		t.Errorf("implausible avg goals per match: %f", avg)
	}
}

func TestBiggestWins(t *testing.T) {
	db := loadDB(t)
	bw := db.BiggestWins(5)
	if len(bw) != 5 {
		t.Fatalf("want 5 got %d", len(bw))
	}
	for i := 1; i < len(bw); i++ {
		di := abs(bw[i-1].HomeGoal - bw[i-1].AwayGoal)
		dj := abs(bw[i].HomeGoal - bw[i].AwayGoal)
		if di < dj {
			t.Errorf("not sorted")
		}
	}
}

func TestPlayersByNationality(t *testing.T) {
	db := loadDB(t)
	brs := db.PlayersByNationality("Brazil")
	if len(brs) < 100 {
		t.Errorf("expected many Brazilian players, got %d", len(brs))
	}
}

func TestPlayersByName(t *testing.T) {
	db := loadDB(t)
	ps := db.PlayersByName("Neymar")
	if len(ps) == 0 {
		t.Fatal("expected to find Neymar")
	}
}

func TestTopPlayers(t *testing.T) {
	db := loadDB(t)
	top := db.TopPlayers(10, "Brazil", "", "")
	if len(top) != 10 {
		t.Fatalf("want 10 got %d", len(top))
	}
	for i := 1; i < len(top); i++ {
		if top[i-1].Overall < top[i].Overall {
			t.Errorf("not sorted by overall")
		}
	}
}

func TestFormatMatches(t *testing.T) {
	db := loadDB(t)
	ms := db.MatchesBetween("Flamengo", "Fluminense")
	if len(ms) == 0 {
		t.Skip("no matches")
	}
	s := FormatMatches(ms[:1])
	if len(s) == 0 {
		t.Fatal("empty format")
	}
}
