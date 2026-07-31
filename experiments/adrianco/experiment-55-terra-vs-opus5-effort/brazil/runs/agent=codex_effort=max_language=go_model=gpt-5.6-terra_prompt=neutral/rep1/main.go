package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	dataDir := flag.String("data-dir", defaultDataDir(), "directory containing the six Kaggle CSV files")
	question := flag.String("query", "", "run one natural-language question and print the answer instead of starting MCP stdio")
	flag.Parse()

	data, err := LoadData(*dataDir)
	if err != nil {
		fmt.Fprintln(os.Stderr, "brazilian-soccer-mcp:", err)
		os.Exit(1)
	}
	server := NewMCPServer(data)
	if strings.TrimSpace(*question) != "" {
		result := server.CallTool("query_brazilian_soccer", map[string]any{"question": *question})
		if len(result.Content) > 0 {
			fmt.Println(result.Content[0].Text)
		}
		if result.IsError {
			os.Exit(2)
		}
		return
	}
	if err := server.Run(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "brazilian-soccer-mcp:", err)
		os.Exit(1)
	}
}

func defaultDataDir() string {
	if configured := strings.TrimSpace(os.Getenv("BRAZILIAN_SOCCER_DATA_DIR")); configured != "" {
		return configured
	}
	// The usual case is running from the repository root. Resolving an absolute
	// executable path as a fallback also makes an installed binary convenient.
	if _, err := os.Stat(filepath.Join("data", "kaggle")); err == nil {
		return filepath.Join("data", "kaggle")
	}
	if executable, err := os.Executable(); err == nil {
		candidate := filepath.Join(filepath.Dir(executable), "data", "kaggle")
		if _, statErr := os.Stat(candidate); statErr == nil {
			return candidate
		}
	}
	return filepath.Join("data", "kaggle")
}
