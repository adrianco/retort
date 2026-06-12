package main

import (
	"fmt"
	"log"
	"os"
)

func main() {
	dataDir := "data/kaggle"
	if len(os.Args) > 1 {
		dataDir = os.Args[1]
	}

	log.SetOutput(os.Stderr)
	log.Printf("Loading data from %s...", dataDir)

	db, err := loadAllData(dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Fatal: failed to load data: %v\n", err)
		os.Exit(1)
	}

	log.Printf("Loaded %d matches and %d players", len(db.Matches), len(db.Players))

	server := newMCPServer(db)
	server.Run()
}
