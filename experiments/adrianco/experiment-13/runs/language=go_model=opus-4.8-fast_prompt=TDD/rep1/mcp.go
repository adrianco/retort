// Package main — Brazilian Soccer MCP Server.
//
// mcp.go: The Model Context Protocol server core — a JSON-RPC 2.0 dispatcher
// over the loaded Dataset. It implements the MCP lifecycle (initialize, the
// initialized notification, ping) and tool surface (tools/list, tools/call),
// translating tool handler results into MCP content blocks. The transport
// (newline-delimited JSON over stdio) lives in main.go; Dispatch is kept
// transport-agnostic and pure so it can be unit-tested directly.
package main

import (
	"encoding/json"
)

// protocolVersion is the MCP revision this server speaks.
const protocolVersion = "2024-11-05"

// serverName/serverVersion identify this server in the initialize handshake.
const (
	serverName    = "brazilian-soccer-mcp"
	serverVersion = "1.0.0"
)

// JSON-RPC standard error codes.
const (
	codeParseError     = -32700
	codeInvalidRequest = -32600
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
	codeInternalError  = -32603
)

// Server holds the loaded dataset and the tool registry, dispatching JSON-RPC
// requests against them.
type Server struct {
	ds    *Dataset
	tools map[string]Tool
	order []string // tool names in catalog order, for tools/list
}

// NewServer builds a Server over the given dataset.
func NewServer(ds *Dataset) *Server {
	s := &Server{ds: ds, tools: map[string]Tool{}}
	for _, t := range Tools() {
		s.tools[t.Name] = t
		s.order = append(s.order, t.Name)
	}
	return s
}

// rpcRequest is an incoming JSON-RPC message. ID is kept as raw JSON so it can
// be echoed back exactly (number or string), and its absence marks a
// notification.
type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// Dispatch handles one raw JSON-RPC request and returns the marshaled response.
// The boolean is false when no response should be sent (notifications), or when
// the input could not be parsed at all as a message with an id to reply to.
func (s *Server) Dispatch(raw []byte) ([]byte, bool) {
	var req rpcRequest
	if err := json.Unmarshal(raw, &req); err != nil {
		return s.errorResponse(nil, codeParseError, "parse error"), true
	}
	isNotification := len(req.ID) == 0

	switch req.Method {
	case "initialize":
		return s.resultResponse(req.ID, s.initializeResult()), true
	case "notifications/initialized", "notifications/cancelled":
		return nil, false
	case "ping":
		return s.resultResponse(req.ID, map[string]any{}), true
	case "tools/list":
		return s.resultResponse(req.ID, s.toolsListResult()), true
	case "tools/call":
		return s.handleToolCall(req)
	default:
		if isNotification {
			return nil, false
		}
		return s.errorResponse(req.ID, codeMethodNotFound, "method not found: "+req.Method), true
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
		"instructions": "Query Brazilian soccer datasets: matches (Brasileirão, Copa do Brasil, Libertadores), team records, standings, head-to-head, and FIFA player data.",
	}
}

func (s *Server) toolsListResult() map[string]any {
	tools := make([]map[string]any, 0, len(s.order))
	for _, name := range s.order {
		t := s.tools[name]
		tools = append(tools, map[string]any{
			"name":        t.Name,
			"description": t.Description,
			"inputSchema": t.InputSchema,
		})
	}
	return map[string]any{"tools": tools}
}

// toolCallParams is the params shape for tools/call.
type toolCallParams struct {
	Name      string         `json:"name"`
	Arguments map[string]any `json:"arguments"`
}

func (s *Server) handleToolCall(req rpcRequest) ([]byte, bool) {
	var p toolCallParams
	if len(req.Params) > 0 {
		if err := json.Unmarshal(req.Params, &p); err != nil {
			return s.errorResponse(req.ID, codeInvalidParams, "invalid params: "+err.Error()), true
		}
	}
	tool, ok := s.tools[p.Name]
	if !ok {
		return s.toolError(req.ID, "unknown tool: "+p.Name), true
	}
	if p.Arguments == nil {
		p.Arguments = map[string]any{}
	}
	text, err := tool.Handler(s.ds, p.Arguments)
	if err != nil {
		return s.toolError(req.ID, err.Error()), true
	}
	return s.resultResponse(req.ID, toolResult(text, false)), true
}

// toolResult builds an MCP tools/call result with a single text content block.
func toolResult(text string, isError bool) map[string]any {
	return map[string]any{
		"content": []map[string]any{
			{"type": "text", "text": text},
		},
		"isError": isError,
	}
}

// toolError returns a tools/call result flagged as an error (the MCP convention
// for tool-level failures, distinct from protocol-level JSON-RPC errors).
func (s *Server) toolError(id json.RawMessage, msg string) []byte {
	return s.resultResponse(id, toolResult("Error: "+msg, true))
}

func (s *Server) resultResponse(id json.RawMessage, result any) []byte {
	resp := map[string]any{
		"jsonrpc": "2.0",
		"result":  result,
	}
	if len(id) > 0 {
		resp["id"] = id
	}
	out, err := json.Marshal(resp)
	if err != nil {
		return s.errorResponse(id, codeInternalError, "failed to marshal result")
	}
	return out
}

func (s *Server) errorResponse(id json.RawMessage, code int, message string) []byte {
	resp := map[string]any{
		"jsonrpc": "2.0",
		"error":   rpcError{Code: code, Message: message},
	}
	if len(id) > 0 {
		resp["id"] = id
	}
	out, _ := json.Marshal(resp)
	return out
}
