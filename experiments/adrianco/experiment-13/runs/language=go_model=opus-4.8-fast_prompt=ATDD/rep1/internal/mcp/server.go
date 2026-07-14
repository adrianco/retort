// Package mcp implements a minimal Model Context Protocol server speaking
// JSON-RPC 2.0 over a newline-delimited stream (the MCP stdio transport).
//
// It is transport-agnostic: callers register tools and then drive it via Serve
// over any io.Reader/io.Writer pair (os.Stdin/os.Stdout in production, in-memory
// pipes in tests).
package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"sync"
)

// ProtocolVersion is the MCP protocol revision this server implements.
const ProtocolVersion = "2024-11-05"

// Tool describes an MCP tool and its handler.
type Tool struct {
	Name        string
	Description string
	// InputSchema is a JSON Schema object describing the tool's arguments.
	InputSchema map[string]any
	// Handler receives the raw arguments object and returns a text result.
	Handler func(args json.RawMessage) (string, error)
}

// Server is an MCP server with a registry of tools.
type Server struct {
	name    string
	version string

	mu    sync.Mutex
	tools []Tool
	index map[string]Tool
}

// NewServer creates a server identifying itself with the given name/version.
func NewServer(name, version string) *Server {
	return &Server{name: name, version: version, index: map[string]Tool{}}
}

// AddTool registers a tool. Later registrations override earlier ones by name.
func (s *Server) AddTool(t Tool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.index[t.Name]; !exists {
		s.tools = append(s.tools, t)
	}
	s.index[t.Name] = t
}

// --- JSON-RPC wire types ----------------------------------------------------

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

// JSON-RPC standard error codes.
const (
	codeParseError     = -32700
	codeInvalidRequest = -32600
	codeMethodNotFound = -32601
	codeInternalError  = -32603
)

// Serve reads JSON-RPC requests from in and writes responses to out until the
// stream closes or the context is cancelled.
func (s *Server) Serve(ctx context.Context, in io.Reader, out io.Writer) error {
	dec := json.NewDecoder(in)
	enc := json.NewEncoder(out)
	var writeMu sync.Mutex

	send := func(resp rpcResponse) {
		writeMu.Lock()
		defer writeMu.Unlock()
		_ = enc.Encode(resp)
	}

	for {
		if err := ctx.Err(); err != nil {
			return nil
		}
		var req rpcRequest
		if err := dec.Decode(&req); err != nil {
			if err == io.EOF {
				return nil
			}
			// Malformed JSON: report a parse error with a null id and continue.
			send(rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"),
				Error: &rpcError{Code: codeParseError, Message: "parse error: " + err.Error()}})
			return nil
		}
		resp, isResponse := s.handle(req)
		if isResponse {
			send(resp)
		}
	}
}

// handle dispatches a single request. The bool result is false for
// notifications (no id), which must not produce a response.
func (s *Server) handle(req rpcRequest) (rpcResponse, bool) {
	isNotification := len(req.ID) == 0 || string(req.ID) == "null"

	resp := rpcResponse{JSONRPC: "2.0", ID: req.ID}

	switch req.Method {
	case "initialize":
		resp.Result = map[string]any{
			"protocolVersion": ProtocolVersion,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": s.name, "version": s.version},
		}
	case "notifications/initialized", "initialized":
		return rpcResponse{}, false // notification, no reply
	case "ping":
		resp.Result = map[string]any{}
	case "tools/list":
		resp.Result = s.listTools()
	case "tools/call":
		resp.Result = s.callTool(req.Params)
	default:
		if isNotification {
			return rpcResponse{}, false
		}
		resp.Error = &rpcError{Code: codeMethodNotFound, Message: "method not found: " + req.Method}
	}

	if isNotification {
		return rpcResponse{}, false
	}
	return resp, true
}

func (s *Server) listTools() map[string]any {
	s.mu.Lock()
	defer s.mu.Unlock()
	tools := make([]map[string]any, 0, len(s.tools))
	for _, t := range s.tools {
		schema := t.InputSchema
		if schema == nil {
			schema = map[string]any{"type": "object", "properties": map[string]any{}}
		}
		tools = append(tools, map[string]any{
			"name":        t.Name,
			"description": t.Description,
			"inputSchema": schema,
		})
	}
	return map[string]any{"tools": tools}
}

// toolResult is the MCP result shape for tools/call.
func toolResult(text string, isError bool) map[string]any {
	return map[string]any{
		"content": []map[string]any{{"type": "text", "text": text}},
		"isError": isError,
	}
}

func (s *Server) callTool(params json.RawMessage) map[string]any {
	var p struct {
		Name      string          `json:"name"`
		Arguments json.RawMessage `json:"arguments"`
	}
	if err := json.Unmarshal(params, &p); err != nil {
		return toolResult("invalid tool call parameters: "+err.Error(), true)
	}
	s.mu.Lock()
	tool, ok := s.index[p.Name]
	s.mu.Unlock()
	if !ok {
		return toolResult(fmt.Sprintf("unknown tool %q", p.Name), true)
	}
	args := p.Arguments
	if len(args) == 0 {
		args = json.RawMessage("{}")
	}
	text, err := tool.Handler(args)
	if err != nil {
		return toolResult(err.Error(), true)
	}
	return toolResult(text, false)
}

var _ = codeInvalidRequest
var _ = codeInternalError
