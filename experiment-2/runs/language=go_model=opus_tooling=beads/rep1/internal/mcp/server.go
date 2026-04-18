// Package mcp implements a minimal Model Context Protocol server over stdio.
// It speaks JSON-RPC 2.0 with newline-delimited messages (LSP-style length
// headers are not required for Claude Desktop's stdio transport when using
// ndjson framing).
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync"
)

type Request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type Response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  any             `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
}

type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

type ToolSchema struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
}

type Tool struct {
	Schema  ToolSchema
	Handler func(args json.RawMessage) (string, error)
}

type Server struct {
	Name    string
	Version string
	tools   map[string]Tool
	mu      sync.Mutex
}

func NewServer(name, version string) *Server {
	return &Server{Name: name, Version: version, tools: map[string]Tool{}}
}

func (s *Server) Register(t Tool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.tools[t.Schema.Name] = t
}

func (s *Server) Serve(in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 1<<20), 1<<22)
	enc := json.NewEncoder(out)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var req Request
		if err := json.Unmarshal(line, &req); err != nil {
			_ = enc.Encode(Response{JSONRPC: "2.0", Error: &RPCError{Code: -32700, Message: "parse error: " + err.Error()}})
			continue
		}
		resp := s.handle(req)
		if resp == nil {
			continue // notification
		}
		if err := enc.Encode(resp); err != nil {
			return err
		}
	}
	return scanner.Err()
}

func (s *Server) handle(req Request) *Response {
	isNotification := len(req.ID) == 0
	resp := &Response{JSONRPC: "2.0", ID: req.ID}
	switch req.Method {
	case "initialize":
		resp.Result = map[string]any{
			"protocolVersion": "2024-11-05",
			"capabilities": map[string]any{
				"tools": map[string]any{},
			},
			"serverInfo": map[string]any{
				"name":    s.Name,
				"version": s.Version,
			},
		}
	case "notifications/initialized", "initialized":
		if isNotification {
			return nil
		}
		resp.Result = map[string]any{}
	case "tools/list":
		schemas := make([]ToolSchema, 0, len(s.tools))
		s.mu.Lock()
		for _, t := range s.tools {
			schemas = append(schemas, t.Schema)
		}
		s.mu.Unlock()
		resp.Result = map[string]any{"tools": schemas}
	case "tools/call":
		var p struct {
			Name      string          `json:"name"`
			Arguments json.RawMessage `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			resp.Error = &RPCError{Code: -32602, Message: err.Error()}
			break
		}
		s.mu.Lock()
		t, ok := s.tools[p.Name]
		s.mu.Unlock()
		if !ok {
			resp.Error = &RPCError{Code: -32601, Message: "unknown tool: " + p.Name}
			break
		}
		text, err := t.Handler(p.Arguments)
		if err != nil {
			resp.Result = map[string]any{
				"content": []map[string]any{{"type": "text", "text": "error: " + err.Error()}},
				"isError": true,
			}
			break
		}
		resp.Result = map[string]any{
			"content": []map[string]any{{"type": "text", "text": text}},
		}
	case "ping":
		resp.Result = map[string]any{}
	default:
		if isNotification {
			return nil
		}
		resp.Error = &RPCError{Code: -32601, Message: fmt.Sprintf("method not found: %s", req.Method)}
	}
	if isNotification {
		return nil
	}
	return resp
}
