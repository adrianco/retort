package main

// Minimal Model Context Protocol server: JSON-RPC 2.0 over newline-delimited
// stdio, implementing initialize, ping, tools/list and tools/call.

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"strconv"
	"strings"
	"sync"
)

const (
	serverName             = "brazilian-soccer-mcp"
	serverVersion          = "1.0.0"
	defaultProtocolVersion = "2024-11-05"
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

// Args are the decoded arguments of a tool call.
type Args map[string]any

func (a Args) Str(k string) string {
	switch v := a[k].(type) {
	case string:
		return strings.TrimSpace(v)
	case float64:
		return strconv.FormatFloat(v, 'f', -1, 64)
	}
	return ""
}

// Int returns an integer argument given as a JSON number or numeric string.
func (a Args) Int(k string, def int) (int, error) {
	switch v := a[k].(type) {
	case nil:
		return def, nil
	case float64:
		if v != float64(int(v)) {
			return 0, fmt.Errorf("argument %q must be an integer, got %v", k, v)
		}
		return int(v), nil
	case int:
		return v, nil
	case string:
		if strings.TrimSpace(v) == "" {
			return def, nil
		}
		n, err := strconv.Atoi(strings.TrimSpace(v))
		if err != nil {
			return 0, fmt.Errorf("argument %q must be an integer, got %q", k, v)
		}
		return n, nil
	}
	return 0, fmt.Errorf("argument %q must be an integer", k)
}

func (a Args) Bool(k string) bool {
	switch v := a[k].(type) {
	case bool:
		return v
	case string:
		return strings.EqualFold(v, "true")
	}
	return false
}

// Tool is one MCP tool.
type Tool struct {
	Name        string
	Description string
	Schema      map[string]any
	Handler     func(s *Store, a Args) (string, error)
}

// Server dispatches MCP requests against a Store.
type Server struct {
	store *Store
	tools []Tool
	index map[string]*Tool
}

func NewServer(store *Store) *Server {
	srv := &Server{store: store, tools: buildTools(), index: map[string]*Tool{}}
	for i := range srv.tools {
		srv.index[srv.tools[i].Name] = &srv.tools[i]
	}
	return srv
}

// CallTool runs a tool by name and returns its text output.
func (srv *Server) CallTool(name string, a Args) (string, error) {
	t, ok := srv.index[name]
	if !ok {
		return "", fmt.Errorf("unknown tool %q", name)
	}
	if a == nil {
		a = Args{}
	}
	return t.Handler(srv.store, a)
}

// Serve reads requests from r until EOF and writes responses to w.
func (srv *Server) Serve(r io.Reader, w io.Writer) error {
	br := bufio.NewReader(r)
	var mu sync.Mutex
	enc := json.NewEncoder(w)
	for {
		line, err := br.ReadBytes('\n')
		if len(strings.TrimSpace(string(line))) > 0 {
			if resp := srv.HandleMessage(line); resp != nil {
				mu.Lock()
				werr := enc.Encode(resp)
				mu.Unlock()
				if werr != nil {
					return werr
				}
			}
		}
		if err == io.EOF {
			return nil
		}
		if err != nil {
			return err
		}
	}
}

// HandleMessage processes one JSON-RPC message; it returns nil for
// notifications, which get no response.
func (srv *Server) HandleMessage(data []byte) *rpcResponse {
	var req rpcRequest
	if err := json.Unmarshal(data, &req); err != nil {
		return &rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &rpcError{-32700, "parse error: " + err.Error()}}
	}
	if len(req.ID) == 0 {
		return nil
	}
	resp := &rpcResponse{JSONRPC: "2.0", ID: req.ID}
	if req.JSONRPC != "2.0" || req.Method == "" {
		resp.Error = &rpcError{-32600, "invalid request"}
		return resp
	}
	switch req.Method {
	case "initialize":
		var p struct {
			ProtocolVersion string `json:"protocolVersion"`
		}
		_ = json.Unmarshal(req.Params, &p)
		version := defaultProtocolVersion
		if supportedProtocols[p.ProtocolVersion] {
			version = p.ProtocolVersion
		}
		resp.Result = map[string]any{
			"protocolVersion": version,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": serverName, "version": serverVersion},
			"instructions": "Knowledge base of Brazilian soccer: Brasileirão (Série A/B/C), Copa do Brasil and Copa Libertadores matches " +
				"plus the FIFA player database. Team names are matched loosely (accents, state suffixes and common aliases are handled). " +
				"All statistics are computed from the bundled datasets; call dataset_info for coverage.",
		}
	case "ping":
		resp.Result = map[string]any{}
	case "tools/list":
		list := make([]map[string]any, 0, len(srv.tools))
		for _, t := range srv.tools {
			list = append(list, map[string]any{"name": t.Name, "description": t.Description, "inputSchema": t.Schema})
		}
		resp.Result = map[string]any{"tools": list}
	case "resources/list":
		resp.Result = map[string]any{"resources": []any{}}
	case "prompts/list":
		resp.Result = map[string]any{"prompts": []any{}}
	case "tools/call":
		var p struct {
			Name      string `json:"name"`
			Arguments Args   `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			resp.Error = &rpcError{-32602, "invalid params: " + err.Error()}
			return resp
		}
		if _, ok := srv.index[p.Name]; !ok {
			resp.Error = &rpcError{-32602, "unknown tool: " + p.Name}
			return resp
		}
		text, err := srv.CallTool(p.Name, p.Arguments)
		isErr := false
		if err != nil {
			text, isErr = "Error: "+err.Error(), true
		}
		resp.Result = map[string]any{
			"content": []map[string]any{{"type": "text", "text": text}},
			"isError": isErr,
		}
	default:
		resp.Error = &rpcError{-32601, "method not found: " + req.Method}
	}
	return resp
}
