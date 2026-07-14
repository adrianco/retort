package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
)

const protocolVersion = "2024-11-05"
const serverName = "brazilian-soccer-mcp"
const serverVersion = "1.0.0"

// Tool describes a single MCP tool: its JSON Schema input contract and the
// Go function that implements it.
type Tool struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     func(args json.RawMessage) (any, error)
}

// Server is a minimal MCP server speaking the stdio transport: newline
// delimited JSON-RPC 2.0 messages, no Content-Length framing.
type Server struct {
	tools map[string]Tool
	order []string
	log   *log.Logger
}

func NewServer(logger *log.Logger) *Server {
	return &Server{tools: map[string]Tool{}, log: logger}
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

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

// Run reads JSON-RPC requests from in, one per line, and writes responses to
// out. It blocks until in is closed (EOF) or an unrecoverable read error
// occurs.
func (s *Server) Run(in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	enc := json.NewEncoder(out)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var req rpcRequest
		if err := json.Unmarshal(line, &req); err != nil {
			s.log.Printf("failed to parse request: %v", err)
			continue
		}
		resp := s.handle(req)
		if resp == nil {
			// Notification: no response expected.
			continue
		}
		if err := enc.Encode(resp); err != nil {
			return fmt.Errorf("writing response: %w", err)
		}
	}
	return scanner.Err()
}

func isNotification(id json.RawMessage) bool {
	return len(id) == 0
}

func (s *Server) handle(req rpcRequest) *rpcResponse {
	switch req.Method {
	case "initialize":
		return s.reply(req, map[string]any{
			"protocolVersion": protocolVersion,
			"capabilities": map[string]any{
				"tools": map[string]any{},
			},
			"serverInfo": map[string]any{
				"name":    serverName,
				"version": serverVersion,
			},
		}, nil)
	case "notifications/initialized", "notifications/cancelled":
		return nil
	case "ping":
		return s.reply(req, map[string]any{}, nil)
	case "tools/list":
		return s.reply(req, s.toolsList(), nil)
	case "tools/call":
		result, rerr := s.callTool(req.Params)
		return s.reply(req, result, rerr)
	default:
		if isNotification(req.ID) {
			return nil
		}
		return s.reply(req, nil, &rpcError{Code: -32601, Message: "method not found: " + req.Method})
	}
}

func (s *Server) reply(req rpcRequest, result any, rerr *rpcError) *rpcResponse {
	if isNotification(req.ID) {
		return nil
	}
	return &rpcResponse{JSONRPC: "2.0", ID: req.ID, Result: result, Error: rerr}
}

func (s *Server) toolsList() map[string]any {
	list := make([]map[string]any, 0, len(s.order))
	for _, name := range s.order {
		t := s.tools[name]
		list = append(list, map[string]any{
			"name":        t.Name,
			"description": t.Description,
			"inputSchema": t.InputSchema,
		})
	}
	return map[string]any{"tools": list}
}

type toolCallParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

func (s *Server) callTool(raw json.RawMessage) (any, *rpcError) {
	var p toolCallParams
	if err := json.Unmarshal(raw, &p); err != nil {
		return nil, &rpcError{Code: -32602, Message: "invalid params: " + err.Error()}
	}
	t, ok := s.tools[p.Name]
	if !ok {
		return nil, &rpcError{Code: -32602, Message: "unknown tool: " + p.Name}
	}
	result, err := t.Handler(p.Arguments)
	if err != nil {
		return map[string]any{
			"content": []map[string]any{
				{"type": "text", "text": err.Error()},
			},
			"isError": true,
		}, nil
	}
	text, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return nil, &rpcError{Code: -32603, Message: "failed to encode result: " + err.Error()}
	}
	return map[string]any{
		"content": []map[string]any{
			{"type": "text", "text": string(text)},
		},
	}, nil
}
