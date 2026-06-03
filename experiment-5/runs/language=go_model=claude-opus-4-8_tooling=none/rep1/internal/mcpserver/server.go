// Context:
//   - This file is the MCP method router. It owns the loaded soccer.Store and
//     the registered tool set, and implements the three protocol methods that
//     matter for a tool server: initialize, tools/list and tools/call (plus
//     ping). The actual tool logic lives in tools.go.
//   - dispatch is pure (request in, result/error out) so it can be exercised
//     directly from tests without going through stdio.
package mcpserver

import (
	"encoding/json"
	"fmt"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// protocolVersion is the MCP revision this server speaks.
const protocolVersion = "2024-11-05"

// Server is an MCP server backed by a soccer knowledge base.
type Server struct {
	store  *soccer.Store
	name   string
	tools  []toolDef
	byName map[string]toolDef
}

// NewServer builds a server over the given store.
func NewServer(store *soccer.Store) *Server {
	s := &Server{
		store: store,
		name:  "brazilian-soccer-mcp",
	}
	s.tools = s.buildTools()
	s.byName = make(map[string]toolDef, len(s.tools))
	for _, t := range s.tools {
		s.byName[t.Name] = t
	}
	return s
}

// dispatch routes a single request to its handler.
func (s *Server) dispatch(req *request) (any, *rpcError) {
	switch req.Method {
	case "initialize":
		return s.handleInitialize(), nil
	case "notifications/initialized", "initialized":
		return nil, nil // notification, ignored
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		return s.handleToolsList(), nil
	case "tools/call":
		return s.handleToolsCall(req.Params)
	default:
		return nil, &rpcError{Code: codeMethodNotFound, Message: "method not found: " + req.Method}
	}
}

func (s *Server) handleInitialize() any {
	return map[string]any{
		"protocolVersion": protocolVersion,
		"capabilities": map[string]any{
			"tools": map[string]any{},
		},
		"serverInfo": map[string]any{
			"name":    s.name,
			"version": "1.0.0",
		},
		"instructions": "Query Brazilian soccer matches, teams, players, competitions and statistics from the bundled Kaggle datasets.",
	}
}

func (s *Server) handleToolsList() any {
	list := make([]map[string]any, 0, len(s.tools))
	for _, t := range s.tools {
		list = append(list, map[string]any{
			"name":        t.Name,
			"description": t.Description,
			"inputSchema": t.InputSchema,
		})
	}
	return map[string]any{"tools": list}
}

// toolCallParams is the params shape for tools/call.
type toolCallParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

func (s *Server) handleToolsCall(raw json.RawMessage) (any, *rpcError) {
	var p toolCallParams
	if err := json.Unmarshal(raw, &p); err != nil {
		return nil, &rpcError{Code: codeInvalidParams, Message: "invalid params: " + err.Error()}
	}
	tool, ok := s.byName[p.Name]
	if !ok {
		return nil, &rpcError{Code: codeMethodNotFound, Message: "unknown tool: " + p.Name}
	}
	args := map[string]any{}
	if len(p.Arguments) > 0 {
		if err := json.Unmarshal(p.Arguments, &args); err != nil {
			return nil, &rpcError{Code: codeInvalidParams, Message: "invalid arguments: " + err.Error()}
		}
	}

	text, err := tool.Handler(s.store, args)
	if err != nil {
		// Tool-level errors are reported via the result with isError=true, per
		// the MCP convention, so the model can read and react to them.
		return toolResult(fmt.Sprintf("Error: %v", err), true), nil
	}
	return toolResult(text, false), nil
}

// toolResult builds an MCP tools/call result payload.
func toolResult(text string, isErr bool) any {
	return map[string]any{
		"content": []map[string]any{
			{"type": "text", "text": text},
		},
		"isError": isErr,
	}
}
