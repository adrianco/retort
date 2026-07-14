// Brazilian Soccer MCP Server
//
// File: mcp.go
// Responsibility: A minimal, dependency-free implementation of the Model
// Context Protocol (MCP) over the stdio transport. MCP uses JSON-RPC 2.0 with
// newline-delimited messages on stdin/stdout. This file implements the protocol
// machinery — message framing, the `initialize` handshake, `tools/list` and
// `tools/call` dispatch — and exposes a small `Server` type that tool handlers
// register against. The actual soccer tools live in tools.go.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync"
)

// protocolVersion is the MCP revision this server implements.
const protocolVersion = "2024-11-05"

// jsonrpcRequest is an incoming JSON-RPC 2.0 request or notification. A request
// with no ID is a notification and receives no response.
type jsonrpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// jsonrpcResponse is an outgoing JSON-RPC 2.0 response.
type jsonrpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  interface{}     `json:"result,omitempty"`
	Error   *jsonrpcError   `json:"error,omitempty"`
}

// jsonrpcError is a JSON-RPC 2.0 error object.
type jsonrpcError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

// Standard JSON-RPC error codes.
const (
	codeParseError     = -32700
	codeInvalidRequest = -32600
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
	codeInternalError  = -32603
)

// Tool describes a callable MCP tool: its name, human description, JSON Schema
// for arguments, and the handler that executes it.
type Tool struct {
	Name        string                                            `json:"name"`
	Description string                                            `json:"description"`
	InputSchema map[string]interface{}                            `json:"inputSchema"`
	Handler     func(args map[string]interface{}) (string, error) `json:"-"`
}

// Server is a minimal MCP server over stdio.
type Server struct {
	name    string
	version string
	tools   []Tool
	toolIdx map[string]Tool

	out *json.Encoder
	mu  sync.Mutex // guards writes to out
}

// NewServer creates a server with the given identity.
func NewServer(name, version string) *Server {
	return &Server{name: name, version: version, toolIdx: map[string]Tool{}}
}

// AddTool registers a tool with the server.
func (s *Server) AddTool(t Tool) {
	s.tools = append(s.tools, t)
	s.toolIdx[t.Name] = t
}

// Serve runs the stdio read/dispatch/write loop until EOF on in.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	s.out = json.NewEncoder(out)
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var req jsonrpcRequest
		if err := json.Unmarshal(line, &req); err != nil {
			s.writeError(nil, codeParseError, "parse error", err.Error())
			continue
		}
		s.handle(req)
	}
	return scanner.Err()
}

// handle routes one request to the appropriate method.
func (s *Server) handle(req jsonrpcRequest) {
	switch req.Method {
	case "initialize":
		s.writeResult(req.ID, map[string]interface{}{
			"protocolVersion": protocolVersion,
			"capabilities": map[string]interface{}{
				"tools": map[string]interface{}{},
			},
			"serverInfo": map[string]interface{}{
				"name":    s.name,
				"version": s.version,
			},
		})
	case "notifications/initialized", "initialized":
		// Notification: no response.
	case "ping":
		s.writeResult(req.ID, map[string]interface{}{})
	case "tools/list":
		s.writeResult(req.ID, map[string]interface{}{"tools": s.tools})
	case "tools/call":
		s.handleToolCall(req)
	default:
		if req.ID != nil {
			s.writeError(req.ID, codeMethodNotFound, "method not found: "+req.Method, nil)
		}
	}
}

// toolCallParams is the params object for a tools/call request.
type toolCallParams struct {
	Name      string                 `json:"name"`
	Arguments map[string]interface{} `json:"arguments"`
}

// handleToolCall dispatches a tools/call request to the named tool handler and
// wraps the result (or error) in the MCP content envelope.
func (s *Server) handleToolCall(req jsonrpcRequest) {
	var p toolCallParams
	if err := json.Unmarshal(req.Params, &p); err != nil {
		s.writeError(req.ID, codeInvalidParams, "invalid params", err.Error())
		return
	}
	tool, ok := s.toolIdx[p.Name]
	if !ok {
		s.writeError(req.ID, codeMethodNotFound, "unknown tool: "+p.Name, nil)
		return
	}
	if p.Arguments == nil {
		p.Arguments = map[string]interface{}{}
	}
	text, err := tool.Handler(p.Arguments)
	if err != nil {
		// Tool execution errors are reported as a successful response carrying
		// isError=true, per the MCP convention, so the model can read them.
		s.writeResult(req.ID, map[string]interface{}{
			"content": []map[string]interface{}{
				{"type": "text", "text": "Error: " + err.Error()},
			},
			"isError": true,
		})
		return
	}
	s.writeResult(req.ID, map[string]interface{}{
		"content": []map[string]interface{}{
			{"type": "text", "text": text},
		},
	})
}

// writeResult sends a successful JSON-RPC response.
func (s *Server) writeResult(id json.RawMessage, result interface{}) {
	if id == nil {
		return // notification — nothing to reply to
	}
	s.write(jsonrpcResponse{JSONRPC: "2.0", ID: id, Result: result})
}

// writeError sends a JSON-RPC error response.
func (s *Server) writeError(id json.RawMessage, code int, msg string, data interface{}) {
	s.write(jsonrpcResponse{
		JSONRPC: "2.0",
		ID:      id,
		Error:   &jsonrpcError{Code: code, Message: msg, Data: data},
	})
}

// write serializes and emits one response line, guarded by a mutex.
func (s *Server) write(resp jsonrpcResponse) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := s.out.Encode(resp); err != nil {
		fmt.Println(`{"jsonrpc":"2.0","error":{"code":-32603,"message":"encode error"}}`)
	}
}
