package soccer

import "testing"

// Behaviour: team-name normalisation collapses spelling variants of the same
// club to one key, while keeping genuinely different clubs apart.

func Test_given_state_suffix_when_normalized_then_matches_bare_name(t *testing.T) {
	// Given two spellings of the same club (with and without a state suffix)
	// When each is normalised
	// Then they produce the same matching key
	if got, want := NormalizeTeam("Palmeiras-SP"), NormalizeTeam("Palmeiras"); got != want {
		t.Fatalf("expected same key, got %q and %q", got, want)
	}
}

func Test_given_accented_name_when_normalized_then_matches_unaccented(t *testing.T) {
	// Given "São Paulo" and "Sao Paulo-SP"
	// When normalised
	// Then accents are folded and keys match
	if got, want := NormalizeTeam("São Paulo"), NormalizeTeam("Sao Paulo-SP"); got != want {
		t.Fatalf("expected accent-folded match, got %q and %q", got, want)
	}
}

func Test_given_two_atleticos_when_normalized_then_keys_differ(t *testing.T) {
	// Given Atlético Mineiro and Atlético Paranaense, which share a base name
	// When normalised
	// Then they resolve to different canonical keys (not merged)
	mg := NormalizeTeam("Atletico-MG")
	pr := NormalizeTeam("Atletico-PR")
	if mg == pr {
		t.Fatalf("expected distinct keys for Mineiro and Paranaense, both were %q", mg)
	}
}

func Test_given_full_and_suffixed_atletico_when_normalized_then_keys_match(t *testing.T) {
	// Given "Atletico-MG" (league file) and "Atletico Mineiro" (stats file)
	// When normalised
	// Then both resolve to the same canonical Mineiro key
	if got, want := NormalizeTeam("Atletico-MG"), NormalizeTeam("Atletico Mineiro"); got != want {
		t.Fatalf("expected same Mineiro key, got %q and %q", got, want)
	}
}

func Test_given_athletico_spellings_when_normalized_then_keys_match(t *testing.T) {
	// Given "Athletico-PR", "Atletico-PR" and "Atletico Paranaense"
	// When normalised
	// Then all three unify to one Paranaense key
	a := NormalizeTeam("Athletico-PR")
	b := NormalizeTeam("Atletico-PR")
	c := NormalizeTeam("Atletico Paranaense")
	if a != b || b != c {
		t.Fatalf("expected all Paranaense spellings equal, got %q %q %q", a, b, c)
	}
}

func Test_given_vasco_variants_when_normalized_then_keys_match(t *testing.T) {
	// Given "Vasco", "Vasco da Gama-RJ" and "Vasco Da Gama RJ"
	// When normalised
	// Then all unify
	a := NormalizeTeam("Vasco")
	b := NormalizeTeam("Vasco da Gama-RJ")
	c := NormalizeTeam("Vasco Da Gama RJ")
	if a != b || b != c {
		t.Fatalf("expected Vasco variants equal, got %q %q %q", a, b, c)
	}
}

func Test_given_club_type_prefix_when_normalized_then_matches_plain(t *testing.T) {
	// Given "EC Bahia" (stats file) and "Bahia-BA" (league file)
	// When normalised
	// Then the club-type prefix is ignored and keys match
	if got, want := NormalizeTeam("EC Bahia"), NormalizeTeam("Bahia-BA"); got != want {
		t.Fatalf("expected Bahia match, got %q and %q", got, want)
	}
}

func Test_given_country_code_when_cleaned_then_suffix_removed(t *testing.T) {
	// Given a Libertadores team "Nacional (URU)"
	// When cleaned for display
	// Then the country code is stripped
	if got, want := CleanTeam("Nacional (URU)"), "Nacional"; got != want {
		t.Fatalf("expected %q, got %q", want, got)
	}
}

func Test_given_empty_name_when_normalized_then_empty_key(t *testing.T) {
	// Given a blank team name
	// When normalised
	// Then the key is empty
	if got := NormalizeTeam("   "); got != "" {
		t.Fatalf("expected empty key, got %q", got)
	}
}
