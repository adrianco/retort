// Minimal Model Context Protocol server over stdio (JSON-RPC 2.0, newline-delimited).
//
// Implements the subset needed for tool use: initialize, notifications,
// ping, tools/list and tools/call.

package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
)

const protocolVersion = "2024-11-05"

// Request is an incoming JSON-RPC message. A nil ID marks a notification.
type Request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// Response is an outgoing JSON-RPC message.
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
}

const (
	errParse          = -32700
	errInvalidRequest = -32600
	errMethodNotFound = -32601
	errInvalidParams  = -32602
)

// Tool describes a tool for tools/list.
type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
}

// Server dispatches requests to a set of tools.
type Server struct {
	Name    string
	Version string
	Tools   []Tool
	// Call runs a tool and returns its text output. An error is reported to
	// the client as a tool error result rather than a protocol error.
	Call func(name string, args map[string]any) (string, error)
}

// Serve reads newline-delimited JSON-RPC from in and writes responses to out
// until in is exhausted.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	sc := bufio.NewScanner(in)
	sc.Buffer(make([]byte, 1024*1024), 16*1024*1024)
	enc := json.NewEncoder(out)

	for sc.Scan() {
		line := sc.Bytes()
		if len(line) == 0 {
			continue
		}
		resp := s.handleLine(line)
		if resp == nil {
			continue
		}
		if err := enc.Encode(resp); err != nil {
			return fmt.Errorf("write response: %w", err)
		}
	}
	return sc.Err()
}

// handleLine parses one message and returns the response, or nil for notifications.
func (s *Server) handleLine(line []byte) *Response {
	var req Request
	if err := json.Unmarshal(line, &req); err != nil {
		return &Response{JSONRPC: "2.0", ID: json.RawMessage("null"),
			Error: &RPCError{Code: errParse, Message: "parse error: " + err.Error()}}
	}
	if req.JSONRPC != "2.0" || req.Method == "" {
		return &Response{JSONRPC: "2.0", ID: nullIfEmpty(req.ID),
			Error: &RPCError{Code: errInvalidRequest, Message: "invalid request"}}
	}
	isNotification := len(req.ID) == 0
	if isNotification {
		// Notifications such as notifications/initialized get no reply.
		return nil
	}
	return s.dispatch(req)
}

func nullIfEmpty(id json.RawMessage) json.RawMessage {
	if len(id) == 0 {
		return json.RawMessage("null")
	}
	return id
}

func (s *Server) dispatch(req Request) *Response {
	ok := func(result any) *Response {
		return &Response{JSONRPC: "2.0", ID: req.ID, Result: result}
	}
	fail := func(code int, msg string) *Response {
		return &Response{JSONRPC: "2.0", ID: req.ID, Error: &RPCError{Code: code, Message: msg}}
	}

	switch req.Method {
	case "initialize":
		return ok(map[string]any{
			"protocolVersion": protocolVersion,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": s.Name, "version": s.Version},
		})
	case "ping":
		return ok(map[string]any{})
	case "tools/list":
		tools := s.Tools
		if tools == nil {
			tools = []Tool{}
		}
		return ok(map[string]any{"tools": tools})
	case "tools/call":
		var p struct {
			Name      string         `json:"name"`
			Arguments map[string]any `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil || p.Name == "" {
			return fail(errInvalidParams, "tools/call requires a tool name")
		}
		if p.Arguments == nil {
			p.Arguments = map[string]any{}
		}
		text, err := s.Call(p.Name, p.Arguments)
		if err != nil {
			return ok(toolResult(err.Error(), true))
		}
		return ok(toolResult(text, false))
	default:
		return fail(errMethodNotFound, "method not found: "+req.Method)
	}
}

func toolResult(text string, isError bool) map[string]any {
	return map[string]any{
		"content": []map[string]any{{"type": "text", "text": text}},
		"isError": isError,
	}
}
