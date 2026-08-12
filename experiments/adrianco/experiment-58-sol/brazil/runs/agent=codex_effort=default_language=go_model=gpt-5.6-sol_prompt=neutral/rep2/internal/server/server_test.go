package server

import (
	"context"
	"path/filepath"
	"testing"

	"brazilian-soccer-mcp/internal/soccer"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestMCPToolsListAndCall(t *testing.T) {
	catalog, err := soccer.LoadDir(filepath.Join("..", "..", "data", "kaggle"))
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	serverTransport, clientTransport := mcp.NewInMemoryTransports()
	serverSession, err := New(catalog).Connect(ctx, serverTransport, nil)
	if err != nil {
		t.Fatal(err)
	}
	defer serverSession.Close()
	client := mcp.NewClient(&mcp.Implementation{Name: "test-client", Version: "1.0.0"}, nil)
	clientSession, err := client.Connect(ctx, clientTransport, nil)
	if err != nil {
		t.Fatal(err)
	}
	defer clientSession.Close()

	listed, err := clientSession.ListTools(ctx, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(listed.Tools) != 8 {
		t.Fatalf("listed %d tools, want 8", len(listed.Tools))
	}
	result, err := clientSession.CallTool(ctx, &mcp.CallToolParams{Name: "head_to_head", Arguments: map[string]any{"team_a": "Palmeiras", "team_b": "Santos", "limit": 3}})
	if err != nil {
		t.Fatal(err)
	}
	if result.IsError || result.StructuredContent == nil {
		t.Fatalf("bad MCP result: %+v", result)
	}
}
