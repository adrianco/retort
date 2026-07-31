package soccer

import "testing"

func TestGraphIsBuilt(t *testing.T) {
	s := testStore(t)
	nodes, edges := s.Graph.Size()
	if nodes < 30000 || edges < 90000 {
		t.Fatalf("graph has %d nodes and %d edges, which is too small for the data", nodes, edges)
	}
	counts := s.Graph.CountsByType()
	for _, kind := range []string{"team", "player", "match", "competition", "season", "state", "country", "stadium"} {
		if counts[kind] == 0 {
			t.Errorf("no %s nodes in the graph", kind)
		}
	}
	if counts["match"] != len(s.Matches) {
		t.Errorf("%d match nodes for %d matches", counts["match"], len(s.Matches))
	}
	if counts["player"] != len(s.Players) {
		t.Errorf("%d player nodes for %d players", counts["player"], len(s.Players))
	}
	edgeCounts := s.Graph.EdgeCountsByType()
	for _, kind := range []string{"home_team", "away_team", "played_in", "in_season", "plays_for", "nationality", "based_in", "rival_of"} {
		if edgeCounts[kind] == 0 {
			t.Errorf("no %s edges in the graph", kind)
		}
	}
}

func TestGraphTeamNeighbours(t *testing.T) {
	s := testStore(t)
	node := s.Graph.Node(TeamNode("flamengo-rj"))
	if node == nil {
		t.Fatal("no node for Flamengo")
	}
	if node.Type != "team" || node.Label != "Flamengo" {
		t.Errorf("node = %+v", node)
	}
	if node.Props["state"] != "RJ" {
		t.Errorf("state property = %q", node.Props["state"])
	}

	states := s.Graph.Neighbors(node.ID, NeighborOpts{EdgeTypes: []string{"based_in"}})
	if len(states) != 1 || states[0].Node.ID != StateNode("RJ") {
		t.Errorf("based_in neighbours = %+v", states)
	}

	rivals := s.Graph.Neighbors(node.ID, NeighborOpts{EdgeTypes: []string{"rival_of"}, Direction: Outgoing})
	if len(rivals) < 3 {
		t.Errorf("Flamengo should have at least three derbies, got %d", len(rivals))
	}

	matches := s.Graph.Neighbors(node.ID, NeighborOpts{NodeTypes: []string{"match"}, Direction: Incoming, Limit: 5})
	if len(matches) != 5 {
		t.Errorf("limit ignored: got %d neighbours", len(matches))
	}
	for _, n := range matches {
		if n.Node.Type != "match" {
			t.Errorf("node type filter leaked a %s", n.Node.Type)
		}
	}
}

func TestGraphPlayerToCompetitionPath(t *testing.T) {
	s := testStore(t)
	squad := s.PlayersForTeam("gremio-rs")
	if len(squad) == 0 {
		t.Skip("no linked squad to walk from")
	}
	from := PlayerNode(squad[0].ID)
	to := CompetitionNode(CompLibertadores)
	steps, ok := s.Graph.Path(from, to, 6)
	if !ok {
		t.Fatalf("no path from %s to %s", from, to)
	}
	if len(steps) == 0 || steps[len(steps)-1].Node.ID != to {
		t.Errorf("path does not end at the competition: %+v", steps)
	}
	if len(steps) > 4 {
		t.Errorf("path is %d hops, expected player -> club -> match -> competition", len(steps))
	}
}

func TestGraphPathHonoursDepth(t *testing.T) {
	s := testStore(t)
	from := PlayerNode(s.PlayersForTeam("gremio-rs")[0].ID)
	to := CompetitionNode(CompLibertadores)
	if _, ok := s.Graph.Path(from, to, 1); ok {
		t.Error("a one hop path between a player and a competition should not exist")
	}
}

func TestGraphMissingNodes(t *testing.T) {
	s := testStore(t)
	if n := s.Graph.Node("team:does-not-exist"); n != nil {
		t.Error("unknown node resolved")
	}
	if got := s.Graph.Neighbors("team:does-not-exist", NeighborOpts{}); got != nil {
		t.Error("neighbours of an unknown node should be empty")
	}
	if _, ok := s.Graph.Path("team:does-not-exist", CompetitionNode(CompBrasileirao), 3); ok {
		t.Error("path from an unknown node should fail")
	}
}

func TestGraphMatchNodeCarriesResult(t *testing.T) {
	s := testStore(t)
	m := s.SeasonMatches(CompBrasileirao, 2019)[0]
	node := s.Graph.Node(MatchNode(m.ID))
	if node == nil {
		t.Fatalf("no node for match %s", m.ID)
	}
	if node.Props["date"] != m.DateString() {
		t.Errorf("date property = %q, want %q", node.Props["date"], m.DateString())
	}
	home := s.Graph.Neighbors(node.ID, NeighborOpts{EdgeTypes: []string{"home_team"}, Direction: Outgoing})
	if len(home) != 1 || home[0].Node.Ref != m.HomeTeamID {
		t.Errorf("home_team edge = %+v, want %s", home, m.HomeTeamID)
	}
}
