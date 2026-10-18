package main

import (
    "testing"
    "brazilian-soccer-mcp-server/internal/mcp"
    "brazilian-soccer-mcp-server/internal/handlers"
    "brazilian-soccer-mcp-server/internal/models"
)

func TestModels(t *testing.T) {
    // Test that models can be created
    match := models.Match{
        Id: "test",
    }
    
    if match.Id != "test" {
        t.Errorf("Expected match.Id to be 'test', got %s", match.Id)
    }
}

func TestMCPHandler(t *testing.T) {
    // Test MCP handler creation
    handler := mcp.NewMCPHandler()
    
    if handler == nil {
        t.Error("Expected MCP handler to be created")
    }
}

func TestDataLoader(t *testing.T) {
    // Test data loader creation
    loader := handlers.NewDataLoader()
    
    if loader == nil {
        t.Error("Expected data loader to be created")
    }
}
