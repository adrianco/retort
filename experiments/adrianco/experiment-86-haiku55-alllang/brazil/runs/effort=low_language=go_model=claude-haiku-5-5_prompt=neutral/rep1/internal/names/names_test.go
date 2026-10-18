package names

import "testing"

// Scenario: club names in every dataset format normalize to one comparable key.
func TestParse(t *testing.T) {
	tests := []struct {
		name        string
		raw         string
		wantDisplay string
		wantBase    string
		wantState   string
	}{
		{"state suffix", "Palmeiras-SP", "Palmeiras", "palmeiras", "SP"},
		{"bare name", "Palmeiras", "Palmeiras", "palmeiras", ""},
		{"country code in parentheses", "Nacional (URU)", "Nacional", "nacional", "URU"},
		{"full official name", "Sport Club Corinthians Paulista", "Sport Club Corinthians Paulista", "corinthians", ""},
		{"full name with state", "Sociedade Esportiva Palmeiras-SP", "Sociedade Esportiva Palmeiras", "palmeiras", "SP"},
		{"antigo note with state", "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "Boavista Sport Club", "boavista sport club", "RJ"},
		{"accented name", "Grêmio-RS", "Grêmio", "gremio", "RS"},
		{"accented cedilla", "Avaí-SC", "Avaí", "avai", "SC"},
		{"athletico alias", "Atlético-PR", "Atlético", "athletico", "PR"},
		{"atletico minas", "Atlético-MG", "Atlético", "atletico", "MG"},
		{"surrounding whitespace", "  Flamengo - RJ ", "Flamengo", "flamengo", "RJ"},
		{"space before state code", "Vasco Da Gama RJ", "Vasco Da Gama", "vasco", "RJ"},
		{"space before state code, hyphen-less", "Botafogo RJ", "Botafogo", "botafogo", "RJ"},
		{"leading club abbreviation", "EC Bahia", "EC Bahia", "bahia", ""},
		{"trailing club abbreviation", "Fortaleza FC", "Fortaleza FC", "fortaleza", ""},
		{"all-caps name is not a state", "CSA", "CSA", "csa", ""},
		{"alias after noise removal", "Atletico Mineiro", "Atletico Mineiro", "atletico", ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Given a raw club name from a dataset
			// When it is parsed
			got := Parse(tt.raw)
			// Then the display, base key and state are normalized
			if got.Display != tt.wantDisplay || got.Base != tt.wantBase || got.State != tt.wantState {
				t.Fatalf("Parse(%q) = %+v, want display=%q base=%q state=%q",
					tt.raw, got, tt.wantDisplay, tt.wantBase, tt.wantState)
			}
		})
	}
}

// Scenario: variant spellings of one club match, different clubs do not.
func TestMatches(t *testing.T) {
	tests := []struct {
		name string
		a, b string
		want bool
	}{
		{"suffix vs bare", "Palmeiras-SP", "Palmeiras", true},
		{"full name vs short", "Sport Club Corinthians Paulista", "Corinthians-SP", true},
		{"accent insensitive", "Sao Paulo", "São Paulo-SP", true},
		{"different states, same base", "Atlético-MG", "Atlético-PR", false},
		{"same state, same base", "Atlético-MG", "Atlético-MG", true},
		{"country code differs from state", "Nacional (URU)", "Nacional-RS", false},
		{"different clubs", "Flamengo-RJ", "Fluminense-RJ", false},
		{"Vasco spellings", "Vasco", "Vasco Da Gama RJ", true},
		{"Bahia spellings", "Bahia", "EC Bahia", true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Given two club names written in different styles
			// When they are compared
			got := Parse(tt.a).Matches(Parse(tt.b))
			// Then they match only when they refer to the same club
			if got != tt.want {
				t.Fatalf("Matches(%q, %q) = %v, want %v", tt.a, tt.b, got, tt.want)
			}
		})
	}
}

func TestFold(t *testing.T) {
	// Given mixed-case accented text
	// When it is folded
	// Then the result is lowercase, accent-free and single-spaced
	if got := Fold("  São  PAULO Avaí "); got != "sao paulo avai" {
		t.Fatalf("Fold = %q", got)
	}
}
