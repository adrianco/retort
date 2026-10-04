package soccer

import (
	"strings"
	"sync"
	"testing"
)

var (
	once   sync.Once
	shared *DB
)

func load(t *testing.T) *DB {
	once.Do(func() {
		var err error
		if shared, err = Load("../data/kaggle"); err != nil {
			t.Fatal(err)
		}
	})
	return shared
}

func TestTeamKeyNormalisesVariations(t *testing.T) {
	if TeamKey("Palmeiras-SP") != TeamKey("Palmeiras") {
		t.Errorf("state suffix not normalised")
	}
	if TeamKey("São Paulo") != TeamKey("Sao Paulo-SP") {
		t.Errorf("accents not normalised")
	}
}

func TestParseDateFormats(t *testing.T) {
	for _, s := range []string{"2023-09-24", "29/03/2003", "2012-05-19 18:30:00"} {
		if _, err := ParseDate(s); err != nil {
			t.Errorf("%s: %v", s, err)
		}
	}
}

func TestQueries(t *testing.T) {
	db := load(t)
	cases := []struct {
		name string
		fn   func(Args) (string, error)
		args Args
		want string
	}{
		{"matches", db.SearchMatches, Args{"team": "Flamengo", "opponent": "Fluminense"}, "Fluminense"},
		{"h2h", db.HeadToHead, Args{"team_a": "Palmeiras", "team_b": "Santos"}, "wins"},
		{"record", db.TeamRecord, Args{"team": "Corinthians", "season": 2022.0}, "Wins"},
		{"standings", db.Standings, Args{"season": 2019.0}, "Flamengo"},
		{"stats", db.StatsSummary, Args{}, "goals"},
		{"biggest", db.BiggestWins, Args{}, "-"},
		{"players", db.SearchPlayers, Args{"name": "Neymar"}, "Neymar"},
		{"nationality", db.SearchPlayers, Args{"nationality": "Brazil"}, "Overall"},
	}
	for _, c := range cases {
		out, err := c.fn(c.args)
		if err != nil || !strings.Contains(out, c.want) {
			t.Errorf("%s: err=%v, missing %q in:\n%.300s", c.name, err, c.want, out)
		}
	}
}
