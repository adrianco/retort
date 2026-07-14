// mcp.go implements a minimal Model Context Protocol server over stdio using
// newline-delimited JSON-RPC 2.0. It exposes the soccer query tools defined in
// tools.go to an MCP-capable LLM client.
package main

import (
	"bufio"
	"encoding/json"
	"io"
	"log"
	"sync"
)

const (
	protocolVersion = "2024-11-05"
	serverName      = "brazilian-soccer-mcp"
	serverVersion   = "1.0.0"
)

// rpcRequest is an incoming JSON-RPC 2.0 message. A nil ID means a notification.
type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// rpcResponse is an outgoing JSON-RPC 2.0 reply.
type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

// rpcError is a JSON-RPC error object.
type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

const (
	errParse          = -32700
	errInvalidRequest = -32600
	errMethodNotFound = -32601
	errInvalidParams  = -32602
	errInternal       = -32603
)

// Server routes MCP requests to the registered tools.
type Server struct {
	tools  []Tool
	byName map[string]Tool
	out    *bufio.Writer
	mu     sync.Mutex // guards writes to out
}

// NewServer builds an MCP server exposing the given tools.
func NewServer(tools []Tool, w io.Writer) *Server {
	s := &Server{
		tools:  tools,
		byName: make(map[string]Tool, len(tools)),
		out:    bufio.NewWriter(w),
	}
	for _, t := range tools {
		s.byName[t.Name] = t
	}
	return s
}

// Serve reads JSON-RPC messages from r until EOF, dispatching each one.
func (s *Server) Serve(r io.Reader) error {
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		s.dispatch(line)
	}
	return scanner.Err()
}

// dispatch parses and handles a single raw JSON-RPC line.
func (s *Server) dispatch(line []byte) {
	var req rpcRequest
	if err := json.Unmarshal(line, &req); err != nil {
		s.writeError(nil, errParse, "parse error")
		return
	}

	switch req.Method {
	case "initialize":
		s.reply(req.ID, map[string]any{
			"protocolVersion": protocolVersion,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo": map[string]any{
				"name":    serverName,
				"version": serverVersion,
			},
		})
	case "notifications/initialized", "notifications/cancelled":
		// Notifications carry no ID and expect no response.
	case "ping":
		s.reply(req.ID, map[string]any{})
	case "tools/list":
		s.reply(req.ID, map[string]any{"tools": s.toolDescriptors()})
	case "tools/call":
		s.handleToolCall(req)
	default:
		if req.ID != nil {
			s.writeError(req.ID, errMethodNotFound, "method not found: "+req.Method)
		}
	}
}

// toolDescriptors returns the tool metadata for tools/list.
func (s *Server) toolDescriptors() []map[string]any {
	out := make([]map[string]any, 0, len(s.tools))
	for _, t := range s.tools {
		out = append(out, map[string]any{
			"name":        t.Name,
			"description": t.Description,
			"inputSchema": t.InputSchema,
		})
	}
	return out
}

// handleToolCall executes a tools/call request and replies with text content.
func (s *Server) handleToolCall(req rpcRequest) {
	var params struct {
		Name      string         `json:"name"`
		Arguments map[string]any `json:"arguments"`
	}
	if err := json.Unmarshal(req.Params, &params); err != nil {
		s.writeError(req.ID, errInvalidParams, "invalid params: "+err.Error())
		return
	}
	tool, ok := s.byName[params.Name]
	if !ok {
		s.writeError(req.ID, errInvalidParams, "unknown tool: "+params.Name)
		return
	}
	if params.Arguments == nil {
		params.Arguments = map[string]any{}
	}

	text, err := tool.Handler(params.Arguments)
	if err != nil {
		// Tool-level errors are reported as MCP error content, not RPC errors,
		// so the model can read and react to them.
		s.reply(req.ID, map[string]any{
			"content": []map[string]any{{"type": "text", "text": "Error: " + err.Error()}},
			"isError": true,
		})
		return
	}
	s.reply(req.ID, map[string]any{
		"content": []map[string]any{{"type": "text", "text": text}},
		"isError": false,
	})
}

// reply writes a successful JSON-RPC response.
func (s *Server) reply(id json.RawMessage, result any) {
	if id == nil {
		return
	}
	s.write(rpcResponse{JSONRPC: "2.0", ID: id, Result: result})
}

// writeError writes a JSON-RPC error response.
func (s *Server) writeError(id json.RawMessage, code int, msg string) {
	resp := rpcResponse{JSONRPC: "2.0", Error: &rpcError{Code: code, Message: msg}}
	if id != nil {
		resp.ID = id
	}
	s.write(resp)
}

// write marshals and emits one newline-delimited JSON message.
func (s *Server) write(resp rpcResponse) {
	data, err := json.Marshal(resp)
	if err != nil {
		log.Printf("marshal response: %v", err)
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	s.out.Write(data)
	s.out.WriteByte('\n')
	if err := s.out.Flush(); err != nil {
		log.Printf("flush response: %v", err)
	}
}
