package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync"

	"brazilian-soccer-mcp/internal/soccer"
)

// Server routes JSON-RPC requests to tool handlers backed by a soccer.Store.
type Server struct {
	store *soccer.Store
	tools []Tool
	// handlers maps tool name to its implementation.
	handlers map[string]func(args map[string]any) ToolResult

	mu  sync.Mutex // serialises writes to out
	out *bufio.Writer
}

// NewServer builds a server over the given store.
func NewServer(store *soccer.Store) *Server {
	s := &Server{store: store, handlers: map[string]func(map[string]any) ToolResult{}}
	s.registerTools()
	return s
}

// Tools exposes the advertised tool list (used by tools/list and tests).
func (s *Server) Tools() []Tool { return s.tools }

// Serve runs the read-eval-respond loop until in reaches EOF. Each line of in
// is one JSON-RPC message; each response is written as one line to out.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	s.out = bufio.NewWriter(out)
	defer s.out.Flush()

	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		s.handleLine(line)
		s.out.Flush()
	}
	return scanner.Err()
}

// handleLine parses and dispatches a single message.
func (s *Server) handleLine(line []byte) {
	var req Request
	if err := json.Unmarshal(line, &req); err != nil {
		s.write(Response{
			JSONRPC: "2.0",
			Error:   &RPCError{Code: CodeParseError, Message: "parse error: " + err.Error()},
		})
		return
	}
	resp, ok := s.dispatch(req)
	if !ok {
		return // notification: no response
	}
	s.write(resp)
}

// dispatch handles a single request, returning the response and whether one
// should be written (notifications return ok=false).
func (s *Server) dispatch(req Request) (Response, bool) {
	base := Response{JSONRPC: "2.0", ID: req.ID}
	switch req.Method {
	case "initialize":
		base.Result = map[string]any{
			"protocolVersion": ProtocolVersion,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo": map[string]any{
				"name":    "brazilian-soccer-mcp",
				"version": "1.0.0",
			},
		}
		return base, true

	case "notifications/initialized", "initialized":
		return Response{}, false

	case "ping":
		base.Result = map[string]any{}
		return base, true

	case "tools/list":
		base.Result = map[string]any{"tools": s.tools}
		return base, true

	case "tools/call":
		if req.IsNotification() {
			return Response{}, false
		}
		base.Result = s.callTool(req.Params)
		return base, true

	default:
		if req.IsNotification() {
			return Response{}, false
		}
		base.Error = &RPCError{Code: CodeMethodNotFound, Message: "method not found: " + req.Method}
		return base, true
	}
}

// callTool decodes tools/call params and invokes the named handler.
func (s *Server) callTool(params json.RawMessage) ToolResult {
	var p struct {
		Name      string         `json:"name"`
		Arguments map[string]any `json:"arguments"`
	}
	if err := json.Unmarshal(params, &p); err != nil {
		return errorResult("invalid tool call params: " + err.Error())
	}
	handler, ok := s.handlers[p.Name]
	if !ok {
		return errorResult(fmt.Sprintf("unknown tool: %q", p.Name))
	}
	if p.Arguments == nil {
		p.Arguments = map[string]any{}
	}
	return handler(p.Arguments)
}

// write serialises a response as a single JSON line.
func (s *Server) write(resp Response) {
	s.mu.Lock()
	defer s.mu.Unlock()
	b, err := json.Marshal(resp)
	if err != nil {
		b, _ = json.Marshal(Response{
			JSONRPC: "2.0", ID: resp.ID,
			Error: &RPCError{Code: CodeInternalError, Message: "marshal error"},
		})
	}
	s.out.Write(b)
	s.out.WriteByte('\n')
}
