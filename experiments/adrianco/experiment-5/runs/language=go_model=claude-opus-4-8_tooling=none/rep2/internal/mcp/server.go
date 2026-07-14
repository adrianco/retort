// Package mcp implements a minimal Model Context Protocol server over a stdio
// JSON-RPC 2.0 transport. It is deliberately dependency-free: messages are
// newline-delimited JSON objects, which is the framing used by the MCP stdio
// transport.
//
// Only the subset of the protocol required to expose tools is implemented:
// initialize, notifications/initialized, tools/list and tools/call. That is
// sufficient for an MCP client (e.g. an LLM host) to discover and invoke the
// Brazilian-soccer query tools.
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sort"
)

// ProtocolVersion is the MCP revision this server speaks.
const ProtocolVersion = "2024-11-05"

// ToolHandler executes a tool call. The raw JSON arguments are passed through;
// the handler returns the text content of the result or an error.
type ToolHandler func(args json.RawMessage) (string, error)

// Tool is a registered, callable tool.
type Tool struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     ToolHandler
}

// Server is an MCP stdio server.
type Server struct {
	name    string
	version string
	tools   map[string]Tool
	order   []string
}

// NewServer creates a server advertising the given name and version.
func NewServer(name, version string) *Server {
	return &Server{name: name, version: version, tools: map[string]Tool{}}
}

// AddTool registers a tool. Re-registering a name overwrites it.
func (s *Server) AddTool(t Tool) {
	if _, exists := s.tools[t.Name]; !exists {
		s.order = append(s.order, t.Name)
	}
	s.tools[t.Name] = t
}

// --- JSON-RPC wire types ---

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

// JSON-RPC standard error codes.
const (
	codeParse          = -32700
	codeInvalidRequest = -32600
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
	codeInternal       = -32603
)

// Serve runs the read/dispatch/write loop until in reaches EOF.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	r := bufio.NewReaderSize(in, 1<<20)
	w := bufio.NewWriter(out)
	enc := json.NewEncoder(w)

	for {
		line, err := readMessage(r)
		if err == io.EOF {
			return nil
		}
		if err != nil {
			return err
		}
		if len(line) == 0 {
			continue
		}

		resp, isNotification := s.handle(line)
		if isNotification {
			continue // notifications get no response
		}
		if err := enc.Encode(resp); err != nil {
			return err
		}
		if err := w.Flush(); err != nil {
			return err
		}
	}
}

// readMessage reads a single newline-delimited JSON message, skipping blank
// lines.
func readMessage(r *bufio.Reader) ([]byte, error) {
	for {
		line, err := r.ReadBytes('\n')
		if len(line) > 0 {
			trimmed := trimSpace(line)
			if len(trimmed) > 0 {
				return trimmed, nil
			}
		}
		if err != nil {
			return nil, err
		}
	}
}

func trimSpace(b []byte) []byte {
	start := 0
	for start < len(b) && isSpace(b[start]) {
		start++
	}
	end := len(b)
	for end > start && isSpace(b[end-1]) {
		end--
	}
	return b[start:end]
}

func isSpace(c byte) bool { return c == ' ' || c == '\t' || c == '\r' || c == '\n' }

// handle dispatches one request and returns the response (or notes that the
// message was a notification needing no reply).
func (s *Server) handle(raw []byte) (response, bool) {
	var req request
	if err := json.Unmarshal(raw, &req); err != nil {
		return errResp(nil, codeParse, "parse error: "+err.Error()), false
	}
	if req.JSONRPC != "2.0" && req.JSONRPC != "" {
		return errResp(req.ID, codeInvalidRequest, "unsupported jsonrpc version"), false
	}

	isNotification := len(req.ID) == 0

	switch req.Method {
	case "initialize":
		return okResp(req.ID, s.initializeResult()), isNotification
	case "notifications/initialized", "initialized", "notifications/cancelled":
		return response{}, true
	case "ping":
		return okResp(req.ID, map[string]any{}), isNotification
	case "tools/list":
		return okResp(req.ID, s.toolsListResult()), isNotification
	case "tools/call":
		return s.callTool(req), isNotification
	default:
		if isNotification {
			return response{}, true
		}
		return errResp(req.ID, codeMethodNotFound, "unknown method: "+req.Method), false
	}
}

func (s *Server) initializeResult() map[string]any {
	return map[string]any{
		"protocolVersion": ProtocolVersion,
		"capabilities": map[string]any{
			"tools": map[string]any{},
		},
		"serverInfo": map[string]any{
			"name":    s.name,
			"version": s.version,
		},
	}
}

type toolDescriptor struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
}

func (s *Server) toolsListResult() map[string]any {
	names := append([]string(nil), s.order...)
	sort.Strings(names)
	descs := make([]toolDescriptor, 0, len(names))
	for _, n := range names {
		t := s.tools[n]
		schema := t.InputSchema
		if schema == nil {
			schema = map[string]any{"type": "object"}
		}
		descs = append(descs, toolDescriptor{
			Name:        t.Name,
			Description: t.Description,
			InputSchema: schema,
		})
	}
	return map[string]any{"tools": descs}
}

type callParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

func (s *Server) callTool(req request) response {
	var p callParams
	if err := json.Unmarshal(req.Params, &p); err != nil {
		return errResp(req.ID, codeInvalidParams, "invalid params: "+err.Error())
	}
	tool, ok := s.tools[p.Name]
	if !ok {
		return errResp(req.ID, codeMethodNotFound, "unknown tool: "+p.Name)
	}
	args := p.Arguments
	if len(args) == 0 {
		args = json.RawMessage(`{}`)
	}
	text, err := tool.Handler(args)
	if err != nil {
		// Tool errors are reported as a successful call carrying isError, per
		// the MCP convention, so the model can read the message.
		return okResp(req.ID, toolResult(fmt.Sprintf("Error: %v", err), true))
	}
	return okResp(req.ID, toolResult(text, false))
}

func toolResult(text string, isError bool) map[string]any {
	return map[string]any{
		"content": []map[string]any{
			{"type": "text", "text": text},
		},
		"isError": isError,
	}
}

func okResp(id json.RawMessage, result any) response {
	return response{JSONRPC: "2.0", ID: id, Result: result}
}

func errResp(id json.RawMessage, code int, msg string) response {
	return response{JSONRPC: "2.0", ID: id, Error: &rpcError{Code: code, Message: msg}}
}
