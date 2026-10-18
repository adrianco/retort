// Minimal Model Context Protocol server over stdio (newline-delimited JSON-RPC 2.0).
//
// Implements initialize, ping, tools/list and tools/call. Notifications (no id)
// never receive a response. Tool failures are reported inside the result with
// isError set, as the MCP spec requires, rather than as JSON-RPC errors.

package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
)

const protocolVersion = "2024-11-05"

const (
	errParse          = -32700
	errInvalidParams  = -32602
	errMethodNotFound = -32601
)

// Tool is an MCP tool: its advertised schema and the handler behind it.
type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	run         func(args json.RawMessage) (string, error)
}

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// Server dispatches JSON-RPC requests to MCP handlers.
type Server struct {
	name    string
	version string
	tools   []Tool
}

// NewServer returns a server that advertises the given tools.
func NewServer(name, version string, tools []Tool) *Server {
	return &Server{name: name, version: version, tools: tools}
}

// Serve reads requests from in and writes responses to out until in is closed.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	reader := bufio.NewReaderSize(in, 1<<16)
	enc := json.NewEncoder(out)
	for {
		line, readErr := reader.ReadBytes('\n')
		if trimmed := bytes.TrimSpace(line); len(trimmed) > 0 {
			if resp := s.handle(trimmed); resp != nil {
				if err := enc.Encode(resp); err != nil {
					return err
				}
			}
		}
		if readErr == io.EOF {
			return nil
		}
		if readErr != nil {
			return readErr
		}
	}
}

// handle processes one line. It returns nil when no response is due.
func (s *Server) handle(line []byte) *rpcResponse {
	var req rpcRequest
	if err := json.Unmarshal(line, &req); err != nil {
		return &rpcResponse{
			JSONRPC: "2.0",
			ID:      json.RawMessage("null"),
			Error:   &rpcError{Code: errParse, Message: "parse error: " + err.Error()},
		}
	}
	if len(req.ID) == 0 {
		return nil // notification
	}

	result, rpcErr := s.dispatch(req)
	resp := &rpcResponse{JSONRPC: "2.0", ID: req.ID}
	if rpcErr != nil {
		resp.Error = rpcErr
	} else {
		resp.Result = result
	}
	return resp
}

func (s *Server) dispatch(req rpcRequest) (any, *rpcError) {
	switch req.Method {
	case "initialize":
		return map[string]any{
			"protocolVersion": protocolVersion,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": s.name, "version": s.version},
		}, nil
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		return map[string]any{"tools": s.tools}, nil
	case "tools/call":
		return s.callTool(req.Params)
	default:
		return nil, &rpcError{Code: errMethodNotFound, Message: "method not found: " + req.Method}
	}
}

func (s *Server) callTool(params json.RawMessage) (any, *rpcError) {
	var p struct {
		Name      string          `json:"name"`
		Arguments json.RawMessage `json:"arguments"`
	}
	if err := json.Unmarshal(params, &p); err != nil {
		return nil, &rpcError{Code: errInvalidParams, Message: "invalid params: " + err.Error()}
	}
	for _, t := range s.tools {
		if t.Name != p.Name {
			continue
		}
		text, err := t.run(p.Arguments)
		if err != nil {
			return toolResult(err.Error(), true), nil
		}
		return toolResult(text, false), nil
	}
	return nil, &rpcError{Code: errInvalidParams, Message: "unknown tool: " + p.Name}
}

func toolResult(text string, isError bool) map[string]any {
	return map[string]any{
		"content": []map[string]any{{"type": "text", "text": text}},
		"isError": isError,
	}
}

// decodeArgs unmarshals tool arguments into T. Missing or null arguments give
// the zero value, so every field is optional by default.
func decodeArgs[T any](raw json.RawMessage) (T, error) {
	var v T
	if len(raw) == 0 || string(raw) == "null" {
		return v, nil
	}
	if err := json.Unmarshal(raw, &v); err != nil {
		return v, fmt.Errorf("invalid arguments: %w", err)
	}
	return v, nil
}
