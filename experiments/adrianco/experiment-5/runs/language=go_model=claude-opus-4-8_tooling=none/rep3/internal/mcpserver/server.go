// Context: the server loop and JSON-RPC dispatch. Server.Serve reads
// newline-delimited JSON-RPC messages from a reader and writes responses to a
// writer, dispatching tool calls to the handlers in tools.go.
package mcpserver

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync"

	"brazilian-soccer-mcp/internal/soccer"
)

// Server is a stateful MCP server bound to a loaded data Store.
type Server struct {
	store *soccer.Store
	tools []tool
	// handlers maps a tool name to its implementation.
	handlers map[string]func(args map[string]any) (string, error)
}

// NewServer builds a Server over the given Store and registers all tools.
func NewServer(store *soccer.Store) *Server {
	s := &Server{store: store, handlers: map[string]func(map[string]any) (string, error){}}
	s.registerTools()
	return s
}

// Serve runs the read/dispatch/write loop until in is exhausted. Writes are
// serialized so concurrent handlers (if ever added) cannot interleave output.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	var writeMu sync.Mutex

	write := func(resp rpcResponse) {
		writeMu.Lock()
		defer writeMu.Unlock()
		resp.JSONRPC = "2.0"
		b, err := json.Marshal(resp)
		if err != nil {
			return
		}
		out.Write(b)
		out.Write([]byte("\n"))
	}

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var req rpcRequest
		if err := json.Unmarshal(line, &req); err != nil {
			write(rpcResponse{Error: &rpcError{Code: codeParseError, Message: "parse error: " + err.Error()}})
			continue
		}
		resp, ok := s.handle(req)
		if ok {
			write(resp)
		}
	}
	return scanner.Err()
}

// handle dispatches a single request. The boolean is false for notifications
// (no response should be sent).
func (s *Server) handle(req rpcRequest) (rpcResponse, bool) {
	switch req.Method {
	case "initialize":
		return rpcResponse{ID: req.ID, Result: initializeResult{
			ProtocolVersion: protocolVersion,
			Capabilities:    capabilities{Tools: &toolsCapability{}},
			ServerInfo:      serverInfo{Name: "brazilian-soccer-mcp", Version: "1.0.0"},
			Instructions:    "Query Brazilian soccer match, team, player and competition data from the bundled Kaggle datasets.",
		}}, true

	case "notifications/initialized", "initialized":
		return rpcResponse{}, false

	case "ping":
		return rpcResponse{ID: req.ID, Result: map[string]any{}}, true

	case "tools/list":
		return rpcResponse{ID: req.ID, Result: toolsListResult{Tools: s.tools}}, true

	case "tools/call":
		return s.handleToolCall(req), true

	default:
		if req.isNotification() {
			return rpcResponse{}, false
		}
		return rpcResponse{ID: req.ID, Error: &rpcError{
			Code:    codeMethodNotFound,
			Message: "method not found: " + req.Method,
		}}, true
	}
}

func (s *Server) handleToolCall(req rpcRequest) rpcResponse {
	var p callToolParams
	if err := json.Unmarshal(req.Params, &p); err != nil {
		return rpcResponse{ID: req.ID, Error: &rpcError{Code: codeInvalidParams, Message: "invalid params: " + err.Error()}}
	}
	handler, ok := s.handlers[p.Name]
	if !ok {
		return rpcResponse{ID: req.ID, Error: &rpcError{Code: codeMethodNotFound, Message: "unknown tool: " + p.Name}}
	}
	args := map[string]any{}
	if len(p.Arguments) > 0 {
		if err := json.Unmarshal(p.Arguments, &args); err != nil {
			return rpcResponse{ID: req.ID, Error: &rpcError{Code: codeInvalidParams, Message: "invalid arguments: " + err.Error()}}
		}
	}
	text, err := handler(args)
	if err != nil {
		// Tool-level errors are reported via isError content, not JSON-RPC errors,
		// per MCP conventions.
		return rpcResponse{ID: req.ID, Result: callToolResult{
			Content: []textContent{{Type: "text", Text: fmt.Sprintf("Error: %v", err)}},
			IsError: true,
		}}
	}
	return rpcResponse{ID: req.ID, Result: callToolResult{
		Content: []textContent{{Type: "text", Text: text}},
	}}
}
