// Package mcp implements a minimal Model Context Protocol server over the stdio
// transport using only the Go standard library.
//
// Context
// -------
// The Brazilian Soccer MCP server speaks JSON-RPC 2.0 framed as newline
// delimited JSON on stdin/stdout, which is the MCP stdio transport. Rather than
// pull in an SDK, this package implements just enough of the protocol for an
// LLM host to discover and call tools:
//
//   - initialize / notifications/initialized handshake
//   - tools/list
//   - tools/call
//   - ping
//
// Tools are registered by the command layer (see cmd / main.go) via Register.
// Each tool exposes a JSON Schema describing its arguments and a handler that
// receives the decoded arguments and returns text.
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync"
)

// ProtocolVersion is the MCP protocol revision this server implements.
const ProtocolVersion = "2024-11-05"

// ToolHandler executes a tool call. args holds the raw JSON of the call's
// "arguments" object (possibly null). It returns the text result or an error.
type ToolHandler func(args json.RawMessage) (string, error)

// Tool is a registered tool: its advertised schema plus its handler.
type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	handler     ToolHandler    `json:"-"`
}

// Server is an MCP server bound to an input/output stream.
type Server struct {
	name    string
	version string

	mu    sync.Mutex
	tools []Tool
	index map[string]ToolHandler
}

// NewServer creates a server with the given identity.
func NewServer(name, version string) *Server {
	return &Server{name: name, version: version, index: map[string]ToolHandler{}}
}

// Register adds a tool. Calling it after Serve has started is safe but the tool
// list returned to an already-initialised client will not refresh.
func (s *Server) Register(name, description string, schema map[string]any, handler ToolHandler) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.tools = append(s.tools, Tool{Name: name, Description: description, InputSchema: schema, handler: handler})
	s.index[name] = handler
}

// --- JSON-RPC wire types ---

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
	Data    any    `json:"data,omitempty"`
}

// Standard JSON-RPC error codes.
const (
	errParse          = -32700
	errInvalidRequest = -32600
	errMethodNotFound = -32601
	errInternal       = -32603
)

// Serve runs the read/dispatch/write loop until the input stream closes.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	// Allow large lines (tool results / arguments can be sizeable).
	scanner.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	writer := bufio.NewWriter(out)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(trimSpace(line)) == 0 {
			continue
		}
		var req request
		if err := json.Unmarshal(line, &req); err != nil {
			s.write(writer, response{
				JSONRPC: "2.0",
				Error:   &rpcError{Code: errParse, Message: "parse error: " + err.Error()},
			})
			continue
		}
		resp, isNotification := s.handle(req)
		if isNotification {
			continue // notifications get no response
		}
		s.write(writer, resp)
	}
	if err := scanner.Err(); err != nil {
		return fmt.Errorf("mcp: reading input: %w", err)
	}
	return nil
}

// handle dispatches a single request. The bool result is true for
// notifications (no ID), which must not produce a response.
func (s *Server) handle(req request) (response, bool) {
	isNotification := len(req.ID) == 0

	switch req.Method {
	case "initialize":
		return s.ok(req, map[string]any{
			"protocolVersion": ProtocolVersion,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": s.name, "version": s.version},
		}), isNotification

	case "notifications/initialized", "initialized":
		return response{}, true

	case "ping":
		return s.ok(req, map[string]any{}), isNotification

	case "tools/list":
		s.mu.Lock()
		tools := make([]Tool, len(s.tools))
		copy(tools, s.tools)
		s.mu.Unlock()
		return s.ok(req, map[string]any{"tools": tools}), isNotification

	case "tools/call":
		return s.handleToolCall(req), isNotification

	default:
		if isNotification {
			return response{}, true
		}
		return s.fail(req, errMethodNotFound, "method not found: "+req.Method), false
	}
}

type toolCallParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

func (s *Server) handleToolCall(req request) response {
	var p toolCallParams
	if err := json.Unmarshal(req.Params, &p); err != nil {
		return s.fail(req, errInvalidRequest, "invalid params: "+err.Error())
	}
	s.mu.Lock()
	handler, ok := s.index[p.Name]
	s.mu.Unlock()
	if !ok {
		return s.fail(req, errMethodNotFound, "unknown tool: "+p.Name)
	}
	text, err := handler(p.Arguments)
	if err != nil {
		// Tool execution errors are reported in-band per the MCP spec so the
		// model can read and react to them.
		return s.ok(req, map[string]any{
			"content": []map[string]any{{"type": "text", "text": "Error: " + err.Error()}},
			"isError": true,
		})
	}
	return s.ok(req, map[string]any{
		"content": []map[string]any{{"type": "text", "text": text}},
		"isError": false,
	})
}

func (s *Server) ok(req request, result any) response {
	return response{JSONRPC: "2.0", ID: req.ID, Result: result}
}

func (s *Server) fail(req request, code int, msg string) response {
	return response{JSONRPC: "2.0", ID: req.ID, Error: &rpcError{Code: code, Message: msg}}
}

func (s *Server) write(w *bufio.Writer, resp response) {
	resp.JSONRPC = "2.0"
	data, err := json.Marshal(resp)
	if err != nil {
		data, _ = json.Marshal(response{
			JSONRPC: "2.0", ID: resp.ID,
			Error: &rpcError{Code: errInternal, Message: "marshal error"},
		})
	}
	w.Write(data)
	w.WriteByte('\n')
	w.Flush()
}

// trimSpace reports the slice with leading/trailing ASCII whitespace removed,
// used to detect blank input lines without allocating a string.
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

func isSpace(c byte) bool {
	return c == ' ' || c == '\t' || c == '\r' || c == '\n'
}
