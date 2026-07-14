// Package mcp is a small, dependency-free implementation of the Model Context
// Protocol server side over the stdio transport. Messages are newline-delimited
// JSON-RPC 2.0 objects (one per line, no embedded newlines), as required by the
// MCP stdio transport. The package implements the handshake (initialize /
// notifications/initialized), tool discovery (tools/list) and invocation
// (tools/call), plus ping; everything else returns "method not found".
//
// It is deliberately generic: register tools with AddTool and call Serve. The
// Brazilian-soccer tools are wired up in package main.
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync"
)

// ProtocolVersion is the MCP revision this server advertises.
const ProtocolVersion = "2024-11-05"

// ToolHandler executes a tool call. arguments is the raw JSON of the call's
// "arguments" object; the returned string is sent back as text content.
type ToolHandler func(arguments json.RawMessage) (string, error)

// Tool is a registered, callable tool.
type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	handler     ToolHandler
}

// Server is an MCP server bound to an input/output stream.
type Server struct {
	name    string
	version string

	mu    sync.Mutex
	tools map[string]*Tool
	order []string

	out *json.Encoder
	w   *bufio.Writer
}

// NewServer creates a server identified by name/version.
func NewServer(name, version string) *Server {
	return &Server{name: name, version: version, tools: map[string]*Tool{}}
}

// AddTool registers a tool. inputSchema must be a JSON-Schema object describing
// the tool's arguments.
func (s *Server) AddTool(name, description string, inputSchema map[string]any, h ToolHandler) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.tools[name]; !exists {
		s.order = append(s.order, name)
	}
	s.tools[name] = &Tool{Name: name, Description: description, InputSchema: inputSchema, handler: h}
}

// --- JSON-RPC wire types ----------------------------------------------------

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
	Data    any    `json:"data,omitempty"`
}

// JSON-RPC error codes.
const (
	codeParseError     = -32700
	codeInvalidRequest = -32600
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
	codeInternalError  = -32603
)

// Serve reads JSON-RPC messages from r until EOF, dispatching each. Responses
// are written to w. It is safe to use os.Stdin/os.Stdout as r/w.
func (s *Server) Serve(r io.Reader, w io.Writer) error {
	bw := bufio.NewWriter(w)
	s.w = bw
	s.out = json.NewEncoder(bw)
	defer bw.Flush()

	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 0, 64*1024), 16*1024*1024) // allow large messages

	for sc.Scan() {
		line := sc.Bytes()
		if len(trimSpace(line)) == 0 {
			continue
		}
		s.handleLine(line)
		bw.Flush()
	}
	return sc.Err()
}

// handleLine parses and dispatches a single JSON-RPC message.
func (s *Server) handleLine(line []byte) {
	var req rpcRequest
	if err := json.Unmarshal(line, &req); err != nil {
		s.writeError(nil, codeParseError, "parse error: "+err.Error())
		return
	}
	if req.JSONRPC != "2.0" {
		// Be lenient on the version field but require a method.
		if req.Method == "" {
			s.writeError(req.ID, codeInvalidRequest, "invalid request")
			return
		}
	}

	isNotification := len(req.ID) == 0 || string(req.ID) == "null"

	switch req.Method {
	case "initialize":
		s.writeResult(req.ID, s.initializeResult())
	case "notifications/initialized", "initialized":
		// notification: no response
	case "ping":
		s.writeResult(req.ID, map[string]any{})
	case "tools/list":
		s.writeResult(req.ID, s.listToolsResult())
	case "tools/call":
		s.handleToolCall(req, isNotification)
	default:
		if !isNotification {
			s.writeError(req.ID, codeMethodNotFound, "method not found: "+req.Method)
		}
	}
}

func (s *Server) initializeResult() map[string]any {
	return map[string]any{
		"protocolVersion": ProtocolVersion,
		"capabilities": map[string]any{
			"tools": map[string]any{"listChanged": false},
		},
		"serverInfo": map[string]any{
			"name":    s.name,
			"version": s.version,
		},
	}
}

func (s *Server) listToolsResult() map[string]any {
	s.mu.Lock()
	defer s.mu.Unlock()
	tools := make([]Tool, 0, len(s.order))
	for _, name := range s.order {
		tools = append(tools, *s.tools[name])
	}
	return map[string]any{"tools": tools}
}

// callParams is the params object of a tools/call request.
type callParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

func (s *Server) handleToolCall(req rpcRequest, isNotification bool) {
	var p callParams
	if len(req.Params) > 0 {
		if err := json.Unmarshal(req.Params, &p); err != nil {
			s.writeError(req.ID, codeInvalidParams, "invalid params: "+err.Error())
			return
		}
	}
	s.mu.Lock()
	tool, ok := s.tools[p.Name]
	s.mu.Unlock()
	if !ok {
		s.writeError(req.ID, codeInvalidParams, "unknown tool: "+p.Name)
		return
	}

	text, err := s.safeInvoke(tool, p.Arguments)
	if isNotification {
		return
	}
	if err != nil {
		// Per MCP, tool execution errors are reported in the result with
		// isError=true rather than as protocol errors.
		s.writeResult(req.ID, toolResult(fmt.Sprintf("Error: %v", err), true))
		return
	}
	s.writeResult(req.ID, toolResult(text, false))
}

// safeInvoke runs a handler, converting panics into errors so one bad tool call
// can never take the server down.
func (s *Server) safeInvoke(tool *Tool, args json.RawMessage) (text string, err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("internal tool panic: %v", r)
		}
	}()
	return tool.handler(args)
}

func toolResult(text string, isError bool) map[string]any {
	return map[string]any{
		"content": []map[string]any{
			{"type": "text", "text": text},
		},
		"isError": isError,
	}
}

func (s *Server) writeResult(id json.RawMessage, result any) {
	s.write(rpcResponse{JSONRPC: "2.0", ID: id, Result: result})
}

func (s *Server) writeError(id json.RawMessage, code int, msg string) {
	s.write(rpcResponse{JSONRPC: "2.0", ID: id, Error: &rpcError{Code: code, Message: msg}})
}

func (s *Server) write(resp rpcResponse) {
	if s.out == nil {
		return
	}
	// json.Encoder.Encode writes a trailing newline, which is exactly the
	// framing the stdio transport expects.
	_ = s.out.Encode(resp)
}

func trimSpace(b []byte) []byte {
	i, j := 0, len(b)
	for i < j && isSpace(b[i]) {
		i++
	}
	for j > i && isSpace(b[j-1]) {
		j--
	}
	return b[i:j]
}

func isSpace(c byte) bool {
	return c == ' ' || c == '\t' || c == '\r' || c == '\n'
}
