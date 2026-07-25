// Package mcpserver exposes the Brazilian football knowledge graph over the
// Model Context Protocol.
//
// Context
//
//	The server is built on the official Go MCP SDK
//	(github.com/modelcontextprotocol/go-sdk). It registers 18 tools grouped into
//	the five capability areas of the specification:
//
//	    match queries        find_matches, match_details, find_derbies
//	    team queries         search_teams, team_profile, team_stats, head_to_head
//	    player queries       search_players, player_profile, club_squad
//	    competition queries  list_competitions, competition_standings,
//	                         competition_stats, compare_seasons
//	    statistical analysis team_leaderboard, notable_matches, graph_summary,
//	                         list_datasets
//
//	Every tool returns both a text block (what the model reads back to the
//	user) and typed structured content (what a program consumes); the SDK
//	derives each tool's JSON schema from the Go argument struct, so the schema
//	and the handler cannot drift apart.
//
//	The whole graph is loaded once at start-up (~0.15s, ~17k matches and 18k
//	players) and served read-only from memory, which keeps every tool call far
//	inside the specification's 2 second simple / 5 second aggregate budget.
package mcpserver

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Version is reported to MCP clients during initialize.
const Version = "1.0.0"

// Instructions tell the connected model how to drive the tool set.
const Instructions = `This server answers questions about Brazilian football from six Kaggle datasets
(Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores and the FIFA player database).

Guidance:
- Team names are fuzzy-matched and normalized, so "Flamengo", "Flamengo-RJ" and "CR Flamengo" all work.
  When a name is ambiguous the tool returns candidates; use search_teams to disambiguate.
- Standings, records and averages are CALCULATED from match results, not read from a table.
- The player dataset is a FIFA 19 snapshot and only contains 15 Brazilian clubs; use club_squad to see which.
- Prefer competition_standings for "who won season X", head_to_head for rivalries,
  and team_leaderboard / competition_stats for "which team has the best ..." questions.`

// Server wraps a loaded graph and the MCP server built over it.
type Server struct {
	graph *soccer.Graph
	mcp   *mcp.Server
}

// New builds an MCP server over an already loaded graph.
func New(g *soccer.Graph) *Server {
	s := &Server{graph: g}
	s.mcp = mcp.NewServer(
		&mcp.Implementation{
			Name:    "brazilian-soccer",
			Title:   "Brazilian Soccer Knowledge Graph",
			Version: Version,
		},
		&mcp.ServerOptions{Instructions: Instructions},
	)
	s.registerTools()
	s.registerResources()
	return s
}

// MCP exposes the underlying SDK server, mainly so tests can connect to it
// over an in-memory transport.
func (s *Server) MCP() *mcp.Server { return s.mcp }

// Run serves the MCP protocol over the given transport until the client
// disconnects or ctx is cancelled.
func (s *Server) Run(ctx context.Context, t mcp.Transport) error {
	return s.mcp.Run(ctx, t)
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// text builds a tool result whose content is a single human readable block.
func text(s string) *mcp.CallToolResult {
	return &mcp.CallToolResult{Content: []mcp.Content{&mcp.TextContent{Text: s}}}
}

// clamp bounds a caller supplied limit, applying a default when unset.
func clamp(limit, def, max int) int {
	if limit <= 0 {
		return def
	}
	if limit > max {
		return max
	}
	return limit
}

// resolveCompetition maps an optional competition argument.
func resolveCompetition(arg string) (soccer.Competition, error) {
	if strings.TrimSpace(arg) == "" {
		return "", nil
	}
	c, ok := soccer.ParseCompetition(arg)
	if !ok {
		names := make([]string, 0, len(soccer.AllCompetitions))
		for _, c := range soccer.AllCompetitions {
			names = append(names, string(c))
		}
		return "", fmt.Errorf("unknown competition %q; known competitions: %s", arg, strings.Join(names, ", "))
	}
	return c, nil
}

// ---------------------------------------------------------------------------
// Tool argument and result types
// ---------------------------------------------------------------------------

type emptyArgs struct{}

// datasetsResult wraps the dataset list; MCP output schemas must be objects,
// so no tool may return a bare array.
type datasetsResult struct {
	Datasets []soccer.DatasetInfo `json:"datasets"`
}

type searchTeamsArgs struct {
	Query string `json:"query,omitempty" jsonschema:"team name or fragment; leave empty to list the most active clubs"`
	Limit int    `json:"limit,omitempty" jsonschema:"maximum clubs to return (default 10, max 100)"`
}

type teamSummary struct {
	ID           string   `json:"id"`
	Name         string   `json:"name"`
	State        string   `json:"state,omitempty"`
	StateName    string   `json:"state_name,omitempty"`
	Country      string   `json:"country,omitempty"`
	Matches      int      `json:"matches"`
	Competitions []string `json:"competitions,omitempty"`
	Aliases      []string `json:"aliases,omitempty"`
}

type searchTeamsResult struct {
	Query string        `json:"query"`
	Count int           `json:"count"`
	Teams []teamSummary `json:"teams"`
}

type teamProfileArgs struct {
	Team string `json:"team" jsonschema:"club name, e.g. Palmeiras, Atletico-MG, Vasco"`
}

type teamStatsArgs struct {
	Team        string `json:"team" jsonschema:"club name"`
	Competition string `json:"competition,omitempty" jsonschema:"Serie A, Serie B, Serie C, Copa do Brasil or Libertadores"`
	Season      int    `json:"season,omitempty" jsonschema:"season year, e.g. 2022"`
	Venue       string `json:"venue,omitempty" jsonschema:"any, home or away (default any)"`
}

type findMatchesArgs struct {
	Team        string `json:"team,omitempty" jsonschema:"club whose matches to search"`
	Opponent    string `json:"opponent,omitempty" jsonschema:"restrict to matches against this club"`
	Venue       string `json:"venue,omitempty" jsonschema:"any, home or away - the venue for 'team' (default any)"`
	Competition string `json:"competition,omitempty" jsonschema:"Serie A, Serie B, Serie C, Copa do Brasil or Libertadores"`
	Season      int    `json:"season,omitempty" jsonschema:"season year"`
	DateFrom    string `json:"date_from,omitempty" jsonschema:"earliest date as YYYY, YYYY-MM or YYYY-MM-DD"`
	DateTo      string `json:"date_to,omitempty" jsonschema:"latest date as YYYY, YYYY-MM or YYYY-MM-DD"`
	Stage       string `json:"stage,omitempty" jsonschema:"stage or round filter, e.g. final, semifinals, group stage, round 22"`
	MinGoalDiff int    `json:"min_goal_difference,omitempty" jsonschema:"only matches won by at least this margin"`
	Order       string `json:"order,omitempty" jsonschema:"newest or oldest (default newest)"`
	Limit       int    `json:"limit,omitempty" jsonschema:"maximum matches to return (default 20, max 200)"`
}

type matchesResult struct {
	Total   int             `json:"total"`
	Shown   int             `json:"shown"`
	Matches []*soccer.Match `json:"matches"`
	Summary *soccer.Record  `json:"record,omitempty"`
}

type matchDetailsArgs struct {
	MatchID string `json:"match_id" jsonschema:"match id returned by find_matches"`
}

type headToHeadArgs struct {
	TeamA       string `json:"team_a" jsonschema:"first club"`
	TeamB       string `json:"team_b" jsonschema:"second club"`
	Competition string `json:"competition,omitempty" jsonschema:"restrict to one competition"`
	Season      int    `json:"season,omitempty" jsonschema:"restrict to one season"`
	Limit       int    `json:"limit,omitempty" jsonschema:"maximum matches to list (default 10, max 200)"`
}

type standingsArgs struct {
	Competition string `json:"competition,omitempty" jsonschema:"competition (default Serie A)"`
	Season      int    `json:"season" jsonschema:"season year, e.g. 2019"`
}

type competitionInfo struct {
	Competition string `json:"competition"`
	Seasons     []int  `json:"seasons"`
	Matches     int    `json:"matches"`
	Clubs       int    `json:"clubs"`
}

type listCompetitionsResult struct {
	Competitions []competitionInfo `json:"competitions"`
}

type competitionStatsArgs struct {
	Competition string `json:"competition,omitempty" jsonschema:"competition; omit for all competitions"`
	Season      int    `json:"season,omitempty" jsonschema:"season year; omit for all seasons"`
}

type leaderboardArgs struct {
	Metric      string `json:"metric,omitempty" jsonschema:"points, wins, win_rate, goals_for, goals_against or goal_difference (default points)"`
	Competition string `json:"competition,omitempty" jsonschema:"competition filter"`
	Season      int    `json:"season,omitempty" jsonschema:"season filter"`
	Venue       string `json:"venue,omitempty" jsonschema:"any, home or away - use home/away for best home or away record questions"`
	MinMatches  int    `json:"min_matches,omitempty" jsonschema:"ignore clubs with fewer matches than this (default 10)"`
	Limit       int    `json:"limit,omitempty" jsonschema:"maximum clubs (default 10, max 100)"`
}

type notableMatchesArgs struct {
	Kind        string `json:"kind,omitempty" jsonschema:"biggest_wins or highest_scoring (default biggest_wins)"`
	Competition string `json:"competition,omitempty" jsonschema:"competition filter"`
	Season      int    `json:"season,omitempty" jsonschema:"season filter"`
	Limit       int    `json:"limit,omitempty" jsonschema:"maximum matches (default 10, max 100)"`
}

type compareSeasonsArgs struct {
	Competition string `json:"competition,omitempty" jsonschema:"competition (default Serie A)"`
	SeasonA     int    `json:"season_a" jsonschema:"first season"`
	SeasonB     int    `json:"season_b" jsonschema:"second season"`
}

type derbiesArgs struct {
	Team        string `json:"team,omitempty" jsonschema:"restrict to derbies involving this club"`
	Competition string `json:"competition,omitempty" jsonschema:"competition filter"`
	Season      int    `json:"season,omitempty" jsonschema:"season filter"`
	Limit       int    `json:"limit,omitempty" jsonschema:"maximum matches per rivalry (default 5, max 50)"`
}

type derbiesResult struct {
	Count   int            `json:"count"`
	Derbies []soccer.Derby `json:"derbies"`
}

type searchPlayersArgs struct {
	Name          string `json:"name,omitempty" jsonschema:"full or partial player name"`
	Nationality   string `json:"nationality,omitempty" jsonschema:"nationality, e.g. Brazil"`
	Club          string `json:"club,omitempty" jsonschema:"club name as spelled in the FIFA data, or a Brazilian club in the graph"`
	Position      string `json:"position,omitempty" jsonschema:"exact FIFA position code, e.g. ST, GK, CAM"`
	PositionGroup string `json:"position_group,omitempty" jsonschema:"Goalkeeper, Defender, Midfielder or Forward"`
	MinOverall    int    `json:"min_overall,omitempty" jsonschema:"minimum FIFA overall rating"`
	MinPotential  int    `json:"min_potential,omitempty" jsonschema:"minimum FIFA potential rating"`
	MaxAge        int    `json:"max_age,omitempty" jsonschema:"maximum age"`
	MinAge        int    `json:"min_age,omitempty" jsonschema:"minimum age"`
	SortBy        string `json:"sort_by,omitempty" jsonschema:"overall, potential, age, name or growth (default overall)"`
	GroupByClub   bool   `json:"group_by_club,omitempty" jsonschema:"also return a per-club breakdown of the matched players"`
	Limit         int    `json:"limit,omitempty" jsonschema:"maximum players (default 20, max 200)"`
}

type searchPlayersResult struct {
	Total   int                        `json:"total"`
	Shown   int                        `json:"shown"`
	Players []*soccer.Player           `json:"players"`
	ByClub  []soccer.ClubPlayerSummary `json:"by_club,omitempty"`
}

type playerProfileArgs struct {
	Name string `json:"name,omitempty" jsonschema:"player name"`
	ID   int    `json:"id,omitempty" jsonschema:"FIFA player id"`
}

type clubSquadArgs struct {
	Club  string `json:"club" jsonschema:"club name"`
	Limit int    `json:"limit,omitempty" jsonschema:"maximum players (default 25, max 100)"`
}

type clubSquadResult struct {
	Club           *soccer.Club     `json:"club"`
	Players        []*soccer.Player `json:"players"`
	InFIFADataset  bool             `json:"in_fifa_dataset"`
	AvailableClubs []string         `json:"clubs_available_in_fifa_dataset,omitempty"`
	MatchRecord    *soccer.Record   `json:"match_record,omitempty"`
}

// ---------------------------------------------------------------------------
// Tool registration
// ---------------------------------------------------------------------------

func (s *Server) registerTools() {
	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "list_datasets",
		Description: "List the loaded source datasets with row counts, licences and coverage. Use this to answer questions about what data is available or where a number came from.",
	}, s.listDatasets)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "graph_summary",
		Description: "Summarise the knowledge graph: club, match and player node counts, edges, competitions and season coverage.",
	}, s.graphSummary)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "search_teams",
		Description: "Find clubs by name or fragment. Handles accents, state suffixes and abbreviations; use it to disambiguate names like Atletico or America.",
	}, s.searchTeams)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "team_profile",
		Description: "Overall profile of one club: identity, the competitions and seasons it appears in, its all-time record and its FIFA squad if present.",
	}, s.teamProfile)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "team_stats",
		Description: "Win/draw/loss record, goals and win rate for a club, optionally scoped to a competition, a season and home or away matches.",
	}, s.teamStats)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "find_matches",
		Description: "Search matches by team, opponent, venue, competition, season, date range or stage. This is the general purpose match query.",
	}, s.findMatches)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "match_details",
		Description: "Full detail for one match including stadium, round, sources and any shot, corner and attack statistics.",
	}, s.matchDetails)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "head_to_head",
		Description: "Head-to-head record and meeting list between two clubs, with the popular name of the fixture when it is a classic derby.",
	}, s.headToHead)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "competition_standings",
		Description: "League table for a competition season, calculated from match results, marking the champion and the relegation places.",
	}, s.competitionStandings)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "list_competitions",
		Description: "List the competitions in the graph with the seasons, match counts and club counts available for each.",
	}, s.listCompetitions)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "competition_stats",
		Description: "Aggregate statistics for a competition or season: goals per match, home advantage, clean sheets, biggest win and highest scoring match.",
	}, s.competitionStats)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "team_leaderboard",
		Description: "Rank clubs by points, wins, win rate, goals scored, goals conceded or goal difference. Set venue to home or away for best home/away record questions.",
	}, s.teamLeaderboard)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "notable_matches",
		Description: "The biggest victories or highest scoring matches in a competition or season.",
	}, s.notableMatches)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "compare_seasons",
		Description: "Compare two seasons of a competition: champions, goals per match, home advantage and how they moved.",
	}, s.compareSeasons)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "find_derbies",
		Description: "Find matches between traditional rivals (Fla-Flu, Derby Paulista, Gre-Nal, Clássico Mineiro and others), optionally scoped to a club, competition or season.",
	}, s.findDerbies)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "search_players",
		Description: "Search the FIFA player dataset by name, nationality, club, position, rating and age. Use nationality=Brazil for Brazilian players.",
	}, s.searchPlayers)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "player_profile",
		Description: "Full profile for one player: ratings, physical attributes, contract values and best skill attributes.",
	}, s.playerProfile)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "club_squad",
		Description: "The FIFA squad for a club, linked to that club's match record. Reports honestly when a club is absent from the FIFA dataset and lists the Brazilian clubs that are present.",
	}, s.clubSquad)
}

func (s *Server) registerResources() {
	s.mcp.AddResource(&mcp.Resource{
		URI:         "brazilian-soccer://datasets",
		Name:        "datasets",
		Title:       "Source datasets and licences",
		Description: "Provenance, licence and coverage of the six Kaggle CSV files behind this server.",
		MIMEType:    "application/json",
	}, func(ctx context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
		body, err := json.MarshalIndent(s.graph.Datasets(), "", "  ")
		if err != nil {
			return nil, err
		}
		return &mcp.ReadResourceResult{Contents: []*mcp.ResourceContents{{
			URI: req.Params.URI, MIMEType: "application/json", Text: string(body),
		}}}, nil
	})

	s.mcp.AddResource(&mcp.Resource{
		URI:         "brazilian-soccer://graph",
		Name:        "graph",
		Title:       "Knowledge graph summary",
		Description: "Node and edge counts, competitions and season coverage of the knowledge graph.",
		MIMEType:    "application/json",
	}, func(ctx context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
		body, err := json.MarshalIndent(s.graph.Summary(), "", "  ")
		if err != nil {
			return nil, err
		}
		return &mcp.ReadResourceResult{Contents: []*mcp.ResourceContents{{
			URI: req.Params.URI, MIMEType: "application/json", Text: string(body),
		}}}, nil
	})
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

func (s *Server) listDatasets(ctx context.Context, _ *mcp.CallToolRequest, _ emptyArgs) (*mcp.CallToolResult, datasetsResult, error) {
	sets := s.graph.Datasets()
	var b strings.Builder
	b.WriteString("Loaded datasets:\n")
	for _, d := range sets {
		fmt.Fprintf(&b, "- %s: %s\n", d.File, d.Description)
		fmt.Fprintf(&b, "  rows: %d, loaded: %d", d.Rows, d.Loaded)
		if d.Rejected > 0 {
			fmt.Fprintf(&b, ", rejected as inconsistent: %d", d.Rejected)
		}
		if d.SeasonMin > 0 {
			fmt.Fprintf(&b, ", seasons: %d-%d", d.SeasonMin, d.SeasonMax)
		}
		fmt.Fprintf(&b, "\n  licence: %s\n  source: %s\n", d.License, d.Source)
	}
	b.WriteString("\nMatches present in several files are merged into a single fixture, so totals are lower than the sum of the row counts.\n")
	return text(b.String()), datasetsResult{Datasets: sets}, nil
}

func (s *Server) graphSummary(ctx context.Context, _ *mcp.CallToolRequest, _ emptyArgs) (*mcp.CallToolResult, soccer.Stats, error) {
	st := s.graph.Summary()
	var b strings.Builder
	fmt.Fprintf(&b, "Brazilian football knowledge graph:\n")
	fmt.Fprintf(&b, "- Clubs: %d\n- Matches: %d\n- Players: %d\n", st.Clubs, st.Matches, st.Players)
	fmt.Fprintf(&b, "- Competitions: %d across %d competition-seasons (%s)\n", st.Competitions, st.Seasons, st.SeasonRange)
	fmt.Fprintf(&b, "- Edges: %d (home_of, away_of, part_of, plays_for)\n", st.Edges)
	b.WriteString("\nCoverage by competition:\n")
	for _, c := range s.graph.CompetitionsPresent() {
		seasons := s.graph.Seasons(c)
		fmt.Fprintf(&b, "- %s: %d seasons (%d-%d)\n", c, len(seasons), seasons[0], seasons[len(seasons)-1])
	}
	return text(b.String()), st, nil
}

func (s *Server) searchTeams(ctx context.Context, _ *mcp.CallToolRequest, args searchTeamsArgs) (*mcp.CallToolResult, searchTeamsResult, error) {
	limit := clamp(args.Limit, 10, 100)
	clubs := s.graph.SearchClubs(args.Query, limit)
	res := searchTeamsResult{Query: args.Query, Count: len(clubs)}
	var b strings.Builder
	if args.Query == "" {
		b.WriteString("Most active clubs in the graph:\n")
	} else {
		fmt.Fprintf(&b, "Clubs matching %q:\n", args.Query)
	}
	if len(clubs) == 0 {
		b.WriteString("No clubs matched.\n")
	}
	for _, c := range clubs {
		summary := s.teamSummaryFor(c)
		res.Teams = append(res.Teams, summary)
		fmt.Fprintf(&b, "- %s (id: %s) - %d matches", c.Label(), c.ID, c.Matches)
		if len(summary.Competitions) > 0 {
			fmt.Fprintf(&b, ", competitions: %s", strings.Join(summary.Competitions, ", "))
		}
		b.WriteString("\n")
	}
	return text(b.String()), res, nil
}

func (s *Server) teamSummaryFor(c *soccer.Club) teamSummary {
	comps := map[soccer.Competition]bool{}
	for _, m := range s.graph.ClubMatches(c.ID) {
		comps[m.Competition] = true
	}
	var list []string
	for _, comp := range soccer.AllCompetitions {
		if comps[comp] {
			list = append(list, string(comp))
		}
	}
	aliases := c.Aliases
	if len(aliases) > 6 {
		aliases = aliases[:6]
	}
	ts := teamSummary{
		ID: c.ID, Name: c.Name, State: c.State, Country: c.Country,
		Matches: c.Matches, Competitions: list, Aliases: aliases,
	}
	if soccer.IsBrazilianState(c.State) {
		ts.StateName = soccer.RegionName(c.State)
	}
	return ts
}

func (s *Server) teamProfile(ctx context.Context, _ *mcp.CallToolRequest, args teamProfileArgs) (*mcp.CallToolResult, soccer.TeamStats, error) {
	club, err := s.graph.MustResolveClub(args.Team)
	if err != nil {
		return nil, soccer.TeamStats{}, err
	}
	ts := s.graph.TeamStats(club, "", 0, soccer.VenueAny)

	var b strings.Builder
	fmt.Fprintf(&b, "%s (id: %s)\n", club.Label(), club.ID)
	if club.State != "" {
		fmt.Fprintf(&b, "- State/region: %s (%s)\n", soccer.RegionName(club.State), club.State)
	}
	if club.Country != "" {
		fmt.Fprintf(&b, "- Country: %s\n", club.Country)
	}
	if len(club.Aliases) > 0 {
		fmt.Fprintf(&b, "- Known in the data as: %s\n", strings.Join(club.Aliases, "; "))
	}
	b.WriteString("\n")
	b.WriteString(soccer.FormatTeamStats(ts))

	if squad := s.graph.PlayersAtClub(club.ID); len(squad) > 0 {
		fmt.Fprintf(&b, "\nFIFA squad in dataset: %d players, best: %s (%d overall)\n",
			len(squad), squad[0].Name, squad[0].Overall)
	}
	return text(b.String()), ts, nil
}

func (s *Server) teamStats(ctx context.Context, _ *mcp.CallToolRequest, args teamStatsArgs) (*mcp.CallToolResult, soccer.TeamStats, error) {
	club, err := s.graph.MustResolveClub(args.Team)
	if err != nil {
		return nil, soccer.TeamStats{}, err
	}
	comp, err := resolveCompetition(args.Competition)
	if err != nil {
		return nil, soccer.TeamStats{}, err
	}
	ts := s.graph.TeamStats(club, comp, args.Season, soccer.ParseVenue(args.Venue))
	if ts.Overall.Played == 0 && ts.Overall.Unscored == 0 {
		return nil, ts, fmt.Errorf("no matches found for %s with those filters; %s appears in %s",
			club.Name, club.Name, s.competitionsForClub(club))
	}
	return text(soccer.FormatTeamStats(ts)), ts, nil
}

func (s *Server) competitionsForClub(club *soccer.Club) string {
	seen := map[soccer.Competition][]int{}
	for _, m := range s.graph.ClubMatches(club.ID) {
		years := seen[m.Competition]
		if len(years) == 0 || years[len(years)-1] != m.Season {
			seen[m.Competition] = append(years, m.Season)
		}
	}
	if len(seen) == 0 {
		return "no competitions in this dataset"
	}
	var parts []string
	for _, c := range soccer.AllCompetitions {
		if years, ok := seen[c]; ok {
			lo, hi := years[0], years[0]
			for _, y := range years {
				if y < lo {
					lo = y
				}
				if y > hi {
					hi = y
				}
			}
			parts = append(parts, fmt.Sprintf("%s (%d-%d)", c, lo, hi))
		}
	}
	return strings.Join(parts, ", ")
}

func (s *Server) findMatches(ctx context.Context, _ *mcp.CallToolRequest, args findMatchesArgs) (*mcp.CallToolResult, matchesResult, error) {
	filter := soccer.MatchFilter{
		Venue:       soccer.ParseVenue(args.Venue),
		Stage:       args.Stage,
		Season:      args.Season,
		MinGoalDiff: args.MinGoalDiff,
		Newest:      !strings.EqualFold(args.Order, "oldest"),
	}
	var club *soccer.Club
	var err error
	if args.Team != "" {
		club, err = s.graph.MustResolveClub(args.Team)
		if err != nil {
			return nil, matchesResult{}, err
		}
		filter.ClubID = club.ID
	}
	if args.Opponent != "" {
		opp, err := s.graph.MustResolveClub(args.Opponent)
		if err != nil {
			return nil, matchesResult{}, err
		}
		filter.OpponentID = opp.ID
	}
	if filter.Competition, err = resolveCompetition(args.Competition); err != nil {
		return nil, matchesResult{}, err
	}
	if filter.DateFrom, err = soccer.ParseDateArg(args.DateFrom, false); err != nil {
		return nil, matchesResult{}, err
	}
	if filter.DateTo, err = soccer.ParseDateArg(args.DateTo, true); err != nil {
		return nil, matchesResult{}, err
	}

	all := s.graph.FindMatches(filter)
	limit := clamp(args.Limit, 20, 200)
	shown := all
	if len(shown) > limit {
		shown = shown[:limit]
	}

	res := matchesResult{Total: len(all), Shown: len(shown), Matches: shown}
	title := "Matches"
	if club != nil {
		title = club.Name + " matches"
		rec := soccer.BuildRecord(club, all)
		res.Summary = &rec
	}
	if args.Opponent != "" {
		title += " vs " + args.Opponent
	}
	body := soccer.FormatMatchList(title+":", shown, len(all))
	if res.Summary != nil && res.Summary.Played > 0 {
		body += fmt.Sprintf("\nRecord across all %d matching matches: %s\n", len(all), res.Summary.Summary())
	}
	return text(body), res, nil
}

func (s *Server) matchDetails(ctx context.Context, _ *mcp.CallToolRequest, args matchDetailsArgs) (*mcp.CallToolResult, *soccer.Match, error) {
	m := s.graph.Match(args.MatchID)
	if m == nil {
		return nil, nil, fmt.Errorf("no match with id %q; ids come from find_matches", args.MatchID)
	}
	body := soccer.FormatMatchDetail(m, s.graph.Club(m.HomeClubID), s.graph.Club(m.AwayClubID))
	return text(body), m, nil
}

func (s *Server) headToHead(ctx context.Context, _ *mcp.CallToolRequest, args headToHeadArgs) (*mcp.CallToolResult, soccer.HeadToHead, error) {
	a, err := s.graph.MustResolveClub(args.TeamA)
	if err != nil {
		return nil, soccer.HeadToHead{}, err
	}
	b, err := s.graph.MustResolveClub(args.TeamB)
	if err != nil {
		return nil, soccer.HeadToHead{}, err
	}
	if a.ID == b.ID {
		return nil, soccer.HeadToHead{}, fmt.Errorf("team_a and team_b both resolve to %s", a.Label())
	}
	comp, err := resolveCompetition(args.Competition)
	if err != nil {
		return nil, soccer.HeadToHead{}, err
	}
	h := s.graph.HeadToHead(a, b, comp, args.Season, clamp(args.Limit, 10, 200))
	return text(soccer.FormatHeadToHead(h)), h, nil
}

func (s *Server) competitionStandings(ctx context.Context, _ *mcp.CallToolRequest, args standingsArgs) (*mcp.CallToolResult, soccer.Standings, error) {
	comp, err := resolveCompetition(args.Competition)
	if err != nil {
		return nil, soccer.Standings{}, err
	}
	if comp == "" {
		comp = soccer.SerieA
	}
	st, err := s.graph.Standings(comp, args.Season)
	if err != nil {
		return nil, soccer.Standings{}, err
	}
	return text(soccer.FormatStandings(st)), st, nil
}

func (s *Server) listCompetitions(ctx context.Context, _ *mcp.CallToolRequest, _ emptyArgs) (*mcp.CallToolResult, listCompetitionsResult, error) {
	var res listCompetitionsResult
	var b strings.Builder
	b.WriteString("Competitions in the knowledge graph:\n")
	for _, c := range s.graph.CompetitionsPresent() {
		seasons := s.graph.Seasons(c)
		matches, clubs := 0, map[string]bool{}
		for _, y := range seasons {
			for _, m := range s.graph.CompetitionMatches(c, y) {
				matches++
				clubs[m.HomeClubID] = true
				clubs[m.AwayClubID] = true
			}
		}
		res.Competitions = append(res.Competitions, competitionInfo{
			Competition: string(c), Seasons: seasons, Matches: matches, Clubs: len(clubs),
		})
		fmt.Fprintf(&b, "- %s: seasons %d-%d (%d seasons), %d matches, %d clubs\n",
			c, seasons[0], seasons[len(seasons)-1], len(seasons), matches, len(clubs))
	}
	return text(b.String()), res, nil
}

func (s *Server) competitionStats(ctx context.Context, _ *mcp.CallToolRequest, args competitionStatsArgs) (*mcp.CallToolResult, soccer.Aggregate, error) {
	comp, err := resolveCompetition(args.Competition)
	if err != nil {
		return nil, soccer.Aggregate{}, err
	}
	agg := s.graph.AggregateStats(comp, args.Season)
	if agg.Matches == 0 {
		return nil, agg, fmt.Errorf("no matches for those filters")
	}
	return text(soccer.FormatAggregate(agg)), agg, nil
}

func (s *Server) teamLeaderboard(ctx context.Context, _ *mcp.CallToolRequest, args leaderboardArgs) (*mcp.CallToolResult, soccer.Leaderboard, error) {
	comp, err := resolveCompetition(args.Competition)
	if err != nil {
		return nil, soccer.Leaderboard{}, err
	}
	minMatches := args.MinMatches
	if minMatches <= 0 {
		minMatches = 10
	}
	lb, err := s.graph.Leaderboard(args.Metric, comp, args.Season,
		soccer.ParseVenue(args.Venue), minMatches, clamp(args.Limit, 10, 100))
	if err != nil {
		return nil, soccer.Leaderboard{}, err
	}
	return text(soccer.FormatLeaderboard(lb)), lb, nil
}

func (s *Server) notableMatches(ctx context.Context, _ *mcp.CallToolRequest, args notableMatchesArgs) (*mcp.CallToolResult, matchesResult, error) {
	comp, err := resolveCompetition(args.Competition)
	if err != nil {
		return nil, matchesResult{}, err
	}
	limit := clamp(args.Limit, 10, 100)
	var matches []*soccer.Match
	var title string
	switch strings.ToLower(strings.TrimSpace(args.Kind)) {
	case "highest_scoring":
		matches = s.graph.HighestScoring(comp, args.Season, limit)
		title = "Highest scoring matches"
	case "", "biggest_wins":
		matches = s.graph.BiggestWins(comp, args.Season, limit)
		title = "Biggest victories"
	default:
		return nil, matchesResult{}, fmt.Errorf("unknown kind %q; use biggest_wins or highest_scoring", args.Kind)
	}
	scope := "all competitions"
	if comp != "" {
		scope = string(comp)
	}
	if args.Season != 0 {
		scope += fmt.Sprintf(" %d", args.Season)
	}
	res := matchesResult{Total: len(matches), Shown: len(matches), Matches: matches}
	return text(soccer.FormatMatchList(fmt.Sprintf("%s in %s:", title, scope), matches, len(matches))), res, nil
}

func (s *Server) compareSeasons(ctx context.Context, _ *mcp.CallToolRequest, args compareSeasonsArgs) (*mcp.CallToolResult, soccer.SeasonComparison, error) {
	comp, err := resolveCompetition(args.Competition)
	if err != nil {
		return nil, soccer.SeasonComparison{}, err
	}
	if comp == "" {
		comp = soccer.SerieA
	}
	sc, err := s.graph.CompareSeasons(comp, args.SeasonA, args.SeasonB)
	if err != nil {
		return nil, soccer.SeasonComparison{}, err
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s: %d vs %d\n\n", comp, args.SeasonA, args.SeasonB)
	b.WriteString(soccer.FormatAggregate(sc.A))
	if sc.ChampionA != "" {
		fmt.Fprintf(&b, "- Winner: %s\n", sc.ChampionA)
	}
	b.WriteString("\n")
	b.WriteString(soccer.FormatAggregate(sc.B))
	if sc.ChampionB != "" {
		fmt.Fprintf(&b, "- Winner: %s\n", sc.ChampionB)
	}
	fmt.Fprintf(&b, "\nChange from %d to %d:\n", args.SeasonA, args.SeasonB)
	fmt.Fprintf(&b, "- Goals per match: %+.2f\n", sc.Deltas["goals_per_match"])
	fmt.Fprintf(&b, "- Home win rate: %+.1f pp\n", sc.Deltas["home_win_pct"])
	fmt.Fprintf(&b, "- Draw rate: %+.1f pp\n", sc.Deltas["draw_pct"])
	fmt.Fprintf(&b, "- Total goals: %+.0f over %+.0f matches\n", sc.Deltas["total_goals"], sc.Deltas["matches"])
	return text(b.String()), sc, nil
}

func (s *Server) findDerbies(ctx context.Context, _ *mcp.CallToolRequest, args derbiesArgs) (*mcp.CallToolResult, derbiesResult, error) {
	comp, err := resolveCompetition(args.Competition)
	if err != nil {
		return nil, derbiesResult{}, err
	}
	clubID := ""
	if args.Team != "" {
		club, err := s.graph.MustResolveClub(args.Team)
		if err != nil {
			return nil, derbiesResult{}, err
		}
		clubID = club.ID
	}
	derbies := s.graph.Derbies(comp, args.Season, clubID, clamp(args.Limit, 5, 50))

	var b strings.Builder
	scope := "all competitions and seasons"
	if comp != "" {
		scope = string(comp)
	}
	if args.Season != 0 {
		scope += fmt.Sprintf(" %d", args.Season)
	}
	fmt.Fprintf(&b, "Classic rivalries in %s:\n", scope)
	if len(derbies) == 0 {
		b.WriteString("No derby matches found for those filters.\n")
	}
	for _, d := range derbies {
		fmt.Fprintf(&b, "\n%s (%s vs %s):\n", d.Name, d.ClubA, d.ClubB)
		for _, m := range d.Matches {
			fmt.Fprintf(&b, "- %s\n", m.Describe())
		}
	}
	return text(b.String()), derbiesResult{Count: len(derbies), Derbies: derbies}, nil
}

func (s *Server) searchPlayers(ctx context.Context, _ *mcp.CallToolRequest, args searchPlayersArgs) (*mcp.CallToolResult, searchPlayersResult, error) {
	filter := soccer.PlayerFilter{
		Name: args.Name, Nationality: args.Nationality, Club: args.Club,
		Position: args.Position, PositionGroup: args.PositionGroup,
		MinOverall: args.MinOverall, MinPotential: args.MinPotential,
		MinAge: args.MinAge, MaxAge: args.MaxAge, SortBy: args.SortBy,
	}
	// A club name that resolves to a graph club is translated into the linked
	// FIFA club, so "Sport" or "Atletico-MG" work as well as the FIFA spelling.
	if args.Club != "" {
		if club, _ := s.graph.ResolveClub(args.Club); club != nil && len(s.graph.PlayersAtClub(club.ID)) > 0 {
			filter.ClubID = club.ID
			filter.Club = ""
		}
	}

	all := s.graph.SearchPlayers(filter)
	limit := clamp(args.Limit, 20, 200)
	shown := all
	if len(shown) > limit {
		shown = shown[:limit]
	}
	res := searchPlayersResult{Total: len(all), Shown: len(shown), Players: shown}

	title := describePlayerQuery(args)
	body := soccer.FormatPlayerList(title, shown, len(all))
	if args.GroupByClub {
		res.ByClub = soccer.SummarizeByClub(all)
		byClub := res.ByClub
		if len(byClub) > 25 {
			byClub = byClub[:25]
		}
		body += "\n" + soccer.FormatClubSummaries("By club:", byClub)
	}
	if len(all) == 0 && args.Club != "" {
		body += "\n" + s.fifaClubHint()
	}
	return text(body), res, nil
}

func describePlayerQuery(args searchPlayersArgs) string {
	var parts []string
	if args.Name != "" {
		parts = append(parts, fmt.Sprintf("name contains %q", args.Name))
	}
	if args.Nationality != "" {
		parts = append(parts, "nationality "+args.Nationality)
	}
	if args.Club != "" {
		parts = append(parts, "club "+args.Club)
	}
	if args.Position != "" {
		parts = append(parts, "position "+args.Position)
	}
	if args.PositionGroup != "" {
		parts = append(parts, args.PositionGroup+"s")
	}
	if args.MinOverall > 0 {
		parts = append(parts, fmt.Sprintf("overall >= %d", args.MinOverall))
	}
	if args.MaxAge > 0 {
		parts = append(parts, fmt.Sprintf("age <= %d", args.MaxAge))
	}
	if len(parts) == 0 {
		return "Players (highest rated first):"
	}
	return "Players matching " + strings.Join(parts, ", ") + ":"
}

func (s *Server) fifaClubHint() string {
	clubs := s.graph.LinkedFIFAClubs()
	names := make([]string, 0, len(clubs))
	for _, c := range clubs {
		names = append(names, c.Name)
	}
	return fmt.Sprintf("Note: the FIFA player dataset is a FIFA 19 snapshot and only licenses %d Brazilian clubs: %s.\n",
		len(names), strings.Join(names, ", "))
}

func (s *Server) playerProfile(ctx context.Context, _ *mcp.CallToolRequest, args playerProfileArgs) (*mcp.CallToolResult, *soccer.Player, error) {
	if args.ID != 0 {
		if p := s.graph.PlayerByID(args.ID); p != nil {
			return text(soccer.FormatPlayerProfile(p, nil)), p, nil
		}
		return nil, nil, fmt.Errorf("no player with FIFA id %d", args.ID)
	}
	if strings.TrimSpace(args.Name) == "" {
		return nil, nil, fmt.Errorf("provide either name or id")
	}
	p, others := s.graph.FindPlayer(args.Name)
	if p == nil {
		return nil, nil, fmt.Errorf("no player matching %q in the FIFA dataset", args.Name)
	}
	if len(others) > 4 {
		others = others[:4]
	}
	return text(soccer.FormatPlayerProfile(p, others)), p, nil
}

func (s *Server) clubSquad(ctx context.Context, _ *mcp.CallToolRequest, args clubSquadArgs) (*mcp.CallToolResult, clubSquadResult, error) {
	club, err := s.graph.MustResolveClub(args.Club)
	if err != nil {
		return nil, clubSquadResult{}, err
	}
	squad := s.graph.PlayersAtClub(club.ID)
	limit := clamp(args.Limit, 25, 100)
	shown := squad
	if len(shown) > limit {
		shown = shown[:limit]
	}
	record := soccer.BuildRecord(club, s.graph.ClubMatches(club.ID))
	res := clubSquadResult{
		Club: club, Players: shown, InFIFADataset: len(squad) > 0, MatchRecord: &record,
	}

	var b strings.Builder
	if len(squad) == 0 {
		fmt.Fprintf(&b, "%s is not in the FIFA player dataset.\n\n", club.Label())
		b.WriteString(s.fifaClubHint())
		for _, c := range s.graph.LinkedFIFAClubs() {
			res.AvailableClubs = append(res.AvailableClubs, c.Name)
		}
	} else {
		b.WriteString(soccer.FormatPlayerList(fmt.Sprintf("%s squad in the FIFA dataset (%d players):", club.Label(), len(squad)), shown, len(squad)))
	}
	fmt.Fprintf(&b, "\nMatch record in the knowledge graph: %s\n", record.Summary())
	return text(b.String()), res, nil
}
