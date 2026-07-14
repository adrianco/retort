// Package mcp implements a minimal Model Context Protocol server over the
// stdio transport using only the Go standard library.
//
// The transport is newline-delimited JSON-RPC 2.0: each request and response is
// a single JSON object on its own line. Only the subset of MCP needed for a
// tool server is implemented: initialize, notifications/initialized, tools/list
// and tools/call. The soccer query engine is wired in via package soccer.
package mcp

import "encoding/json"

// ProtocolVersion is the MCP revision this server speaks.
const ProtocolVersion = "2024-11-05"

// Request is an incoming JSON-RPC 2.0 request or notification. A notification
// has no ID.
type Request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// IsNotification reports whether the request lacks an ID (and so expects no
// response).
func (r Request) IsNotification() bool { return len(r.ID) == 0 }

// Response is an outgoing JSON-RPC 2.0 response.
type Response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  interface{}     `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
}

// RPCError is a JSON-RPC 2.0 error object.
type RPCError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

// Standard JSON-RPC error codes.
const (
	CodeParseError     = -32700
	CodeInvalidRequest = -32600
	CodeMethodNotFound = -32601
	CodeInvalidParams  = -32602
	CodeInternalError  = -32603
)

// Tool describes a tool advertised via tools/list.
type Tool struct {
	Name        string      `json:"name"`
	Description string      `json:"description"`
	InputSchema interface{} `json:"inputSchema"`
}

// ToolContent is one content block in a tools/call result.
type ToolContent struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

// ToolResult is the payload of a tools/call response.
type ToolResult struct {
	Content []ToolContent `json:"content"`
	IsError bool          `json:"isError,omitempty"`
}

// textResult wraps a plain string as a single-block tool result.
func textResult(s string) ToolResult {
	return ToolResult{Content: []ToolContent{{Type: "text", Text: s}}}
}

// errorResult wraps a message as a tool-level error result.
func errorResult(s string) ToolResult {
	return ToolResult{Content: []ToolContent{{Type: "text", Text: s}}, IsError: true}
}
