package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
)

func main() {
	var dataDir string
	var version bool
	flag.StringVar(&dataDir, "data-dir", "", "directory containing the six supplied CSV files")
	flag.BoolVar(&version, "version", false, "print the server version and exit")
	flag.Parse()
	if version {
		fmt.Println(serverName + " " + serverVersion)
		return
	}

	resolvedDataDir, err := resolveDataDir(dataDir)
	if err != nil {
		fmt.Fprintln(os.Stderr, "brazilian-soccer-mcp:", err)
		os.Exit(1)
	}
	store, err := LoadData(resolvedDataDir)
	if err != nil {
		fmt.Fprintln(os.Stderr, "brazilian-soccer-mcp:", err)
		os.Exit(1)
	}
	if err := NewMCPServer(store).Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "brazilian-soccer-mcp:", err)
		os.Exit(1)
	}
}

func resolveDataDir(requested string) (string, error) {
	candidates := make([]string, 0, 5)
	if requested != "" {
		candidates = append(candidates, requested)
	}
	if configured := os.Getenv("BRAZILIAN_SOCCER_DATA_DIR"); configured != "" {
		candidates = append(candidates, configured)
	}
	if currentDir, err := os.Getwd(); err == nil {
		candidates = append(candidates, filepath.Join(currentDir, "data", "kaggle"))
	}
	if executable, err := os.Executable(); err == nil {
		executableDir := filepath.Dir(executable)
		candidates = append(candidates,
			filepath.Join(executableDir, "data", "kaggle"),
			filepath.Join(executableDir, "..", "data", "kaggle"),
		)
	}
	for _, candidate := range candidates {
		if hasDatasetFiles(candidate) {
			return candidate, nil
		}
	}
	return "", fmt.Errorf("could not find the CSV data; pass --data-dir or set BRAZILIAN_SOCCER_DATA_DIR")
}

func hasDatasetFiles(directory string) bool {
	for _, file := range []string{brasileiraoFile, cupFile, libertadoresFile, extendedFile, historicalFile, fifaFile} {
		info, err := os.Stat(filepath.Join(directory, file))
		if err != nil || info.IsDir() {
			return false
		}
	}
	return true
}
