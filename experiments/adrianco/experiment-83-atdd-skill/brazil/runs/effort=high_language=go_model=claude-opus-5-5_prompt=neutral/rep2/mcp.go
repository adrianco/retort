// Minimal Model Context Protocol server: JSON-RPC 2.0 over newline-delimited
// stdio, implementing initialize, ping, tools/list and tools/call (plus empty
// resources/prompts lists for clients that probe them).
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"strings"
	"sync"
	"time"
)

const (
	serverName      = "brazilian-soccer-mcp"
	serverVersion   = "1.0.0"
	protocolVersion = "2025-06-18"
)

var supportedProtocols = map[string]bool{"2024-11-05": true, "2025-03-26": true, "2025-06-18": true}

// JSON-RPC error codes.
const (
	codeParseError     = -32700
	codeInvalidRequest = -32600
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
)

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

// Server dispatches MCP requests to tools.
type Server struct {
	store  *Store
	tools  []Tool
	byName map[string]Tool
	logger *log.Logger
}

// NewServer creates a server over a loaded store.
func NewServer(store *Store, logger *log.Logger) *Server {
	s := &Server{store: store, tools: Tools(), byName: map[string]Tool{}, logger: logger}
	for _, t := range s.tools {
		s.byName[t.Name] = t
	}
	return s
}

// Serve reads requests from r and writes responses to w until EOF.
func (s *Server) Serve(r io.Reader, w io.Writer) error {
	var mu sync.Mutex
	enc := json.NewEncoder(w)
	write := func(v any) {
		mu.Lock()
		defer mu.Unlock()
		if err := enc.Encode(v); err != nil && s.logger != nil {
			s.logger.Printf("write error: %v", err)
		}
	}
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 0, 1<<20), 64<<20)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" {
			continue
		}
		if resp := s.HandleMessage([]byte(line)); resp != nil {
			write(resp)
		}
	}
	return sc.Err()
}

// HandleMessage processes one JSON-RPC message (single or batch) and
// returns the response to send, or nil for notifications.
func (s *Server) HandleMessage(data []byte) any {
	if len(data) > 0 && data[0] == '[' {
		var batch []json.RawMessage
		if err := json.Unmarshal(data, &batch); err != nil || len(batch) == 0 {
			return rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &rpcError{codeParseError, "invalid batch"}}
		}
		var out []rpcResponse
		for _, item := range batch {
			if resp := s.handleOne(item); resp != nil {
				out = append(out, *resp)
			}
		}
		if len(out) == 0 {
			return nil
		}
		return out
	}
	if resp := s.handleOne(data); resp != nil {
		return *resp
	}
	return nil
}

func (s *Server) handleOne(data []byte) *rpcResponse {
	var req rpcRequest
	if err := json.Unmarshal(data, &req); err != nil {
		return &rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &rpcError{codeParseError, "parse error: " + err.Error()}}
	}
	isNotification := len(req.ID) == 0 || string(req.ID) == "null"
	if req.Method == "" {
		if isNotification {
			return nil // a response from the client; nothing to do
		}
		return &rpcResponse{JSONRPC: "2.0", ID: req.ID, Error: &rpcError{codeInvalidRequest, "missing method"}}
	}
	result, rerr := s.dispatch(req)
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

func (s *Server) dispatch(req rpcRequest) (any, *rpcError) {
	switch req.Method {
	case "initialize":
		var p struct {
			ProtocolVersion string `json:"protocolVersion"`
		}
		_ = json.Unmarshal(req.Params, &p)
		version := protocolVersion
		if supportedProtocols[p.ProtocolVersion] {
			version = p.ProtocolVersion
		}
		return map[string]any{
			"protocolVersion": version,
			"capabilities":    map[string]any{"tools": map[string]any{"listChanged": false}},
			"serverInfo":      map[string]any{"name": serverName, "version": serverVersion},
			"instructions": "Answers questions about Brazilian soccer from Kaggle datasets: Brasileirão Série A 2003-2023 (plus Série B/C 2014-2023), " +
				"Copa do Brasil 2012-2023, Copa Libertadores 2013-2022 and FIFA 19 player ratings. Team names are normalised, so any common spelling works. " +
				"Use search_matches/head_to_head for fixtures, team_record/team_overview for clubs, standings/knockout_matches for competitions, " +
				"team_rankings/league_stats/biggest_wins for statistics and search_players/get_player for players.",
		}, nil
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		list := make([]map[string]any, 0, len(s.tools))
		for _, t := range s.tools {
			list = append(list, map[string]any{"name": t.Name, "description": t.Description, "inputSchema": t.InputSchema})
		}
		return map[string]any{"tools": list}, nil
	case "tools/call":
		var p struct {
			Name      string         `json:"name"`
			Arguments map[string]any `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			return nil, &rpcError{codeInvalidParams, "invalid params: " + err.Error()}
		}
		if _, ok := s.byName[p.Name]; !ok {
			return nil, &rpcError{codeInvalidParams, fmt.Sprintf("unknown tool %q", p.Name)}
		}
		text, err := s.CallTool(p.Name, p.Arguments)
		if err != nil {
			return map[string]any{"content": []map[string]any{{"type": "text", "text": "Error: " + err.Error()}}, "isError": true}, nil
		}
		return map[string]any{"content": []map[string]any{{"type": "text", "text": text}}, "isError": false}, nil
	case "resources/list":
		return map[string]any{"resources": []any{}}, nil
	case "prompts/list":
		return map[string]any{"prompts": []any{}}, nil
	}
	if strings.HasPrefix(req.Method, "notifications/") {
		return nil, nil
	}
	return nil, &rpcError{codeMethodNotFound, "method not found: " + req.Method}
}

// CallTool runs a tool by name, recovering from panics so a bad query can
// never take the server down.
func (s *Server) CallTool(name string, args map[string]any) (text string, err error) {
	t, ok := s.byName[name]
	if !ok {
		return "", fmt.Errorf("unknown tool %q", name)
	}
	start := time.Now()
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("internal error in %s: %v", name, r)
		}
		if s.logger != nil {
			s.logger.Printf("tool %s %v -> %s (err=%v)", name, args, time.Since(start).Round(time.Microsecond), err)
		}
	}()
	if args == nil {
		args = map[string]any{}
	}
	return t.Handler(s.store, Args(args))
}
