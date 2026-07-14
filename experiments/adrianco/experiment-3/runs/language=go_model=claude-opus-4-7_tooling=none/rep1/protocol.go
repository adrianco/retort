// Minimal MCP (Model Context Protocol) implementation: JSON-RPC 2.0 over
// stdio, supporting initialize, tools/list, tools/call and ping.
package main

import "encoding/json"

const (
	protocolVersion = "2025-06-18"
	serverName      = "brazilian-soccer-mcp"
	serverVersion   = "1.0.0"
)

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// isNotification reports whether the request carries no id (and so expects no
// response).
func (r *rpcRequest) isNotification() bool { return len(r.ID) == 0 }

// handleRequest processes a single JSON-RPC request and returns the response,
// or nil when the request is a notification.
func handleRequest(db *DB, req *rpcRequest) *rpcResponse {
	resp := &rpcResponse{JSONRPC: "2.0", ID: req.ID}
	switch req.Method {
	case "initialize":
		resp.Result = initializeResult(req.Params)
	case "notifications/initialized", "notifications/cancelled":
		return nil
	case "ping":
		resp.Result = map[string]any{}
	case "tools/list":
		resp.Result = map[string]any{"tools": toolSchemas()}
	case "tools/call":
		resp.Result = handleToolCall(db, req.Params)
	default:
		if req.isNotification() {
			return nil
		}
		resp.Error = &rpcError{Code: -32601, Message: "method not found: " + req.Method}
	}
	if req.isNotification() {
		return nil
	}
	return resp
}

func initializeResult(params json.RawMessage) map[string]any {
	version := protocolVersion
	if len(params) > 0 {
		var p struct {
			ProtocolVersion string `json:"protocolVersion"`
		}
		if json.Unmarshal(params, &p) == nil && p.ProtocolVersion != "" {
			version = p.ProtocolVersion
		}
	}
	return map[string]any{
		"protocolVersion": version,
		"capabilities":    map[string]any{"tools": map[string]any{}},
		"serverInfo":      map[string]any{"name": serverName, "version": serverVersion},
	}
}

// handleToolCall dispatches a tools/call request to the named tool and wraps
// the result in MCP content format.
func handleToolCall(db *DB, params json.RawMessage) map[string]any {
	var p struct {
		Name      string         `json:"name"`
		Arguments map[string]any `json:"arguments"`
	}
	if err := json.Unmarshal(params, &p); err != nil {
		return toolErrorResult("invalid tools/call parameters: " + err.Error())
	}
	tool, ok := toolByName[p.Name]
	if !ok {
		return toolErrorResult("unknown tool: " + p.Name)
	}
	text, err := tool.Handler(db, p.Arguments)
	if err != nil {
		return toolErrorResult(err.Error())
	}
	return map[string]any{
		"content": []map[string]any{{"type": "text", "text": text}},
	}
}

func toolErrorResult(msg string) map[string]any {
	return map[string]any{
		"content": []map[string]any{{"type": "text", "text": msg}},
		"isError": true,
	}
}
