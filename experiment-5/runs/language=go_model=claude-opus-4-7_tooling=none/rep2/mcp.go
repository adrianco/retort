package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"strings"
	"sync"
	"time"
)

// MCP protocol implementation. Speaks JSON-RPC 2.0 over a duplex stream
// (typically stdin/stdout). Supports the subset of the protocol required
// for tool calling: initialize, tools/list, tools/call.

const (
	mcpProtocolVersion = "2024-11-05"
	mcpServerName      = "brazilian-soccer-mcp"
	mcpServerVersion   = "1.0.0"
)

type jsonrpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type jsonrpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

type jsonrpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  any             `json:"result,omitempty"`
	Error   *jsonrpcError   `json:"error,omitempty"`
}

// Server holds the MCP server state.
type Server struct {
	ds    *Dataset
	tools []tool
	mu    sync.Mutex
}

// NewServer wires up tool handlers over the loaded dataset.
func NewServer(ds *Dataset) *Server {
	s := &Server{ds: ds}
	s.tools = s.buildTools()
	return s
}

// Serve reads JSON-RPC requests from r and writes responses to w until EOF.
// Each line of input is expected to be a single JSON-RPC message
// (LSP-style framing with Content-Length headers is also supported).
func (s *Server) Serve(r io.Reader, w io.Writer) error {
	br := bufio.NewReader(r)
	bw := bufio.NewWriter(w)
	defer bw.Flush()

	for {
		msg, err := readMessage(br)
		if err == io.EOF {
			return nil
		}
		if err != nil {
			return err
		}
		if len(msg) == 0 {
			continue
		}

		var req jsonrpcRequest
		if err := json.Unmarshal(msg, &req); err != nil {
			writeResponse(bw, jsonrpcResponse{
				JSONRPC: "2.0",
				Error:   &jsonrpcError{Code: -32700, Message: "Parse error: " + err.Error()},
			})
			continue
		}

		resp := s.handle(req)
		if resp == nil {
			continue
		}
		if err := writeResponse(bw, *resp); err != nil {
			return err
		}
		bw.Flush()
	}
}

// readMessage reads either a single JSON line or an LSP-style framed message.
func readMessage(br *bufio.Reader) ([]byte, error) {
	// Peek to see whether we have a Content-Length header.
	for {
		peek, err := br.Peek(1)
		if err != nil {
			return nil, err
		}
		if peek[0] == ' ' || peek[0] == '\t' || peek[0] == '\r' || peek[0] == '\n' {
			br.Discard(1)
			continue
		}
		break
	}
	peek, err := br.Peek(15)
	if err == nil && strings.HasPrefix(string(peek), "Content-Length:") {
		// LSP-style framed message.
		length := 0
		for {
			line, err := br.ReadString('\n')
			if err != nil {
				return nil, err
			}
			line = strings.TrimRight(line, "\r\n")
			if line == "" {
				break
			}
			if strings.HasPrefix(line, "Content-Length:") {
				v := strings.TrimSpace(strings.TrimPrefix(line, "Content-Length:"))
				fmt.Sscanf(v, "%d", &length)
			}
		}
		buf := make([]byte, length)
		if _, err := io.ReadFull(br, buf); err != nil {
			return nil, err
		}
		return buf, nil
	}
	// Newline-delimited JSON.
	line, err := br.ReadBytes('\n')
	if err != nil && len(line) == 0 {
		return nil, err
	}
	return line, nil
}

func writeResponse(w io.Writer, resp jsonrpcResponse) error {
	resp.JSONRPC = "2.0"
	buf, err := json.Marshal(resp)
	if err != nil {
		return err
	}
	// Use newline framing for simplicity.
	buf = append(buf, '\n')
	_, err = w.Write(buf)
	return err
}

func (s *Server) handle(req jsonrpcRequest) *jsonrpcResponse {
	switch req.Method {
	case "initialize":
		return &jsonrpcResponse{ID: req.ID, Result: map[string]any{
			"protocolVersion": mcpProtocolVersion,
			"serverInfo": map[string]any{
				"name":    mcpServerName,
				"version": mcpServerVersion,
			},
			"capabilities": map[string]any{
				"tools": map[string]any{},
			},
		}}
	case "notifications/initialized", "initialized":
		// Notifications produce no response.
		return nil
	case "ping":
		return &jsonrpcResponse{ID: req.ID, Result: map[string]any{}}
	case "tools/list":
		return &jsonrpcResponse{ID: req.ID, Result: map[string]any{
			"tools": s.listTools(),
		}}
	case "tools/call":
		return s.handleToolCall(req)
	case "shutdown":
		return &jsonrpcResponse{ID: req.ID, Result: nil}
	}
	if len(req.ID) == 0 {
		// notification we don't recognise — silently drop
		return nil
	}
	return &jsonrpcResponse{ID: req.ID, Error: &jsonrpcError{Code: -32601, Message: "Method not found: " + req.Method}}
}

type toolCallParams struct {
	Name      string         `json:"name"`
	Arguments map[string]any `json:"arguments"`
}

func (s *Server) handleToolCall(req jsonrpcRequest) *jsonrpcResponse {
	var params toolCallParams
	if len(req.Params) > 0 {
		if err := json.Unmarshal(req.Params, &params); err != nil {
			return &jsonrpcResponse{ID: req.ID, Error: &jsonrpcError{Code: -32602, Message: "Invalid params: " + err.Error()}}
		}
	}
	if params.Arguments == nil {
		params.Arguments = map[string]any{}
	}
	for _, t := range s.tools {
		if t.Name != params.Name {
			continue
		}
		start := time.Now()
		out, isError := t.Handler(params.Arguments)
		_ = start // could be logged
		return &jsonrpcResponse{ID: req.ID, Result: map[string]any{
			"content": []map[string]any{{
				"type": "text",
				"text": out,
			}},
			"isError": isError,
		}}
	}
	return &jsonrpcResponse{ID: req.ID, Error: &jsonrpcError{Code: -32601, Message: "Unknown tool: " + params.Name}}
}

func (s *Server) listTools() []map[string]any {
	out := make([]map[string]any, 0, len(s.tools))
	for _, t := range s.tools {
		out = append(out, map[string]any{
			"name":        t.Name,
			"description": t.Description,
			"inputSchema": t.InputSchema,
		})
	}
	return out
}
