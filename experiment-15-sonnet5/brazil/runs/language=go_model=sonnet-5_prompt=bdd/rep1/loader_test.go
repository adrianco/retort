package main

import "testing"

// These tests load the real datasets shipped in data/kaggle/ to verify the
// loaders, deduplication, and normalization work correctly together end to
// end - not just in isolated unit tests.

func Test_GivenTheProvidedDatasets_WhenLoadingAll_ThenEveryFileContributesMatchesOrPlayers(t *testing.T) {
	// Given the six CSV files shipped in data/kaggle/

	// When loading them all
	store, err := LoadAll("data/kaggle")

	// Then loading succeeds and produces a substantial, non-trivial dataset
	if err != nil {
		t.Fatalf("LoadAll returned error: %v", err)
	}
	if len(store.Matches) < 10000 {
		t.Errorf("got %d matches, want at least 10000", len(store.Matches))
	}
	if len(store.Players) < 15000 {
		t.Errorf("got %d players, want at least 15000", len(store.Players))
	}
}

func Test_GivenOverlappingBrasileiraoSources_WhenLoadingAll_ThenDuplicateFixturesAreRemoved(t *testing.T) {
	// Given that Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv, and
	// BR-Football-Dataset.csv all cover the real 2019 Brasileirao season

	// When loading all datasets and computing the 2019 standings
	store, err := LoadAll("data/kaggle")
	if err != nil {
		t.Fatalf("LoadAll returned error: %v", err)
	}
	rows := store.Standings(2019, "Brasileirao")

	// Then the champion, Flamengo, has exactly one real season's worth of
	// matches (38 games), matching the actual historical result of
	// 90 points from 28 wins, 6 draws, 4 losses - not a multiple of it
	if len(rows) == 0 {
		t.Fatal("expected standings rows, got none")
	}
	champion := rows[0]
	if champion.Team != "Flamengo" {
		t.Fatalf("got champion %q, want Flamengo", champion.Team)
	}
	if champion.Played != 38 {
		t.Errorf("got %d matches played, want 38 (deduplication likely failed)", champion.Played)
	}
	if champion.Points != 90 {
		t.Errorf("got %d points, want 90", champion.Points)
	}
}

func Test_GivenAKnownMajorClub_WhenLoadingAll_ThenItsMatchesFromDifferentFilesShareOneKey(t *testing.T) {
	// Given Palmeiras appears as "Palmeiras-SP" in Brasileirao_Matches.csv and
	// plainly as "Palmeiras" elsewhere

	// When loading all datasets
	store, err := LoadAll("data/kaggle")
	if err != nil {
		t.Fatalf("LoadAll returned error: %v", err)
	}

	// Then searching by either spelling returns a non-empty, identical result set
	bySuffixed := store.FilterMatches(MatchFilter{Team: "Palmeiras-SP", Limit: 1000})
	byPlain := store.FilterMatches(MatchFilter{Team: "Palmeiras", Limit: 1000})
	if len(bySuffixed) == 0 {
		t.Fatal("expected matches for Palmeiras-SP, got none")
	}
	if len(bySuffixed) != len(byPlain) {
		t.Errorf("got %d matches for 'Palmeiras-SP' but %d for 'Palmeiras', want equal", len(bySuffixed), len(byPlain))
	}
}

func Test_GivenTheFifaDataset_WhenLoadingAll_ThenBrazilianPlayersAreFound(t *testing.T) {
	// Given fifa_data.csv includes Brazilian internationals such as Neymar

	// When loading all datasets and searching for Brazilian players
	store, err := LoadAll("data/kaggle")
	if err != nil {
		t.Fatalf("LoadAll returned error: %v", err)
	}
	got := store.SearchPlayers(PlayerFilter{Nationality: "Brazil", Limit: 5})

	// Then at least one Brazilian player is found
	if len(got) == 0 {
		t.Error("expected at least one Brazilian player, got none")
	}
}
