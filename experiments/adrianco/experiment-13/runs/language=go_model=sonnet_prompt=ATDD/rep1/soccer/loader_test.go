package soccer

import (
	"testing"
)

func TestLoadStore(t *testing.T) {
	store, err := LoadStore("../data/kaggle")
	if err != nil {
		t.Fatalf("LoadStore failed: %v", err)
	}
	if len(store.Matches) == 0 {
		t.Error("expected matches to be loaded")
	}
	if len(store.Players) == 0 {
		t.Error("expected players to be loaded")
	}
	t.Logf("Loaded %d matches and %d players", len(store.Matches), len(store.Players))
}

func TestParseDate(t *testing.T) {
	cases := []struct {
		input string
		want  string
	}{
		{"2012-05-19 18:30:00", "2012-05-19"},
		{"29/03/2003", "2003-03-29"},
		{"2023-09-24", "2023-09-24"},
	}
	for _, c := range cases {
		got := parseDate(c.input)
		if got != c.want {
			t.Errorf("parseDate(%q) = %q, want %q", c.input, got, c.want)
		}
	}
}

func TestParseGoals(t *testing.T) {
	cases := []struct {
		input string
		want  int
	}{
		{"1", 1},
		{"1.0", 1},
		{"2.0", 2},
		{"0", 0},
		{"", 0},
	}
	for _, c := range cases {
		got := parseGoals(c.input)
		if got != c.want {
			t.Errorf("parseGoals(%q) = %d, want %d", c.input, got, c.want)
		}
	}
}
