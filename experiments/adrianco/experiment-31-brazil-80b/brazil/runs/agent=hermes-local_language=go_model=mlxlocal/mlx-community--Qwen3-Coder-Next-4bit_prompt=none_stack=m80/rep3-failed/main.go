// Main entry point for the Brazilian Soccer MCP Server
package main

import (
	"flag"
	"fmt"
	"log"

	"brazilian-soccer-mcp/internal/server"
)

func main() {
	port := flag.String("port", "8080", "Port to run the server on")
	sample := flag.Bool("sample", false, "Run sample queries")
	flag.Parse()

	srv, err := server.New()
	if err != nil {
		log.Fatalf("Failed to create server: %v", err)
	}

	if *sample {
		if err := srv.RunSampleQueries(); err != nil {
			log.Fatalf("Failed to run sample queries: %v", err)
		}
		return
	}

	if err := srv.Start(*port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

// PrintWelcome prints the welcome message
func PrintWelcome() {
	fmt.Println("Brazilian Soccer MCP Server")
	fmt.Println("============================")
	fmt.Println()
	fmt.Println("Usage:")
	fmt.Println("  Run server: go run main.go")
	fmt.Println("  Run sample queries: go run main.go -sample")
	fmt.Println("  Custom port: go run main.go -port 9000")
	fmt.Println()
	fmt.Println("API Endpoints:")
	fmt.Println("  GET  /health      - Health check")
	fmt.Println("  GET  /capabilities - API capabilities")
	fmt.Println("  POST /query       - Submit a query")
	fmt.Println()
}
