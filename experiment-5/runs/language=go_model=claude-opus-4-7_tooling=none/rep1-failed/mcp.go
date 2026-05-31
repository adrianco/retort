package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"strings"
	"sync"
)

// JSON-RPC 2.0 envelope types.
type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type rpcResponse struct {
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

// MCP error/response shapes.
type mcpToolDef struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
}

type mcpContent struct {
	Type string `json:"type"`
	Text string `json:"text,omitempty"`
}

type mcpToolResult struct {
	Content []mcpContent `json:"content"`
	IsError bool         `json:"isError,omitempty"`
}

// Server is the MCP JSON-RPC server.
type Server struct {
	db    *DB
	tools []Tool
	mu    sync.Mutex
	out   io.Writer
}

// Tool describes a callable tool, its schema, and its handler.
type Tool struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     func(s *Server, args map[string]any) (string, error)
}

// NewServer constructs an MCP server with the given DB writing responses to out.
func NewServer(db *DB, out io.Writer) *Server {
	s := &Server{db: db, out: out}
	s.tools = RegisterTools()
	return s
}

// Serve reads JSON-RPC requests as newline-delimited JSON objects from in,
// dispatches them, and writes responses to out.
func (s *Server) Serve(in io.Reader) error {
	r := bufio.NewReader(in)
	for {
		line, err := r.ReadString('\n')
		if len(strings.TrimSpace(line)) > 0 {
			s.handleLine(line)
		}
		if err != nil {
			if err == io.EOF {
				return nil
			}
			return err
		}
	}
}

func (s *Server) handleLine(line string) {
	var req rpcRequest
	if err := json.Unmarshal([]byte(line), &req); err != nil {
		s.send(rpcResponse{
			JSONRPC: "2.0",
			Error:   &rpcError{Code: -32700, Message: "parse error: " + err.Error()},
		})
		return
	}
	switch req.Method {
	case "initialize":
		s.send(rpcResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result: map[string]any{
				"protocolVersion": "2024-11-05",
				"capabilities": map[string]any{
					"tools": map[string]any{},
				},
				"serverInfo": map[string]any{
					"name":    "brsoccer-mcp",
					"version": "0.1.0",
				},
			},
		})
	case "initialized", "notifications/initialized":
		// Notification only - no response.
		return
	case "tools/list":
		defs := make([]mcpToolDef, 0, len(s.tools))
		for _, t := range s.tools {
			defs = append(defs, mcpToolDef{
				Name:        t.Name,
				Description: t.Description,
				InputSchema: t.InputSchema,
			})
		}
		s.send(rpcResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result:  map[string]any{"tools": defs},
		})
	case "tools/call":
		s.handleToolCall(req)
	case "ping":
		s.send(rpcResponse{JSONRPC: "2.0", ID: req.ID, Result: map[string]any{}})
	case "shutdown":
		s.send(rpcResponse{JSONRPC: "2.0", ID: req.ID, Result: nil})
	default:
		if req.ID != nil {
			s.send(rpcResponse{
				JSONRPC: "2.0",
				ID:      req.ID,
				Error:   &rpcError{Code: -32601, Message: "method not found: " + req.Method},
			})
		}
	}
}

func (s *Server) handleToolCall(req rpcRequest) {
	var params struct {
		Name      string         `json:"name"`
		Arguments map[string]any `json:"arguments"`
	}
	if err := json.Unmarshal(req.Params, &params); err != nil {
		s.send(rpcResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error:   &rpcError{Code: -32602, Message: "invalid params: " + err.Error()},
		})
		return
	}
	var tool *Tool
	for i := range s.tools {
		if s.tools[i].Name == params.Name {
			tool = &s.tools[i]
			break
		}
	}
	if tool == nil {
		s.send(rpcResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result: mcpToolResult{
				Content: []mcpContent{{Type: "text", Text: "unknown tool: " + params.Name}},
				IsError: true,
			},
		})
		return
	}
	text, err := tool.Handler(s, params.Arguments)
	if err != nil {
		s.send(rpcResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result: mcpToolResult{
				Content: []mcpContent{{Type: "text", Text: err.Error()}},
				IsError: true,
			},
		})
		return
	}
	s.send(rpcResponse{
		JSONRPC: "2.0",
		ID:      req.ID,
		Result:  mcpToolResult{Content: []mcpContent{{Type: "text", Text: text}}},
	})
}

func (s *Server) send(resp rpcResponse) {
	s.mu.Lock()
	defer s.mu.Unlock()
	resp.JSONRPC = "2.0"
	b, err := json.Marshal(resp)
	if err != nil {
		fmt.Fprintf(s.out, "%s\n", `{"jsonrpc":"2.0","error":{"code":-32603,"message":"marshal error"}}`)
		return
	}
	fmt.Fprintf(s.out, "%s\n", b)
}
