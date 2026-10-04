package app

import (
	"fmt"
	"strings"
	"time"

	"brsoccer/internal/mcpserver"
	"brsoccer/internal/soccer"
)

// tools lists the questions the server can answer, as MCP tools.
func tools(store *soccer.Store) []mcpserver.Tool {
	h := handlers{store}
	matchFilters := map[string]any{
		"team":        text("Team name, in any common spelling, e.g. \"Flamengo\", \"Palmeiras-SP\", \"Sao Paulo\""),
		"opponent":    text("Only matches against this team"),
		"venue":       enum("Only the team's home or away matches", "home", "away", "any"),
		"competition": text(competitionHelp),
		"season":      integer("Season year, e.g. 2019"),
		"date_from":   text("Earliest match date, YYYY-MM-DD or DD/MM/YYYY"),
		"date_to":     text("Latest match date, YYYY-MM-DD or DD/MM/YYYY"),
	}
	return []mcpserver.Tool{
		{
			Name: "search_matches",
			Description: "Find matches by team, opponent, home/away, competition, season, date range or knockout stage " +
				"(e.g. all Copa do Brasil finals). Most recent first. With team and opponent, also gives the head-to-head record.",
			InputSchema: schema(with(matchFilters, map[string]any{
				"stage": text("Knockout stage: final, semifinals, quarterfinals, round of 16, group stage"),
				"limit": integer("Most matches to list (default 20); the total found is always reported"),
				"order": enum("Order of the list", "newest_first", "oldest_first"),
			})),
			Handler: h.searchMatches,
		},
		{
			Name:        "last_meeting",
			Description: "When two teams last played each other, and the score.",
			InputSchema: schema(map[string]any{"team": text("First team"), "opponent": text("Second team")}, "team", "opponent"),
			Handler:     h.lastMeeting,
		},
		{
			Name:        "head_to_head",
			Description: "Compare two teams head-to-head: meetings, wins, draws, goals, per competition, biggest win and recent meetings.",
			InputSchema: schema(map[string]any{"team_a": text("First team"), "team_b": text("Second team"), "competition": text(competitionHelp)}, "team_a", "team_b"),
			Handler:     h.headToHead,
		},
		{
			Name:        "find_derbies",
			Description: "Find matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, Clássico Mineiro, Ba-Vi...).",
			InputSchema: schema(map[string]any{"season": integer("Season year"), "competition": text(competitionHelp),
				"team": text("Only this team's derbies"), "limit": integer("Most matches to list (default 50)")}),
			Handler: h.findDerbies,
		},
		{
			Name: "team_record",
			Description: "A team's win/draw/loss record, goals for and against, points and win rate — optionally for one season, " +
				"competition, or only home or away matches — with a breakdown by competition.",
			InputSchema: schema(map[string]any{"team": matchFilters["team"], "season": matchFilters["season"],
				"competition": matchFilters["competition"], "venue": matchFilters["venue"]}, "team"),
			Handler: h.teamRecord,
		},
		{
			Name: "rank_teams",
			Description: "Rank teams by win rate, points, goals scored, goals conceded, goal difference or wins — e.g. the best home " +
				"record, best away record, or the team that scored most goals in a season.",
			InputSchema: schema(map[string]any{
				"metric":      enum("What to rank by (default win_rate)", soccer.MetricNames()...),
				"venue":       matchFilters["venue"],
				"competition": matchFilters["competition"],
				"season":      matchFilters["season"],
				"min_matches": integer("Only rank teams with at least this many matches (default: a quarter of the most played, for rates)"),
				"limit":       integer("How many teams to list (default 10)"),
			}),
			Handler: h.rankTeams,
		},
		{
			Name:        "team_competitions",
			Description: "Which competitions a team has played in, with matches, seasons and results in each.",
			InputSchema: schema(map[string]any{"team": matchFilters["team"]}, "team"),
			Handler:     h.teamCompetitions,
		},
		{
			Name:        "find_team",
			Description: "Identify which team a name refers to and list the spellings the datasets use for it.",
			InputSchema: schema(map[string]any{"name": text("Team name or part of it")}, "name"),
			Handler:     h.findTeam,
		},
		{
			Name:        "club_profile",
			Description: "Everything about a club: its squad and ratings from the FIFA player data together with its results from the match data.",
			InputSchema: schema(map[string]any{"team": matchFilters["team"]}, "team"),
			Handler:     h.clubProfile,
		},
		{
			Name:        "standings",
			Description: "League table for a Brasileirão season, calculated from match results, naming the champion and relegated teams.",
			InputSchema: schema(map[string]any{"season": integer("Season year (default: latest)"),
				"competition": text("Brasileirão Série A (default), Série B or Série C")}),
			Handler: h.standings,
		},
		{
			Name:        "knockout_bracket",
			Description: "Knockout ties of a Copa Libertadores or Copa do Brasil season, stage by stage, with aggregate scores and winners.",
			InputSchema: schema(map[string]any{"competition": text("Copa Libertadores (default) or Copa do Brasil"),
				"season": integer("Season year (default: latest)")}),
			Handler: h.bracket,
		},
		{
			Name:        "search_players",
			Description: "Find players in the FIFA player data by name, nationality, club or position (forward, midfielder, defender, goalkeeper or codes like ST), highest rated first.",
			InputSchema: schema(map[string]any{
				"name":        text("Part of the player's name"),
				"nationality": text("Country, e.g. Brazil"),
				"club":        text("Club name"),
				"position":    text("forward, midfielder, defender, goalkeeper, or position codes such as ST,LW"),
				"min_overall": integer("Minimum overall rating"),
				"max_age":     integer("Maximum age"),
				"limit":       integer("Most players to list (default 20); the total found is always reported"),
			}),
			Handler: h.searchPlayers,
		},
		{
			Name:        "get_player",
			Description: "Who a player is: club, nationality, position, ratings, physical details and best attributes.",
			InputSchema: schema(map[string]any{"name": text("Player name")}, "name"),
			Handler:     h.getPlayer,
		},
		{
			Name:        "brazilian_players_by_club",
			Description: "How many players of a nationality (default Brazil) play at each Brazilian club, with average ratings. Combines player and match data.",
			InputSchema: schema(map[string]any{"nationality": text("Nationality (default Brazil)")}),
			Handler:     h.playersByClub,
		},
		{
			Name:        "competition_stats",
			Description: "Aggregate statistics: matches, average goals per match, home win, draw and away win rates, average corners and shots where recorded.",
			InputSchema: schema(map[string]any{"competition": matchFilters["competition"], "season": matchFilters["season"],
				"team": text("Only this team's matches")}),
			Handler: h.competitionStats,
		},
		{
			Name:        "biggest_wins",
			Description: "The most one-sided results, largest winning margin first.",
			InputSchema: schema(map[string]any{"competition": matchFilters["competition"], "season": matchFilters["season"],
				"team": text("Only this team's matches"), "limit": integer("How many results (default 10)")}),
			Handler: h.biggestWins,
		},
		{
			Name:        "compare_seasons",
			Description: "Compare seasons of a competition: goals per match, results split, champion and top-scoring team.",
			InputSchema: schema(map[string]any{"seasons": text("Seasons to compare, e.g. \"2018,2019\""),
				"competition": text("Default Brasileirão Série A")}, "seasons"),
			Handler: h.compareSeasons,
		},
		{
			Name:        "dataset_overview",
			Description: "What data the server holds: each provided dataset, its records and seasons, and totals.",
			InputSchema: schema(map[string]any{}),
			Handler:     h.overview,
		},
	}
}

const competitionHelp = "Brasileirão (Série A), Série B, Série C, Copa do Brasil or Libertadores"

func text(desc string) map[string]any { return map[string]any{"type": "string", "description": desc} }
func integer(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}

func enum(desc string, values ...string) map[string]any {
	return map[string]any{"type": "string", "description": desc, "enum": values}
}

func schema(props map[string]any, required ...string) map[string]any {
	s := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

func with(base, extra map[string]any) map[string]any {
	out := map[string]any{}
	for k, v := range base {
		out[k] = v
	}
	for k, v := range extra {
		out[k] = v
	}
	return out
}

type handlers struct{ store *soccer.Store }

func (h handlers) team(a mcpserver.Args, name string) (string, error) {
	v := a.String(name)
	if v == "" {
		return "", nil
	}
	return h.store.ResolveTeam(v)
}

func (h handlers) requiredTeam(a mcpserver.Args, name string) (string, error) {
	if a.String(name) == "" {
		return "", fmt.Errorf("%s is required", name)
	}
	return h.team(a, name)
}

func competition(a mcpserver.Args) (soccer.Competition, error) {
	v := a.String("competition")
	if v == "" {
		return "", nil
	}
	c, ok := soccer.ResolveCompetition(v)
	if !ok {
		return "", &soccer.NotFoundError{Kind: "competition", Name: v,
			Suggestions: []string{string(soccer.SerieA), string(soccer.SerieB), string(soccer.SerieC), string(soccer.CopaDoBrasil), string(soccer.Libertadores)}}
	}
	return c, nil
}

func venue(a mcpserver.Args) (string, error) {
	switch v := strings.ToLower(a.String("venue")); v {
	case "", "any", "all", "both":
		return "", nil
	case "home", "away":
		return v, nil
	default:
		return "", fmt.Errorf("venue should be home, away or any, not %q", v)
	}
}

// query reads the match filters common to many tools.
func (h handlers) query(a mcpserver.Args) (soccer.MatchQuery, error) {
	var q soccer.MatchQuery
	var err error
	if q.Team, err = h.team(a, "team"); err != nil {
		return q, err
	}
	if q.Opponent, err = h.team(a, "opponent"); err != nil {
		return q, err
	}
	if q.Venue, err = venue(a); err != nil {
		return q, err
	}
	if q.Competition, err = competition(a); err != nil {
		return q, err
	}
	if q.Season, err = a.Int("season", 0); err != nil {
		return q, err
	}
	if q.From, err = date(a, "date_from"); err != nil {
		return q, err
	}
	if q.To, err = date(a, "date_to"); err != nil {
		return q, err
	}
	q.Stage = a.String("stage")
	return q, nil
}

func date(a mcpserver.Args, name string) (time.Time, error) {
	v := a.String(name)
	if v == "" {
		return time.Time{}, nil
	}
	t, ok := soccer.ParseDate(v)
	if !ok {
		return time.Time{}, fmt.Errorf("%s %q is not a date; use YYYY-MM-DD", name, v)
	}
	return t, nil
}

type texter interface{ Text() string }

func answer(v texter) (mcpserver.Result, error) {
	return mcpserver.Result{Text: v.Text(), Structured: v}, nil
}

func (h handlers) searchMatches(a mcpserver.Args) (mcpserver.Result, error) {
	q, err := h.query(a)
	if err != nil {
		return mcpserver.Result{}, err
	}
	limit, err := a.Int("limit", 20)
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(h.store.SearchMatches(q, limit, a.String("order") == "oldest_first"))
}

func (h handlers) lastMeeting(a mcpserver.Args) (mcpserver.Result, error) {
	team, err := h.requiredTeam(a, "team")
	if err != nil {
		return mcpserver.Result{}, err
	}
	opponent, err := h.requiredTeam(a, "opponent")
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(h.store.LastMeeting(team, opponent))
}

func (h handlers) headToHead(a mcpserver.Args) (mcpserver.Result, error) {
	teamA, err := h.requiredTeam(a, "team_a")
	if err != nil {
		return mcpserver.Result{}, err
	}
	teamB, err := h.requiredTeam(a, "team_b")
	if err != nil {
		return mcpserver.Result{}, err
	}
	c, err := competition(a)
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(h.store.HeadToHead(teamA, teamB, c))
}

func (h handlers) findDerbies(a mcpserver.Args) (mcpserver.Result, error) {
	q, err := h.query(a)
	if err != nil {
		return mcpserver.Result{}, err
	}
	q.DerbiesOnly = true
	limit, err := a.Int("limit", 50)
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(h.store.SearchMatches(q, limit, false))
}

func (h handlers) teamRecord(a mcpserver.Args) (mcpserver.Result, error) {
	if a.String("team") == "" {
		return mcpserver.Result{}, fmt.Errorf("team is required")
	}
	q, err := h.query(a)
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(h.store.TeamRecord(q))
}

func (h handlers) rankTeams(a mcpserver.Args) (mcpserver.Result, error) {
	q, err := h.query(a)
	if err != nil {
		return mcpserver.Result{}, err
	}
	minMatches, err := a.Int("min_matches", 0)
	if err != nil {
		return mcpserver.Result{}, err
	}
	limit, err := a.Int("limit", 10)
	if err != nil {
		return mcpserver.Result{}, err
	}
	r, err := h.store.RankTeams(q, a.String("metric"), minMatches, limit)
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(r)
}

func (h handlers) teamCompetitions(a mcpserver.Args) (mcpserver.Result, error) {
	team, err := h.requiredTeam(a, "team")
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(h.store.TeamCompetitions(team))
}

func (h handlers) findTeam(a mcpserver.Args) (mcpserver.Result, error) {
	name := a.String("name")
	if name == "" {
		return mcpserver.Result{}, fmt.Errorf("name is required")
	}
	found := h.store.FindTeams(name)
	if len(found.Teams) == 0 {
		return mcpserver.Result{}, &soccer.NotFoundError{Kind: "team", Name: name}
	}
	return answer(found)
}

func (h handlers) clubProfile(a mcpserver.Args) (mcpserver.Result, error) {
	team := a.String("team")
	if team == "" {
		return mcpserver.Result{}, fmt.Errorf("team is required")
	}
	p, err := h.store.ClubProfile(team)
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(p)
}

func (h handlers) standings(a mcpserver.Args) (mcpserver.Result, error) {
	c, err := competition(a)
	if err != nil {
		return mcpserver.Result{}, err
	}
	season, err := a.Int("season", 0)
	if err != nil {
		return mcpserver.Result{}, err
	}
	st, err := h.store.Standings(c, season)
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(st)
}

func (h handlers) bracket(a mcpserver.Args) (mcpserver.Result, error) {
	c, err := competition(a)
	if err != nil {
		return mcpserver.Result{}, err
	}
	season, err := a.Int("season", 0)
	if err != nil {
		return mcpserver.Result{}, err
	}
	b, err := h.store.Bracket(c, season)
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(b)
}

func (h handlers) searchPlayers(a mcpserver.Args) (mcpserver.Result, error) {
	q := soccer.PlayerQuery{Name: a.String("name"), Nationality: a.String("nationality"), Club: a.String("club"), Position: a.String("position")}
	var err error
	if q.MinOverall, err = a.Int("min_overall", 0); err != nil {
		return mcpserver.Result{}, err
	}
	if q.MaxAge, err = a.Int("max_age", 0); err != nil {
		return mcpserver.Result{}, err
	}
	limit, err := a.Int("limit", 20)
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(h.store.SearchPlayers(q, limit))
}

func (h handlers) getPlayer(a mcpserver.Args) (mcpserver.Result, error) {
	name := a.String("name")
	if name == "" {
		return mcpserver.Result{}, fmt.Errorf("name is required")
	}
	p, err := h.store.PlayerProfile(name)
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(p)
}

func (h handlers) playersByClub(a mcpserver.Args) (mcpserver.Result, error) {
	return answer(h.store.PlayersAtBrazilianClubs(a.String("nationality")))
}

func (h handlers) competitionStats(a mcpserver.Args) (mcpserver.Result, error) {
	q, err := h.query(a)
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(h.store.CompetitionStats(q))
}

func (h handlers) biggestWins(a mcpserver.Args) (mcpserver.Result, error) {
	q, err := h.query(a)
	if err != nil {
		return mcpserver.Result{}, err
	}
	limit, err := a.Int("limit", 10)
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(h.store.BiggestWins(q, limit))
}

func (h handlers) compareSeasons(a mcpserver.Args) (mcpserver.Result, error) {
	seasons, err := a.Ints("seasons")
	if err != nil {
		return mcpserver.Result{}, err
	}
	if len(seasons) == 0 {
		return mcpserver.Result{}, fmt.Errorf("seasons is required, e.g. \"2018,2019\"")
	}
	c, err := competition(a)
	if err != nil {
		return mcpserver.Result{}, err
	}
	return answer(h.store.CompareSeasons(c, seasons))
}

func (h handlers) overview(mcpserver.Args) (mcpserver.Result, error) {
	return answer(h.store.Overview())
}
