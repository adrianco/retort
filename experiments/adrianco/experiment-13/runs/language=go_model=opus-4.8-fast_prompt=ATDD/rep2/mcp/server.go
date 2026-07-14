// The Server type: it loads the soccer data, registers the domain tools, and
// dispatches JSON-RPC requests to them. Handle is the single public entry point
// used by both the stdio transport and the acceptance tests.
package mcp

import (
	"encoding/json"
	"fmt"
	"sort"

	"brazilian-soccer-mcp/soccer"
)

// tool binds an advertised descriptor to its implementation.
type tool struct {
	descriptor toolDescriptor
	handler    func(store *soccer.Store, args map[string]any) (string, error)
}

// Server is an MCP server backed by an in-memory soccer Store.
type Server struct {
	store *soccer.Store
	tools map[string]tool
	order []string
}

// NewServer loads all recognised datasets from dataDir and returns a ready
// server with the soccer tools registered.
func NewServer(dataDir string) (*Server, error) {
	store, err := soccer.LoadDir(dataDir)
	if err != nil {
		return nil, fmt.Errorf("loading data from %s: %w", dataDir, err)
	}
	s := &Server{store: store, tools: map[string]tool{}}
	s.registerTools()
	return s, nil
}

// NewServerWithStore builds a server around an already-populated store (used by
// unit tests).
func NewServerWithStore(store *soccer.Store) *Server {
	s := &Server{store: store, tools: map[string]tool{}}
	s.registerTools()
	return s
}

func (s *Server) register(t tool) {
	s.tools[t.descriptor.Name] = t
	s.order = append(s.order, t.descriptor.Name)
}

// Handle processes a single JSON-RPC request and returns the response bytes. A
// nil return means the message was a notification requiring no reply.
func (s *Server) Handle(raw []byte) []byte {
	var req request
	if err := json.Unmarshal(raw, &req); err != nil {
		return s.errorResponse(nil, codeParseError, "parse error")
	}
	switch req.Method {
	case "initialize":
		return s.reply(req.ID, s.initializeResult())
	case "notifications/initialized", "initialized":
		return nil // notification: no response
	case "ping":
		return s.reply(req.ID, map[string]any{})
	case "tools/list":
		return s.reply(req.ID, map[string]any{"tools": s.listTools()})
	case "tools/call":
		return s.handleToolCall(req)
	default:
		return s.errorResponse(req.ID, codeMethodNotFound, "method not found: "+req.Method)
	}
}

func (s *Server) initializeResult() map[string]any {
	return map[string]any{
		"protocolVersion": protocolVersion,
		"capabilities": map[string]any{
			"tools": map[string]any{},
		},
		"serverInfo": map[string]any{
			"name":    "brazilian-soccer-mcp",
			"version": "1.0.0",
		},
		"instructions": fmt.Sprintf(
			"Brazilian soccer knowledge graph. Loaded %d matches across %v and %d players. "+
				"Use find_matches, get_team_stats, compare_teams, search_players, get_standings, and league_statistics.",
			s.store.MatchCount(), s.store.Competitions(), s.store.PlayerCount()),
	}
}

func (s *Server) listTools() []toolDescriptor {
	names := append([]string(nil), s.order...)
	sort.Strings(names)
	out := make([]toolDescriptor, 0, len(names))
	for _, n := range names {
		out = append(out, s.tools[n].descriptor)
	}
	return out
}

func (s *Server) handleToolCall(req request) []byte {
	var params struct {
		Name      string          `json:"name"`
		Arguments json.RawMessage `json:"arguments"`
	}
	if err := json.Unmarshal(req.Params, &params); err != nil {
		return s.errorResponse(req.ID, codeInvalidParams, "invalid params")
	}
	t, ok := s.tools[params.Name]
	if !ok {
		return s.reply(req.ID, toolResult{
			Content: []textContent{{Type: "text", Text: "unknown tool: " + params.Name}},
			IsError: true,
		})
	}
	args := map[string]any{}
	if len(params.Arguments) > 0 {
		if err := json.Unmarshal(params.Arguments, &args); err != nil {
			return s.reply(req.ID, toolResult{
				Content: []textContent{{Type: "text", Text: "invalid arguments: " + err.Error()}},
				IsError: true,
			})
		}
	}
	text, err := t.handler(s.store, args)
	if err != nil {
		return s.reply(req.ID, toolResult{
			Content: []textContent{{Type: "text", Text: err.Error()}},
			IsError: true,
		})
	}
	return s.reply(req.ID, toolResult{Content: []textContent{{Type: "text", Text: text}}})
}

func (s *Server) reply(id json.RawMessage, result any) []byte {
	b, err := json.Marshal(response{JSONRPC: "2.0", ID: id, Result: result})
	if err != nil {
		return s.errorResponse(id, codeInternalError, "failed to encode result")
	}
	return b
}

func (s *Server) errorResponse(id json.RawMessage, code int, msg string) []byte {
	b, _ := json.Marshal(response{JSONRPC: "2.0", ID: id, Error: &rpcError{Code: code, Message: msg}})
	return b
}
