package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/mark3labs/mcp-go/server"
)

func main() {
	store := NewDataStore()

	dataDir := "data/kaggle"
	if len(os.Args) > 1 {
		dataDir = os.Args[1]
	}

	fmt.Printf("Loading data from %s...\n", dataDir)
	if err := store.LoadAll(dataDir); err != nil {
		log.Fatalf("Failed to load data: %v", err)
	}

	brasileirao := store.GetBrasilieiraoMatches()
	copaDoBrasil := store.GetCopaDoBrasilMatches()
	libertadores := store.GetLibertadoresMatches()
	brFootball := store.GetBRFootballMatches()
	novoCampeonato := store.GetNovoCampeonatoMatches()
	fifaPlayers := store.GetFIFAPlayers()

	fmt.Printf("Loaded %d Brasileirao matches\n", len(brasileirao))
	fmt.Printf("Loaded %d Copa do Brasil matches\n", len(copaDoBrasil))
	fmt.Printf("Loaded %d Libertadores matches\n", len(libertadores))
	fmt.Printf("Loaded %d BR Football matches\n", len(brFootball))
	fmt.Printf("Loaded %d Novo Campeonato matches\n", len(novoCampeonato))
	fmt.Printf("Loaded %d FIFA players\n", len(fifaPlayers))

	analyzer := NewQueryAnalyzer(store)
	mcpServer := BuildMCPServer(analyzer, store)

	sseServer := server.NewSSEServer(mcpServer)

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	go func() {
		fmt.Println("Starting MCP Server on :8080...")
		if err := sseServer.Start("localhost:8080"); err != nil {
			log.Fatalf("Server failed: %v", err)
		}
	}()

	<-ctx.Done()
	fmt.Println("Shutting down server...")
	cancel()
}
