package main

import (
	"fmt"
	"os"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: brazilian-soccer-mcp <command> [args]")
		fmt.Println("\nCommands:")
		fmt.Println("  load <data_dir>     Load all CSV data from directory")
		fmt.Println("  query <question>    Answer a question about Brazilian soccer")
		fmt.Println("  test                Run tests")
		fmt.Println("\nExamples:")
		fmt.Println("  brazilian-soccer-mcp load ./data/kaggle")
		fmt.Println("  brazilian-soccer-mcp query 'Who won the 2019 Brasileirão?'")
		os.Exit(1)
	}

	command := os.Args[1]

	switch command {
	case "load":
		if len(os.Args) < 3 {
			fmt.Println("Usage: brazilian-soccer-mcp load <data_dir>")
			os.Exit(1)
		}
		dataDir := os.Args[2]
		server := NewServer()
		if err := server.LoadData(dataDir); err != nil {
			fmt.Printf("Error loading data: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("Data loaded successfully!\n")
		fmt.Printf("  - Brasileirão matches: %d\n", len(server.Data.BrasileiraoMatches))
		fmt.Printf("  - Copa do Brasil matches: %d\n", len(server.Data.CopaDoBrasilMatches))
		fmt.Printf("  - Copa Libertadores matches: %d\n", len(server.Data.CopaLibertadoresMatches))
		fmt.Printf("  - BR Football matches: %d\n", len(server.Data.BRFootballMatches))
		fmt.Printf("  - Novo Campeonato matches: %d\n", len(server.Data.NovoCampeonatoMatches))
		fmt.Printf("  - Players: %d\n", len(server.Data.Players))

	case "query":
		if len(os.Args) < 3 {
			fmt.Println("Usage: brazilian-soccer-mcp query <question>")
			os.Exit(1)
		}
		query := os.Args[2]
		server := NewServer()
		if err := server.LoadData("data/kaggle"); err != nil {
			fmt.Printf("Error loading data: %v\n", err)
			os.Exit(1)
		}
		response, err := server.Query(query)
		if err != nil {
			fmt.Printf("Error: %v\n", err)
			os.Exit(1)
		}
		fmt.Println(response)

	case "test":
		fmt.Println("Running tests...")
		// Run tests
		if err := runTests(); err != nil {
			fmt.Printf("Tests failed: %v\n", err)
			os.Exit(1)
		}
		fmt.Println("All tests passed!")

	default:
		fmt.Printf("Unknown command: %s\n", command)
		os.Exit(1)
	}
}
