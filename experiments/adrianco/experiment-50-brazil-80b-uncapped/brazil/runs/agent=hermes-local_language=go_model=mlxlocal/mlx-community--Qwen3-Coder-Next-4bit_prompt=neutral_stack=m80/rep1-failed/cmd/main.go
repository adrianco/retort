package main

import (
	"fmt"
	"log"

	"brazilian-soccer-mcp/internal/store"
)

func main() {
	// Load data from CSV files
	storePath := "./data/kaggle"
	db, err := store.LoadData(storePath)
	if err != nil {
		log.Fatalf("Failed to load data: %v", err)
	}

	fmt.Println("Brazilian Soccer MCP Server started successfully!")
	fmt.Printf("Loaded %d matches, %d players\n", db.MatchCount(), db.PlayerCount())
	fmt.Println("Server is ready to handle queries...")

	// For now, just keep running (MCP server would be started here)
	// In a real implementation, this would start an MCP server
	<-make(chan struct{})
}
