package main

import (
	"fmt"
	"os"
	"path/filepath"
)

func main() {
	dataDir := findDataDir()

	db, err := LoadAll(dataDir)
	if err != nil {
		// Log to stderr so it doesn't interfere with MCP protocol on stdout
		fmt.Fprintf(os.Stderr, "Warning during data load: %v\n", err)
	}

	fmt.Fprintf(os.Stderr, "Loaded %d matches and %d players\n", len(db.Matches), len(db.Players))

	srv := NewServer(db)
	if err := srv.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Server error: %v\n", err)
		os.Exit(1)
	}
}

// findDataDir finds the data directory relative to the executable or working directory
func findDataDir() string {
	// Check environment variable first
	if dir := os.Getenv("SOCCER_DATA_DIR"); dir != "" {
		return dir
	}

	candidates := []string{
		"data/kaggle",
		"../data/kaggle",
	}

	// Also try relative to executable
	if exe, err := os.Executable(); err == nil {
		exeDir := filepath.Dir(exe)
		candidates = append(candidates,
			filepath.Join(exeDir, "data/kaggle"),
			filepath.Join(exeDir, "../data/kaggle"),
		)
	}

	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			return c
		}
	}

	// Default
	return "data/kaggle"
}
