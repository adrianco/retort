// Package mcp implements a minimal Model Context Protocol server over a stdio
// JSON-RPC 2.0 transport, with no external dependencies.
//
// Context: MCP's stdio transport exchanges newline-delimited JSON-RPC messages.
// This file defines the wire types and the Server loop (read request -> dispatch
// -> write response). Tool registration and the soccer-specific handlers live in
// tools.go / server.go. We implement the subset of MCP needed for an LLM to
// discover and call tools: initialize, notifications/initialized, tools/list,
// tools/call, and ping.
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync"
)

// ProtocolVersion advertised in the initialize response.
const ProtocolVersion = "2024-11-05"

// Request is an incoming JSON-RPC 2.0 request or notification.
type Request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"` // absent => notification
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// Response is an outgoing JSON-RPC 2.0 response.
type Response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  interface{}     `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
}

// RPCError is a JSON-RPC 2.0 error object.
type RPCError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

// Standard JSON-RPC error codes.
const (
	CodeParseError     = -32700
	CodeInvalidRequest = -32600
	CodeMethodNotFound = -32601
	CodeInvalidParams  = -32602
	CodeInternalError  = -32603
)

// Tool is a callable tool exposed over MCP.
type Tool struct {
	Name        string                 `json:"name"`
	Description string                 `json:"description"`
	InputSchema map[string]interface{} `json:"inputSchema"`

	// Handler executes the tool. It is not serialized.
	Handler func(args map[string]interface{}) (string, error) `json:"-"`
}

// Server is an MCP server bound to an input/output stream.
type Server struct {
	name    string
	version string
	tools   []Tool
	byName  map[string]Tool

	in  io.Reader
	out io.Writer
	mu  sync.Mutex // serializes writes
}

// NewServer creates a server with the given identity reading/writing the
// provided streams (typically os.Stdin/os.Stdout).
func NewServer(name, version string, in io.Reader, out io.Writer) *Server {
	return &Server{
		name:    name,
		version: version,
		byName:  map[string]Tool{},
		in:      in,
		out:     out,
	}
}

// Register adds a tool to the server.
func (s *Server) Register(t Tool) {
	s.tools = append(s.tools, t)
	s.byName[t.Name] = t
}

// Serve runs the read/dispatch/write loop until the input stream closes.
func (s *Server) Serve() error {
	sc := bufio.NewScanner(s.in)
	sc.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)
	for sc.Scan() {
		line := sc.Bytes()
		if len(line) == 0 {
			continue
		}
		var req Request
		if err := json.Unmarshal(line, &req); err != nil {
			s.writeError(nil, CodeParseError, "parse error: "+err.Error())
			continue
		}
		s.handle(&req)
	}
	return sc.Err()
}

// handle dispatches one request. Notifications (no ID) never produce a response.
func (s *Server) handle(req *Request) {
	isNotification := len(req.ID) == 0
	result, rpcErr := s.dispatch(req)
	if isNotification {
		return
	}
	if rpcErr != nil {
		s.writeError(req.ID, rpcErr.Code, rpcErr.Message)
		return
	}
	s.write(Response{JSONRPC: "2.0", ID: req.ID, Result: result})
}

func (s *Server) write(resp Response) {
	s.mu.Lock()
	defer s.mu.Unlock()
	enc := json.NewEncoder(s.out)
	_ = enc.Encode(resp) // newline-delimited
}

func (s *Server) writeError(id json.RawMessage, code int, msg string) {
	if id == nil {
		id = json.RawMessage("null")
	}
	s.write(Response{JSONRPC: "2.0", ID: id, Error: &RPCError{Code: code, Message: msg}})
}

func errf(code int, format string, a ...interface{}) *RPCError {
	return &RPCError{Code: code, Message: fmt.Sprintf(format, a...)}
}
