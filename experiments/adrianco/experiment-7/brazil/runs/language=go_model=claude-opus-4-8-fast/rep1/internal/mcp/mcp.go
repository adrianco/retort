// Package mcp implements a minimal Model Context Protocol server over a
// stdio JSON-RPC 2.0 transport.
//
// Context:
//   - The MCP stdio transport exchanges newline-delimited JSON-RPC 2.0 messages
//     (one JSON object per line). See https://modelcontextprotocol.io.
//   - This implementation is dependency-free and supports the subset needed for
//     a tools-only server: initialize, notifications/initialized, ping,
//     tools/list, tools/call.
//   - Tools are registered via AddTool; each handler receives the raw JSON
//     arguments object and returns a text result (or an error, surfaced to the
//     client as an isError tool result).
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync"
)

// ProtocolVersion is the MCP revision this server advertises.
const ProtocolVersion = "2024-11-05"

// ToolHandler executes a tool call. args is the raw JSON "arguments" object
// (may be nil/empty). It returns the textual result or an error.
type ToolHandler func(args json.RawMessage) (string, error)

// Tool is a registered MCP tool.
type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	handler     ToolHandler
}

// Server is a tools-only MCP server.
type Server struct {
	name    string
	version string

	mu    sync.RWMutex
	tools map[string]*Tool
	order []string
}

// NewServer creates a server identified by name/version.
func NewServer(name, version string) *Server {
	return &Server{name: name, version: version, tools: map[string]*Tool{}}
}

// AddTool registers a tool. A later registration with the same name overwrites
// the earlier one (but preserves list order).
func (s *Server) AddTool(name, description string, schema map[string]any, h ToolHandler) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.tools[name]; !exists {
		s.order = append(s.order, name)
	}
	s.tools[name] = &Tool{Name: name, Description: description, InputSchema: schema, handler: h}
}

// --- JSON-RPC types ---

type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// JSON-RPC standard error codes.
const (
	codeParseError     = -32700
	codeInvalidRequest = -32600
	codeMethodNotFound = -32601
	codeInternalError  = -32603
)

// Serve runs the read/dispatch/write loop until r reaches EOF.
func (s *Server) Serve(r io.Reader, w io.Writer) error {
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	enc := json.NewEncoder(w)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		resp, ok := s.handle(line)
		if !ok {
			continue // notification: no response
		}
		if err := enc.Encode(resp); err != nil {
			return err
		}
	}
	return scanner.Err()
}

// handle processes one raw message, returning the response and whether one
// should be written (notifications produce no response).
func (s *Server) handle(line []byte) (response, bool) {
	var req request
	if err := json.Unmarshal(line, &req); err != nil {
		return errorResp(nil, codeParseError, "parse error"), true
	}
	if req.JSONRPC != "2.0" {
		return errorResp(req.ID, codeInvalidRequest, "invalid jsonrpc version"), true
	}
	// Notifications have no id and expect no response.
	isNotification := len(req.ID) == 0

	switch req.Method {
	case "initialize":
		return okResp(req.ID, s.initializeResult()), true
	case "notifications/initialized", "initialized":
		return response{}, false
	case "ping":
		return okResp(req.ID, map[string]any{}), true
	case "tools/list":
		return okResp(req.ID, s.listToolsResult()), true
	case "tools/call":
		return s.callTool(req), true
	default:
		if isNotification {
			return response{}, false
		}
		return errorResp(req.ID, codeMethodNotFound, "method not found: "+req.Method), true
	}
}

func (s *Server) initializeResult() map[string]any {
	return map[string]any{
		"protocolVersion": ProtocolVersion,
		"capabilities": map[string]any{
			"tools": map[string]any{},
		},
		"serverInfo": map[string]any{
			"name":    s.name,
			"version": s.version,
		},
	}
}

func (s *Server) listToolsResult() map[string]any {
	s.mu.RLock()
	defer s.mu.RUnlock()
	tools := make([]Tool, 0, len(s.order))
	for _, name := range s.order {
		t := s.tools[name]
		tools = append(tools, Tool{
			Name:        t.Name,
			Description: t.Description,
			InputSchema: t.InputSchema,
		})
	}
	return map[string]any{"tools": tools}
}

type callParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

func (s *Server) callTool(req request) response {
	var p callParams
	if err := json.Unmarshal(req.Params, &p); err != nil {
		return errorResp(req.ID, codeInvalidRequest, "invalid params")
	}
	s.mu.RLock()
	tool, ok := s.tools[p.Name]
	s.mu.RUnlock()
	if !ok {
		return errorResp(req.ID, codeMethodNotFound, "unknown tool: "+p.Name)
	}
	text, err := tool.handler(p.Arguments)
	if err != nil {
		// Tool execution errors are reported as a tool result with isError.
		return okResp(req.ID, toolResult(fmt.Sprintf("Error: %v", err), true))
	}
	return okResp(req.ID, toolResult(text, false))
}

// toolResult builds an MCP tools/call result payload.
func toolResult(text string, isErr bool) map[string]any {
	return map[string]any{
		"content": []map[string]any{
			{"type": "text", "text": text},
		},
		"isError": isErr,
	}
}

func okResp(id json.RawMessage, result any) response {
	return response{JSONRPC: "2.0", ID: id, Result: result}
}

func errorResp(id json.RawMessage, code int, msg string) response {
	return response{JSONRPC: "2.0", ID: id, Error: &rpcError{Code: code, Message: msg}}
}
