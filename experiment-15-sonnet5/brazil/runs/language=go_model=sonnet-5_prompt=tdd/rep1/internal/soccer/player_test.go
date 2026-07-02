package soccer

import (
	"strings"
	"testing"
)

func TestLoadFIFAPlayers(t *testing.T) {
	csv := "\ufeff,ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number,Joined,Loaned From\n" +
		`0,158023,L. Messi,31,http://x,Argentina,http://x,94,94,FC Barcelona,http://x,€110.5M,€565K,2202,Left,5,4,4,Medium/ Medium,Messi,Yes,RF,10,"Jul 1, 2004",` + "\n" +
		`1,192318,Alisson,25,http://x,Brazil,http://x,89,93,Liverpool,http://x,€58.5M,€135K,1478,Right,3,3,1,Medium/ Medium,Normal,No,GK,1,"Jul 19, 2018",` + "\n"

	players, err := LoadFIFAPlayers(strings.NewReader(csv))
	if err != nil {
		t.Fatalf("LoadFIFAPlayers returned error: %v", err)
	}
	if len(players) != 2 {
		t.Fatalf("got %d players, want 2", len(players))
	}

	p := players[1]
	if p.ID != 192318 {
		t.Errorf("unexpected ID: %d", p.ID)
	}
	if p.Name != "Alisson" {
		t.Errorf("unexpected name: %q", p.Name)
	}
	if p.Age != 25 {
		t.Errorf("unexpected age: %d", p.Age)
	}
	if p.Nationality != "Brazil" {
		t.Errorf("unexpected nationality: %q", p.Nationality)
	}
	if p.Overall != 89 || p.Potential != 93 {
		t.Errorf("unexpected ratings: overall=%d potential=%d", p.Overall, p.Potential)
	}
	if p.Club != "Liverpool" {
		t.Errorf("unexpected club: %q", p.Club)
	}
	if p.Position != "GK" {
		t.Errorf("unexpected position: %q", p.Position)
	}
	if p.JerseyNumber != 1 {
		t.Errorf("unexpected jersey number: %d", p.JerseyNumber)
	}
}
