// Package mcp implements a minimal Model Context Protocol (MCP) server over the
// stdio transport for the Brazilian soccer knowledge graph.
//
// Context
// -------
// The MCP stdio transport exchanges newline-delimited JSON-RPC 2.0 messages on
// stdin/stdout. This file defines the JSON-RPC envelope types and the MCP
// content/tool types used by the server. The server itself (server.go) handles
// the initialize / tools.list / tools.call methods; the concrete tools and
// their dispatch to the soccer query layer live in tools.go.
package mcp

import "encoding/json"

// ProtocolVersion is the MCP protocol revision this server implements.
const ProtocolVersion = "2024-11-05"

// Request is an incoming JSON-RPC 2.0 request or notification. A notification
// has no ID and expects no response.
type Request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// IsNotification reports whether the request is a notification (no ID).
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
	codeParseError     = -32700
	codeInvalidRequest = -32600
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
	codeInternalError  = -32603
)

// InitializeResult is returned from the initialize handshake.
type InitializeResult struct {
	ProtocolVersion string       `json:"protocolVersion"`
	Capabilities    Capabilities `json:"capabilities"`
	ServerInfo      ServerInfo   `json:"serverInfo"`
}

// Capabilities advertises which MCP features the server supports.
type Capabilities struct {
	Tools *ToolsCapability `json:"tools,omitempty"`
}

// ToolsCapability indicates tool support (and whether the list can change).
type ToolsCapability struct {
	ListChanged bool `json:"listChanged"`
}

// ServerInfo identifies the server to the client.
type ServerInfo struct {
	Name    string `json:"name"`
	Version string `json:"version"`
}

// Tool describes a callable tool exposed via tools/list.
type Tool struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	InputSchema json.RawMessage `json:"inputSchema"`
}

// ToolsListResult is the result of tools/list.
type ToolsListResult struct {
	Tools []Tool `json:"tools"`
}

// CallToolParams are the params of a tools/call request.
type CallToolParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

// CallToolResult is the result of a tools/call request.
type CallToolResult struct {
	Content []Content `json:"content"`
	IsError bool      `json:"isError,omitempty"`
}

// Content is a single content block returned by a tool. Only text is used here.
type Content struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

// textResult builds a non-error CallToolResult from a text body.
func textResult(text string) CallToolResult {
	return CallToolResult{Content: []Content{{Type: "text", Text: text}}}
}

// errorResult builds an error CallToolResult from a text body.
func errorResult(text string) CallToolResult {
	return CallToolResult{Content: []Content{{Type: "text", Text: text}}, IsError: true}
}
