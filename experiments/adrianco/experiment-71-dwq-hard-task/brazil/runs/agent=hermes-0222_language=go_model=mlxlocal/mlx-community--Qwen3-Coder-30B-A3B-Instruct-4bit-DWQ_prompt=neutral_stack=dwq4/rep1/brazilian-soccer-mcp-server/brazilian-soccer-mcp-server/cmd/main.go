package main

import (
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gorilla/mux"
	"github.com/sirupsen/logrus"

	"brazilian-soccer-mcp-server/internal/mcp"
)

func main() {
	// Set up logging
	logrus.SetFormatter(&logrus.JSONFormatter{})
	
	// Create router
	router := mux.NewRouter()
	
	// Create MCP server handler
	mcpServer := mcp.NewMCPHandler()
	
	// Set up routes
	router.HandleFunc("/mcp", mcpServer.HandleMCP).Methods("POST")
	router.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	}).Methods("GET")
	
	// Get port from environment or default to 8080
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	
	// Start server
	server := &http.Server{
		Addr:         ":" + port,
		Handler:      router,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
	}
	
	log.Printf("Starting Brazilian Soccer MCP server on port %s", port)
	log.Fatal(server.ListenAndServe())
}
