package main

import (
	"log"

	"soccer-mcp/server"
)

func main() {
	// Initialize the server with the data directory
	dataDir := "./data/kaggle"
	srv, err := server.NewSoccerServer(dataDir)
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	// Run the server
	if err := srv.Run(); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
