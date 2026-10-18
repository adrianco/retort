// BDD scenarios for team name normalization.

package main

import "testing"

func TestTeamNameNormalization(t *testing.T) {
	t.Run("Given a team written with a state suffix", func(t *testing.T) {
		t.Run("When normalized, Then the base name and state are separated", func(t *testing.T) {
			got := ParseTeam("Palmeiras-SP", "")
			if got.Base != "palmeiras" || got.State != "SP" {
				t.Fatalf("got base=%q state=%q", got.Base, got.State)
			}
		})
		t.Run("When the suffix has spaces around the dash, Then it is still a state", func(t *testing.T) {
			got := ParseTeam("América - MG", "")
			if got.Base != "america" || got.State != "MG" {
				t.Fatalf("got base=%q state=%q", got.Base, got.State)
			}
		})
		t.Run("When the suffix has no dash, Then it is still a state", func(t *testing.T) {
			got := ParseTeam("Vasco Da Gama RJ", "")
			if got.Base != "vasco gama" || got.State != "RJ" {
				t.Fatalf("got base=%q state=%q", got.Base, got.State)
			}
		})
	})

	t.Run("Given accented and full club names", func(t *testing.T) {
		t.Run("When normalized, Then accents are removed", func(t *testing.T) {
			if got := ParseTeam("São Paulo-SP", "").Base; got != "sao paulo" {
				t.Fatalf("got %q", got)
			}
			if got := ParseTeam("Grêmio", "").Base; got != "gremio" {
				t.Fatalf("got %q", got)
			}
			if got := ParseTeam("Avaí", "").Base; got != "avai" {
				t.Fatalf("got %q", got)
			}
		})
		t.Run("When the full official name is used, Then noise words are dropped", func(t *testing.T) {
			if got := ParseTeam("Sport Club Corinthians Paulista", "").Base; got != "corinthians paulista" {
				t.Fatalf("got %q", got)
			}
		})
		t.Run("When a parenthetical history is present, Then it is ignored", func(t *testing.T) {
			got := ParseTeam("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "")
			if got.Base != "boavista" || got.State != "RJ" {
				t.Fatalf("got base=%q state=%q", got.Base, got.State)
			}
		})
		t.Run("When a name ends in FC, Then FC is not mistaken for a state", func(t *testing.T) {
			if got := ParseTeam("Fluminense FC", ""); got.State != "" || got.Base != "fluminense" {
				t.Fatalf("got base=%q state=%q", got.Base, got.State)
			}
		})
		t.Run("When a fallback state is supplied, Then it is used", func(t *testing.T) {
			if got := ParseTeam("Guarani", "sp"); got.State != "SP" {
				t.Fatalf("got state=%q", got.State)
			}
		})
	})

	t.Run("Given a short query and a dataset name", func(t *testing.T) {
		t.Run("When the query is the bare name, Then it matches the suffixed dataset name", func(t *testing.T) {
			if !ParseTeam("Flamengo", "").Matches(ParseTeam("Flamengo-RJ", "")) {
				t.Fatal("expected Flamengo to match Flamengo-RJ")
			}
		})
		t.Run("When the query is the full name, Then it matches the short dataset name", func(t *testing.T) {
			if !ParseTeam("Corinthians", "").Matches(ParseTeam("Sport Club Corinthians Paulista", "")) {
				t.Fatal("expected Corinthians to match the full name")
			}
		})
		t.Run("When the query states a different state, Then it does not match", func(t *testing.T) {
			if ParseTeam("Atletico-PR", "").Matches(ParseTeam("Atletico-MG", "")) {
				t.Fatal("Atletico-PR must not match Atletico-MG")
			}
		})
		t.Run("When the query is empty, Then nothing matches", func(t *testing.T) {
			if ParseTeam("", "").Matches(ParseTeam("Flamengo", "")) {
				t.Fatal("empty query must not match")
			}
		})
	})
}
