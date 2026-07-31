// load_test.go covers the CSV parsing helpers and the cross-dataset
// deduplication that stops the same fixture being counted several times.
package soccer

import "testing"

func TestParseDateHandlesEveryFormatInTheData(t *testing.T) {
	cases := map[string]string{
		"2023-09-24":            "2023-09-24",
		"2012-05-19 18:30:00":   "2012-05-19",
		"29/03/2003":            "2003-03-29",
		`"2019-11-24 16:00:00"`: "2019-11-24",
	}
	for in, want := range cases {
		got, _, err := ParseDate(in)
		if err != nil {
			t.Fatalf("ParseDate(%q): %v", in, err)
		}
		if got.Format("2006-01-02") != want {
			t.Errorf("ParseDate(%q) = %s, want %s", in, got.Format("2006-01-02"), want)
		}
	}
	if _, _, err := ParseDate("not a date"); err == nil {
		t.Error("expected an error for an unparseable date")
	}
}

func TestParseIntTolerance(t *testing.T) {
	cases := map[string]int{"3": 3, `"4"`: 4, "1.0": 1, " 2 ": 2, "2.6": 3}
	for in, want := range cases {
		got, ok := parseInt(in)
		if !ok || got != want {
			t.Errorf("parseInt(%q) = %d, %v; want %d", in, got, ok, want)
		}
	}
	if _, ok := parseInt(""); ok {
		t.Error("empty string should not parse")
	}
}

func TestDeduplicationAcrossDatasets(t *testing.T) {
	s := store(t)
	// A Série A season is 380 matches however many files describe it.
	for _, season := range []int{2015, 2019, 2022} {
		got := s.SearchMatches(MatchFilter{Competition: "Serie A", Season: season})
		if len(got) != 380 {
			t.Errorf("season %d: expected 380 unique matches, got %d", season, len(got))
		}
	}
	// Matches present in more than one dataset record every source.
	multi := 0
	for _, m := range s.Matches {
		if len(m.Sources) > 1 {
			multi++
		}
	}
	if multi == 0 {
		t.Error("expected some matches to be merged from several datasets")
	}
	// The merge carries the extended statistics over from BR-Football.
	withStats := 0
	for _, m := range s.Matches {
		if m.Stats != nil {
			withStats++
		}
	}
	if withStats < 5000 {
		t.Errorf("expected extended stats on most BR-Football matches, got %d", withStats)
	}
}

func TestUTF8IsPreserved(t *testing.T) {
	s := store(t)
	found := false
	for _, m := range s.Matches {
		if m.Venue == "Maracanã" || m.HomeTeam == "Grêmio" || m.HomeTeam == "Avaí" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected accented Portuguese text to survive loading")
	}
}
