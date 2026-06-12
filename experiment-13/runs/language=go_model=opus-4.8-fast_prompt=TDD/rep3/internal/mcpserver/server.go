// Context: Brazilian Soccer MCP Server.
// File: server.go
// Purpose: Minimal MCP server over a JSON-RPC 2.0 stdio transport. Reads
// newline-delimited JSON-RPC requests, dispatches initialize / tools/list /
// tools/call (plus ping and the initialized notification), and writes
// newline-delimited responses. Tool failures are reported as MCP tool errors
// (result.isError) rather than protocol errors, per the MCP spec.
package mcpserver

import (
	"bufio"
	"encoding/json"
	"io"
)

// protocolVersion is the MCP protocol revision this server implements.
const protocolVersion = "2024-11-05"

const (
	codeParseError    = -32700
	codeInvalidReq    = -32600
	codeMethodNotFnd  = -32601
	codeInvalidParams = -32602
	codeInternal      = -32603
)

// Server wires the JSON-RPC transport to the tool Handler.
type Server struct {
	handler *Handler
	name    string
	version string
}

// NewServer creates a Server exposing the given handler's tools.
func NewServer(h *Handler) *Server {
	return &Server{handler: h, name: "brazilian-soccer-mcp", version: "1.0.0"}
}

type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

type response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// Serve runs the read/dispatch/write loop until the input is exhausted.
func (s *Server) Serve(r io.Reader, w io.Writer) error {
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)
	bw := bufio.NewWriter(w)
	defer bw.Flush()
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		resp, send := s.handleMessage(line)
		if !send {
			continue
		}
		bw.Write(resp)
		bw.WriteByte('\n')
		bw.Flush()
	}
	return scanner.Err()
}

// handleMessage processes one JSON-RPC message, returning the response bytes
// and whether a response should be sent (notifications produce none).
func (s *Server) handleMessage(raw []byte) ([]byte, bool) {
	var req request
	if err := json.Unmarshal(raw, &req); err != nil {
		return s.errorResponse(nil, codeParseError, "parse error"), true
	}
	// Requests carry an id; notifications do not.
	isNotification := len(req.ID) == 0

	switch req.Method {
	case "initialize":
		return s.marshal(req.ID, s.initializeResult()), true
	case "ping":
		return s.marshal(req.ID, map[string]any{}), true
	case "tools/list":
		return s.marshal(req.ID, map[string]any{"tools": Tools()}), true
	case "tools/call":
		return s.handleToolsCall(req), true
	case "notifications/initialized", "notifications/cancelled":
		return nil, false
	default:
		if isNotification {
			return nil, false
		}
		return s.errorResponse(req.ID, codeMethodNotFnd, "method not found: "+req.Method), true
	}
}

func (s *Server) initializeResult() map[string]any {
	return map[string]any{
		"protocolVersion": protocolVersion,
		"capabilities":    map[string]any{"tools": map[string]any{}},
		"serverInfo":      map[string]any{"name": s.name, "version": s.version},
	}
}

type toolCallParams struct {
	Name      string         `json:"name"`
	Arguments map[string]any `json:"arguments"`
}

func (s *Server) handleToolsCall(req request) []byte {
	var p toolCallParams
	if len(req.Params) > 0 {
		if err := json.Unmarshal(req.Params, &p); err != nil {
			return s.errorResponse(req.ID, codeInvalidParams, "invalid params")
		}
	}
	if p.Name == "" {
		return s.errorResponse(req.ID, codeInvalidParams, "missing tool name")
	}
	text, err := s.handler.Call(p.Name, p.Arguments)
	if err != nil {
		// Tool-level failures are surfaced as MCP tool errors, not protocol errors.
		return s.marshal(req.ID, toolResult(err.Error(), true))
	}
	return s.marshal(req.ID, toolResult(text, false))
}

func toolResult(text string, isError bool) map[string]any {
	res := map[string]any{
		"content": []map[string]any{{"type": "text", "text": text}},
	}
	if isError {
		res["isError"] = true
	}
	return res
}

func (s *Server) marshal(id json.RawMessage, result any) []byte {
	out, err := json.Marshal(response{JSONRPC: "2.0", ID: idOrNull(id), Result: result})
	if err != nil {
		return s.errorResponse(id, codeInternal, "internal error")
	}
	return out
}

func (s *Server) errorResponse(id json.RawMessage, code int, msg string) []byte {
	out, _ := json.Marshal(response{
		JSONRPC: "2.0",
		ID:      idOrNull(id),
		Error:   &rpcError{Code: code, Message: msg},
	})
	return out
}

// idOrNull ensures the response always carries an id field (JSON null when the
// request id was absent or unparseable).
func idOrNull(id json.RawMessage) json.RawMessage {
	if len(id) == 0 {
		return json.RawMessage("null")
	}
	return id
}
