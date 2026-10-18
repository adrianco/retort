package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	// Simple MCP server implementation
	http.HandleFunc("/mcp", func(w http.ResponseWriter, r *http.Request) {
		// Simple response for now to indicate it's working
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"status": "Brazilian Soccer MCP server is running", "version": "1.0"}`)
	})

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Brazilian Soccer MCP server starting on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}