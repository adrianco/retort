// Package mcp implements a minimal Model Context Protocol server over the stdio
// transport using only the Go standard library.
//
// Context:
//   - Project: Brazilian Soccer MCP Server (see TASK.md).
//   - Role of this file: JSON-RPC 2.0 message types and the stdio read/write
//     loop. MCP's stdio transport frames each JSON-RPC message as a single line
//     of JSON on stdin/stdout; logs go to stderr. This file is transport-only —
//     the soccer tools live in tools.go.
//   - Implementing the protocol directly (rather than via a third-party SDK)
//     keeps the build dependency-free and fully reproducible offline.
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync"
)

// protocolVersion is the MCP revision this server advertises.
const protocolVersion = "2024-11-05"

// Request is an incoming JSON-RPC request or notification. A notification has no
// ID field.
type Request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// Response is an outgoing JSON-RPC response.
type Response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  interface{}     `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
}

// RPCError is a JSON-RPC error object.
type RPCError struct {
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

// handlerFunc processes a request's params and returns a result or an error.
type handlerFunc func(params json.RawMessage) (interface{}, *RPCError)

// Server dispatches JSON-RPC methods read from an io.Reader to registered
// handlers, writing responses to an io.Writer.
type Server struct {
	in       io.Reader
	out      io.Writer
	logf     func(string, ...interface{})
	handlers map[string]handlerFunc
	wmu      sync.Mutex
}

// NewServer creates a Server reading from in and writing to out. logf receives
// diagnostic messages (typically wired to stderr).
func NewServer(in io.Reader, out io.Writer, logf func(string, ...interface{})) *Server {
	if logf == nil {
		logf = func(string, ...interface{}) {}
	}
	return &Server{
		in:       in,
		out:      out,
		logf:     logf,
		handlers: map[string]handlerFunc{},
	}
}

// Handle registers a handler for a JSON-RPC method.
func (s *Server) Handle(method string, h handlerFunc) { s.handlers[method] = h }

// Serve runs the read/dispatch loop until the input stream is exhausted.
func (s *Server) Serve() error {
	scanner := bufio.NewScanner(s.in)
	scanner.Buffer(make([]byte, 0, 1<<20), 1<<24) // allow large messages
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(trimSpace(line)) == 0 {
			continue
		}
		s.dispatch(line)
	}
	return scanner.Err()
}

func trimSpace(b []byte) []byte {
	start, end := 0, len(b)
	for start < end && isSpace(b[start]) {
		start++
	}
	for end > start && isSpace(b[end-1]) {
		end--
	}
	return b[start:end]
}

func isSpace(c byte) bool { return c == ' ' || c == '\t' || c == '\r' || c == '\n' }

func (s *Server) dispatch(line []byte) {
	var req Request
	if err := json.Unmarshal(line, &req); err != nil {
		s.writeError(nil, codeParseError, "parse error: "+err.Error())
		return
	}
	h, ok := s.handlers[req.Method]
	if !ok {
		// Notifications (no ID) never get a response, even when unknown.
		if len(req.ID) == 0 {
			s.logf("ignoring unknown notification %q", req.Method)
			return
		}
		s.writeError(req.ID, codeMethodNotFound, "method not found: "+req.Method)
		return
	}
	result, rpcErr := h(req.Params)
	if len(req.ID) == 0 {
		// Notification: handler ran for side effects, no response.
		return
	}
	if rpcErr != nil {
		s.writeResponse(Response{JSONRPC: "2.0", ID: req.ID, Error: rpcErr})
		return
	}
	s.writeResponse(Response{JSONRPC: "2.0", ID: req.ID, Result: result})
}

func (s *Server) writeError(id json.RawMessage, code int, msg string) {
	s.writeResponse(Response{JSONRPC: "2.0", ID: id, Error: &RPCError{Code: code, Message: msg}})
}

func (s *Server) writeResponse(resp Response) {
	b, err := json.Marshal(resp)
	if err != nil {
		s.logf("failed to marshal response: %v", err)
		return
	}
	s.wmu.Lock()
	defer s.wmu.Unlock()
	if _, err := fmt.Fprintf(s.out, "%s\n", b); err != nil {
		s.logf("failed to write response: %v", err)
	}
}
