// Package mcpserver implements a minimal Model Context Protocol (MCP) server
// over stdio for the Brazilian Soccer dataset.
//
// Context:
//   - Speaks JSON-RPC 2.0 framed as newline-delimited JSON, which is the MCP
//     stdio transport. No third-party dependencies are used.
//   - Handles the lifecycle methods (initialize, notifications/initialized,
//     ping) and the tool methods (tools/list, tools/call).
//   - Tools wrap the soccer.Store query engine and return text content shaped
//     like the answer formats in TASK.md.
package mcpserver

import "encoding/json"

// protocolVersion is the MCP revision this server advertises.
const protocolVersion = "2024-11-05"

// rpcRequest is an incoming JSON-RPC request or notification. A notification has
// no ID and expects no response.
type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

func (r rpcRequest) isNotification() bool { return len(r.ID) == 0 }

// rpcResponse is an outgoing JSON-RPC response.
type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  interface{}     `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
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

// --- MCP payload shapes ---------------------------------------------------

type initializeResult struct {
	ProtocolVersion string       `json:"protocolVersion"`
	Capabilities    capabilities `json:"capabilities"`
	ServerInfo      serverInfo   `json:"serverInfo"`
	Instructions    string       `json:"instructions,omitempty"`
}

type capabilities struct {
	Tools *toolsCapability `json:"tools,omitempty"`
}

type toolsCapability struct {
	ListChanged bool `json:"listChanged"`
}

type serverInfo struct {
	Name    string `json:"name"`
	Version string `json:"version"`
}

// tool is one entry in tools/list.
type tool struct {
	Name        string      `json:"name"`
	Description string      `json:"description"`
	InputSchema interface{} `json:"inputSchema"`
}

type toolsListResult struct {
	Tools []tool `json:"tools"`
}

type callToolParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

type textContent struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type callToolResult struct {
	Content []textContent `json:"content"`
	IsError bool          `json:"isError,omitempty"`
}
