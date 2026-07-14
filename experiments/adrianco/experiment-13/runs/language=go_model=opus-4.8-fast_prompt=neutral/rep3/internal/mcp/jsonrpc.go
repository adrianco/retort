// Package mcp implements a minimal Model Context Protocol (MCP) server over a
// stdio JSON-RPC 2.0 transport, dependency-free (standard library only).
//
// jsonrpc.go defines the wire types and the newline-delimited transport used by
// MCP stdio servers: each JSON-RPC message occupies exactly one line on stdin
// and one line on stdout; diagnostics go to stderr.
package mcp

import "encoding/json"

// JSON-RPC 2.0 error codes (subset) used by this server.
const (
	codeParseError     = -32700
	codeInvalidRequest = -32600
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
	codeInternalError  = -32603
)

// request is an incoming JSON-RPC message. A nil ID denotes a notification.
type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

func (r request) isNotification() bool { return len(r.ID) == 0 }

// response is an outgoing JSON-RPC message.
type response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  interface{}     `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

// rpcError is a JSON-RPC error object.
type rpcError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

func (e *rpcError) Error() string { return e.Message }

func newError(code int, msg string) *rpcError { return &rpcError{Code: code, Message: msg} }
