// Package mcpserver exposes the Brazilian soccer knowledge graph as a Model
// Context Protocol server.
//
// Every tool returns two things: a human-readable text block that an LLM can
// quote directly, and a structured JSON payload with the full detail. Tools
// are named for the question they answer rather than for the table they read,
// so the model can pick one from the natural-language question without knowing
// anything about the CSV layout.
package mcpserver

import (
	"context"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// Version is reported in the MCP initialize handshake.
const Version = "1.0.0"

// New builds an MCP server backed by the given graph.
func New(g *soccer.Graph) *mcp.Server {
	s := mcp.NewServer(&mcp.Implementation{
		Name:    "brazilian-soccer",
		Title:   "Brazilian Soccer Knowledge Graph",
		Version: Version,
	}, &mcp.ServerOptions{
		Instructions: instructions(g),
	})
	registerTools(s, g)
	return s
}

func instructions(g *soccer.Graph) string {
	var b strings.Builder
	b.WriteString("Knowledge graph of Brazilian club football built from six Kaggle datasets.\n\n")
	b.WriteString("Coverage:\n")
	comps := g.Competitions()
	names := make([]string, 0, len(comps))
	for c := range comps {
		names = append(names, c)
	}
	sort.Strings(names)
	for _, c := range names {
		seasons := comps[c]
		fmt.Fprintf(&b, "  - %s: %d-%d\n", c, seasons[0], seasons[len(seasons)-1])
	}
	st := g.Stats()
	fmt.Fprintf(&b, "  - %d unique matches, %d clubs, %d FIFA player records\n",
		st.Matches, st.Teams, st.Players)
	b.WriteString(`
Team names may be given in any spelling found in the data ("Flamengo",
"Flamengo-RJ", "CR Flamengo", "Gremio", "Grêmio"); they are normalised
internally. Competition names accept shorthands ("brasileirao", "serie b",
"libertadores", "copa do brasil").

Player data comes from a FIFA 19 snapshot and is a squad/attribute source
only - it contains no goals or appearances, so questions about top scorers
cannot be answered from it. Standings are calculated from match results, not
read from an official table.`)
	return b.String()
}

// text builds a CallToolResult carrying both prose and structured JSON.
func text(summary string, payload any) (*mcp.CallToolResult, any, error) {
	res := &mcp.CallToolResult{
		Content: []mcp.Content{&mcp.TextContent{Text: summary}},
	}
	return res, payload, nil
}

// fail turns a query error into a tool error the model can act on, keeping
// "team not found" style hints intact.
func fail(err error) (*mcp.CallToolResult, any, error) {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{&mcp.TextContent{Text: err.Error()}},
	}, nil, nil
}

// --- tool input schemas ---------------------------------------------------

type FindMatchesInput struct {
	Team        string `json:"team,omitempty" jsonschema:"Club name in any spelling; matches where it played home or away"`
	Opponent    string `json:"opponent,omitempty" jsonschema:"Restrict to fixtures against this club"`
	Venue       string `json:"venue,omitempty" jsonschema:"Restrict 'team' to home or away fixtures. One of: home, away"`
	Competition string `json:"competition,omitempty" jsonschema:"brasileirao / serie a / serie b / serie c / copa do brasil / libertadores"`
	Season      int    `json:"season,omitempty" jsonschema:"Single season year, e.g. 2019"`
	SeasonFrom  int    `json:"season_from,omitempty" jsonschema:"Earliest season to include"`
	SeasonTo    int    `json:"season_to,omitempty" jsonschema:"Latest season to include"`
	DateFrom    string `json:"date_from,omitempty" jsonschema:"Earliest match date as YYYY-MM-DD"`
	DateTo      string `json:"date_to,omitempty" jsonschema:"Latest match date as YYYY-MM-DD"`
	Round       string `json:"round,omitempty" jsonschema:"Round or knockout stage substring, e.g. 'final', 'semi', '22'"`
	MinGoals    int    `json:"min_total_goals,omitempty" jsonschema:"Only matches with at least this many goals in total"`
	Limit       int    `json:"limit,omitempty" jsonschema:"Maximum matches to return (default 25)"`
	Oldest      bool   `json:"oldest_first,omitempty" jsonschema:"Return oldest matches first instead of most recent"`
}

type TeamStatsInput struct {
	Team        string `json:"team" jsonschema:"Club name in any spelling"`
	Season      int    `json:"season,omitempty" jsonschema:"Restrict to one season"`
	Competition string `json:"competition,omitempty" jsonschema:"Restrict to one competition"`
	Venue       string `json:"venue,omitempty" jsonschema:"Restrict to home or away fixtures. One of: home, away"`
}

type HeadToHeadInput struct {
	TeamA       string `json:"team_a" jsonschema:"First club"`
	TeamB       string `json:"team_b" jsonschema:"Second club"`
	Competition string `json:"competition,omitempty" jsonschema:"Restrict to one competition"`
	Season      int    `json:"season,omitempty" jsonschema:"Restrict to one season"`
}

type CompareTeamsInput struct {
	TeamA       string `json:"team_a" jsonschema:"First club"`
	TeamB       string `json:"team_b" jsonschema:"Second club"`
	Season      int    `json:"season,omitempty" jsonschema:"Restrict to one season"`
	Competition string `json:"competition,omitempty" jsonschema:"Restrict to one competition"`
}

type SearchTeamsInput struct {
	Query string `json:"query,omitempty" jsonschema:"Partial club name; omit to list clubs"`
	State string `json:"state,omitempty" jsonschema:"Two-letter Brazilian state code, e.g. SP"`
	Limit int    `json:"limit,omitempty" jsonschema:"Maximum clubs to return (default 25)"`
}

type FindPlayersInput struct {
	Name          string `json:"name,omitempty" jsonschema:"Full or partial player name"`
	Nationality   string `json:"nationality,omitempty" jsonschema:"Country of the player, e.g. Brazil"`
	Club          string `json:"club,omitempty" jsonschema:"Club the player is registered at"`
	Position      string `json:"position,omitempty" jsonschema:"FIFA position code, e.g. ST, LW, GK, CDM"`
	MinOverall    int    `json:"min_overall,omitempty" jsonschema:"Minimum FIFA overall rating"`
	MaxOverall    int    `json:"max_overall,omitempty" jsonschema:"Maximum FIFA overall rating"`
	MinAge        int    `json:"min_age,omitempty" jsonschema:"Minimum age"`
	MaxAge        int    `json:"max_age,omitempty" jsonschema:"Maximum age"`
	BrazilianClub bool   `json:"at_brazilian_clubs_only,omitempty" jsonschema:"Only players whose club appears in the Brazilian match data"`
	SortBy        string `json:"sort_by,omitempty" jsonschema:"overall (default), potential, age or name"`
	Limit         int    `json:"limit,omitempty" jsonschema:"Maximum players to return (default 20)"`
}

type SquadInput struct {
	Club           string `json:"club" jsonschema:"Club name in any spelling"`
	IncludePlayers bool   `json:"include_players,omitempty" jsonschema:"Include the full player list, not just the summary"`
}

type ClubRatingsInput struct {
	Nationality string `json:"nationality,omitempty" jsonschema:"Only count players of this nationality, e.g. Brazil"`
	MinPlayers  int    `json:"min_players,omitempty" jsonschema:"Ignore clubs with fewer players than this (default 3)"`
	Limit       int    `json:"limit,omitempty" jsonschema:"Maximum clubs to return (default 20)"`
}

type StandingsInput struct {
	Competition     string `json:"competition,omitempty" jsonschema:"League competition; defaults to Brasileirao Serie A"`
	Season          int    `json:"season" jsonschema:"Season year, e.g. 2019"`
	RelegationSpots int    `json:"relegation_spots,omitempty" jsonschema:"Override how many bottom places count as relegated"`
}

type StatsInput struct {
	Competition string `json:"competition,omitempty" jsonschema:"Restrict to one competition"`
	Season      int    `json:"season,omitempty" jsonschema:"Restrict to one season"`
	SeasonFrom  int    `json:"season_from,omitempty" jsonschema:"Earliest season to include"`
	SeasonTo    int    `json:"season_to,omitempty" jsonschema:"Latest season to include"`
	Team        string `json:"team,omitempty" jsonschema:"Restrict to matches involving this club"`
	TopN        int    `json:"top_n,omitempty" jsonschema:"How many notable matches to list (default 5)"`
}

type LeaderboardInput struct {
	Metric      string `json:"metric" jsonschema:"One of: points, wins, draws, losses, matches, goals_for, goals_against, goal_difference, win_rate, points_per_game"`
	Competition string `json:"competition,omitempty" jsonschema:"Restrict to one competition"`
	Season      int    `json:"season,omitempty" jsonschema:"Restrict to one season"`
	SeasonFrom  int    `json:"season_from,omitempty" jsonschema:"Earliest season to include"`
	SeasonTo    int    `json:"season_to,omitempty" jsonschema:"Latest season to include"`
	Venue       string `json:"venue,omitempty" jsonschema:"Count only home or away fixtures. One of: home, away"`
	MinMatches  int    `json:"min_matches,omitempty" jsonschema:"Ignore clubs with fewer matches than this"`
	Limit       int    `json:"limit,omitempty" jsonschema:"Maximum clubs to return (default 10)"`
	Worst       bool   `json:"ascending,omitempty" jsonschema:"Rank from lowest to highest instead of highest to lowest"`
}

type CompareSeasonsInput struct {
	Competition string `json:"competition,omitempty" jsonschema:"Competition to compare within; defaults to Brasileirao Serie A"`
	SeasonA     int    `json:"season_a" jsonschema:"First season"`
	SeasonB     int    `json:"season_b" jsonschema:"Second season"`
}

type DerbiesInput struct {
	Season int `json:"season,omitempty" jsonschema:"Restrict to one season"`
	Limit  int `json:"limit,omitempty" jsonschema:"Maximum matches per derby (default 10)"`
}

type EmptyInput struct{}

// --- registration ---------------------------------------------------------

func registerTools(s *mcp.Server, g *soccer.Graph) {
	mcp.AddTool(s, &mcp.Tool{
		Name: "find_matches",
		Description: "Search match results by club, opponent, competition, season, date range or round. " +
			"Answers questions like 'show me all Flamengo vs Fluminense matches', " +
			"'what matches did Palmeiras play in 2023' and 'find all Copa do Brasil finals'. " +
			"When both team and opponent are given the head-to-head record is included.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, in FindMatchesInput) (*mcp.CallToolResult, any, error) {
		f := soccer.MatchFilter{
			Team: in.Team, Opponent: in.Opponent, Venue: strings.ToLower(in.Venue),
			Competition: in.Competition, Season: in.Season,
			SeasonFrom: in.SeasonFrom, SeasonTo: in.SeasonTo,
			Round: in.Round, MinGoals: in.MinGoals, Limit: in.Limit,
			Ascending: in.Oldest,
		}
		var err error
		if f.From, err = optDate(in.DateFrom); err != nil {
			return fail(err)
		}
		if f.To, err = optDate(in.DateTo); err != nil {
			return fail(err)
		}
		res, err := g.FindMatches(f)
		if err != nil {
			return fail(err)
		}
		return text(renderMatches(res), res)
	})

	mcp.AddTool(s, &mcp.Tool{
		Name: "team_statistics",
		Description: "Win/draw/loss record, goals for and against, and home vs away splits for one club, " +
			"optionally scoped to a season, competition or venue. Answers " +
			"'what is Corinthians' home record in 2022'.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, in TeamStatsInput) (*mcp.CallToolResult, any, error) {
		st, err := g.TeamStatistics(soccer.TeamStatsFilter{
			Team: in.Team, Season: in.Season,
			Competition: in.Competition, Venue: strings.ToLower(in.Venue),
		})
		if err != nil {
			return fail(err)
		}
		return text(renderTeamStats(st), st)
	})

	mcp.AddTool(s, &mcp.Tool{
		Name:        "head_to_head",
		Description: "Complete head-to-head record between two clubs: meetings, wins each way, draws, goals and the biggest result.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, in HeadToHeadInput) (*mcp.CallToolResult, any, error) {
		h, err := g.HeadToHead(in.TeamA, in.TeamB, in.Competition, in.Season)
		if err != nil {
			return fail(err)
		}
		return text(renderH2H(h), h)
	})

	mcp.AddTool(s, &mcp.Tool{
		Name:        "compare_teams",
		Description: "Put two clubs side by side: each one's full record plus their head-to-head. Answers 'compare Palmeiras and Santos'.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, in CompareTeamsInput) (*mcp.CallToolResult, any, error) {
		c, err := g.Compare(in.TeamA, in.TeamB, in.Season, in.Competition)
		if err != nil {
			return fail(err)
		}
		var b strings.Builder
		b.WriteString(renderTeamStats(c.A))
		b.WriteString("\n")
		b.WriteString(renderTeamStats(c.B))
		b.WriteString("\n")
		b.WriteString(renderH2H(c.HeadToHead))
		return text(b.String(), c)
	})

	mcp.AddTool(s, &mcp.Tool{
		Name: "search_teams",
		Description: "Find clubs by partial name or state, and see how many matches, which competitions and which seasons " +
			"the datasets hold for them. Use this to disambiguate a name before other tools.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, in SearchTeamsInput) (*mcp.CallToolResult, any, error) {
		teams := g.SearchTeams(in.Query, in.State, in.Limit)
		if len(teams) == 0 {
			return fail(fmt.Errorf("no clubs match %q", in.Query))
		}
		var b strings.Builder
		fmt.Fprintf(&b, "%d clubs found:\n", len(teams))
		for _, t := range teams {
			fmt.Fprintf(&b, "- %s", t.Name)
			if t.State != "" {
				fmt.Fprintf(&b, " (%s)", t.State)
			}
			fmt.Fprintf(&b, ": %d matches", t.MatchCount)
			if len(t.Seasons) > 0 {
				fmt.Fprintf(&b, ", %d-%d", t.Seasons[0], t.Seasons[len(t.Seasons)-1])
			}
			fmt.Fprintf(&b, ", %s\n", strings.Join(t.Competitions, "; "))
		}
		return text(b.String(), map[string]any{"teams": teams, "count": len(teams)})
	})

	mcp.AddTool(s, &mcp.Tool{
		Name: "find_players",
		Description: "Search the FIFA player database by name, nationality, club, position, rating or age. " +
			"Answers 'who is Gabriel Barbosa', 'find all Brazilian players', 'show me all forwards from Sao Paulo FC'. " +
			"Note: this is an attribute/squad snapshot with no goals or appearances.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, in FindPlayersInput) (*mcp.CallToolResult, any, error) {
		res := g.FindPlayers(soccer.PlayerFilter{
			Name: in.Name, Nationality: in.Nationality, Club: in.Club,
			Position: in.Position, MinOverall: in.MinOverall, MaxOverall: in.MaxOverall,
			MinAge: in.MinAge, MaxAge: in.MaxAge,
			BrazilianClubsOnly: in.BrazilianClub, SortBy: in.SortBy, Limit: in.Limit,
		})
		if res.Total == 0 {
			return fail(fmt.Errorf("no players matched that search"))
		}
		return text(renderPlayers(res), res)
	})

	mcp.AddTool(s, &mcp.Tool{
		Name:        "club_squad",
		Description: "Summarise the FIFA players registered at one club: size, average rating and age, nationalities, top player.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, in SquadInput) (*mcp.CallToolResult, any, error) {
		sq, err := g.Squad(in.Club, in.IncludePlayers)
		if err != nil {
			return fail(err)
		}
		var b strings.Builder
		b.WriteString(sq.Summary + "\n")
		for _, p := range sq.Squad {
			fmt.Fprintf(&b, "  %s - Overall: %d, Position: %s, Age: %d, %s\n",
				p.Name, p.Overall, p.Position, p.Age, p.Nationality)
		}
		return text(b.String(), sq)
	})

	mcp.AddTool(s, &mcp.Tool{
		Name: "brazilian_club_ratings",
		Description: "Cross-reference the FIFA player file with the match graph: for every club that appears in both, " +
			"report squad size and average rating. Answers 'Brazilian players at Brazilian clubs'.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, in ClubRatingsInput) (*mcp.CallToolResult, any, error) {
		limit := in.Limit
		if limit <= 0 {
			limit = 20
		}
		rows := g.BrazilianClubRatings(in.Nationality, in.MinPlayers, limit)
		if len(rows) == 0 {
			return fail(fmt.Errorf("no clubs appear in both the player and match datasets for that filter"))
		}
		var b strings.Builder
		who := "players"
		if in.Nationality != "" {
			who = in.Nationality + " players"
		}
		fmt.Fprintf(&b, "%s at clubs present in the Brazilian match data:\n", strings.ToUpper(who[:1])+who[1:])
		for _, r := range rows {
			fmt.Fprintf(&b, "- %s: %d players (avg rating %.1f), top: %s (%d), %d matches in fixture data\n",
				r.Club, r.Players, r.AvgOverall, r.TopPlayer, r.TopOverall, r.MatchCount)
		}
		return text(b.String(), map[string]any{"clubs": rows})
	})

	mcp.AddTool(s, &mcp.Tool{
		Name: "league_standings",
		Description: "Calculate a full league table for a season from the match results, with champion and relegated clubs. " +
			"Answers 'who won the 2019 Brasileirao' and 'which teams were relegated in 2020'. " +
			"League competitions only; for cups use find_matches with round='final'.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, in StandingsInput) (*mcp.CallToolResult, any, error) {
		st, err := g.LeagueStandings(in.Competition, in.Season, in.RelegationSpots)
		if err != nil {
			return fail(err)
		}
		return text(renderStandings(st), st)
	})

	mcp.AddTool(s, &mcp.Tool{
		Name: "competition_stats",
		Description: "Aggregate statistics over a scope: goals per match, home/away/draw rates, clean sheets, " +
			"biggest wins and highest-scoring matches. Answers 'what's the average goals per match in the Brasileirao' " +
			"and 'show me the biggest wins'.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, in StatsInput) (*mcp.CallToolResult, any, error) {
		st, err := g.AggregateStats(soccer.StatsFilter{
			Competition: in.Competition, Season: in.Season,
			SeasonFrom: in.SeasonFrom, SeasonTo: in.SeasonTo,
			Team: in.Team, TopN: in.TopN,
		})
		if err != nil {
			return fail(err)
		}
		return text(renderStats(st), st)
	})

	mcp.AddTool(s, &mcp.Tool{
		Name: "team_leaderboard",
		Description: "Rank clubs by a metric over a scope. Answers 'which team scored the most goals in Serie A 2023', " +
			"'which team has the best home record' and 'which team has the best away record'.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, in LeaderboardInput) (*mcp.CallToolResult, any, error) {
		rows, err := g.Leaderboard(soccer.LeaderboardFilter{
			Metric: in.Metric, Competition: in.Competition, Season: in.Season,
			SeasonFrom: in.SeasonFrom, SeasonTo: in.SeasonTo,
			Venue: strings.ToLower(in.Venue), MinMatches: in.MinMatches,
			Limit: in.Limit, Ascending: in.Worst,
		})
		if err != nil {
			return fail(err)
		}
		var b strings.Builder
		fmt.Fprintf(&b, "Clubs ranked by %s:\n", in.Metric)
		for _, r := range rows {
			fmt.Fprintf(&b, "%2d. %s - %g (%s)\n", r.Rank, r.Team, r.Value, r.Detail)
		}
		return text(b.String(), map[string]any{"metric": in.Metric, "leaderboard": rows})
	})

	mcp.AddTool(s, &mcp.Tool{
		Name:        "compare_seasons",
		Description: "Contrast two seasons of a competition on goals per match, home advantage and draw rate.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, in CompareSeasonsInput) (*mcp.CallToolResult, any, error) {
		c, err := g.CompareSeasons(in.Competition, in.SeasonA, in.SeasonB)
		if err != nil {
			return fail(err)
		}
		return text(c.Summary, c)
	})

	mcp.AddTool(s, &mcp.Tool{
		Name:        "find_derbies",
		Description: "List matches between traditional rivals (Fla-Flu, Derby Paulista, Grenal, Clássico Mineiro, Atletiba, Ba-Vi and others), optionally for one season.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, in DerbiesInput) (*mcp.CallToolResult, any, error) {
		derbies, err := g.DerbyMatches(in.Season, in.Limit)
		if err != nil {
			return fail(err)
		}
		names := make([]string, 0, len(derbies))
		for n := range derbies {
			names = append(names, n)
		}
		sort.Strings(names)
		var b strings.Builder
		for _, n := range names {
			fmt.Fprintf(&b, "%s:\n", n)
			for _, line := range derbies[n] {
				fmt.Fprintf(&b, "  - %s\n", line)
			}
		}
		return text(b.String(), derbies)
	})

	mcp.AddTool(s, &mcp.Tool{
		Name:        "dataset_info",
		Description: "Report what data is loaded: files, row counts, deduplication, competitions and season coverage. Use this when unsure whether a question is answerable.",
	}, func(ctx context.Context, _ *mcp.CallToolRequest, _ EmptyInput) (*mcp.CallToolResult, any, error) {
		st := g.Stats()
		payload := map[string]any{
			"load":         st,
			"competitions": g.Competitions(),
			"version":      Version,
		}
		raw, _ := json.MarshalIndent(payload, "", "  ")
		return text(string(raw), payload)
	})
}

func optDate(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, nil
	}
	for _, layout := range []string{"2006-01-02", "02/01/2006", "2006"} {
		if t, err := time.Parse(layout, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("cannot parse date %q; use YYYY-MM-DD", s)
}
