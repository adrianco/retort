package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
)

func main() {
	dataDir := flag.String("data", defaultDataDir(), "directory containing the six Kaggle CSV files")
	showVersion := flag.Bool("version", false, "print version and exit")
	flag.Parse()
	if *showVersion {
		fmt.Println(serverVersion)
		return
	}
	db, err := LoadDatabase(*dataDir)
	if err != nil {
		log.Fatalf("load soccer datasets: %v", err)
	}
	if err := NewMCPServer(db).Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatalf("serve MCP: %v", err)
	}
}

func defaultDataDir() string {
	if value := os.Getenv("BRAZILIAN_SOCCER_DATA"); value != "" {
		return value
	}
	if executable, err := os.Executable(); err == nil {
		candidate := filepath.Join(filepath.Dir(executable), "data", "kaggle")
		if _, err := os.Stat(candidate); err == nil {
			return candidate
		}
	}
	return filepath.Join("data", "kaggle")
}
