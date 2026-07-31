// Package mcp implements the subset of the Model Context Protocol needed by a
// stdio tool server: JSON-RPC 2.0 framing over newline delimited JSON, the
// initialize handshake, tools/list and tools/call.
//
// Only the standard library is used, so the server has no external
// dependencies and starts instantly.
package mcp

import "encoding/json"

// ProtocolVersion is the MCP revision this server implements.
const ProtocolVersion = "2025-06-18"

// JSON-RPC 2.0 error codes used by this server.
const (
	CodeParseError     = -32700
	CodeInvalidRequest = -32600
	CodeMethodNotFound = -32601
	CodeInvalidParams  = -32602
	CodeInternalError  = -32603
)

// Request is an incoming JSON-RPC request or notification. A notification has
// no ID and must not be answered.
type Request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// IsNotification reports whether no response should be sent.
func (r *Request) IsNotification() bool { return len(r.ID) == 0 || string(r.ID) == "null" }

// Response is an outgoing JSON-RPC response.
type Response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
}

// RPCError is a JSON-RPC error object.
type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

func (e *RPCError) Error() string { return e.Message }

// Errorf builds an RPCError.
func Errorf(code int, msg string) *RPCError { return &RPCError{Code: code, Message: msg} }

// Implementation identifies a party in the handshake.
type Implementation struct {
	Name    string `json:"name"`
	Title   string `json:"title,omitempty"`
	Version string `json:"version"`
}

// InitializeResult is returned from the initialize handshake.
type InitializeResult struct {
	ProtocolVersion string         `json:"protocolVersion"`
	Capabilities    Capabilities   `json:"capabilities"`
	ServerInfo      Implementation `json:"serverInfo"`
	Instructions    string         `json:"instructions,omitempty"`
}

// Capabilities advertises what the server supports.
type Capabilities struct {
	Tools *ToolsCapability `json:"tools,omitempty"`
}

// ToolsCapability advertises tool support.
type ToolsCapability struct {
	ListChanged bool `json:"listChanged"`
}

// Tool is a tool advertised by tools/list.
type Tool struct {
	Name        string `json:"name"`
	Title       string `json:"title,omitempty"`
	Description string `json:"description"`
	InputSchema Schema `json:"inputSchema"`
}

// Schema is a minimal JSON Schema object description.
type Schema struct {
	Type       string           `json:"type"`
	Properties map[string]*Prop `json:"properties,omitempty"`
	Required   []string         `json:"required,omitempty"`
}

// Prop describes one input property.
type Prop struct {
	Type        string   `json:"type"`
	Description string   `json:"description,omitempty"`
	Enum        []string `json:"enum,omitempty"`
	Default     any      `json:"default,omitempty"`
}

// ListToolsResult is the tools/list response.
type ListToolsResult struct {
	Tools []Tool `json:"tools"`
}

// Content is a single content block in a tool result.
type Content struct {
	Type string `json:"type"`
	Text string `json:"text,omitempty"`
}

// TextContent builds a text content block.
func TextContent(s string) Content { return Content{Type: "text", Text: s} }

// CallToolResult is the tools/call response.
type CallToolResult struct {
	Content           []Content `json:"content"`
	StructuredContent any       `json:"structuredContent,omitempty"`
	IsError           bool      `json:"isError,omitempty"`
}

// CallToolParams are the tools/call arguments.
type CallToolParams struct {
	Name      string         `json:"name"`
	Arguments map[string]any `json:"arguments"`
}
