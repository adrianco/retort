package soccer

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// loadReal loads the bundled Kaggle datasets, skipping the test if they are not
// present (so unit tests still run in a trimmed checkout).
func loadReal(t *testing.T) *Store {
	t.Helper()
	dir := filepath.Join("..", "data", "kaggle")
	if _, err := os.Stat(filepath.Join(dir, "Brasileirao_Matches.csv")); err != nil {
		t.Skipf("datasets not available at %s: %v", dir, err)
	}
	store, rep, err := LoadAll(dir)
	if err != nil {
		t.Fatalf("LoadAll: %v", err)
	}
	if len(rep.Missing) != 0 {
		t.Fatalf("missing datasets: %v", rep.Missing)
	}
	if len(rep.Files) != 6 {
		t.Fatalf("want 6 files loaded, got %d", len(rep.Files))
	}
	return store
}

func TestLoadAllCoverage(t *testing.T) {
	store := loadReal(t)
	if len(store.Matches) < 15000 {
		t.Errorf("expected many matches, got %d", len(store.Matches))
	}
	if len(store.Players) != 18207 {
		t.Errorf("expected 18207 players, got %d", len(store.Players))
	}
	// All five canonical competitions should be present.
	want := []string{CompSerieA, CompSerieB, CompSerieC, CompCopaBrasil, CompLibertadores}
	have := map[string]bool{}
	for _, c := range store.Competitions() {
		have[c] = true
	}
	for _, c := range want {
		if !have[c] {
			t.Errorf("competition %q missing", c)
		}
	}
}

// Test2019Champion validates the full standings pipeline against a known result:
// Flamengo won the 2019 Brasileirão with 90 points (28W 6D 4L), matching the
// spec's worked example.
func Test2019Champion(t *testing.T) {
	store := loadReal(t)
	matches := store.FindMatchesClean(MatchFilter{Competition: CompSerieA, Season: 2019})
	if len(matches) != 380 {
		t.Fatalf("2019 Série A should have 380 matches, got %d", len(matches))
	}
	table := Standings(matches, store.Display)
	champ := table[0]
	if !strings.Contains(champ.Team, "Flamengo") {
		t.Errorf("2019 champion = %q, want Flamengo", champ.Team)
	}
	if champ.Points() != 90 || champ.Wins != 28 || champ.Draws != 6 || champ.Losses != 4 {
		t.Errorf("2019 champion record = %d pts (%dW %dD %dL), want 90 (28W 6D 4L)",
			champ.Points(), champ.Wins, champ.Draws, champ.Losses)
	}
}

func TestStandingsQueryOutput(t *testing.T) {
	store := loadReal(t)
	out := store.StandingsQuery("Brasileirão", 2019, 5)
	for _, want := range []string{"Flamengo", "90 pts", "Champion"} {
		if !strings.Contains(out, want) {
			t.Errorf("standings output missing %q:\n%s", want, out)
		}
	}
}

func TestHeadToHeadFlaFlu(t *testing.T) {
	store := loadReal(t)
	out := store.HeadToHeadQuery("Flamengo", "Fluminense", "", 0, 3)
	if !strings.Contains(out, "Flamengo") || !strings.Contains(out, "Fluminense") {
		t.Errorf("Fla-Flu output unexpected:\n%s", out)
	}
	if !strings.Contains(out, "Matches:") {
		t.Errorf("missing match count:\n%s", out)
	}
}

func TestTeamRecordQueryReal(t *testing.T) {
	store := loadReal(t)
	out := store.TeamRecordQuery("Corinthians", "Brasileirão", 2019, VenueHome)
	if !strings.Contains(out, "Corinthians") || !strings.Contains(out, "home") {
		t.Errorf("team record output unexpected:\n%s", out)
	}
}

func TestPlayerQueriesReal(t *testing.T) {
	store := loadReal(t)

	br := store.FindPlayers(PlayerFilter{NationKey: NormalizeName("Brazil")})
	if len(br) < 500 {
		t.Errorf("expected many Brazilian players, got %d", len(br))
	}
	if br[0].Overall < 80 {
		t.Errorf("top Brazilian should be highly rated, got %+v", br[0])
	}

	info := store.PlayerInfoQuery("Neymar")
	if !strings.Contains(info, "Neymar") || !strings.Contains(info, "Brazil") {
		t.Errorf("Neymar lookup unexpected:\n%s", info)
	}

	// Exact club match must not leak Santos Laguna into the Santos squad.
	squad := store.ClubPlayersQuery("Santos", 50)
	if strings.Contains(squad, "Laguna") {
		t.Errorf("Santos squad leaked Santos Laguna:\n%s", squad)
	}
}

func TestCompetitionStatsReal(t *testing.T) {
	store := loadReal(t)
	out := store.CompetitionStatsQuery("Brasileirão", 2019)
	if !strings.Contains(out, "Average goals per match") {
		t.Errorf("stats output unexpected:\n%s", out)
	}
}

func TestPalmeirasCompetitions(t *testing.T) {
	store := loadReal(t)
	out := store.TeamCompetitionsQuery("Palmeiras")
	for _, want := range []string{CompSerieA, CompCopaBrasil, CompLibertadores} {
		if !strings.Contains(out, want) {
			t.Errorf("Palmeiras competitions missing %q:\n%s", want, out)
		}
	}
}
