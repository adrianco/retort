// mcp.go implements the Model Context Protocol server side over stdio:
// newline-delimited JSON-RPC 2.0 messages supporting initialize, ping,
// tools/list and tools/call.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"sync"
)

const (
	serverName      = "brazilian-soccer-mcp"
	serverVersion   = "1.0.0"
	protocolVersion = "2024-11-05"
)

var supportedProtocolVersions = map[string]bool{
	"2024-11-05": true,
	"2025-03-26": true,
	"2025-06-18": true,
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
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

const (
	codeParseError     = -32700
	codeInvalidRequest = -32600
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
)

// Server is an MCP server bound to a data store.
type Server struct {
	store  *Store
	tools  []Tool
	byName map[string]*Tool

	mu  sync.Mutex // serializes writes to out
	out io.Writer
}

// NewServer creates an MCP server for the given store.
func NewServer(store *Store) *Server {
	s := &Server{store: store, tools: AllTools(), byName: map[string]*Tool{}}
	for i := range s.tools {
		s.byName[s.tools[i].Name] = &s.tools[i]
	}
	return s
}

// Serve reads newline-delimited JSON-RPC requests from in and writes
// responses to out until in is exhausted.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	s.out = out
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		if resp := s.HandleMessage(line); resp != nil {
			s.send(resp)
		}
	}
	return scanner.Err()
}

func (s *Server) send(resp *rpcResponse) {
	s.mu.Lock()
	defer s.mu.Unlock()
	data, err := json.Marshal(resp)
	if err != nil {
		log.Printf("marshal response: %v", err)
		return
	}
	data = append(data, '\n')
	if _, err := s.out.Write(data); err != nil {
		log.Printf("write response: %v", err)
	}
}

// HandleMessage processes one JSON-RPC message and returns the response, or
// nil for notifications (which get no response).
func (s *Server) HandleMessage(line []byte) *rpcResponse {
	var req rpcRequest
	if err := json.Unmarshal(line, &req); err != nil {
		return &rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"),
			Error: &rpcError{Code: codeParseError, Message: "parse error: " + err.Error()}}
	}
	isNotification := len(req.ID) == 0 || string(req.ID) == "null"
	result, rpcErr := s.dispatch(&req)
	if isNotification {
		return nil
	}
	resp := &rpcResponse{JSONRPC: "2.0", ID: req.ID}
	if rpcErr != nil {
		resp.Error = rpcErr
	} else {
		resp.Result = result
	}
	return resp
}

func (s *Server) dispatch(req *rpcRequest) (any, *rpcError) {
	switch req.Method {
	case "initialize":
		return s.handleInitialize(req.Params), nil
	case "notifications/initialized", "initialized", "notifications/cancelled":
		return nil, nil
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		return s.handleToolsList(), nil
	case "tools/call":
		return s.handleToolsCall(req.Params)
	case "resources/list":
		return map[string]any{"resources": []any{}}, nil
	case "prompts/list":
		return map[string]any{"prompts": []any{}}, nil
	default:
		return nil, &rpcError{Code: codeMethodNotFound, Message: "method not found: " + req.Method}
	}
}

func (s *Server) handleInitialize(params json.RawMessage) any {
	version := protocolVersion
	var p struct {
		ProtocolVersion string `json:"protocolVersion"`
	}
	if err := json.Unmarshal(params, &p); err == nil && supportedProtocolVersions[p.ProtocolVersion] {
		version = p.ProtocolVersion
	}
	return map[string]any{
		"protocolVersion": version,
		"capabilities": map[string]any{
			"tools": map[string]any{},
		},
		"serverInfo": map[string]any{
			"name":    serverName,
			"version": serverVersion,
		},
		"instructions": fmt.Sprintf(
			"Knowledge base for Brazilian soccer: %d matches (Brasileirão Série A/B/C, Copa do Brasil, "+
				"Copa Libertadores, 2003-2023) and %d FIFA player profiles. Team names are normalized across "+
				"datasets. Use search_matches/head_to_head for fixtures, get_team_stats and get_standings for "+
				"records and tables, search_players/get_player_details for players, and get_competition_stats "+
				"for aggregate analysis.",
			len(s.store.Matches), len(s.store.Players)),
	}
}

func (s *Server) handleToolsList() any {
	tools := make([]map[string]any, 0, len(s.tools))
	for _, t := range s.tools {
		tools = append(tools, map[string]any{
			"name":        t.Name,
			"description": t.Description,
			"inputSchema": t.InputSchema,
		})
	}
	return map[string]any{"tools": tools}
}

func (s *Server) handleToolsCall(params json.RawMessage) (any, *rpcError) {
	var p struct {
		Name      string         `json:"name"`
		Arguments map[string]any `json:"arguments"`
	}
	if err := json.Unmarshal(params, &p); err != nil {
		return nil, &rpcError{Code: codeInvalidParams, Message: "invalid params: " + err.Error()}
	}
	tool, ok := s.byName[p.Name]
	if !ok {
		return nil, &rpcError{Code: codeInvalidParams, Message: "unknown tool: " + p.Name}
	}
	if p.Arguments == nil {
		p.Arguments = map[string]any{}
	}
	text, err := tool.Handler(s.store, p.Arguments)
	isError := false
	if err != nil {
		text = "Error: " + err.Error()
		isError = true
	}
	return map[string]any{
		"content": []map[string]any{{"type": "text", "text": text}},
		"isError": isError,
	}, nil
}
