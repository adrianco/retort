package main

import (
	"context"
	"flag"
	"log"
	"os"

	"brazilian-soccer-mcp/internal/server"
	"brazilian-soccer-mcp/internal/soccer"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func main() {
	dataDir := flag.String("data", "data/kaggle", "directory containing the six CSV datasets")
	flag.Parse()
	catalog, err := soccer.LoadDir(*dataDir)
	if err != nil {
		log.New(os.Stderr, "", log.LstdFlags).Fatal(err)
	}
	if err := server.New(catalog).Run(context.Background(), &mcp.StdioTransport{}); err != nil {
		log.New(os.Stderr, "", log.LstdFlags).Fatal(err)
	}
}
