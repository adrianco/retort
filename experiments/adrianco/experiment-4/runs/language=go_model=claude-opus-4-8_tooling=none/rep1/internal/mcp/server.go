// Context
// -------
// Server wires a populated soccer.Graph to the MCP JSON-RPC dispatch loop. It
// reads newline-delimited JSON-RPC messages from an io.Reader, routes the core
// MCP methods (initialize, notifications/initialized, ping, tools/list,
// tools/call) and writes responses to an io.Writer. Serve() blocks until the
// input stream closes, making it suitable to drive directly from os.Stdin/Stdout
// or from an in-memory pipe in tests.
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync"

	"brazilian-soccer-mcp/internal/soccer"
)

// Server is an MCP server backed by a soccer knowledge graph.
type Server struct {
	graph *soccer.Graph
	name  string
	ver   string

	mu  sync.Mutex // serializes writes to out
	out *bufio.Writer
}

// NewServer constructs a Server over the given graph.
func NewServer(graph *soccer.Graph) *Server {
	return &Server{graph: graph, name: "brazilian-soccer-mcp", ver: "1.0.0"}
}

// Serve runs the JSON-RPC loop, reading requests from in and writing responses
// to out, until in reaches EOF. A large buffer accommodates long lines.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	s.out = bufio.NewWriter(out)
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		s.handleLine(line)
	}
	return scanner.Err()
}

// handleLine decodes and dispatches a single JSON-RPC message.
func (s *Server) handleLine(line []byte) {
	var req Request
	if err := json.Unmarshal(line, &req); err != nil {
		s.writeError(nil, codeParseError, "parse error: "+err.Error())
		return
	}
	resp, isNotification := s.dispatch(req)
	if isNotification {
		return // notifications get no response
	}
	s.write(resp)
}

// dispatch routes a request to its handler, returning the response and whether
// the request was a notification (in which case the response is ignored).
func (s *Server) dispatch(req Request) (Response, bool) {
	switch req.Method {
	case "initialize":
		return s.ok(req.ID, InitializeResult{
			ProtocolVersion: ProtocolVersion,
			Capabilities:    Capabilities{Tools: &ToolsCapability{ListChanged: false}},
			ServerInfo:      ServerInfo{Name: s.name, Version: s.ver},
		}), false
	case "notifications/initialized", "initialized":
		return Response{}, true
	case "ping":
		return s.ok(req.ID, struct{}{}), false
	case "tools/list":
		return s.ok(req.ID, ToolsListResult{Tools: toolDefinitions()}), false
	case "tools/call":
		return s.handleToolCall(req), false
	default:
		if req.IsNotification() {
			return Response{}, true // ignore unknown notifications
		}
		return s.fail(req.ID, codeMethodNotFound, "method not found: "+req.Method), false
	}
}

// handleToolCall parses the call params, dispatches to the tool, and wraps the
// result. Tool-level failures are reported as result.isError (per MCP) rather
// than as protocol errors so the client/LLM can read the message.
func (s *Server) handleToolCall(req Request) Response {
	if req.IsNotification() {
		return Response{}
	}
	var p CallToolParams
	if err := json.Unmarshal(req.Params, &p); err != nil {
		return s.fail(req.ID, codeInvalidParams, "invalid tool params: "+err.Error())
	}
	result := s.callTool(p)
	return s.ok(req.ID, result)
}

func (s *Server) ok(id json.RawMessage, result interface{}) Response {
	return Response{JSONRPC: "2.0", ID: id, Result: result}
}

func (s *Server) fail(id json.RawMessage, code int, msg string) Response {
	return Response{JSONRPC: "2.0", ID: id, Error: &RPCError{Code: code, Message: msg}}
}

func (s *Server) write(resp Response) {
	s.mu.Lock()
	defer s.mu.Unlock()
	enc := json.NewEncoder(s.out)
	if err := enc.Encode(resp); err != nil { // Encode appends a newline
		fmt.Fprintf(s.out, "\n")
	}
	s.out.Flush()
}

func (s *Server) writeError(id json.RawMessage, code int, msg string) {
	s.write(Response{JSONRPC: "2.0", ID: id, Error: &RPCError{Code: code, Message: msg}})
}
