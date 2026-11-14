// mcp.go - a minimal Model Context Protocol server: JSON-RPC 2.0 over
// newline-delimited stdio, implementing initialize, ping, tools/list and
// tools/call. No third-party dependencies.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
)

const (
	serverName     = "brazilian-soccer-mcp"
	serverVersion  = "1.0.0"
	latestProtocol = "2025-06-18"
)

var supportedProtocols = map[string]bool{"2024-11-05": true, "2025-03-26": true, "2025-06-18": true}

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

// Server serves MCP requests against a DB.
type Server struct{ db *DB }

func NewServer(db *DB) *Server { return &Server{db: db} }

// Serve reads requests line by line until EOF.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	sc := bufio.NewScanner(in)
	sc.Buffer(make([]byte, 1<<16), 16<<20)
	enc := json.NewEncoder(out)
	enc.SetEscapeHTML(false)
	for sc.Scan() {
		line := sc.Bytes()
		if len(trimSpace(line)) == 0 {
			continue
		}
		if resp := s.HandleLine(line); resp != nil {
			if err := enc.Encode(resp); err != nil {
				return err
			}
		}
	}
	return sc.Err()
}

func trimSpace(b []byte) []byte {
	for len(b) > 0 && (b[0] == ' ' || b[0] == '\t' || b[0] == '\r' || b[0] == '\n') {
		b = b[1:]
	}
	return b
}

// HandleLine processes one JSON-RPC message; nil means no reply (notification).
func (s *Server) HandleLine(line []byte) *rpcResponse {
	var req rpcRequest
	if err := json.Unmarshal(line, &req); err != nil {
		return &rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &rpcError{-32700, "parse error: " + err.Error()}}
	}
	isNotification := len(req.ID) == 0
	result, rerr := s.dispatch(&req)
	if isNotification {
		return nil
	}
	resp := &rpcResponse{JSONRPC: "2.0", ID: req.ID}
	if rerr != nil {
		resp.Error = rerr
	} else {
		resp.Result = result
	}
	return resp
}

func (s *Server) dispatch(req *rpcRequest) (any, *rpcError) {
	switch req.Method {
	case "initialize":
		var p struct {
			ProtocolVersion string `json:"protocolVersion"`
		}
		_ = json.Unmarshal(req.Params, &p)
		v := latestProtocol
		if supportedProtocols[p.ProtocolVersion] {
			v = p.ProtocolVersion
		}
		return map[string]any{
			"protocolVersion": v,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": serverName, "version": serverVersion},
			"instructions":    "Knowledge graph of Brazilian soccer built from Kaggle datasets: Brasileirão (2003-2023), Copa do Brasil, Copa Libertadores, Serie B/C matches and FIFA player data. Team names are normalized, so any common spelling works. Start with dataset_info to see coverage.",
		}, nil
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		list := make([]map[string]any, 0, len(Tools))
		for _, t := range Tools {
			schema := map[string]any{"type": "object", "properties": t.Props}
			if len(t.Required) > 0 {
				schema["required"] = t.Required
			}
			list = append(list, map[string]any{"name": t.Name, "description": t.Description, "inputSchema": schema})
		}
		return map[string]any{"tools": list}, nil
	case "tools/call":
		var p struct {
			Name      string `json:"name"`
			Arguments Args   `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			return nil, &rpcError{-32602, "invalid params: " + err.Error()}
		}
		known := false
		for _, t := range Tools {
			known = known || t.Name == p.Name
		}
		if !known {
			return nil, &rpcError{-32602, fmt.Sprintf("unknown tool %q", p.Name)}
		}
		text, err := s.call(p.Name, p.Arguments)
		if err != nil {
			return map[string]any{"content": []map[string]any{{"type": "text", "text": "Error: " + err.Error()}}, "isError": true}, nil
		}
		return map[string]any{"content": []map[string]any{{"type": "text", "text": text}}, "isError": false}, nil
	case "resources/list":
		return map[string]any{"resources": []any{}}, nil
	case "prompts/list":
		return map[string]any{"prompts": []any{}}, nil
	}
	return nil, &rpcError{-32601, "method not found: " + req.Method}
}

func (s *Server) call(name string, args Args) (text string, err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("internal error: %v", r)
		}
	}()
	if args == nil {
		args = Args{}
	}
	return CallTool(s.db, name, args)
}
