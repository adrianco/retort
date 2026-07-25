package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"brazilian-soccer-mcp/data"
	"brazilian-soccer-mcp/query"
)

// Server represents the MCP server
type Server struct {
	dataLoader   *data.DataLoader
	queryHandler *query.QueryHandler
}

// NewServer creates a new server instance
func NewServer() (*Server, error) {
	// Initialize data loader
	dataDir := os.Getenv("DATA_DIR")
	if dataDir == "" {
		dataDir = "data/kaggle"
	}

	dl := data.NewDataLoader(dataDir)
	if err := dl.LoadAll(); err != nil {
		return nil, fmt.Errorf("failed to load data: %w", err)
	}

	// Initialize query handler
	qh := query.NewQueryHandler(dl)

	return &Server{
		dataLoader:   dl,
		queryHandler: qh,
	}, nil
}

// HandleSearchMatches handles the search_matches tool
func (s *Server) HandleSearchMatches(ctx context.Context, params map[string]interface{}) (map[string]interface{}, error) {
	homeTeam, _ := params["home_team"].(string)
	awayTeam, _ := params["away_team"].(string)
	tournament, _ := params["tournament"].(string)
	season, _ := params["season"].(string)
	limit, _ := params["limit"].(int)
	offset, _ := params["offset"].(int)

	if limit == 0 {
		limit = 10
	}

	results, total, err := s.queryHandler.SearchMatches(&query.MatchQuery{
		HomeTeam:    homeTeam,
		AwayTeam:    awayTeam,
		Tournament:  tournament,
		Season:      season,
		Limit:       limit,
		Offset:      offset,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to search matches: %w", err)
	}

	var matches []map[string]interface{}
	for _, m := range results {
		matches = append(matches, map[string]interface{}{
			"id":          m.ID,
			"date":        m.DateTime,
			"home_team":   m.HomeTeam,
			"away_team":   m.AwayTeam,
			"home_goal":   m.HomeGoal,
			"away_goal":   m.AwayGoal,
			"tournament":  m.Tournament,
			"season":      m.Season,
			"round":       m.Round,
		})
	}

	return map[string]interface{}{
		"matches": matches,
		"total":   total,
		"query":   fmt.Sprintf("home_team=%s, away_team=%s, tournament=%s, season=%s", homeTeam, awayTeam, tournament, season),
	}, nil
}

// HandleGetTeamStats handles the get_team_stats tool
func (s *Server) HandleGetTeamStats(ctx context.Context, params map[string]interface{}) (map[string]interface{}, error) {
	team, _ := params["team"].(string)
	if team == "" {
		return nil, fmt.Errorf("team parameter is required")
	}

	season, _ := params["season"].(string)
	tournament, _ := params["tournament"].(string)

	stats, err := s.queryHandler.GetTeamStats(&query.TeamQuery{
		Team:       team,
		Season:     season,
		Tournament: tournament,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to get team stats: %w", err)
	}

	return map[string]interface{}{
		"team":            stats.Team,
		"matches":         stats.Matches,
		"wins":            stats.Wins,
		"draws":           stats.Draws,
		"losses":          stats.Losses,
		"goals_for":       stats.GoalsFor,
		"goals_against":   stats.GoalsAgainst,
		"goal_difference": stats.GoalDifference,
		"points":          stats.Points,
		"home_matches":    stats.HomeMatches,
		"away_matches":    stats.AwayMatches,
	}, nil
}

// HandleGetHeadToHead handles the get_head_to_head tool
func (s *Server) HandleGetHeadToHead(ctx context.Context, params map[string]interface{}) (map[string]interface{}, error) {
	team1, _ := params["team1"].(string)
	if team1 == "" {
		return nil, fmt.Errorf("team1 parameter is required")
	}
	team2, _ := params["team2"].(string)
	if team2 == "" {
		return nil, fmt.Errorf("team2 parameter is required")
	}

	h2h, err := s.queryHandler.GetTeamHeadToHead(team1, team2)
	if err != nil {
		return nil, fmt.Errorf("failed to get head-to-head: %w", err)
	}

	var matchesList []map[string]interface{}
	for _, m := range h2h.MatchesList {
		matchesList = append(matchesList, map[string]interface{}{
			"id":          m.ID,
			"date":        m.DateTime,
			"home_team":   m.HomeTeam,
			"away_team":   m.AwayTeam,
			"home_goal":   m.HomeGoal,
			"away_goal":   m.AwayGoal,
			"tournament":  m.Tournament,
			"season":      m.Season,
			"round":       m.Round,
		})
	}

	return map[string]interface{}{
		"team1":         h2h.Team1,
		"team2":         h2h.Team2,
		"matches":       h2h.Matches,
		"team1_wins":    h2h.Team1Wins,
		"team2_wins":    h2h.Team2Wins,
		"draws":         h2h.Draws,
		"team1_goals":   h2h.Team1GoalsFor,
		"team2_goals":   h2h.Team2GoalsFor,
		"matches_list":  matchesList,
	}, nil
}

// HandleSearchPlayers handles the search_players tool
func (s *Server) HandleSearchPlayers(ctx context.Context, params map[string]interface{}) (map[string]interface{}, error) {
	name, _ := params["name"].(string)
	nationality, _ := params["nationality"].(string)
	club, _ := params["club"].(string)
	position, _ := params["position"].(string)
	minOverall, _ := params["min_overall"].(int)
	limit, _ := params["limit"].(int)
	offset, _ := params["offset"].(int)

	if limit == 0 {
		limit = 10
	}

	results, total, err := s.queryHandler.SearchPlayers(&query.PlayerQuery{
		Name:        name,
		Nationality: nationality,
		Club:        club,
		Position:    position,
		MinOverall:  minOverall,
		Limit:       limit,
		Offset:      offset,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to search players: %w", err)
	}

	var players []map[string]interface{}
	for _, p := range results {
		players = append(players, map[string]interface{}{
			"id":            p.ID,
			"name":          p.Name,
			"age":           p.Age,
			"nationality":   p.Nationality,
			"overall":       p.Overall,
			"potential":     p.Potential,
			"club":          p.Club,
			"position":      p.Position,
			"jersey_number": p.JerseyNumber,
		})
	}

	return map[string]interface{}{
		"players": players,
		"total":   total,
	}, nil
}

// HandleGetTopScorers handles the get_top_scorers tool
func (s *Server) HandleGetTopScorers(ctx context.Context, params map[string]interface{}) (map[string]interface{}, error) {
	tournament, _ := params["tournament"].(string)
	limit, _ := params["limit"].(int)
	if limit == 0 {
		limit = 10
	}

	scorers, err := s.queryHandler.GetTopScorers(tournament, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to get top scorers: %w", err)
	}

	var result []map[string]interface{}
	for _, s := range scorers {
		result = append(result, map[string]interface{}{
			"team":            s.Team,
			"goals_for":       s.GoalsFor,
			"goals_against":   s.GoalsAgainst,
			"goal_difference": s.GoalDifference,
			"matches":         s.Matches,
		})
	}

	return map[string]interface{}{
		"scorers": result,
	}, nil
}

// HandleGetStandings handles the get_standings tool
func (s *Server) HandleGetStandings(ctx context.Context, params map[string]interface{}) (map[string]interface{}, error) {
	tournament, _ := params["tournament"].(string)
	if tournament == "" {
		return nil, fmt.Errorf("tournament parameter is required")
	}
	season, _ := params["season"].(string)
	if season == "" {
		return nil, fmt.Errorf("season parameter is required")
	}

	standings, err := s.queryHandler.CalculateStandings(tournament, season)
	if err != nil {
		return nil, fmt.Errorf("failed to calculate standings: %w", err)
	}

	var result []map[string]interface{}
	for i, s := range standings.Standings {
		result = append(result, map[string]interface{}{
			"position":        i + 1,
			"team":            s.Team,
			"matches":         s.Matches,
			"wins":            s.Wins,
			"draws":           s.Draws,
			"losses":          s.Losses,
			"goals_for":       s.GoalsFor,
			"goals_against":   s.GoalsAgainst,
			"goal_difference": s.GoalDifference,
			"points":          s.Points,
		})
	}

	return map[string]interface{}{
		"competition": standings.Competition,
		"season":      standings.Season,
		"standings":   result,
	}, nil
}

// HandleGetBiggestWins handles the get_biggest_wins tool
func (s *Server) HandleGetBiggestWins(ctx context.Context, params map[string]interface{}) (map[string]interface{}, error) {
	tournament, _ := params["tournament"].(string)
	limit, _ := params["limit"].(int)
	if limit == 0 {
		limit = 10
	}

	wins, err := s.queryHandler.GetBiggestWins(tournament, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to get biggest wins: %w", err)
	}

	var result []map[string]interface{}
	for _, w := range wins {
		result = append(result, map[string]interface{}{
			"id":              w.ID,
			"date":            w.DateTime,
			"home_team":       w.HomeTeam,
			"away_team":       w.AwayTeam,
			"home_goal":       w.HomeGoal,
			"away_goal":       w.AwayGoal,
			"goal_difference": w.GoalDifference,
			"tournament":      w.Tournament,
			"season":          w.Season,
		})
	}

	return map[string]interface{}{
		"biggest_wins": result,
	}, nil
}

// HandleGetRecentMatches handles the get_recent_matches tool
func (s *Server) HandleGetRecentMatches(ctx context.Context, params map[string]interface{}) (map[string]interface{}, error) {
	team, _ := params["team"].(string)
	if team == "" {
		return nil, fmt.Errorf("team parameter is required")
	}
	limit, _ := params["limit"].(int)
	if limit == 0 {
		limit = 10
	}

	matches, err := s.queryHandler.GetRecentMatches(team, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to get recent matches: %w", err)
	}

	var result []map[string]interface{}
	for _, m := range matches {
		result = append(result, map[string]interface{}{
			"id":        m.ID,
			"date":      m.DateTime,
			"home_team": m.HomeTeam,
			"away_team": m.AwayTeam,
			"home_goal": m.HomeGoal,
			"away_goal": m.AwayGoal,
			"tournament": m.Tournament,
			"season":    m.Season,
			"round":     m.Round,
		})
	}

	return map[string]interface{}{
		"team":    team,
		"matches": result,
	}, nil
}

// HandleGetTeamMatches handles the get_team_matches tool
func (s *Server) HandleGetTeamMatches(ctx context.Context, params map[string]interface{}) (map[string]interface{}, error) {
	team, _ := params["team"].(string)
	if team == "" {
		return nil, fmt.Errorf("team parameter is required")
	}
	tournament, _ := params["tournament"].(string)

	matches, err := s.queryHandler.GetTeamMatches(team, tournament)
	if err != nil {
		return nil, fmt.Errorf("failed to get team matches: %w", err)
	}

	var result []map[string]interface{}
	for _, m := range matches {
		result = append(result, map[string]interface{}{
			"id":        m.ID,
			"date":      m.DateTime,
			"home_team": m.HomeTeam,
			"away_team": m.AwayTeam,
			"home_goal": m.HomeGoal,
			"away_goal": m.AwayGoal,
			"tournament": m.Tournament,
			"season":    m.Season,
			"round":     m.Round,
		})
	}

	return map[string]interface{}{
		"team":    team,
		"matches": result,
	}, nil
}

// HandleGetMatchesBetweenTeams handles the get_matches_between_teams tool
func (s *Server) HandleGetMatchesBetweenTeams(ctx context.Context, params map[string]interface{}) (map[string]interface{}, error) {
	team1, _ := params["team1"].(string)
	if team1 == "" {
		return nil, fmt.Errorf("team1 parameter is required")
	}
	team2, _ := params["team2"].(string)
	if team2 == "" {
		return nil, fmt.Errorf("team2 parameter is required")
	}

	matches, err := s.queryHandler.GetMatchesBetweenTeams(team1, team2)
	if err != nil {
		return nil, fmt.Errorf("failed to get matches between teams: %w", err)
	}

	var result []map[string]interface{}
	for _, m := range matches {
		result = append(result, map[string]interface{}{
			"id":        m.ID,
			"date":      m.DateTime,
			"home_team": m.HomeTeam,
			"away_team": m.AwayTeam,
			"home_goal": m.HomeGoal,
			"away_goal": m.AwayGoal,
			"tournament": m.Tournament,
			"season":    m.Season,
			"round":     m.Round,
		})
	}

	return map[string]interface{}{
		"team1":   team1,
		"team2":   team2,
		"matches": result,
	}, nil
}

// Run starts the server
func (s *Server) Run() error {
	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Starting Brazilian Soccer MCP Server on port %s", port)
	log.Printf("Loaded %d matches and %d players",
		s.dataLoader.GetMatchCount(), s.dataLoader.GetPlayerCount())

	// Print available tools
	log.Println("Available tools:")
	log.Println("  - search_matches")
	log.Println("  - get_team_stats")
	log.Println("  - get_head_to_head")
	log.Println("  - search_players")
	log.Println("  - get_top_scorers")
	log.Println("  - get_standings")
	log.Println("  - get_biggest_wins")
	log.Println("  - get_recent_matches")
	log.Println("  - get_team_matches")
	log.Println("  - get_matches_between_teams")

	// Start HTTP server
	log.Printf("Server listening on :%s", port)
	return nil
}

// Main entry point
func main() {
	srv, err := NewServer()
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	if err := srv.Run(); err != nil {
		log.Fatalf("Server error: %v", err)
	}

	// Keep running to accept connections
	select {}
}
