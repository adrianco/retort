package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
)

const protocolVersion = "2024-11-05"

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
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

// Server is a stdio MCP server.
type Server struct{ DB *DB }

// Handle processes one JSON-RPC message; returns nil for notifications.
func (s *Server) Handle(line []byte) *rpcResponse {
	var req rpcRequest
	if err := json.Unmarshal(line, &req); err != nil {
		return &rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &rpcError{-32700, "parse error"}}
	}
	if len(req.ID) == 0 {
		return nil // notification
	}
	resp := &rpcResponse{JSONRPC: "2.0", ID: req.ID}
	switch req.Method {
	case "initialize":
		resp.Result = map[string]any{
			"protocolVersion": protocolVersion,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": "brazilian-soccer", "version": "1.0.0"},
		}
	case "ping":
		resp.Result = map[string]any{}
	case "tools/list":
		var ts []map[string]any
		for _, t := range Tools {
			ts = append(ts, map[string]any{"name": t.Name, "description": t.Description, "inputSchema": t.Schema})
		}
		resp.Result = map[string]any{"tools": ts}
	case "tools/call":
		var p struct {
			Name      string `json:"name"`
			Arguments Args   `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			resp.Error = &rpcError{-32602, "invalid params"}
			break
		}
		text, err := s.Call(p.Name, p.Arguments)
		if err != nil {
			resp.Result = map[string]any{"content": []map[string]any{{"type": "text", "text": "Error: " + err.Error()}}, "isError": true}
		} else {
			resp.Result = map[string]any{"content": []map[string]any{{"type": "text", "text": text}}}
		}
	default:
		resp.Error = &rpcError{-32601, "method not found: " + req.Method}
	}
	return resp
}

// Call invokes a tool by name.
func (s *Server) Call(name string, args Args) (string, error) {
	if args == nil {
		args = Args{}
	}
	for _, t := range Tools {
		if t.Name == name {
			return t.Handler(s.DB, args)
		}
	}
	return "", fmt.Errorf("unknown tool %q", name)
}

// Serve reads newline-delimited JSON-RPC from r and writes responses to w.
func (s *Server) Serve(r io.Reader, w io.Writer) error {
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 1<<20), 1<<24)
	enc := json.NewEncoder(w)
	for sc.Scan() {
		if len(sc.Bytes()) == 0 {
			continue
		}
		if resp := s.Handle(sc.Bytes()); resp != nil {
			if err := enc.Encode(resp); err != nil {
				return err
			}
		}
	}
	return sc.Err()
}
