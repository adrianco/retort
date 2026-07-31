// tools.go defines the MCP tool surface: the arguments a model may pass, how
// they map onto soccer.MatchFilter and friends, and the dual text + structured
// result every tool returns.
//
// Argument style is deliberately forgiving because the caller is a language
// model: club names accept any spelling found in the data, competitions accept
// "brasileirao", "Série A" or "libertadores", seasons are plain years and dates
// are ISO strings. Anything that cannot be resolved comes back as a tool error
// with the valid alternatives listed, which the model can act on.
package mcpserver

import (
	"context"
	"fmt"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// toolCatalog documents the tool surface; it backs the soccer://tools resource
// and the -list-tools CLI flag.
var toolCatalog = []struct{ name, summary string }{
	{"search_matches", "Find matches by club, opponent, competition, season, date range, round, stage or venue."},
	{"head_to_head", "Full head-to-head record between two clubs, with biggest wins and recent form."},
	{"team_stats", "Win/draw/loss record, goals and form for one club, optionally home only or away only."},
	{"team_profile", "Everything the graph knows about a club: competitions, titles, rivalries, stadiums and FIFA squad."},
	{"list_teams", "Browse or search the club directory, including name variants and nicknames."},
	{"search_players", "Search the FIFA player database by name, nationality, club, position, rating or age."},
	{"player_profile", "Detailed attributes for one player plus their club in the match graph."},
	{"standings", "League table computed from match results, with champion and relegation zones."},
	{"champions", "Winners of a competition per season, including cup finals decided on aggregate."},
	{"competition_bracket", "Knockout bracket of a cup season with two-legged ties aggregated."},
	{"competition_summary", "Season headline numbers, and a comparison when several seasons are requested."},
	{"team_rankings", "Rank clubs by wins, points, win rate, goals, defence, clean sheets or goal difference."},
	{"aggregate_stats", "Goals per match, home advantage, biggest wins and highest scoring matches for any subset."},
	{"list_derbies", "Traditional Brazilian derbies with their records, optionally within one season."},
	{"dataset_info", "Provenance, row counts, licences and known gaps of the six source files."},
}

// registerTools installs every tool on the MCP server.
func (s *Server) registerTools() {
	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "search_matches",
		Description: "Find matches by club, opponent, competition, season, date range, round, stage or venue. Returns the most recent matches first, plus a head-to-head summary when two clubs are named.",
	}, s.searchMatches)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "head_to_head",
		Description: "Compare two clubs: overall record, goals, home and away splits, biggest wins, recent form and the list of meetings.",
	}, s.headToHead)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "team_stats",
		Description: "Win/draw/loss record, goals for and against, points, clean sheets and form for one club. Filter by competition and season, and restrict to home or away matches.",
	}, s.teamStats)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "team_profile",
		Description: "Cross-dataset overview of one club: name variants, competitions played, titles computed from results, rivalries, stadiums and squad from the FIFA database.",
	}, s.teamProfile)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "list_teams",
		Description: "List or search the clubs in the knowledge graph. Use this to resolve an ambiguous name such as 'Atlético' or 'Botafogo'.",
	}, s.listTeams)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "search_players",
		Description: "Search the FIFA player database by name, nationality, club, position or rating. Set group_by_club to get the per-club breakdown with average ratings.",
	}, s.searchPlayers)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "player_profile",
		Description: "Full attributes for one player: ratings, physical data, contract, best skills and, when the club is Brazilian, the link into the match graph.",
	}, s.playerProfile)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "standings",
		Description: "League table for a Brasileirão season, computed from match results with CBF tie-breaks. Reports the champion and the relegation zone when the season is complete in the data.",
	}, s.standings)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "champions",
		Description: "Champions per season. League titles come from the computed table; cup titles from the final, aggregated over both legs.",
	}, s.champions)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "competition_bracket",
		Description: "Knockout bracket for a Copa do Brasil or Copa Libertadores season: stages, ties, aggregate scores and the winner of each tie.",
	}, s.bracket)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "competition_summary",
		Description: "Headline numbers for one or more seasons of a competition: matches, teams, goals per match, home advantage, champion, top scoring teams and best defences. Several seasons produce a comparison.",
	}, s.competitionSummary)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "team_rankings",
		Description: "Rank clubs by a metric such as most_wins, most_points, best_win_rate, most_goals_scored, best_defence, most_clean_sheets or best_goal_difference, optionally home only or away only.",
	}, s.rankings)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "aggregate_stats",
		Description: "Aggregate statistics over any subset of matches: goals per match, home/draw/away split, home advantage, biggest wins and highest scoring matches, broken down by season and competition.",
	}, s.aggregateStats)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "list_derbies",
		Description: "The traditional Brazilian derbies (Fla-Flu, Derby Paulista, Grenal, Clássico Mineiro and more) with their head-to-head records; filter by season to answer 'show me all derbies in 2023'.",
	}, s.listDerbies)

	mcp.AddTool(s.mcp, &mcp.Tool{
		Name:        "dataset_info",
		Description: "What is loaded: source files, licences, row counts, seasons covered, how overlapping files were de-duplicated and what the data cannot answer.",
	}, s.datasetInfo)
}

// ---------------------------------------------------------------- shared args

// scopeArgs are the filter fields shared by the match-oriented tools.
type scopeArgs struct {
	Competition string `json:"competition,omitempty" jsonschema:"competition name: Serie A / Brasileirao, Serie B, Serie C, Copa do Brasil or Libertadores. Omit for all competitions."`
	Season      int    `json:"season,omitempty" jsonschema:"a single season, e.g. 2019"`
	SeasonFrom  int    `json:"season_from,omitempty" jsonschema:"first season of a range, inclusive"`
	SeasonTo    int    `json:"season_to,omitempty" jsonschema:"last season of a range, inclusive"`
}

// filter converts the shared arguments into a match filter.
func (a scopeArgs) filter() (soccer.MatchFilter, error) {
	comp, err := soccer.ParseCompetition(a.Competition)
	if err != nil {
		return soccer.MatchFilter{}, err
	}
	return soccer.MatchFilter{
		Competition: comp,
		Season:      a.Season,
		SeasonFrom:  a.SeasonFrom,
		SeasonTo:    a.SeasonTo,
	}, nil
}

// parseDate accepts an ISO date, returning a helpful error otherwise.
func parseDate(field, s string) (time.Time, error) {
	if s == "" {
		return time.Time{}, nil
	}
	t, err := time.Parse("2006-01-02", s)
	if err != nil {
		return time.Time{}, fmt.Errorf("%s must be an ISO date such as 2023-09-24, got %q", field, s)
	}
	return t, nil
}

// limitOr applies a default and a ceiling to a requested result count.
func limitOr(requested, def, max int) int {
	if requested <= 0 {
		return def
	}
	if requested > max {
		return max
	}
	return requested
}

// ------------------------------------------------------------------- matches

type searchMatchesArgs struct {
	scopeArgs
	Team              string `json:"team,omitempty" jsonschema:"club that played in the match, home or away. Any spelling: Palmeiras, Palmeiras-SP, Verdão."`
	Opponent          string `json:"opponent,omitempty" jsonschema:"restrict to matches against this club"`
	HomeTeam          string `json:"home_team,omitempty" jsonschema:"club that must have been at home"`
	AwayTeam          string `json:"away_team,omitempty" jsonschema:"club that must have been away"`
	DateFrom          string `json:"date_from,omitempty" jsonschema:"earliest match date, ISO format YYYY-MM-DD"`
	DateTo            string `json:"date_to,omitempty" jsonschema:"latest match date, ISO format YYYY-MM-DD"`
	Round             int    `json:"round,omitempty" jsonschema:"league round number"`
	Stage             string `json:"stage,omitempty" jsonschema:"knockout stage: final, semifinals, quarterfinals, round of 16, group stage"`
	Venue             string `json:"venue,omitempty" jsonschema:"stadium name, matched as a substring; only the historic Brasileirão file records stadiums"`
	MinTotalGoals     int    `json:"min_total_goals,omitempty" jsonschema:"only matches with at least this many goals in total"`
	MinGoalDifference int    `json:"min_goal_difference,omitempty" jsonschema:"only matches won by at least this margin"`
	Limit             int    `json:"limit,omitempty" jsonschema:"maximum matches to return, default 25, maximum 500"`
	IncludeDuplicates bool   `json:"include_duplicates,omitempty" jsonschema:"return the raw per-file rows instead of the de-duplicated view; useful to inspect overlapping datasets"`
}

func (s *Server) searchMatches(ctx context.Context, req *mcp.CallToolRequest, in searchMatchesArgs) (*mcp.CallToolResult, *soccer.MatchSearchResult, error) {
	f, err := in.filter()
	if err != nil {
		return nil, nil, err
	}
	if f.DateFrom, err = parseDate("date_from", in.DateFrom); err != nil {
		return nil, nil, err
	}
	if f.DateTo, err = parseDate("date_to", in.DateTo); err != nil {
		return nil, nil, err
	}
	f.Team, f.Opponent = in.Team, in.Opponent
	f.HomeTeam, f.AwayTeam = in.HomeTeam, in.AwayTeam
	f.Round, f.Stage, f.Venue = in.Round, in.Stage, in.Venue
	f.MinTotalGoals, f.MinGoalDifference = in.MinTotalGoals, in.MinGoalDifference
	f.IncludeDuplicates = in.IncludeDuplicates

	res, err := s.graph.SearchMatches(f, limitOr(in.Limit, 25, 500))
	if err != nil {
		return nil, nil, err
	}
	return textResult(soccer.FormatMatchSearch(res)), res, nil
}

type headToHeadArgs struct {
	scopeArgs
	TeamA string `json:"team_a" jsonschema:"first club"`
	TeamB string `json:"team_b" jsonschema:"second club"`
	Limit int    `json:"limit,omitempty" jsonschema:"maximum meetings to list, default 20, maximum 500"`
}

func (s *Server) headToHead(ctx context.Context, req *mcp.CallToolRequest, in headToHeadArgs) (*mcp.CallToolResult, *soccer.HeadToHeadResult, error) {
	if in.TeamA == "" || in.TeamB == "" {
		return nil, nil, fmt.Errorf("both team_a and team_b are required")
	}
	f, err := in.filter()
	if err != nil {
		return nil, nil, err
	}
	res, err := s.graph.HeadToHead(in.TeamA, in.TeamB, f, limitOr(in.Limit, 20, 500))
	if err != nil {
		return nil, nil, err
	}
	return textResult(soccer.FormatHeadToHead(res)), res, nil
}

// --------------------------------------------------------------------- teams

type teamStatsArgs struct {
	scopeArgs
	Team  string `json:"team" jsonschema:"club to report on"`
	Venue string `json:"venue,omitempty" jsonschema:"restrict to home or away matches: home, away or all (default)"`
}

func (s *Server) teamStats(ctx context.Context, req *mcp.CallToolRequest, in teamStatsArgs) (*mcp.CallToolResult, *soccer.TeamStatsResult, error) {
	if in.Team == "" {
		return nil, nil, fmt.Errorf("team is required")
	}
	f, err := in.filter()
	if err != nil {
		return nil, nil, err
	}
	venue, err := soccer.ParseVenue(in.Venue)
	if err != nil {
		return nil, nil, err
	}
	res, err := s.graph.TeamStats(in.Team, f, venue)
	if err != nil {
		return nil, nil, err
	}
	return textResult(soccer.FormatTeamStats(res)), res, nil
}

type teamProfileArgs struct {
	Team       string `json:"team" jsonschema:"club to profile"`
	SquadLimit int    `json:"squad_limit,omitempty" jsonschema:"how many squad players to list, default 10"`
}

func (s *Server) teamProfile(ctx context.Context, req *mcp.CallToolRequest, in teamProfileArgs) (*mcp.CallToolResult, *soccer.TeamProfileResult, error) {
	if in.Team == "" {
		return nil, nil, fmt.Errorf("team is required")
	}
	res, err := s.graph.TeamProfile(in.Team, limitOr(in.SquadLimit, 10, 100))
	if err != nil {
		return nil, nil, err
	}
	return textResult(soccer.FormatTeamProfile(res)), res, nil
}

type listTeamsArgs struct {
	Query string `json:"query,omitempty" jsonschema:"free text to match against names, nicknames, aliases and states; omit to list every club"`
	Limit int    `json:"limit,omitempty" jsonschema:"maximum clubs to return, default 50"`
}

// TeamListResult is the structured payload of list_teams.
type TeamListResult struct {
	Query      string                 `json:"query,omitempty"`
	TotalTeams int                    `json:"total_teams"`
	Returned   int                    `json:"returned"`
	Teams      []soccer.TeamListEntry `json:"teams"`
}

func (s *Server) listTeams(ctx context.Context, req *mcp.CallToolRequest, in listTeamsArgs) (*mcp.CallToolResult, *TeamListResult, error) {
	all := s.graph.ListTeams(in.Query, 0)
	limited := s.graph.ListTeams(in.Query, limitOr(in.Limit, 50, 1000))
	res := &TeamListResult{Query: in.Query, TotalTeams: len(all), Returned: len(limited), Teams: limited}
	return textResult(soccer.FormatTeamList(limited, len(all))), res, nil
}

// ------------------------------------------------------------------- players

type searchPlayersArgs struct {
	Name               string `json:"name,omitempty" jsonschema:"substring of the player name"`
	Nationality        string `json:"nationality,omitempty" jsonschema:"country, e.g. Brazil"`
	Club               string `json:"club,omitempty" jsonschema:"club name; Brazilian clubs are resolved through the match graph"`
	Position           string `json:"position,omitempty" jsonschema:"FIFA position code (ST, GK, CB, CAM) or a group: goalkeeper, defender, midfielder, forward"`
	MinOverall         int    `json:"min_overall,omitempty" jsonschema:"minimum FIFA overall rating"`
	MaxOverall         int    `json:"max_overall,omitempty" jsonschema:"maximum FIFA overall rating"`
	MinPotential       int    `json:"min_potential,omitempty" jsonschema:"minimum FIFA potential rating"`
	MinAge             int    `json:"min_age,omitempty" jsonschema:"minimum age"`
	MaxAge             int    `json:"max_age,omitempty" jsonschema:"maximum age"`
	BrazilianClubsOnly bool   `json:"brazilian_clubs_only,omitempty" jsonschema:"only players whose club appears in the Brazilian match data"`
	SortBy             string `json:"sort_by,omitempty" jsonschema:"overall (default), potential, age, value, wage or name"`
	Limit              int    `json:"limit,omitempty" jsonschema:"maximum players to return, default 20, maximum 500"`
	GroupByClub        bool   `json:"group_by_club,omitempty" jsonschema:"also return a per-club breakdown with player counts and average ratings"`
}

func (s *Server) searchPlayers(ctx context.Context, req *mcp.CallToolRequest, in searchPlayersArgs) (*mcp.CallToolResult, *soccer.PlayerSearchResult, error) {
	f := soccer.PlayerFilter{
		Name: in.Name, Nationality: in.Nationality, Club: in.Club, Position: in.Position,
		MinOverall: in.MinOverall, MaxOverall: in.MaxOverall, MinPotential: in.MinPotential,
		MinAge: in.MinAge, MaxAge: in.MaxAge, SortBy: in.SortBy,
		BrazilianClubsOnly: in.BrazilianClubsOnly,
	}
	res, err := s.graph.SearchPlayers(f, limitOr(in.Limit, 20, 500), in.GroupByClub)
	if err != nil {
		return nil, nil, err
	}
	return textResult(soccer.FormatPlayerSearch(res)), res, nil
}

type playerProfileArgs struct {
	Name string `json:"name" jsonschema:"player name or part of it, e.g. Neymar or Gabriel Barbosa"`
}

func (s *Server) playerProfile(ctx context.Context, req *mcp.CallToolRequest, in playerProfileArgs) (*mcp.CallToolResult, *soccer.PlayerProfileResult, error) {
	res, err := s.graph.PlayerProfile(in.Name)
	if err != nil {
		return nil, nil, err
	}
	return textResult(soccer.FormatPlayerProfile(res)), res, nil
}

// -------------------------------------------------------------- competitions

type standingsArgs struct {
	Competition string `json:"competition,omitempty" jsonschema:"Serie A (default), Serie B or Serie C"`
	Season      int    `json:"season" jsonschema:"season year, e.g. 2019"`
	Venue       string `json:"venue,omitempty" jsonschema:"home, away or all (default); use home to rank clubs by home form"`
}

func (s *Server) standings(ctx context.Context, req *mcp.CallToolRequest, in standingsArgs) (*mcp.CallToolResult, *soccer.StandingsResult, error) {
	comp, err := soccer.ParseCompetition(in.Competition)
	if err != nil {
		return nil, nil, err
	}
	if comp == "" {
		comp = soccer.SerieA
	}
	if in.Season == 0 {
		return nil, nil, fmt.Errorf("season is required, e.g. 2019")
	}
	venue, err := soccer.ParseVenue(in.Venue)
	if err != nil {
		return nil, nil, err
	}
	res, err := s.graph.Standings(comp, in.Season, venue)
	if err != nil {
		return nil, nil, err
	}
	return textResult(soccer.FormatStandings(res)), res, nil
}

type championsArgs struct {
	Competition string `json:"competition,omitempty" jsonschema:"competition to report; omit for all of them"`
	SeasonFrom  int    `json:"season_from,omitempty" jsonschema:"first season, inclusive"`
	SeasonTo    int    `json:"season_to,omitempty" jsonschema:"last season, inclusive"`
}

func (s *Server) champions(ctx context.Context, req *mcp.CallToolRequest, in championsArgs) (*mcp.CallToolResult, *soccer.ChampionsResult, error) {
	comp, err := soccer.ParseCompetition(in.Competition)
	if err != nil {
		return nil, nil, err
	}
	res := s.graph.Champions(comp, in.SeasonFrom, in.SeasonTo)
	return textResult(soccer.FormatChampions(res)), res, nil
}

type bracketArgs struct {
	Competition string `json:"competition,omitempty" jsonschema:"Copa do Brasil or Copa Libertadores (default)"`
	Season      int    `json:"season" jsonschema:"season year, e.g. 2018"`
}

func (s *Server) bracket(ctx context.Context, req *mcp.CallToolRequest, in bracketArgs) (*mcp.CallToolResult, *soccer.BracketResult, error) {
	comp, err := soccer.ParseCompetition(in.Competition)
	if err != nil {
		return nil, nil, err
	}
	if comp == "" {
		comp = soccer.Libertadores
	}
	if in.Season == 0 {
		return nil, nil, fmt.Errorf("season is required, e.g. 2018")
	}
	res, err := s.graph.Bracket(comp, in.Season)
	if err != nil {
		return nil, nil, err
	}
	return textResult(soccer.FormatBracket(res)), res, nil
}

type competitionSummaryArgs struct {
	Competition string `json:"competition" jsonschema:"competition to summarise"`
	Seasons     []int  `json:"seasons,omitempty" jsonschema:"seasons to summarise; two or more produce a comparison. Defaults to the latest season."`
}

func (s *Server) competitionSummary(ctx context.Context, req *mcp.CallToolRequest, in competitionSummaryArgs) (*mcp.CallToolResult, *soccer.CompetitionSummaryResult, error) {
	comp, err := soccer.ParseCompetition(in.Competition)
	if err != nil {
		return nil, nil, err
	}
	if comp == "" {
		return nil, nil, fmt.Errorf("competition is required")
	}
	res, err := s.graph.CompetitionSummary(comp, in.Seasons)
	if err != nil {
		return nil, nil, err
	}
	return textResult(soccer.FormatCompetitionSummary(res)), res, nil
}

// ----------------------------------------------------------------- analytics

type rankingsArgs struct {
	scopeArgs
	Metric     string `json:"metric,omitempty" jsonschema:"most_wins, most_points (default), best_win_rate, most_goals_scored, best_defence, most_clean_sheets, most_draws, best_goal_difference or most_matches"`
	Venue      string `json:"venue,omitempty" jsonschema:"home, away or all (default); use away with best_win_rate for 'best away record'"`
	MinMatches int    `json:"min_matches,omitempty" jsonschema:"exclude clubs with fewer matches than this, default 10"`
	Limit      int    `json:"limit,omitempty" jsonschema:"how many clubs to rank, default 10"`
}

func (s *Server) rankings(ctx context.Context, req *mcp.CallToolRequest, in rankingsArgs) (*mcp.CallToolResult, *soccer.LeaderboardResult, error) {
	f, err := in.filter()
	if err != nil {
		return nil, nil, err
	}
	metric, err := soccer.ParseMetric(in.Metric)
	if err != nil {
		return nil, nil, err
	}
	venue, err := soccer.ParseVenue(in.Venue)
	if err != nil {
		return nil, nil, err
	}
	minMatches := in.MinMatches
	if minMatches <= 0 {
		minMatches = 10
	}
	res, err := s.graph.Leaderboard(metric, f, venue, minMatches, limitOr(in.Limit, 10, 200))
	if err != nil {
		return nil, nil, err
	}
	return textResult(soccer.FormatLeaderboard(res)), res, nil
}

type aggregateArgs struct {
	scopeArgs
	Team string `json:"team,omitempty" jsonschema:"restrict the statistics to one club's matches"`
	Top  int    `json:"top,omitempty" jsonschema:"how many biggest wins and highest scoring matches to list, default 5"`
}

func (s *Server) aggregateStats(ctx context.Context, req *mcp.CallToolRequest, in aggregateArgs) (*mcp.CallToolResult, *soccer.AggregateStats, error) {
	f, err := in.filter()
	if err != nil {
		return nil, nil, err
	}
	f.Team = in.Team
	res, err := s.graph.Aggregate(f, limitOr(in.Top, 5, 50))
	if err != nil {
		return nil, nil, err
	}
	return textResult(soccer.FormatAggregate(res)), res, nil
}

type derbiesArgs struct {
	scopeArgs
	IncludeMatches bool `json:"include_matches,omitempty" jsonschema:"also list the individual derby matches in scope"`
}

func (s *Server) listDerbies(ctx context.Context, req *mcp.CallToolRequest, in derbiesArgs) (*mcp.CallToolResult, *soccer.DerbiesResult, error) {
	f, err := in.filter()
	if err != nil {
		return nil, nil, err
	}
	res, err := s.graph.Derbies(f, in.IncludeMatches)
	if err != nil {
		return nil, nil, err
	}
	return textResult(soccer.FormatDerbies(res)), res, nil
}

// datasetInfoArgs has no fields: the tool takes no arguments.
type datasetInfoArgs struct{}

func (s *Server) datasetInfo(ctx context.Context, req *mcp.CallToolRequest, in datasetInfoArgs) (*mcp.CallToolResult, *soccer.DatasetInfoResult, error) {
	res := s.graph.DatasetInfo()
	return textResult(soccer.FormatDatasetInfo(res)), res, nil
}
