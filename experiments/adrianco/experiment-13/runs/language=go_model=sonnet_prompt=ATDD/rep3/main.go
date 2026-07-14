package main

import (
	"log"

	mcpserver "brazilian-soccer-mcp/internal/server"
	"github.com/mark3labs/mcp-go/server"
)

func main() {
	serverTools, err := mcpserver.RegisterTools("./data/kaggle/")
	if err != nil {
		log.Fatal(err)
	}
	s := server.NewMCPServer("Brazilian Soccer MCP", "1.0.0")
	s.AddTools(serverTools...)
	if err := server.ServeStdio(s); err != nil {
		log.Fatal(err)
	}
}
