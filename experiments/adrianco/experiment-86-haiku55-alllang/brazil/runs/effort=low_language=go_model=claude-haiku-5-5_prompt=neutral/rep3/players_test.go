// BDD scenarios for player search across the FIFA dataset.

package main

import (
	"strings"
	"testing"
)

func TestSearchPlayers(t *testing.T) {
	ds := loadTestDataset(t)

	t.Run("Given the FIFA player data", func(t *testing.T) {
		t.Run("When I search by name, Then matching players are returned", func(t *testing.T) {
			got := ds.SearchPlayers(PlayerFilter{Name: "Messi"})
			if len(got) == 0 {
				t.Fatal("expected Messi")
			}
			for _, p := range got {
				if !containsFold(p.Name, "Messi") {
					t.Fatalf("unexpected player %q", p.Name)
				}
			}
		})

		t.Run("When I filter by nationality, Then only that nationality is returned", func(t *testing.T) {
			got := ds.SearchPlayers(PlayerFilter{Nationality: "Brazil"})
			if len(got) == 0 {
				t.Fatal("expected Brazilian players")
			}
			for _, p := range got {
				if p.Nationality != "Brazil" {
					t.Fatalf("nationality %q", p.Nationality)
				}
			}
		})

		t.Run("When I filter by position group, Then every result is a forward", func(t *testing.T) {
			for _, p := range ds.SearchPlayers(PlayerFilter{Position: "FORWARD", MinOverall: 85}) {
				if !positionMatches(p.Position, "FORWARD") {
					t.Fatalf("%s is %s", p.Name, p.Position)
				}
				if p.Overall < 85 {
					t.Fatalf("%s overall %d below minimum", p.Name, p.Overall)
				}
			}
		})

		t.Run("When results are returned, Then they are sorted by overall rating", func(t *testing.T) {
			got := ds.SearchPlayers(PlayerFilter{Nationality: "Argentina"})
			for i := 1; i < len(got); i++ {
				if got[i].Overall > got[i-1].Overall {
					t.Fatal("not sorted by overall")
				}
			}
		})

		t.Run("When I restrict to Brazilian clubs, Then only clubs seen in the Brasileirão data remain", func(t *testing.T) {
			got := ds.SearchPlayers(PlayerFilter{Nationality: "Brazil", BrazilianClubsOnly: true})
			if len(got) == 0 {
				t.Fatal("expected Brazilian players at Brazilian clubs")
			}
			for _, p := range got {
				if !ds.BrazilianClubs[ParseTeam(p.Club, "").Base] {
					t.Fatalf("club %q is not Brazilian", p.Club)
				}
			}
		})
	})
}

func TestPositionMatches(t *testing.T) {
	cases := []struct {
		player, want string
		ok           bool
	}{
		{"ST", "ST", true},
		{"CF", "FORWARD", true},
		{"CDM", "MIDFIELDER", true},
		{"GK", "GOALKEEPER", true},
		{"GK", "DEFENDER", false},
		{"ST", "ST2", false},
	}
	for _, c := range cases {
		t.Run("Given player position "+c.player+" and query "+c.want, func(t *testing.T) {
			if got := positionMatches(c.player, c.want); got != c.ok {
				t.Fatalf("got %v, want %v", got, c.ok)
			}
		})
	}
}

// containsFold reports whether s contains sub, ignoring case and accents.
func containsFold(s, sub string) bool {
	return strings.Contains(stripAccents(s), stripAccents(sub))
}
