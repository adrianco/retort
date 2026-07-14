// Package mcp implements a minimal Model Context Protocol server over JSON-RPC
// 2.0 for the Brazilian soccer knowledge graph. It speaks the MCP methods an
// LLM client needs -- initialize, tools/list, tools/call -- and exposes the
// soccer domain as a set of well-described tools. The transport (stdio) lives
// in package main; this package is transport-agnostic: it turns a request's
// bytes into a response's bytes.
//
// This file defines the JSON-RPC wire types and standard error codes.
package mcp

import "encoding/json"

const protocolVersion = "2024-11-05"

// Standard JSON-RPC 2.0 error codes.
const (
	codeParseError     = -32700
	codeInvalidRequest = -32600
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
	codeInternalError  = -32603
)

type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// Tool content blocks returned by tools/call.
type textContent struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type toolResult struct {
	Content []textContent `json:"content"`
	IsError bool          `json:"isError,omitempty"`
}

// toolDescriptor is the public, advertised description of a tool.
type toolDescriptor struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
}
