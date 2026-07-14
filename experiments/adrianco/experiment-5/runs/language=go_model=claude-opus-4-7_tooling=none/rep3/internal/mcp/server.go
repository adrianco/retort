// Package mcp implements a minimal Model Context Protocol server over
// JSON-RPC 2.0 on stdio. It exposes a configurable set of "tools" that the
// host LLM can call to query the Brazilian soccer dataset.
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync"
)

const ProtocolVersion = "2024-11-05"

type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	Handler     ToolHandler    `json:"-"`
}

// ToolHandler executes a tool. It returns the textual content shown to the
// model, or an error describing the failure.
type ToolHandler func(args map[string]any) (string, error)

type Server struct {
	name    string
	version string
	tools   map[string]Tool
	order   []string

	mu  sync.Mutex
	enc *json.Encoder
}

func NewServer(name, version string) *Server {
	return &Server{
		name:    name,
		version: version,
		tools:   make(map[string]Tool),
	}
}

func (s *Server) Register(t Tool) {
	if _, exists := s.tools[t.Name]; !exists {
		s.order = append(s.order, t.Name)
	}
	s.tools[t.Name] = t
}

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

func (s *Server) Serve(in io.Reader, out io.Writer) error {
	s.enc = json.NewEncoder(out)
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var req rpcRequest
		if err := json.Unmarshal(line, &req); err != nil {
			s.writeError(nil, -32700, "parse error", err.Error())
			continue
		}
		s.dispatch(req)
	}
	return scanner.Err()
}

func (s *Server) dispatch(req rpcRequest) {
	switch req.Method {
	case "initialize":
		s.writeResult(req.ID, map[string]any{
			"protocolVersion": ProtocolVersion,
			"capabilities": map[string]any{
				"tools": map[string]any{},
			},
			"serverInfo": map[string]any{
				"name":    s.name,
				"version": s.version,
			},
		})
	case "notifications/initialized":
		// notification, no response.
	case "ping":
		s.writeResult(req.ID, map[string]any{})
	case "tools/list":
		tools := make([]map[string]any, 0, len(s.order))
		for _, n := range s.order {
			t := s.tools[n]
			tools = append(tools, map[string]any{
				"name":        t.Name,
				"description": t.Description,
				"inputSchema": t.InputSchema,
			})
		}
		s.writeResult(req.ID, map[string]any{"tools": tools})
	case "tools/call":
		var p struct {
			Name      string         `json:"name"`
			Arguments map[string]any `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			s.writeError(req.ID, -32602, "invalid params", err.Error())
			return
		}
		t, ok := s.tools[p.Name]
		if !ok {
			s.writeError(req.ID, -32601, fmt.Sprintf("unknown tool: %s", p.Name), nil)
			return
		}
		text, err := t.Handler(p.Arguments)
		if err != nil {
			s.writeResult(req.ID, map[string]any{
				"content": []map[string]any{{"type": "text", "text": "Error: " + err.Error()}},
				"isError": true,
			})
			return
		}
		s.writeResult(req.ID, map[string]any{
			"content": []map[string]any{{"type": "text", "text": text}},
			"isError": false,
		})
	default:
		if len(req.ID) > 0 {
			s.writeError(req.ID, -32601, "method not found: "+req.Method, nil)
		}
	}
}

func (s *Server) writeResult(id json.RawMessage, result any) {
	if len(id) == 0 {
		return
	}
	s.write(rpcResponse{JSONRPC: "2.0", ID: id, Result: result})
}

func (s *Server) writeError(id json.RawMessage, code int, msg string, data any) {
	s.write(rpcResponse{JSONRPC: "2.0", ID: id, Error: &rpcError{Code: code, Message: msg, Data: data}})
}

func (s *Server) write(resp rpcResponse) {
	s.mu.Lock()
	defer s.mu.Unlock()
	_ = s.enc.Encode(resp)
}

// CallTool exposes a tool directly (used by tests).
func (s *Server) CallTool(name string, args map[string]any) (string, error) {
	t, ok := s.tools[name]
	if !ok {
		return "", fmt.Errorf("unknown tool: %s", name)
	}
	return t.Handler(args)
}

// ToolNames returns the registered tool names in registration order.
func (s *Server) ToolNames() []string {
	out := make([]string, len(s.order))
	copy(out, s.order)
	return out
}
