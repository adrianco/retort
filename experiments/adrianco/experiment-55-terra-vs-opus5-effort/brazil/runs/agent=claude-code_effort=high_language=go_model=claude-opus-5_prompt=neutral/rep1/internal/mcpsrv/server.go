// Package mcpsrv exposes the Brazilian soccer knowledge graph as a Model
// Context Protocol server.
//
// Every tool returns two things: a human-readable text block formatted the way
// the specification's examples show, and the same answer as validated
// structured JSON. An LLM can therefore quote the text directly or drill into
// the structure, and clients that do not support structured content still get a
// usable answer.
package mcpsrv

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// Version is reported to MCP clients during initialisation.
const Version = "1.0.0"

// Server wraps the knowledge graph and the MCP server built over it.
type Server struct {
	Graph *soccer.Graph
	MCP   *mcp.Server
}

// New builds the MCP server and registers every tool, resource and prompt.
func New(g *soccer.Graph) *Server {
	impl := &mcp.Implementation{
		Name:    "brazilian-soccer",
		Title:   "Brazilian Soccer Knowledge Graph",
		Version: Version,
	}
	s := &Server{
		Graph: g,
		MCP: mcp.NewServer(impl, &mcp.ServerOptions{
			Instructions: instructions,
		}),
	}
	s.registerTools()
	s.registerResources()
	s.registerPrompts()
	return s
}

const instructions = `This server answers natural-language questions about Brazilian soccer from six
Kaggle datasets: Campeonato Brasileiro Série A (2003-2023), Série B and C
(2014-2023), Copa do Brasil (2012-2023), Copa Libertadores (2013-2022) and the
FIFA 19 player database.

Guidance:
  * Club names are matched loosely — "Sao Paulo", "São Paulo-SP" and "São Paulo"
    all resolve to the same club. If a name is ambiguous (for example
    "Atletico", which exists in seven Brazilian states) the tool says so and
    lists the candidates; call search_teams to disambiguate.
  * League tables are computed from the raw match results, not copied from a
    standings file, so a champion is only named when every fixture is present.
  * The FIFA player dataset is a snapshot of FIFA 19 and only licenses fifteen
    Brazilian clubs; club_squad reports which ones when a lookup comes back
    empty. Goalscorer data is not present in any of the datasets.`

// ---------------------------------------------------------------------------
// Tool input types
// ---------------------------------------------------------------------------

type emptyInput struct{}

type searchTeamsInput struct {
	Query string `json:"query" jsonschema:"club name or fragment to look up, e.g. \"Flamengo\", \"atletico mg\", \"São Paulo\""`
	Limit int    `json:"limit,omitempty" jsonschema:"maximum number of candidates to return (default 10)"`
}

type searchMatchesInput struct {
	Team        string `json:"team,omitempty" jsonschema:"club that played in the match, home or away"`
	Opponent    string `json:"opponent,omitempty" jsonschema:"restrict to matches between team and this opponent"`
	HomeTeam    string `json:"home_team,omitempty" jsonschema:"club that played at home"`
	AwayTeam    string `json:"away_team,omitempty" jsonschema:"club that played away"`
	Competition string `json:"competition,omitempty" jsonschema:"serie-a, serie-b, serie-c, copa-do-brasil or libertadores"`
	Season      int    `json:"season,omitempty" jsonschema:"single season year, e.g. 2023"`
	SeasonFrom  int    `json:"season_from,omitempty" jsonschema:"first season of an inclusive range"`
	SeasonTo    int    `json:"season_to,omitempty" jsonschema:"last season of an inclusive range"`
	DateFrom    string `json:"date_from,omitempty" jsonschema:"earliest match date (YYYY-MM-DD or DD/MM/YYYY)"`
	DateTo      string `json:"date_to,omitempty" jsonschema:"latest match date (YYYY-MM-DD or DD/MM/YYYY)"`
	Round       int    `json:"round,omitempty" jsonschema:"league round number"`
	Stage       string `json:"stage,omitempty" jsonschema:"knockout stage: final, semifinals, quarterfinals, round of 16 or group stage"`
	Venue       string `json:"venue,omitempty" jsonschema:"home or away - interpreted relative to \"team\""`
	MinGoalDiff int    `json:"min_goal_difference,omitempty" jsonschema:"only matches won by at least this margin"`
	MinGoals    int    `json:"min_total_goals,omitempty" jsonschema:"only matches with at least this many goals"`
	DerbiesOnly bool   `json:"derbies_only,omitempty" jsonschema:"only matches between traditional rivals"`
	Sort        string `json:"sort,omitempty" jsonschema:"date_desc (default), date_asc, goal_diff or total_goals"`
	Limit       int    `json:"limit,omitempty" jsonschema:"maximum matches to list (default 25)"`
}

type headToHeadInput struct {
	TeamA       string `json:"team_a" jsonschema:"first club"`
	TeamB       string `json:"team_b" jsonschema:"second club"`
	Competition string `json:"competition,omitempty" jsonschema:"restrict to one competition"`
	SeasonFrom  int    `json:"season_from,omitempty" jsonschema:"first season of an inclusive range"`
	SeasonTo    int    `json:"season_to,omitempty" jsonschema:"last season of an inclusive range"`
	Limit       int    `json:"limit,omitempty" jsonschema:"maximum meetings to list (default 20)"`
}

type teamStatsInput struct {
	Team        string `json:"team" jsonschema:"club to report on"`
	Competition string `json:"competition,omitempty" jsonschema:"restrict to one competition"`
	Season      int    `json:"season,omitempty" jsonschema:"single season year"`
	SeasonFrom  int    `json:"season_from,omitempty" jsonschema:"first season of an inclusive range"`
	SeasonTo    int    `json:"season_to,omitempty" jsonschema:"last season of an inclusive range"`
	Venue       string `json:"venue,omitempty" jsonschema:"home or away to restrict to one venue"`
}

type standingsInput struct {
	Competition string `json:"competition,omitempty" jsonschema:"serie-a (default), serie-b or serie-c"`
	Season      int    `json:"season" jsonschema:"season year, e.g. 2019"`
}

type bracketInput struct {
	Competition string `json:"competition" jsonschema:"libertadores or copa-do-brasil"`
	Season      int    `json:"season" jsonschema:"season year, e.g. 2018"`
}

type leagueStatsInput struct {
	Competition string `json:"competition,omitempty" jsonschema:"restrict to one competition"`
	Team        string `json:"team,omitempty" jsonschema:"restrict to one club's matches"`
	Season      int    `json:"season,omitempty" jsonschema:"single season year"`
	SeasonFrom  int    `json:"season_from,omitempty" jsonschema:"first season of an inclusive range"`
	SeasonTo    int    `json:"season_to,omitempty" jsonschema:"last season of an inclusive range"`
	TopN        int    `json:"top_n,omitempty" jsonschema:"length of each leaderboard (default 5)"`
	MinMatches  int    `json:"min_matches,omitempty" jsonschema:"minimum matches for a club to appear in a leaderboard (default 10)"`
}

type compareSeasonsInput struct {
	Competition string `json:"competition,omitempty" jsonschema:"competition to compare (default serie-a)"`
	Seasons     []int  `json:"seasons" jsonschema:"season years to compare, e.g. [2018, 2019]"`
}

type searchPlayersInput struct {
	Name               string `json:"name,omitempty" jsonschema:"full or partial player name"`
	Nationality        string `json:"nationality,omitempty" jsonschema:"country of the player, e.g. Brazil"`
	Club               string `json:"club,omitempty" jsonschema:"club name, matched against both FIFA and match-data spellings"`
	Position           string `json:"position,omitempty" jsonschema:"FIFA position code (ST, GK, CAM...) or a role: goalkeeper, defender, midfielder, forward"`
	MinOverall         int    `json:"min_overall,omitempty" jsonschema:"minimum FIFA overall rating"`
	MaxOverall         int    `json:"max_overall,omitempty" jsonschema:"maximum FIFA overall rating"`
	MinPotential       int    `json:"min_potential,omitempty" jsonschema:"minimum FIFA potential rating"`
	MinAge             int    `json:"min_age,omitempty" jsonschema:"minimum age"`
	MaxAge             int    `json:"max_age,omitempty" jsonschema:"maximum age"`
	BrazilianClubsOnly bool   `json:"brazilian_clubs_only,omitempty" jsonschema:"only players at clubs that appear in the Brazilian match data"`
	SortBy             string `json:"sort_by,omitempty" jsonschema:"overall (default), potential, age, oldest, value, wage or name"`
	GroupBy            string `json:"group_by,omitempty" jsonschema:"also return counts grouped by club, nationality or position"`
	Limit              int    `json:"limit,omitempty" jsonschema:"maximum players to list (default 20)"`
}

type playerProfileInput struct {
	Name string `json:"name,omitempty" jsonschema:"player name, exact or partial"`
	ID   int    `json:"id,omitempty" jsonschema:"FIFA player ID, if known"`
}

type clubSquadInput struct {
	Club  string `json:"club" jsonschema:"club name, e.g. Flamengo, Grêmio, Atlético Mineiro"`
	Limit int    `json:"limit,omitempty" jsonschema:"maximum squad members to list (default 30)"`
}

type derbiesInput struct {
	Competition string `json:"competition,omitempty" jsonschema:"restrict to one competition"`
	Season      int    `json:"season,omitempty" jsonschema:"single season year, e.g. 2023"`
	SeasonFrom  int    `json:"season_from,omitempty" jsonschema:"first season of an inclusive range"`
	SeasonTo    int    `json:"season_to,omitempty" jsonschema:"last season of an inclusive range"`
	Limit       int    `json:"limit,omitempty" jsonschema:"maximum matches to list (default 25)"`
}

// ---------------------------------------------------------------------------
// Output wrappers
// ---------------------------------------------------------------------------

type teamsOutput struct {
	Query   string            `json:"query"`
	Matches []soccer.TeamView `json:"teams"`
	Note    string            `json:"note,omitempty"`
}

type competitionsOutput struct {
	Competitions []soccer.CompetitionCoverage `json:"competitions"`
}

type rivalriesOutput struct {
	Rivalries []soccer.Rivalry    `json:"rivalries"`
	Report    *soccer.DerbyReport `json:"report,omitempty"`
}

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

func (s *Server) registerTools() {
	g := s.Graph

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:  "dataset_info",
		Title: "Dataset coverage",
		Description: "Describe the loaded datasets: files, licences, row counts, how many " +
			"teams, matches and players are in the knowledge graph, and which competitions " +
			"and seasons are covered. Call this first when you are unsure what can be answered.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in emptyInput) (*mcp.CallToolResult, soccer.LoadStats, error) {
		st := g.Stats
		var b strings.Builder
		b.WriteString("Brazilian soccer knowledge graph\n\n")
		fmt.Fprintf(&b, "Teams: %d, matches: %d (%d duplicate rows merged across datasets), players: %d\n\n",
			st.Teams, st.Matches, st.MergedDuplicates, st.Players)
		b.WriteString("Source files:\n")
		for _, d := range st.Datasets {
			fmt.Fprintf(&b, "- %s — %s [%s]: %d rows read, %d used\n",
				d.File, d.Description, d.License, d.RowsRead, d.RowsUsed)
		}
		b.WriteString("\nCompetition coverage:\n")
		for _, c := range g.CompetitionCoverage() {
			fmt.Fprintf(&b, "- %s (%s): seasons %d-%d, %d matches, %d clubs\n",
				c.Name, c.ID, c.FirstSeason, c.LastSeason, c.MatchCount, c.TeamCount)
		}
		return textResult(b.String()), st, nil
	})

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:        "list_competitions",
		Title:       "List competitions",
		Description: "List every competition in the graph with the seasons, match counts and club counts available for each.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in emptyInput) (*mcp.CallToolResult, competitionsOutput, error) {
		cov := g.CompetitionCoverage()
		var b strings.Builder
		for _, c := range cov {
			fmt.Fprintf(&b, "%s (id: %s, %s)\n  seasons %d-%d, %d matches, %d clubs\n",
				c.Name, c.ID, c.Kind, c.FirstSeason, c.LastSeason, c.MatchCount, c.TeamCount)
		}
		return textResult(b.String()), competitionsOutput{Competitions: cov}, nil
	})

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:  "search_teams",
		Title: "Find clubs",
		Description: "Resolve a club name to the canonical clubs in the graph. Handles state " +
			"suffixes, accents and alternative spellings, and is the way to disambiguate names " +
			"such as \"Atletico\" that exist in several states.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in searchTeamsInput) (*mcp.CallToolResult, teamsOutput, error) {
		limit := in.Limit
		if limit <= 0 {
			limit = 10
		}
		hits := g.SearchTeams(in.Query, limit)
		out := teamsOutput{Query: in.Query, Matches: []soccer.TeamView{}}
		var b strings.Builder
		if len(hits) == 0 {
			out.Note = fmt.Sprintf("no club matching %q is present in the datasets", in.Query)
			b.WriteString(out.Note + "\n")
			return textResult(b.String()), out, nil
		}
		fmt.Fprintf(&b, "Clubs matching %q:\n", in.Query)
		for _, h := range hits {
			out.Matches = append(out.Matches, h.Team.ToView())
			where := h.Team.State
			if where == "" {
				where = h.Team.Country
			}
			if where == "" {
				where = "region unknown"
			}
			fmt.Fprintf(&b, "- %s (id: %s, %s) — %d matches on record [matched by %s]\n",
				h.Team.Name, h.Team.ID, where, h.Team.MatchCount(), h.How)
		}
		return textResult(b.String()), out, nil
	})

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:  "search_matches",
		Title: "Search matches",
		Description: "Find matches by club, opponent, competition, season, date range, round or " +
			"knockout stage. Also supports \"biggest win\" style queries via sort=goal_diff and " +
			"min_goal_difference. When both team and opponent are given the head-to-head record is included.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in searchMatchesInput) (*mcp.CallToolResult, *soccer.MatchSearchResult, error) {
		res, err := g.SearchMatches(soccer.MatchFilter{
			Team: in.Team, Opponent: in.Opponent, HomeTeam: in.HomeTeam, AwayTeam: in.AwayTeam,
			Competition: in.Competition, Season: in.Season,
			SeasonFrom: in.SeasonFrom, SeasonTo: in.SeasonTo,
			DateFrom: in.DateFrom, DateTo: in.DateTo,
			Round: in.Round, Stage: in.Stage, Venue: in.Venue,
			MinGoalDiff: in.MinGoalDiff, MinGoals: in.MinGoals,
			DerbiesOnly: in.DerbiesOnly, Sort: in.Sort, Limit: in.Limit,
		})
		if err != nil {
			return nil, nil, err
		}
		return textResult(formatMatchSearch(res)), res, nil
	})

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:  "head_to_head",
		Title: "Head-to-head record",
		Description: "Compare two clubs: total meetings, wins each way, draws, goals, the split " +
			"by competition, first and most recent meetings, biggest wins and the derby name if the " +
			"fixture is a traditional rivalry.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in headToHeadInput) (*mcp.CallToolResult, *soccer.HeadToHeadResult, error) {
		res, err := g.HeadToHead(in.TeamA, in.TeamB, in.Competition, in.SeasonFrom, in.SeasonTo, in.Limit)
		if err != nil {
			return nil, nil, err
		}
		return textResult(formatHeadToHead(res)), res, nil
	})

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:  "team_stats",
		Title: "Club statistics",
		Description: "Wins, draws, losses, goals for and against, points, win rate and recent form " +
			"for a club, with home/away splits and breakdowns by competition and season. Narrow with " +
			"competition, season and venue.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in teamStatsInput) (*mcp.CallToolResult, *soccer.TeamStatsResult, error) {
		res, err := g.TeamStats(in.Team, in.Competition, in.Season, in.SeasonFrom, in.SeasonTo, in.Venue)
		if err != nil {
			return nil, nil, err
		}
		return textResult(formatTeamStats(res)), res, nil
	})

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:  "standings",
		Title: "League table",
		Description: "Compute a league table for one season directly from the match results, " +
			"including the champion and the relegation places when every fixture of the season is " +
			"present. Use this to answer \"who won\" and \"who was relegated\" questions.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in standingsInput) (*mcp.CallToolResult, *soccer.StandingsResult, error) {
		res, err := g.Standings(in.Competition, in.Season)
		if err != nil {
			return nil, nil, err
		}
		return textResult(formatStandings(res)), res, nil
	})

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:  "competition_bracket",
		Title: "Knockout bracket",
		Description: "Show a knockout competition season stage by stage, collapsing home-and-away " +
			"legs into aggregate ties and naming the champion when the final was decided on aggregate.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in bracketInput) (*mcp.CallToolResult, *soccer.BracketResult, error) {
		res, err := g.Bracket(in.Competition, in.Season)
		if err != nil {
			return nil, nil, err
		}
		return textResult(formatBracket(res)), res, nil
	})

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:  "league_stats",
		Title: "Aggregate statistics",
		Description: "Aggregate statistics for a scope: average goals per match, home advantage, " +
			"biggest victories, highest scoring matches, and leaderboards for goals scored, goals " +
			"conceded and home and away records.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in leagueStatsInput) (*mcp.CallToolResult, *soccer.AggregateStatsResult, error) {
		res, err := g.AggregateStats(soccer.StatsScope{
			Competition: in.Competition, Team: in.Team, Season: in.Season,
			SeasonFrom: in.SeasonFrom, SeasonTo: in.SeasonTo,
			TopN: in.TopN, MinMatches: in.MinMatches,
		})
		if err != nil {
			return nil, nil, err
		}
		return textResult(formatAggregate(res)), res, nil
	})

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:        "compare_seasons",
		Title:       "Compare seasons",
		Description: "Contrast two or more seasons of a competition: matches, goals per match, home/draw/away rates, champion and top scoring club.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in compareSeasonsInput) (*mcp.CallToolResult, *soccer.SeasonComparison, error) {
		res, err := g.CompareSeasons(in.Competition, in.Seasons)
		if err != nil {
			return nil, nil, err
		}
		var b strings.Builder
		fmt.Fprintf(&b, "%s — season comparison\n\n", res.Competition)
		fmt.Fprintf(&b, "%-6s %8s %7s %9s %9s %9s\n", "Season", "Matches", "Goals", "G/match", "Home win%", "Draw%")
		for _, s := range res.Seasons {
			fmt.Fprintf(&b, "%-6d %8d %7d %9.2f %9.1f %9.1f\n",
				s.Season, s.Matches, s.Goals, s.GoalsPerMatch, s.HomeWinPct, s.DrawPct)
		}
		b.WriteString("\n")
		for _, l := range res.Leaders {
			fmt.Fprintf(&b, "%d: champion %s (%d pts), top scoring club %s (%d goals)\n",
				l.Season, orDash(l.Champion), l.Points, orDash(l.TopScorer), l.Goals)
		}
		fmt.Fprintf(&b, "\n%s\n", res.Commentary)
		return textResult(b.String()), res, nil
	})

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:  "search_players",
		Title: "Search players",
		Description: "Search the FIFA 19 player database by name, nationality, club, position, " +
			"rating and age. Use group_by=club with nationality=Brazil to summarise Brazilian " +
			"players per club.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in searchPlayersInput) (*mcp.CallToolResult, *soccer.PlayerSearchResult, error) {
		res, err := g.SearchPlayers(soccer.PlayerFilter{
			Name: in.Name, Nationality: in.Nationality, Club: in.Club, Position: in.Position,
			MinOverall: in.MinOverall, MaxOverall: in.MaxOverall, MinPotential: in.MinPotential,
			MinAge: in.MinAge, MaxAge: in.MaxAge, BrazilianClubsOnly: in.BrazilianClubsOnly,
			SortBy: in.SortBy, GroupBy: in.GroupBy, Limit: in.Limit,
		})
		if err != nil {
			return nil, nil, err
		}
		return textResult(formatPlayers(res)), res, nil
	})

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:        "player_profile",
		Title:       "Player profile",
		Description: "Full FIFA attribute profile for one player, looked up by name or FIFA ID, including the link to the club's match-data record.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in playerProfileInput) (*mcp.CallToolResult, *soccer.PlayerProfileView, error) {
		res, err := g.PlayerProfile(in.Name, in.ID)
		if err != nil {
			return nil, nil, err
		}
		return textResult(formatPlayerProfile(res)), res, nil
	})

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:  "club_squad",
		Title: "Club squad",
		Description: "The FIFA squad for a club, joined to the club's record in the match data. " +
			"This is the cross-dataset query: it links player data to match data. If FIFA 19 does " +
			"not license the club, the answer says so and lists the Brazilian clubs it does cover.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in clubSquadInput) (*mcp.CallToolResult, *soccer.ClubSquadResult, error) {
		res, err := g.ClubSquad(in.Club, in.Limit)
		if err != nil {
			return nil, nil, err
		}
		return textResult(formatSquad(res)), res, nil
	})

	mcp.AddTool(s.MCP, &mcp.Tool{
		Name:  "derbies",
		Title: "Derbies and rivalries",
		Description: "List the traditional Brazilian derbies (clássicos) and, when a season or " +
			"competition is given, every derby match played in that window.",
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in derbiesInput) (*mcp.CallToolResult, rivalriesOutput, error) {
		out := rivalriesOutput{Rivalries: g.Rivalries()}
		var b strings.Builder
		if in.Season != 0 || in.SeasonFrom != 0 || in.SeasonTo != 0 || in.Competition != "" {
			rep, err := g.Derbies(in.Competition, in.Season, in.SeasonFrom, in.SeasonTo, in.Limit)
			if err != nil {
				return nil, out, err
			}
			out.Report = rep
			fmt.Fprintf(&b, "Derbies in %s — %d matches\n\n", rep.Description, rep.Total)
			for _, d := range rep.Derbies {
				fmt.Fprintf(&b, "- %s (%s vs %s): %d meeting(s)\n", d.Rivalry, d.TeamA, d.TeamB, d.Played)
			}
			b.WriteString("\n")
			writeMatches(&b, rep.Matches)
			return textResult(b.String()), out, nil
		}
		b.WriteString("Traditional Brazilian derbies known to this server:\n")
		for _, r := range out.Rivalries {
			fmt.Fprintf(&b, "- %s: %s vs %s (%s)\n", r.Name, r.TeamA, r.TeamB, r.Region)
		}
		return textResult(b.String()), out, nil
	})
}

func (s *Server) registerResources() {
	g := s.Graph

	s.MCP.AddResource(&mcp.Resource{
		URI:         "soccer://datasets",
		Name:        "datasets",
		Title:       "Loaded datasets",
		Description: "Provenance, licence and row counts for each source CSV.",
		MIMEType:    "application/json",
	}, func(ctx context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
		return jsonResource(req.Params.URI, g.Stats)
	})

	s.MCP.AddResource(&mcp.Resource{
		URI:         "soccer://teams",
		Name:        "teams",
		Title:       "Club index",
		Description: "Every club in the graph with its canonical id, state and match count.",
		MIMEType:    "application/json",
	}, func(ctx context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
		views := make([]soccer.TeamView, 0, len(g.Teams))
		for _, t := range g.AllTeams() {
			views = append(views, t.ToView())
		}
		return jsonResource(req.Params.URI, views)
	})

	s.MCP.AddResource(&mcp.Resource{
		URI:         "soccer://competitions",
		Name:        "competitions",
		Title:       "Competition coverage",
		Description: "Competitions with the seasons available for each.",
		MIMEType:    "application/json",
	}, func(ctx context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
		return jsonResource(req.Params.URI, g.CompetitionCoverage())
	})
}

func (s *Server) registerPrompts() {
	s.MCP.AddPrompt(&mcp.Prompt{
		Name:        "club_report",
		Title:       "Club report",
		Description: "Draft a full report on a club: overall record, home/away split, rivalries and squad.",
		Arguments: []*mcp.PromptArgument{
			{Name: "club", Description: "the club to report on", Required: true},
			{Name: "season", Description: "optional season to focus on"},
		},
	}, func(ctx context.Context, req *mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
		club := req.Params.Arguments["club"]
		season := req.Params.Arguments["season"]
		scope := "across all available seasons"
		if season != "" {
			scope = "for the " + season + " season"
		}
		text := fmt.Sprintf(
			"Produce a report on %s %s using the brazilian-soccer tools.\n"+
				"1. Call team_stats for the overall record and the home/away split.\n"+
				"2. Call search_matches for the most recent results.\n"+
				"3. Call head_to_head against the club's main rival (use the derbies tool to find it).\n"+
				"4. Call club_squad for the FIFA squad, and say so plainly if the club is not licensed.\n"+
				"Present the numbers exactly as the tools report them and do not invent goalscorers.",
			club, scope)
		return &mcp.GetPromptResult{
			Description: "Club report",
			Messages:    []*mcp.PromptMessage{{Role: "user", Content: &mcp.TextContent{Text: text}}},
		}, nil
	})

	s.MCP.AddPrompt(&mcp.Prompt{
		Name:        "season_review",
		Title:       "Season review",
		Description: "Draft a review of one season of a competition.",
		Arguments: []*mcp.PromptArgument{
			{Name: "competition", Description: "competition id, e.g. serie-a", Required: true},
			{Name: "season", Description: "season year", Required: true},
		},
	}, func(ctx context.Context, req *mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
		text := fmt.Sprintf(
			"Review the %s %s season using the brazilian-soccer tools: call standings for the "+
				"final table, league_stats for goals per match and the biggest wins, and derbies "+
				"for the classic fixtures played that year. State clearly if the table is partial.",
			req.Params.Arguments["season"], req.Params.Arguments["competition"])
		return &mcp.GetPromptResult{
			Description: "Season review",
			Messages:    []*mcp.PromptMessage{{Role: "user", Content: &mcp.TextContent{Text: text}}},
		}, nil
	})
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

func textResult(s string) *mcp.CallToolResult {
	return &mcp.CallToolResult{Content: []mcp.Content{&mcp.TextContent{Text: strings.TrimRight(s, "\n")}}}
}

func jsonResource(uri string, v any) (*mcp.ReadResourceResult, error) {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return nil, err
	}
	return &mcp.ReadResourceResult{
		Contents: []*mcp.ResourceContents{{URI: uri, MIMEType: "application/json", Text: string(data)}},
	}, nil
}

func orDash(s string) string {
	if s == "" {
		return "-"
	}
	return s
}
