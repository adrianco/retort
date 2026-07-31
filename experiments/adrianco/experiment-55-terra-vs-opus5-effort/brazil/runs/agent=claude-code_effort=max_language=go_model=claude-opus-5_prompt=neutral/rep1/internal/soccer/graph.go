// graph.go turns the loaded rows into an actual knowledge graph so that the
// MCP server can answer relationship questions ("how is this player connected
// to that competition?") instead of only tabular ones.
//
// Node types: team, player, match, competition, season, state, country,
// stadium and club.
//
// Edge types: home_team, away_team, played_in, in_season, season_of,
// played_at, plays_for, nationality, based_in, in_country and rival_of.
package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// NodeID identifies a graph node, e.g. "team:flamengo-rj".
type NodeID string

// Node is one entity in the knowledge graph.
type Node struct {
	ID    NodeID            `json:"id"`
	Type  string            `json:"type"`
	Label string            `json:"label"`
	Ref   string            `json:"ref,omitempty"`
	Props map[string]string `json:"props,omitempty"`
}

// Edge is a typed, directed relationship.
type Edge struct {
	Type string `json:"type"`
	From NodeID `json:"from"`
	To   NodeID `json:"to"`
}

// Graph is an in-memory property graph with reverse adjacency.
type Graph struct {
	nodes map[NodeID]*Node
	out   map[NodeID][]Edge
	in    map[NodeID][]Edge
	order []NodeID
	edges int
}

func newGraph() *Graph {
	return &Graph{nodes: map[NodeID]*Node{}, out: map[NodeID][]Edge{}, in: map[NodeID][]Edge{}}
}

func (g *Graph) addNode(n *Node) *Node {
	if existing, ok := g.nodes[n.ID]; ok {
		return existing
	}
	g.nodes[n.ID] = n
	g.order = append(g.order, n.ID)
	return n
}

func (g *Graph) addEdge(typ string, from, to NodeID) {
	e := Edge{Type: typ, From: from, To: to}
	g.out[from] = append(g.out[from], e)
	g.in[to] = append(g.in[to], e)
	g.edges++
}

// Size returns the node and edge counts.
func (g *Graph) Size() (nodes, edges int) { return len(g.nodes), g.edges }

// Node looks a node up by id.
func (g *Graph) Node(id NodeID) *Node { return g.nodes[id] }

// CountsByType reports how many nodes exist per type.
func (g *Graph) CountsByType() map[string]int {
	out := map[string]int{}
	for _, n := range g.nodes {
		out[n.Type]++
	}
	return out
}

// EdgeCountsByType reports how many edges exist per type.
func (g *Graph) EdgeCountsByType() map[string]int {
	out := map[string]int{}
	for _, edges := range g.out {
		for _, e := range edges {
			out[e.Type]++
		}
	}
	return out
}

// Direction selects which way edges are followed.
type Direction string

// Traversal directions.
const (
	Outgoing Direction = "out"
	Incoming Direction = "in"
	Both     Direction = "both"
)

// NeighborOpts filters a neighbourhood query.
type NeighborOpts struct {
	Direction Direction
	EdgeTypes []string
	NodeTypes []string
	Limit     int
}

// Neighbor is one step away from a node.
type Neighbor struct {
	Edge      string `json:"edge"`
	Direction string `json:"direction"`
	Node      *Node  `json:"node"`
}

// Neighbors returns the nodes adjacent to id.
func (g *Graph) Neighbors(id NodeID, opts NeighborOpts) []Neighbor {
	if _, ok := g.nodes[id]; !ok {
		return nil
	}
	edgeOK := setOf(opts.EdgeTypes)
	nodeOK := setOf(opts.NodeTypes)
	var out []Neighbor
	// A symmetric relationship (rival_of) is stored in both directions, so the
	// same neighbour is only reported once.
	seen := map[string]bool{}
	visit := func(edges []Edge, dir Direction) {
		for _, e := range edges {
			if edgeOK != nil && !edgeOK[e.Type] {
				continue
			}
			other := e.To
			if dir == Incoming {
				other = e.From
			}
			n := g.nodes[other]
			if n == nil {
				continue
			}
			if nodeOK != nil && !nodeOK[n.Type] {
				continue
			}
			key := e.Type + "|" + string(other)
			if seen[key] {
				continue
			}
			seen[key] = true
			out = append(out, Neighbor{Edge: e.Type, Direction: string(dir), Node: n})
		}
	}
	if opts.Direction == "" || opts.Direction == Both || opts.Direction == Outgoing {
		visit(g.out[id], Outgoing)
	}
	if opts.Direction == "" || opts.Direction == Both || opts.Direction == Incoming {
		visit(g.in[id], Incoming)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Edge != out[j].Edge {
			return out[i].Edge < out[j].Edge
		}
		return out[i].Node.Label < out[j].Node.Label
	})
	if opts.Limit > 0 && len(out) > opts.Limit {
		out = out[:opts.Limit]
	}
	return out
}

// PathStep is one hop of a path.
type PathStep struct {
	Edge      string `json:"edge"`
	Direction string `json:"direction"`
	Node      *Node  `json:"node"`
}

// Path finds the shortest path between two nodes, following edges in either
// direction, and returns the steps taken (excluding the start node).
func (g *Graph) Path(from, to NodeID, maxDepth int) ([]PathStep, bool) {
	if _, ok := g.nodes[from]; !ok {
		return nil, false
	}
	if _, ok := g.nodes[to]; !ok {
		return nil, false
	}
	if from == to {
		return nil, true
	}
	if maxDepth <= 0 {
		maxDepth = 6
	}
	seen := map[NodeID]crumb{from: {}}
	frontier := []NodeID{from}
	for depth := 0; depth < maxDepth && len(frontier) > 0; depth++ {
		var next []NodeID
		for _, cur := range frontier {
			for _, e := range g.out[cur] {
				if _, ok := seen[e.To]; ok {
					continue
				}
				seen[e.To] = crumb{prev: cur, step: PathStep{Edge: e.Type, Direction: string(Outgoing), Node: g.nodes[e.To]}}
				if e.To == to {
					return buildPath(seen, from, to), true
				}
				next = append(next, e.To)
			}
			for _, e := range g.in[cur] {
				if _, ok := seen[e.From]; ok {
					continue
				}
				seen[e.From] = crumb{prev: cur, step: PathStep{Edge: e.Type, Direction: string(Incoming), Node: g.nodes[e.From]}}
				if e.From == to {
					return buildPath(seen, from, to), true
				}
				next = append(next, e.From)
			}
		}
		frontier = next
	}
	return nil, false
}

// crumb is the breadcrumb left by the BFS in Path.
type crumb struct {
	prev NodeID
	step PathStep
}

func buildPath(seen map[NodeID]crumb, from, to NodeID) []PathStep {
	var rev []PathStep
	for cur := to; cur != from; {
		c := seen[cur]
		rev = append(rev, c.step)
		cur = c.prev
	}
	for i, j := 0, len(rev)-1; i < j; i, j = i+1, j-1 {
		rev[i], rev[j] = rev[j], rev[i]
	}
	return rev
}

func setOf(items []string) map[string]bool {
	if len(items) == 0 {
		return nil
	}
	m := make(map[string]bool, len(items))
	for _, i := range items {
		m[strings.ToLower(strings.TrimSpace(i))] = true
	}
	return m
}

// ---------------------------------------------------------------------------
// Node id helpers
// ---------------------------------------------------------------------------

// TeamNode returns the node id of a team.
func TeamNode(id string) NodeID { return NodeID("team:" + id) }

// PlayerNode returns the node id of a player.
func PlayerNode(id int) NodeID { return NodeID(fmt.Sprintf("player:%d", id)) }

// MatchNode returns the node id of a match.
func MatchNode(id string) NodeID { return NodeID("match:" + id) }

// CompetitionNode returns the node id of a competition.
func CompetitionNode(id string) NodeID { return NodeID("competition:" + id) }

// SeasonNode returns the node id of a competition season.
func SeasonNode(comp string, season int) NodeID {
	return NodeID(fmt.Sprintf("season:%s:%d", comp, season))
}

// StateNode returns the node id of a Brazilian state.
func StateNode(uf string) NodeID { return NodeID("state:" + strings.ToUpper(uf)) }

// CountryNode returns the node id of a country, keyed by folded name.
func CountryNode(name string) NodeID { return NodeID("country:" + Slug(name)) }

// StadiumNode returns the node id of a stadium.
func StadiumNode(name string) NodeID { return NodeID("stadium:" + Slug(name)) }

// ClubNode returns the node id of a FIFA club that is not in the match data.
func ClubNode(name string) NodeID { return NodeID("club:" + Slug(name)) }

// ---------------------------------------------------------------------------
// Building
// ---------------------------------------------------------------------------

func buildGraph(s *Store) *Graph {
	g := newGraph()

	for _, c := range s.CompetitionsWithData() {
		g.addNode(&Node{ID: CompetitionNode(c.ID), Type: "competition", Label: c.Name, Ref: c.ID,
			Props: map[string]string{"kind": c.Kind, "country": c.Country}})
		for _, season := range s.Seasons(c.ID) {
			g.addNode(&Node{ID: SeasonNode(c.ID, season), Type: "season",
				Label: fmt.Sprintf("%s %d", c.Short, season), Ref: fmt.Sprintf("%s:%d", c.ID, season),
				Props: map[string]string{"season": fmt.Sprint(season)}})
			g.addEdge("season_of", SeasonNode(c.ID, season), CompetitionNode(c.ID))
		}
	}

	for _, t := range s.Teams.Teams() {
		props := map[string]string{}
		if t.State != "" {
			props["state"] = t.State
		}
		if t.Country != "" {
			props["country"] = t.Country
		}
		g.addNode(&Node{ID: TeamNode(t.ID), Type: "team", Label: t.Name, Ref: t.ID, Props: props})
		if t.State != "" {
			name := BrazilianStates[t.State]
			if name == "" {
				name = t.State
			}
			g.addNode(&Node{ID: StateNode(t.State), Type: "state", Label: name, Ref: t.State})
			g.addEdge("based_in", TeamNode(t.ID), StateNode(t.State))
			g.addNode(&Node{ID: CountryNode("Brazil"), Type: "country", Label: "Brazil", Ref: "BRA"})
			g.addEdge("in_country", StateNode(t.State), CountryNode("Brazil"))
		}
		if t.Country != "" {
			name := CountryNames[t.Country]
			if name == "" {
				name = t.Country
			}
			g.addNode(&Node{ID: CountryNode(name), Type: "country", Label: name, Ref: t.Country})
			g.addEdge("in_country", TeamNode(t.ID), CountryNode(name))
		}
	}

	for _, r := range Rivalries() {
		if s.Teams.Team(r.TeamA) == nil || s.Teams.Team(r.TeamB) == nil {
			continue
		}
		g.addEdge("rival_of", TeamNode(r.TeamA), TeamNode(r.TeamB))
		g.addEdge("rival_of", TeamNode(r.TeamB), TeamNode(r.TeamA))
	}

	for _, m := range s.Matches {
		props := map[string]string{
			"date":   m.DateString(),
			"score":  fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals),
			"season": fmt.Sprint(m.Season),
		}
		if r := m.RoundLabel(); r != "" {
			props["round"] = r
		}
		g.addNode(&Node{ID: MatchNode(m.ID), Type: "match", Label: m.DateString() + " " + m.Label(), Ref: m.ID, Props: props})
		g.addEdge("home_team", MatchNode(m.ID), TeamNode(m.HomeTeamID))
		g.addEdge("away_team", MatchNode(m.ID), TeamNode(m.AwayTeamID))
		g.addEdge("played_in", MatchNode(m.ID), CompetitionNode(m.CompetitionID))
		g.addEdge("in_season", MatchNode(m.ID), SeasonNode(m.CompetitionID, m.Season))
		if m.Venue != "" {
			g.addNode(&Node{ID: StadiumNode(m.Venue), Type: "stadium", Label: m.Venue, Ref: Slug(m.Venue)})
			g.addEdge("played_at", MatchNode(m.ID), StadiumNode(m.Venue))
		}
	}

	for _, p := range s.Players {
		props := map[string]string{"overall": fmt.Sprint(p.Overall)}
		if p.Position != "" {
			props["position"] = p.Position
		}
		if p.Club != "" {
			props["club"] = p.Club
		}
		g.addNode(&Node{ID: PlayerNode(p.ID), Type: "player", Label: p.Name, Ref: fmt.Sprint(p.ID), Props: props})
		switch {
		case p.TeamID != "":
			g.addEdge("plays_for", PlayerNode(p.ID), TeamNode(p.TeamID))
		case p.Club != "":
			g.addNode(&Node{ID: ClubNode(p.Club), Type: "club", Label: p.Club, Ref: Slug(p.Club)})
			g.addEdge("plays_for", PlayerNode(p.ID), ClubNode(p.Club))
		}
		if p.Nationality != "" {
			g.addNode(&Node{ID: CountryNode(p.Nationality), Type: "country", Label: p.Nationality, Ref: Slug(p.Nationality)})
			g.addEdge("nationality", PlayerNode(p.ID), CountryNode(p.Nationality))
		}
	}
	return g
}
