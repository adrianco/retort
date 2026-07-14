package main

import "testing"

func Test_GivenStateSuffixedTeamName_WhenNormalizing_ThenSuffixIsStrippedFromDisplayName(t *testing.T) {
	// Given a team name with a decorative state suffix, as seen in Brasileirao_Matches.csv
	raw := "Palmeiras-SP"

	// When normalizing it
	_, display := NormalizeTeamName(raw)

	// Then the state suffix is stripped from the display name
	if display != "Palmeiras" {
		t.Errorf("got display %q, want %q", display, "Palmeiras")
	}
}

func Test_GivenTwoSpellingsOfSameClub_WhenNormalizing_ThenBothProduceTheSameKey(t *testing.T) {
	// Given two different spellings of Flamengo seen across datasets
	full := "Clube de Regatas do Flamengo"
	short := "Flamengo-RJ"

	// When normalizing both
	fullKey, _ := NormalizeTeamName(full)
	shortKey, _ := NormalizeTeamName(short)

	// Then they resolve to the same canonical key
	if fullKey != shortKey {
		t.Errorf("got keys %q and %q, want them equal", fullKey, shortKey)
	}
}

func Test_GivenAccentedAndPlainSpellings_WhenNormalizing_ThenBothProduceTheSameKey(t *testing.T) {
	// Given a club name with and without its Portuguese accent
	accented := "Grêmio"
	plain := "Gremio"

	// When normalizing both
	accentedKey, _ := NormalizeTeamName(accented)
	plainKey, _ := NormalizeTeamName(plain)

	// Then they resolve to the same canonical key
	if accentedKey != plainKey {
		t.Errorf("got keys %q and %q, want them equal", accentedKey, plainKey)
	}
}

func Test_GivenClubWhoseIdentityEmbedsAStateCode_WhenNormalizing_ThenTheStateCodeIsKept(t *testing.T) {
	// Given three genuinely different clubs that all use "Atletico" plus a state code as part of their identity
	cases := map[string]string{
		"Atletico-MG":            "Atletico-MG",
		"Clube Atletico Mineiro": "Atletico-MG",
		"Atletico-PR":            "Athletico-PR",
		"Atletico-GO":            "Atletico-GO",
	}

	// When normalizing each
	for raw, wantDisplay := range cases {
		_, display := NormalizeTeamName(raw)

		// Then each keeps its distinguishing state code rather than collapsing to a bare "Atletico"
		if display != wantDisplay {
			t.Errorf("NormalizeTeamName(%q) display = %q, want %q", raw, display, wantDisplay)
		}
	}

	mgKey, _ := NormalizeTeamName("Atletico-MG")
	prKey, _ := NormalizeTeamName("Atletico-PR")
	goKey, _ := NormalizeTeamName("Atletico-GO")
	if mgKey == prKey || mgKey == goKey || prKey == goKey {
		t.Errorf("expected distinct keys for Atletico-MG/PR/GO, got %q, %q, %q", mgKey, prKey, goKey)
	}
}

func Test_GivenUnrelatedMinorClubSharingAMajorClubsName_WhenNormalizing_ThenItDoesNotCollapseIntoTheMajorClub(t *testing.T) {
	// Given a lower-tier "Botafogo" from Sao Paulo state, as seen in BR-Football-Dataset.csv,
	// distinct from the well-known Rio de Janeiro "Botafogo"
	minorClub := "Botafogo SP"
	majorClub := "Botafogo"

	// When normalizing both
	minorKey, _ := NormalizeTeamName(minorClub)
	majorKey, _ := NormalizeTeamName(majorClub)

	// Then they do not collapse into the same key
	if minorKey == majorKey {
		t.Errorf("expected %q and %q to normalize to different keys, both got %q", minorClub, majorClub, minorKey)
	}
}

func Test_GivenNameWithParentheticalNote_WhenNormalizing_ThenTheNoteIsRemoved(t *testing.T) {
	// Given a team name with a parenthetical aside, as seen in Brazilian_Cup_Matches.csv
	raw := "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"

	// When normalizing it
	_, display := NormalizeTeamName(raw)

	// Then the parenthetical note is removed and the state suffix stripped
	if display != "Boavista Sport Club" {
		t.Errorf("got display %q, want %q", display, "Boavista Sport Club")
	}
}
