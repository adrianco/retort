package main

import (
	"log"
	"os"
	"path/filepath"

	"github.com/mark3labs/mcp-go/server"
	"brazilian-soccer-mcp/soccer"
	"brazilian-soccer-mcp/tools"
)

func main() {
	// Find data directory relative to executable
	execPath, err := os.Executable()
	if err != nil {
		log.Fatal("failed to get executable path:", err)
	}
	dataDir := filepath.Join(filepath.Dir(execPath), "data", "kaggle")

	store, err := soccer.LoadStore(dataDir)
	if err != nil {
		log.Fatal("failed to load data:", err)
	}

	s := server.NewMCPServer("Brazilian Soccer MCP", "1.0.0")
	tools.RegisterTools(s, store)

	if err := server.ServeStdio(s); err != nil {
		log.Fatal("server error:", err)
	}
}
