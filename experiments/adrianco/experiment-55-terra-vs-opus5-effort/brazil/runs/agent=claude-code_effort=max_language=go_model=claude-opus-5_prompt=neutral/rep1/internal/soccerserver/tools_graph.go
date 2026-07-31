// tools_graph.go exposes the knowledge graph itself: neighbourhood queries and
// shortest paths between any two entities.
package soccerserver

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// maxGraphDepth bounds a path search, matching the schema's advertised range.
const maxGraphDepth = 10

const graphSchemaText = `Node types:  team, player, match, competition, season, state, country, stadium, club
Edge types:  home_team, away_team (match -> team), played_in (match -> competition),
             in_season (match -> season), season_of (season -> competition),
             played_at (match -> stadium), plays_for (player -> team|club),
             nationality (player -> country), based_in (team -> state),
             in_country (state|team -> country), rival_of (team <-> team)
Node ids:    team:flamengo-rj, player:158023, competition:brasileirao,
             season:brasileirao:2019, state:RJ, country:brazil, stadium:maracana`

func (a *api) graphNeighborsTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "graph_neighbors",
		Title:       "Explore the knowledge graph",
		Description: "Walk the knowledge graph from any entity. Accepts a node id (\"team:flamengo-rj\") or free text plus a type, and returns the typed relationships around it.\n\n" + graphSchemaText,
		InputSchema: mcp.Object(map[string]*mcp.Prop{
			"entity":     mcp.Str("Node id, or free text such as \"Flamengo\", \"Neymar\", \"Brasileirão\"."),
			"type":       mcp.Enum("Entity type to resolve free text against.", "team", "player", "competition", "season", "state", "country", "stadium", "club", "match"),
			"edge_types": mcp.StrArray("Only follow these edge types."),
			"node_types": mcp.StrArray("Only return neighbours of these node types."),
			"direction":  mcp.Enum("Follow outgoing edges, incoming edges or both (default both).", "out", "in", "both"),
			"limit":      mcp.IntRange("Maximum neighbours to return (default 25, max 200).", 1, maxLimit),
		}, "entity"),
		Handler: a.graphNeighbors,
	}
}

func (a *api) graphNeighbors(args mcp.Args) (*mcp.ToolResult, error) {
	node, res := a.resolveNode(args.String("entity"), args.String("type"))
	if res != nil {
		return res, nil
	}
	limit, res := limitArg(args, 25)
	if res != nil {
		return res, nil
	}
	opts := soccer.NeighborOpts{
		Direction: soccer.Direction(strings.ToLower(args.String("direction"))),
		EdgeTypes: args.Strings("edge_types"),
		NodeTypes: args.Strings("node_types"),
		Limit:     limit,
	}
	neighbors := a.store.Graph.Neighbors(node.ID, opts)

	var b strings.Builder
	fmt.Fprintf(&b, "%s [%s] %s\n", node.Label, node.Type, node.ID)
	if len(node.Props) > 0 {
		parts := make([]string, 0, len(node.Props))
		for k, v := range node.Props {
			parts = append(parts, k+"="+v)
		}
		sortStrings(parts)
		fmt.Fprintf(&b, "Properties: %s\n", strings.Join(parts, ", "))
	}
	if len(neighbors) == 0 {
		b.WriteString("No neighbours match those filters.\n")
	} else {
		fmt.Fprintf(&b, "\n%d relationships:\n", len(neighbors))
		for _, n := range neighbors {
			arrow := "->"
			if n.Direction == "in" {
				arrow = "<-"
			}
			fmt.Fprintf(&b, "- %s %s %s [%s] %s\n", arrow, n.Edge, n.Node.Label, n.Node.Type, n.Node.ID)
		}
	}
	items := make([]map[string]any, 0, len(neighbors))
	for _, n := range neighbors {
		items = append(items, map[string]any{
			"edge": n.Edge, "direction": n.Direction,
			"id": string(n.Node.ID), "type": n.Node.Type, "label": n.Node.Label, "props": n.Node.Props,
		})
	}
	return mcp.TextWithData(b.String(), map[string]any{
		"node":      map[string]any{"id": string(node.ID), "type": node.Type, "label": node.Label, "props": node.Props},
		"neighbors": items,
	}), nil
}

func (a *api) graphPathTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "graph_path",
		Title:       "Path between entities",
		Description: "Find the shortest chain of relationships between two entities, for example from a player to a competition via his club and its matches.\n\n" + graphSchemaText,
		InputSchema: mcp.Object(map[string]*mcp.Prop{
			"from":      mcp.Str("Start entity: node id or free text."),
			"to":        mcp.Str("End entity: node id or free text."),
			"from_type": mcp.Enum("Type to resolve `from` against.", "team", "player", "competition", "season", "state", "country", "stadium", "club", "match"),
			"to_type":   mcp.Enum("Type to resolve `to` against.", "team", "player", "competition", "season", "state", "country", "stadium", "club", "match"),
			"max_depth": mcp.IntRange("Maximum number of hops (default 6).", 1, 10),
		}, "from", "to"),
		Handler: a.graphPath,
	}
}

func (a *api) graphPath(args mcp.Args) (*mcp.ToolResult, error) {
	from, res := a.resolveNode(args.String("from"), args.String("from_type"))
	if res != nil {
		return res, nil
	}
	to, res := a.resolveNode(args.String("to"), args.String("to_type"))
	if res != nil {
		return res, nil
	}
	depth, err := args.Int("max_depth", 6)
	if err != nil {
		return mcp.ErrorResult("%v", err), nil
	}
	if depth < 1 || depth > maxGraphDepth {
		depth = maxGraphDepth // the schema advertises the bound; keep it true
	}
	steps, ok := a.store.Graph.Path(from.ID, to.ID, depth)
	if !ok {
		return mcp.TextWithData(fmt.Sprintf("No path of up to %d hops connects %s and %s.\n", depth, from.Label, to.Label),
			map[string]any{"connected": false}), nil
	}

	var b strings.Builder
	fmt.Fprintf(&b, "Path from %s [%s] to %s [%s] in %d hops:\n", from.Label, from.Type, to.Label, to.Type, len(steps))
	fmt.Fprintf(&b, "  %s [%s]\n", from.Label, from.Type)
	items := make([]map[string]any, 0, len(steps))
	for _, s := range steps {
		arrow := "->"
		if s.Direction == "in" {
			arrow = "<-"
		}
		fmt.Fprintf(&b, "  %s %s: %s [%s]\n", arrow, s.Edge, s.Node.Label, s.Node.Type)
		items = append(items, map[string]any{
			"edge": s.Edge, "direction": s.Direction,
			"id": string(s.Node.ID), "type": s.Node.Type, "label": s.Node.Label,
		})
	}
	return mcp.TextWithData(b.String(), map[string]any{"connected": true, "hops": len(steps), "steps": items}), nil
}

// resolveNode turns "team:flamengo-rj", "Flamengo" or "Neymar" into a graph
// node, using the type hint when the text is ambiguous.
func (a *api) resolveNode(entity, typeHint string) (*soccer.Node, *mcp.ToolResult) {
	entity = strings.TrimSpace(entity)
	if entity == "" {
		return nil, mcp.ErrorResult("give an entity id or name")
	}
	g := a.store.Graph
	if n := g.Node(soccer.NodeID(entity)); n != nil {
		return n, nil
	}
	typeHint = strings.ToLower(strings.TrimSpace(typeHint))
	order := []string{"team", "player", "competition", "season", "stadium", "state", "country", "club", "match"}
	if typeHint != "" {
		order = []string{typeHint}
	}
	for _, kind := range order {
		if n := a.lookupNode(kind, entity); n != nil {
			return n, nil
		}
	}
	suggestions := a.store.Teams.Suggest(entity, 5)
	if len(suggestions) > 0 {
		return nil, mcp.ErrorResult("no graph node matches %q. Closest clubs: %s. You can also pass an explicit id such as team:flamengo-rj.",
			entity, strings.Join(suggestions, ", "))
	}
	return nil, mcp.ErrorResult("no graph node matches %q; pass an explicit id such as team:flamengo-rj or player:158023.", entity)
}

func (a *api) lookupNode(kind, entity string) *soccer.Node {
	g := a.store.Graph
	switch kind {
	case "team":
		if t, _, err := a.store.ResolveTeam(entity); err == nil {
			return g.Node(soccer.TeamNode(t.ID))
		}
	case "player":
		if id, err := strconv.Atoi(entity); err == nil {
			if n := g.Node(soccer.PlayerNode(id)); n != nil {
				return n
			}
		}
		page := a.store.FindPlayers(soccer.PlayerFilter{Name: entity, Limit: 1})
		if len(page.Players) > 0 {
			return g.Node(soccer.PlayerNode(page.Players[0].ID))
		}
	case "competition":
		if id, ok := soccer.ResolveCompetition(entity); ok {
			return g.Node(soccer.CompetitionNode(id))
		}
	case "season":
		fields := strings.Fields(entity)
		if len(fields) >= 2 {
			if year, err := strconv.Atoi(fields[len(fields)-1]); err == nil {
				if id, ok := soccer.ResolveCompetition(strings.Join(fields[:len(fields)-1], " ")); ok {
					return g.Node(soccer.SeasonNode(id, year))
				}
			}
		}
	case "stadium":
		return g.Node(soccer.StadiumNode(entity))
	case "state":
		return g.Node(soccer.StateNode(entity))
	case "country":
		return g.Node(soccer.CountryNode(entity))
	case "club":
		return g.Node(soccer.ClubNode(entity))
	case "match":
		return g.Node(soccer.MatchNode(entity))
	}
	return nil
}

func sortStrings(s []string) {
	for i := 1; i < len(s); i++ {
		for j := i; j > 0 && s[j] < s[j-1]; j-- {
			s[j], s[j-1] = s[j-1], s[j]
		}
	}
}
