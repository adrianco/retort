// Context: The MCP server transport for the Brazilian Soccer knowledge graph.
// It speaks the Model Context Protocol over a newline-delimited JSON-RPC 2.0
// stream (the MCP stdio transport): handling the initialize handshake, the
// tools/list discovery call, and tools/call invocations which it routes to the
// handlers in tools.go. This is the only entry point an MCP client (an LLM) or
// the acceptance tests use to talk to the system. The server is stateless
// between requests and reads its data from the Store it is constructed with.
package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"sync"
)

const (
	protocolVersion = "2024-11-05"
	serverName      = "brazilian-soccer-mcp"
	serverVersion   = "1.0.0"
)

// JSON-RPC error codes.
const (
	codeParseError     = -32700
	codeInvalidRequest = -32600
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
	codeInternalError  = -32603
)

// Server routes MCP requests to tool handlers over a JSON-RPC stream.
type Server struct {
	store   *Store
	tools   []Tool
	byName  map[string]Tool
	writeMu sync.Mutex
}

// NewServer builds a server exposing the soccer tools backed by store.
func NewServer(store *Store) *Server {
	tools := buildTools()
	byName := make(map[string]Tool, len(tools))
	for _, t := range tools {
		byName[t.Name] = t
	}
	return &Server{store: store, tools: tools, byName: byName}
}

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

// Serve reads JSON-RPC messages from in (one per line) and writes responses to
// out until the input is exhausted or the context is cancelled.
func (s *Server) Serve(ctx context.Context, in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)
	for scanner.Scan() {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		line := scanner.Bytes()
		if len(trimSpace(line)) == 0 {
			continue
		}
		s.handleLine(line, out)
	}
	return scanner.Err()
}

func trimSpace(b []byte) []byte {
	start, end := 0, len(b)
	for start < end && (b[start] == ' ' || b[start] == '\t' || b[start] == '\r' || b[start] == '\n') {
		start++
	}
	for end > start && (b[end-1] == ' ' || b[end-1] == '\t' || b[end-1] == '\r' || b[end-1] == '\n') {
		end--
	}
	return b[start:end]
}

func (s *Server) handleLine(line []byte, out io.Writer) {
	var req rpcRequest
	if err := json.Unmarshal(line, &req); err != nil {
		s.writeError(out, nil, codeParseError, "parse error")
		return
	}
	isNotification := len(req.ID) == 0 || string(req.ID) == "null"

	switch req.Method {
	case "initialize":
		s.writeResult(out, req.ID, s.initializeResult())
	case "notifications/initialized", "initialized":
		// no response to notifications
	case "ping":
		if !isNotification {
			s.writeResult(out, req.ID, map[string]any{})
		}
	case "tools/list":
		s.writeResult(out, req.ID, s.toolsListResult())
	case "tools/call":
		s.handleToolsCall(out, req)
	default:
		if !isNotification {
			s.writeError(out, req.ID, codeMethodNotFound, fmt.Sprintf("method not found: %s", req.Method))
		}
	}
}

func (s *Server) initializeResult() map[string]any {
	return map[string]any{
		"protocolVersion": protocolVersion,
		"capabilities": map[string]any{
			"tools": map[string]any{},
		},
		"serverInfo": map[string]any{
			"name":    serverName,
			"version": serverVersion,
		},
	}
}

func (s *Server) toolsListResult() map[string]any {
	list := make([]map[string]any, 0, len(s.tools))
	for _, t := range s.tools {
		list = append(list, map[string]any{
			"name":        t.Name,
			"description": t.Description,
			"inputSchema": t.InputSchema,
		})
	}
	return map[string]any{"tools": list}
}

func (s *Server) handleToolsCall(out io.Writer, req rpcRequest) {
	var params struct {
		Name      string         `json:"name"`
		Arguments map[string]any `json:"arguments"`
	}
	if len(req.Params) > 0 {
		if err := json.Unmarshal(req.Params, &params); err != nil {
			s.writeError(out, req.ID, codeInvalidParams, "invalid params: "+err.Error())
			return
		}
	}
	if params.Arguments == nil {
		params.Arguments = map[string]any{}
	}
	tool, ok := s.byName[params.Name]
	if !ok {
		s.writeResult(out, req.ID, toolError(fmt.Sprintf("unknown tool: %q", params.Name)))
		return
	}
	text, err := tool.Handler(s.store, params.Arguments)
	if err != nil {
		s.writeResult(out, req.ID, toolError(err.Error()))
		return
	}
	s.writeResult(out, req.ID, toolText(text))
}

// toolText wraps successful tool output as MCP content.
func toolText(text string) map[string]any {
	return map[string]any{
		"content": []map[string]any{{"type": "text", "text": text}},
		"isError": false,
	}
}

// toolError wraps a tool-level failure as an MCP error result.
func toolError(msg string) map[string]any {
	return map[string]any{
		"content": []map[string]any{{"type": "text", "text": "Error: " + msg}},
		"isError": true,
	}
}

func (s *Server) writeResult(out io.Writer, id json.RawMessage, result any) {
	resp := map[string]any{"jsonrpc": "2.0", "result": result}
	if len(id) > 0 {
		resp["id"] = id
	}
	s.writeJSON(out, resp)
}

func (s *Server) writeError(out io.Writer, id json.RawMessage, code int, message string) {
	resp := map[string]any{
		"jsonrpc": "2.0",
		"error":   map[string]any{"code": code, "message": message},
	}
	if len(id) > 0 {
		resp["id"] = id
	} else {
		resp["id"] = nil
	}
	s.writeJSON(out, resp)
}

func (s *Server) writeJSON(out io.Writer, v any) {
	s.writeMu.Lock()
	defer s.writeMu.Unlock()
	data, err := json.Marshal(v)
	if err != nil {
		return
	}
	data = append(data, '\n')
	_, _ = out.Write(data)
}
