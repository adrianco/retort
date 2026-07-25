package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/sirupsen/logrus"
)

// MCP Protocol constants
const (
	MCPVersion       = "2024-11-05"
	ContentTypeText  = "text"
	ContentTypeImage = "image"
)

// Request represents an MCP request
type Request struct {
	ID      string      `json:"id"`
	Method  string      `json:"method"`
	Params  interface{} `json:"params,omitempty"`
}

// Response represents an MCP response
type Response struct {
	ID      string      `json:"id"`
	Result  interface{} `json:"result,omitempty"`
	Error   *Error      `json:"error,omitempty"`
}

// Error represents an MCP error
type Error struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    string `json:"data,omitempty"`
}

// Notification represents an MCP notification
type Notification struct {
	Method string      `json:"method"`
	Params interface{} `json:"params,omitempty"`
}

// Server represents the MCP server
type Server struct {
	dataDir    string
	matchData  *MatchDataStore
	playerData *PlayerDataStore
	log        *logrus.Logger
}

// NewServer creates a new MCP server
func NewServer(dataDir string) *Server {
	return &Server{
		dataDir:    dataDir,
		matchData:  NewMatchDataStore(dataDir),
		playerData: NewPlayerDataStore(dataDir),
		log:        logrus.New(),
	}
}

// Listen starts the MCP server
func (s *Server) Listen() error {
	logrus.Info("Starting Brazilian Soccer MCP Server")

	// Load all data
	if err := s.LoadData(); err != nil {
		return fmt.Errorf("failed to load data: %w", err)
	}

	logrus.Info("Data loaded successfully")
	logrus.Infof("Total matches loaded: %d", s.matchData.TotalMatches())
	logrus.Infof("Total players loaded: %d", s.playerData.TotalPlayers())

	// In a real implementation, this would start listening for MCP requests
	// For now, we'll provide a simple CLI interface for testing
	return s.runCLI()
}

// LoadData loads all CSV files
func (s *Server) LoadData() error {
	// Load match data
	matchFiles := []string{
		"Brasileirao_Matches.csv",
		"Brazilian_Cup_Matches.csv",
		"Libertadores_Matches.csv",
		"BR-Football-Dataset.csv",
		"novo_campeonato_brasileiro.csv",
	}

	for _, file := range matchFiles {
		filePath := filepath.Join(s.dataDir, "data", "kaggle", file)
		if err := s.matchData.LoadCSV(filePath, file); err != nil {
			return fmt.Errorf("failed to load %s: %w", file, err)
		}
	}

	// Load player data
	playerFile := filepath.Join(s.dataDir, "data", "kaggle", "fifa_data.csv")
	if err := s.playerData.LoadCSV(playerFile); err != nil {
		return fmt.Errorf("failed to load player data: %w", err)
	}

	return nil
}

// runCLI provides a simple CLI for testing
func (s *Server) runCLI() error {
	logrus.Info("Enter commands (type 'quit' to exit):")
	logrus.Info("  matches <team>       - Find matches for a team")
	logrus.Info("  teams <name>         - Find teams containing name")
	logrus.Info("  players <name>       - Find players containing name")
	logrus.Info("  stats <team> <year>  - Get team statistics")
	logrus.Info("  standings <year>     - Get Brasileirao standings")
	logrus.Info("  quit                 - Exit")

	scanner := NewScanner()
	for {
		fmt.Print("> ")
		input := scanner.Scan()
		if input == "quit" || input == "exit" {
			break
		}

		if input == "" {
			continue
		}

		s.handleCommand(input)
	}

	return nil
}

// handleCommand processes CLI commands
func (s *Server) handleCommand(input string) {
	parts := strings.Fields(input)
	if len(parts) == 0 {
		return
	}

	command := strings.ToLower(parts[0])
	args := parts[1:]

	switch command {
	case "matches":
		s.handleMatches(args)
	case "teams":
		s.handleTeams(args)
	case "players":
		s.handlePlayers(args)
	case "stats":
		s.handleStats(args)
	case "standings":
		s.handleStandings(args)
	case "help":
		s.showHelp()
	default:
		fmt.Printf("Unknown command: %s\n", command)
		s.showHelp()
	}
}

func (s *Server) handleMatches(args []string) {
	if len(args) == 0 {
		fmt.Println("Usage: matches <team-name>")
		return
	}

	teamName := strings.Join(args, " ")
	matches := s.matchData.FindMatchesByTeam(teamName)

	fmt.Printf("\nFound %d matches for '%s':\n", len(matches), teamName)
	for i, m := range matches {
		fmt.Printf("%d. %s %d-%d %s (%s)\n",
			i+1, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, m.Competition)
	}
}

func (s *Server) handleTeams(args []string) {
	if len(args) == 0 {
		fmt.Println("Usage: teams <team-name>")
		return
	}

	teamName := strings.Join(args, " ")
	teams := s.matchData.FindTeams(teamName)

	fmt.Printf("\nFound %d teams containing '%s':\n", len(teams), teamName)
	for _, team := range teams {
		fmt.Printf("  - %s\n", team)
	}
}

func (s *Server) handlePlayers(args []string) {
	if len(args) == 0 {
		fmt.Println("Usage: players <player-name>")
		return
	}

	playerName := strings.Join(args, " ")
	players := s.playerData.SearchPlayers(playerName)

	fmt.Printf("\nFound %d players containing '%s':\n", len(players), playerName)
	for i, p := range players {
		fmt.Printf("%d. %s (%s, %s) - Overall: %d\n",
			i+1, p.Name, p.Position, p.Nationality, p.Overall)
	}
}

func (s *Server) handleStats(args []string) {
	if len(args) < 2 {
		fmt.Println("Usage: stats <team-name> <year>")
		return
	}

	teamName := args[0]
	year := args[1]

	stats := s.matchData.GetTeamStats(teamName, year)

	fmt.Printf("\n%s stats for %s:\n", teamName, year)
	fmt.Printf("  Matches: %d\n", stats.Matches)
	fmt.Printf("  Wins: %d\n", stats.Wins)
	fmt.Printf("  Draws: %d\n", stats.Draws)
	fmt.Printf("  Losses: %d\n", stats.Losses)
	fmt.Printf("  Goals For: %d\n", stats.GoalsFor)
	fmt.Printf("  Goals Against: %d\n", stats.GoalsAgainst)
	fmt.Printf("  Win Rate: %.1f%%\n", stats.WinRate)
}

func (s *Server) handleStandings(args []string) {
	if len(args) == 0 {
		fmt.Println("Usage: standings <year>")
		return
	}

	yearStr := args[0]
	standings := s.matchData.GetBrasileiraoStandings(yearStr)

	fmt.Printf("\n%s Brasileirão Standings:\n", yearStr)
	fmt.Printf("%-3s %-25s %3s %3s %3s %5s %5s %5s\n",
		"#", "Team", "MP", "W", "D", "GF", "GA", "Pts")
	fmt.Println(strings.Repeat("-", 55))

	for i, standing := range standings {
		fmt.Printf("%-3d %-25s %3d %3d %3d %5d %5d %5d\n",
			i+1, standing.Team, standing.Played, standing.Wins, standing.Draws, standing.GoalsFor, standing.GoalsAgainst, standing.Points)
	}
}

func (s *Server) showHelp() {
	fmt.Println("\nCommands:")
	fmt.Println("  matches <team>       - Find matches for a team")
	fmt.Println("  teams <name>         - Find teams containing name")
	fmt.Println("  players <name>       - Find players containing name")
	fmt.Println("  stats <team> <year>  - Get team statistics")
	fmt.Println("  standings <year>     - Get Brasileirao standings")
	fmt.Println("  quit                 - Exit")
	fmt.Println()
}

// Scanner provides simple input scanning
type Scanner struct{}

func NewScanner() *Scanner {
	return &Scanner{}
}

func (s *Scanner) Scan() string {
	var input string
	fmt.Scanln(&input)
	return input
}

// Main entry point
func main() {
	dataDir := "."
	if len(os.Args) > 1 {
		dataDir = os.Args[1]
	}

	server := NewServer(dataDir)
	if err := server.Listen(); err != nil {
		logrus.Fatal(err)
	}
}
