// store_test.go — BDD (Given/When/Then) scenarios for data loading,
// deduplication and team-name normalization.
package main

import (
	"sync"
	"testing"
)

var (
	testStoreOnce sync.Once
	testStore     *Store
	testStoreErr  error
)

// givenTheDataIsLoaded loads the CSV datasets once and shares the store
// across all test scenarios.
func givenTheDataIsLoaded(t *testing.T) *Store {
	t.Helper()
	testStoreOnce.Do(func() {
		testStore, testStoreErr = LoadStore("data/kaggle")
	})
	if testStoreErr != nil {
		t.Fatalf("Given the match data is loaded: %v", testStoreErr)
	}
	return testStore
}

func TestScenario_AllSixDatasetsAreLoadable(t *testing.T) {
	// Given the six Kaggle CSV files in data/kaggle
	// When the store is loaded
	s := givenTheDataIsLoaded(t)

	// Then matches from every match file are present
	bySource := map[string]int{}
	for _, m := range s.Matches {
		bySource[m.Source]++
	}
	for _, src := range []string{
		"Brasileirao_Matches.csv",
		"novo_campeonato_brasileiro.csv",
		"Brazilian_Cup_Matches.csv",
		"Libertadores_Matches.csv",
		"BR-Football-Dataset.csv",
	} {
		if bySource[src] == 0 {
			t.Errorf("expected matches loaded from %s, got none", src)
		}
	}
	// And the FIFA player file is loaded
	if len(s.Players) < 18000 {
		t.Errorf("expected ~18207 players, got %d", len(s.Players))
	}
	if len(s.Matches) < 10000 {
		t.Errorf("expected >10000 deduplicated matches, got %d", len(s.Matches))
	}
	t.Logf("loaded %d matches (%v) and %d players", len(s.Matches), bySource, len(s.Players))
}

func TestScenario_TeamNameVariationsNormalizeToTheSameKey(t *testing.T) {
	// Given team names as spelled in the different datasets
	// When each is normalized
	// Then variations of the same club share one key
	same := [][]string{
		{"Palmeiras-SP", "Palmeiras", "palmeiras"},
		{"Flamengo-RJ", "Flamengo", "FLAMENGO"},
		{"Sao Paulo-SP", "São Paulo", "Sao Paulo"},
		{"Gremio-RS", "Grêmio", "Gremio"},
		{"Vasco da Gama-RJ", "Vasco", "vasco da gama"},
		{"Athletico Paranaense - PR", "Atletico-PR", "Athletico-PR", "Athletico Paranaense"},
		{"Atletico-MG", "Atlético-MG", "Atletico Mineiro"},
		{"Avai-SC", "Avaí"},
		{"Ceara-CE", "Ceará"},
		{"Red Bull Bragantino-SP", "Bragantino"},
		{"America - MG", "América-MG", "America MG"},
	}
	for _, group := range same {
		want := teamKey(group[0])
		for _, name := range group[1:] {
			if got := teamKey(name); got != want {
				t.Errorf("teamKey(%q) = %q, want %q (same as %q)", name, got, want, group[0])
			}
		}
	}
}

func TestScenario_AmbiguousClubsStayDistinct(t *testing.T) {
	// Given clubs that share a base name but are different teams
	// When their names are normalized
	// Then they do NOT collide
	distinct := [][2]string{
		{"Atlético-MG", "Atlético-GO"},
		{"Atlético-MG", "Athletico-PR"},
		{"América-MG", "América-RN"},
		{"Botafogo-RJ", "Botafogo PB"},
		{"Botafogo-RJ", "Botafogo SP"},
		{"Grêmio", "Grêmio Prudente"},
	}
	for _, pair := range distinct {
		if k1, k2 := teamKey(pair[0]), teamKey(pair[1]); k1 == k2 {
			t.Errorf("teamKey(%q) == teamKey(%q) == %q; want distinct keys", pair[0], pair[1], k1)
		}
	}
}

func TestScenario_UTF8AccentsAreHandled(t *testing.T) {
	// Given Brazilian Portuguese names with accents and cedillas
	cases := map[string]string{
		"São Paulo":               "sao paulo",
		"Grêmio":                  "gremio",
		"Avaí":                    "avai",
		"Fortaleza Esporte Clube": "fortaleza esporte clube",
		"Criciúma":                "criciuma",
		"Goiás":                   "goias",
	}
	// When normalized / Then accents are transliterated
	for in, want := range cases {
		if got := normalizeText(in); got != want {
			t.Errorf("normalizeText(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestScenario_MultipleDateFormatsAreParsed(t *testing.T) {
	// Given the three date formats used across the datasets
	cases := map[string]string{
		"2023-09-24":          "2023-09-24",
		"29/03/2003":          "2003-03-29",
		"2012-05-19 18:30:00": "2012-05-19",
	}
	// When parsed / Then all succeed
	for in, want := range cases {
		d, ok := parseDate(in)
		if !ok {
			t.Errorf("parseDate(%q) failed", in)
			continue
		}
		if got := d.Format("2006-01-02"); got != want {
			t.Errorf("parseDate(%q) = %s, want %s", in, got, want)
		}
	}
}

func TestScenario_OverlappingSerieASeasonsAreDeduplicated(t *testing.T) {
	// Given Série A 2012-2019 appears in Brasileirao_Matches.csv,
	// novo_campeonato_brasileiro.csv and BR-Football-Dataset.csv
	s := givenTheDataIsLoaded(t)

	// When counting Série A matches per overlapping season
	// Then each season has at most 380 matches (20 teams, double round-robin)
	for season := 2012; season <= 2019; season++ {
		n := 0
		for _, m := range s.Matches {
			if m.Competition == CompSerieA && m.Season == season {
				n++
			}
		}
		if n > 380 {
			t.Errorf("season %d: %d Série A matches after dedup, want <= 380", season, n)
		}
		if n < 370 {
			t.Errorf("season %d: only %d Série A matches, expected a full season (~380)", season, n)
		}
	}
}

func TestScenario_ExtendedStatsAreMergedIntoDeduplicatedMatches(t *testing.T) {
	// Given BR-Football-Dataset.csv carries shots/corners for matches that
	// also exist in other files
	s := givenTheDataIsLoaded(t)

	// Then at least some stored matches expose extended stats
	n := 0
	for _, m := range s.Matches {
		if m.HasStats() {
			n++
		}
	}
	if n == 0 {
		t.Error("expected some matches with extended stats (shots/corners), got none")
	}
}
