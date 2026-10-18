// Package mcp implements a minimal Model Context Protocol server over
// newline-delimited JSON-RPC 2.0 on stdio. It exposes the soccer queries as tools.
package mcp

import (
	"bufio"
	"bytes"
	"encoding/json"
	"io"
)

const protocolVersion = "2024-11-05"

// JSON-RPC error codes.
const (
	codeParseError     = -32700
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
)

// RPCError is a JSON-RPC protocol error.
type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
}

// Tool describes one callable tool and how to run it.
type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	handler     func(args json.RawMessage) (string, error)
}

// Server dispatches JSON-RPC requests to registered tools.
type Server struct {
	name    string
	version string
	tools   []Tool
	byName  map[string]Tool
}

func newServer(name, version string) *Server {
	return &Server{name: name, version: version, byName: make(map[string]Tool)}
}

func (s *Server) register(t Tool) {
	s.tools = append(s.tools, t)
	s.byName[t.Name] = t
}

// Serve reads newline-delimited requests from in and writes responses to out
// until in is closed. Notifications (requests without an id) get no response.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 1<<20), 16<<20)
	enc := json.NewEncoder(out)
	for scanner.Scan() {
		line := bytes.TrimSpace(scanner.Bytes())
		if len(line) == 0 {
			continue
		}
		resp, ok := s.handle(line)
		if !ok {
			continue
		}
		if err := enc.Encode(resp); err != nil {
			return err
		}
	}
	return scanner.Err()
}

// handle processes one raw message. It returns false when no reply is due.
func (s *Server) handle(line []byte) (response, bool) {
	var req request
	if err := json.Unmarshal(line, &req); err != nil {
		return response{JSONRPC: "2.0", ID: json.RawMessage("null"),
			Error: &RPCError{Code: codeParseError, Message: "parse error: " + err.Error()}}, true
	}
	if len(req.ID) == 0 {
		return response{}, false // notification, e.g. notifications/initialized
	}

	resp := response{JSONRPC: "2.0", ID: req.ID}
	switch req.Method {
	case "initialize":
		resp.Result = map[string]any{
			"protocolVersion": protocolVersion,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": s.name, "version": s.version},
		}
	case "ping":
		resp.Result = map[string]any{}
	case "tools/list":
		resp.Result = map[string]any{"tools": s.tools}
	case "tools/call":
		result, rpcErr := s.callTool(req.Params)
		resp.Result, resp.Error = result, rpcErr
	default:
		resp.Error = &RPCError{Code: codeMethodNotFound, Message: "method not found: " + req.Method}
	}
	return resp, true
}

type callParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

func (s *Server) callTool(raw json.RawMessage) (any, *RPCError) {
	var p callParams
	if err := json.Unmarshal(raw, &p); err != nil {
		return nil, &RPCError{Code: codeInvalidParams, Message: "invalid tools/call params: " + err.Error()}
	}
	tool, ok := s.byName[p.Name]
	if !ok {
		return nil, &RPCError{Code: codeInvalidParams, Message: "unknown tool: " + p.Name}
	}
	text, err := tool.handler(p.Arguments)
	if err != nil {
		// Tool failures are reported in-band so the model can correct its arguments.
		return toolResult("Error: "+err.Error(), true), nil
	}
	return toolResult(text, false), nil
}

func toolResult(text string, isError bool) map[string]any {
	return map[string]any{
		"content": []map[string]string{{"type": "text", "text": text}},
		"isError": isError,
	}
}
