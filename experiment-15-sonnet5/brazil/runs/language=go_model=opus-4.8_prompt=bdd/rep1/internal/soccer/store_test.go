package soccer

import "testing"

// Behaviour: overlapping fixtures from different datasets are deduplicated,
// even when the recorded date differs by a day or the naming differs.

func Test_given_same_fixture_twice_when_indexed_then_deduplicated(t *testing.T) {
	// Given the same fixture from two sources on the exact same day
	s := NewStore()
	s.AddMatches([]Match{
		mkMatch(CompBrasileirao, "Flamengo-RJ", "Cruzeiro-MG", 3, 1, 2019, "2019-04-27"),
		mkMatch(CompBrasileirao, "Flamengo", "Cruzeiro", 3, 1, 2019, "2019-04-27"),
	})
	// When the store is indexed
	s.Index()
	// Then only one copy remains
	if len(s.Matches) != 1 {
		t.Fatalf("expected 1 match after dedup, got %d", len(s.Matches))
	}
}

func Test_given_fixture_one_day_apart_when_indexed_then_deduplicated(t *testing.T) {
	// Given the same fixture recorded a day apart (kick-off vs UTC date)
	s := NewStore()
	s.AddMatches([]Match{
		mkMatch(CompBrasileirao, "Flamengo", "Cruzeiro", 3, 1, 2019, "2019-04-27"),
		mkMatch(CompBrasileirao, "Flamengo", "Cruzeiro", 3, 1, 2019, "2019-04-28"),
	})
	// When indexed
	s.Index()
	// Then the two are treated as one fixture
	if len(s.Matches) != 1 {
		t.Fatalf("expected 1 match after ±1 day dedup, got %d", len(s.Matches))
	}
}

func Test_given_stats_only_on_duplicate_when_deduped_then_stats_merged(t *testing.T) {
	// Given a league record without stats and a duplicate carrying shot stats
	s := NewStore()
	league := mkMatch(CompBrasileirao, "Flamengo", "Cruzeiro", 3, 1, 2019, "2019-04-27")
	withStats := mkMatch(CompBrasileirao, "Flamengo", "Cruzeiro", 3, 1, 2019, "2019-04-28")
	withStats.HomeShots = 20
	withStats.AwayShots = 5
	s.AddMatches([]Match{league, withStats})
	// When indexed
	s.Index()
	// Then the surviving record is enriched with the stats from the duplicate
	if len(s.Matches) != 1 {
		t.Fatalf("expected 1 match, got %d", len(s.Matches))
	}
	if s.Matches[0].HomeShots != 20 {
		t.Errorf("expected merged home_shots=20, got %d", s.Matches[0].HomeShots)
	}
}

func Test_given_different_fixtures_when_indexed_then_both_kept(t *testing.T) {
	// Given two genuinely different fixtures (different opponents)
	s := NewStore()
	s.AddMatches([]Match{
		mkMatch(CompBrasileirao, "Flamengo", "Cruzeiro", 3, 1, 2019, "2019-04-27"),
		mkMatch(CompBrasileirao, "Flamengo", "Santos", 2, 0, 2019, "2019-04-27"),
	})
	// When indexed
	s.Index()
	// Then both are kept
	if len(s.Matches) != 2 {
		t.Fatalf("expected 2 distinct matches, got %d", len(s.Matches))
	}
}

func Test_given_curated_club_when_display_name_then_pretty_name_returned(t *testing.T) {
	// Given the canonical key for Atlético Mineiro
	s := NewStore()
	s.AddMatches([]Match{mkMatch(CompBrasileirao, "Atletico-MG", "Flamengo", 1, 0, 2019, "2019-04-27")})
	s.Index()
	// When asking for its display name
	got := s.DisplayName(NormalizeTeam("Atletico-MG"))
	// Then the curated, accented name is returned
	if got != "Atlético Mineiro" {
		t.Fatalf("expected \"Atlético Mineiro\", got %q", got)
	}
}
