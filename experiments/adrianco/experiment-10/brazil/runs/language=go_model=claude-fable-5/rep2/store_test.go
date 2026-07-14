// store_test.go - BDD (Given/When/Then) tests for data loading and
// normalization in the Brazilian Soccer MCP server.
//
// Context: Verifies that all six Kaggle CSV files load, that team-name
// variations ("Palmeiras-SP", "Botafogo RJ", "Atlético Mineiro") normalize
// to consistent keys, that multiple date formats parse, and that
// cross-dataset deduplication yields exactly one record per real match.
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

// sharedStore loads the datasets once for the whole test binary.
func sharedStore(t *testing.T) *Store {
	t.Helper()
	testStoreOnce.Do(func() {
		testStore, testStoreErr = LoadStore("data/kaggle")
	})
	if testStoreErr != nil {
		t.Fatalf("loading store: %v", testStoreErr)
	}
	return testStore
}

func TestDataLoading(t *testing.T) {
	// Scenario: All six CSV files are loadable and queryable.
	// Given the data directory data/kaggle
	// When the store is loaded
	s := sharedStore(t)

	// Then matches from every match dataset are present
	bySource := map[string]int{}
	for _, m := range s.Matches {
		bySource[m.Source]++
	}
	for _, src := range []string{SrcSerieA, SrcSerieAHist, SrcCopaDoBrasil, SrcLibertadores, SrcExtended} {
		if bySource[src] == 0 {
			t.Errorf("no matches loaded from source %s", src)
		}
	}
	// And the total reflects all datasets minus cross-dataset duplicates
	if len(s.Matches) < 15000 {
		t.Errorf("expected >15000 deduplicated matches, got %d", len(s.Matches))
	}
	// And the full FIFA player database is loaded
	if len(s.Players) != 18207 {
		t.Errorf("expected 18207 players, got %d", len(s.Players))
	}
}

func TestTeamNameNormalization(t *testing.T) {
	// Scenario: Team name variations normalize to a consistent key.
	cases := []struct {
		raw, state string
		wantBase   string
		wantState  string
	}{
		// Given names with state suffixes, official long forms and accents
		{"Palmeiras-SP", "SP", "palmeiras", "sp"},
		{"Palmeiras", "", "palmeiras", ""},
		{"São Paulo-SP", "", "sao paulo", "sp"},
		{"Sao Paulo", "", "sao paulo", ""},
		{"Grêmio", "", "gremio", ""},
		{"Athletico-PR", "", "atletico", "pr"},
		{"Atletico Paranaense", "", "atletico", "pr"},
		{"Atletico Mineiro", "", "atletico", "mg"},
		{"Atlético-MG", "MG", "atletico", "mg"},
		{"Botafogo RJ", "", "botafogo", "rj"},
		{"América - MG", "", "america", "mg"},
		{"Vasco da Gama RJ", "", "vasco", "rj"},
		{"Vasco", "", "vasco", ""},
		{"EC Bahia", "", "bahia", ""},
		{"Sport Recife", "", "sport", "pe"},
		{"Red Bull Bragantino", "", "bragantino", "sp"},
		{"Fortaleza FC", "", "fortaleza", ""},
		{"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "", "boavista sport club", "rj"},
		{"Barcelona-EQU", "", "barcelona", ""},
	}
	for _, c := range cases {
		// When the name is parsed
		got := parseTeam(c.raw, c.state)
		// Then the normalized base and state are as expected
		if got.Base != c.wantBase || got.State != c.wantState {
			t.Errorf("parseTeam(%q,%q) = base %q state %q, want %q %q",
				c.raw, c.state, got.Base, got.State, c.wantBase, c.wantState)
		}
	}
}

func TestTeamQueryMatching(t *testing.T) {
	// Scenario: User queries match team-name variations.
	cases := []struct {
		teamRaw, query string
		want           bool
	}{
		// Given a stored team and a user's spelling of it
		{"Palmeiras-SP", "Palmeiras", true},
		{"Sport Club Corinthians Paulista", "Corinthians", true},
		{"São Paulo-SP", "Sao Paulo", true},
		{"Athletico-PR", "Atletico Paranaense", true},
		{"Atlético-MG", "Atletico Mineiro", true},
		{"Atlético-MG", "Atletico Paranaense", false}, // different state
		{"Flamengo-RJ", "Fluminense", false},
		{"Vasco da Gama", "Vasco", true},
	}
	for _, c := range cases {
		// When the query is compared against the team
		got := teamQueryMatches(parseTeam(c.teamRaw, ""), parseTeam(c.query, ""))
		// Then matching respects variations and state disambiguation
		if got != c.want {
			t.Errorf("teamQueryMatches(%q, %q) = %v, want %v", c.teamRaw, c.query, got, c.want)
		}
	}
}

func TestDateFormatParsing(t *testing.T) {
	// Scenario: All date formats present in the datasets parse correctly.
	cases := []struct {
		in   string
		want string
	}{
		// Given ISO, Brazilian, and datetime formats
		{"2023-09-24", "2023-09-24"},
		{"29/03/2003", "2003-03-29"},
		{"2012-05-19 18:30:00", "2012-05-19"},
	}
	for _, c := range cases {
		// When parsed
		d, ok := parseDate(c.in)
		// Then the calendar day is correct
		if !ok || d.Format("2006-01-02") != c.want {
			t.Errorf("parseDate(%q) = %v ok=%v, want %s", c.in, d, ok, c.want)
		}
	}
}

func TestCrossDatasetDeduplication(t *testing.T) {
	// Scenario: The 2019 Brasileirão appears in three datasets but each real
	// match must be stored exactly once.
	// Given the loaded store
	s := sharedStore(t)
	// When counting 2019 Série A matches
	n := 0
	for _, m := range s.Matches {
		if m.Season == 2019 && m.Competition == CompSerieA {
			n++
		}
	}
	// Then exactly the 380 real matches of a 20-team double round-robin remain
	if n != 380 {
		t.Errorf("2019 Brasileirão: got %d matches after dedup, want 380", n)
	}
}

func TestUTF8Handling(t *testing.T) {
	// Scenario: Brazilian Portuguese characters are preserved in display names.
	// Given the loaded store
	s := sharedStore(t)
	// When searching for matches of Grêmio using the accented spelling
	matches := s.FilterMatches(MatchFilter{Team: "Grêmio", Season: 2019, Competition: "Brasileirão"})
	// Then matches are found (accent-insensitive matching)
	if len(matches) != 38 {
		t.Errorf("Grêmio 2019 Brasileirão: got %d matches, want 38", len(matches))
	}
}
