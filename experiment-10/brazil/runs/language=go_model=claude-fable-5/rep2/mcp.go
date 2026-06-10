// mcp.go - Minimal MCP (Model Context Protocol) server over stdio.
//
// Context: Implements the JSON-RPC 2.0 message layer and the MCP methods
// needed for a tools-only server: initialize, ping, tools/list, tools/call
// (plus empty resources/prompts lists for client compatibility). Messages
// are newline-delimited JSON on stdin/stdout per the MCP stdio transport.
// No external dependencies - encoding/json and bufio only.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"strings"
)

const protocolVersion = "2024-11-05"

// Tool is one MCP tool: JSON schema metadata plus its handler.
type Tool struct {
	Name        string                                    `json:"name"`
	Description string                                    `json:"description"`
	InputSchema map[string]any                            `json:"inputSchema"`
	Handler     func(args map[string]any) (string, error) `json:"-"`
}

// MCPServer dispatches JSON-RPC requests to registered tools.
type MCPServer struct {
	Name    string
	Version string
	Tools   []Tool
}

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

// JSON-RPC error codes.
const (
	codeParseError     = -32700
	codeInvalidParams  = -32602
	codeMethodNotFound = -32601
	codeInternalError  = -32603
)

type textContent struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type callResult struct {
	Content []textContent `json:"content"`
	IsError bool          `json:"isError"`
}

// Handle processes one JSON-RPC message and returns the response, or nil if
// no response should be sent (notifications).
func (s *MCPServer) Handle(raw []byte) *rpcResponse {
	var req rpcRequest
	if err := json.Unmarshal(raw, &req); err != nil {
		return &rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"),
			Error: &rpcError{Code: codeParseError, Message: "parse error: " + err.Error()}}
	}
	isNotification := len(req.ID) == 0 || string(req.ID) == "null"

	result, rpcErr := s.dispatch(&req)
	if isNotification {
		return nil
	}
	resp := &rpcResponse{JSONRPC: "2.0", ID: req.ID}
	if rpcErr != nil {
		resp.Error = rpcErr
	} else {
		resp.Result = result
	}
	return resp
}

func (s *MCPServer) dispatch(req *rpcRequest) (any, *rpcError) {
	switch req.Method {
	case "initialize":
		var p struct {
			ProtocolVersion string `json:"protocolVersion"`
		}
		_ = json.Unmarshal(req.Params, &p)
		v := protocolVersion
		if p.ProtocolVersion != "" {
			v = p.ProtocolVersion
		}
		return map[string]any{
			"protocolVersion": v,
			"capabilities": map[string]any{
				"tools": map[string]any{"listChanged": false},
			},
			"serverInfo": map[string]any{
				"name":    s.Name,
				"version": s.Version,
			},
			"instructions": "Knowledge-graph style query interface over Brazilian soccer data: " +
				"Brasileirão Série A (2003-2023), Copa do Brasil, Copa Libertadores matches " +
				"and the FIFA player database. Team names are normalized, so 'Palmeiras', " +
				"'Palmeiras-SP' and 'Sociedade Esportiva Palmeiras' all match.",
		}, nil

	case "ping":
		return map[string]any{}, nil

	case "tools/list":
		tools := make([]Tool, len(s.Tools))
		copy(tools, s.Tools)
		return map[string]any{"tools": tools}, nil

	case "tools/call":
		var p struct {
			Name      string         `json:"name"`
			Arguments map[string]any `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			return nil, &rpcError{Code: codeInvalidParams, Message: "invalid params: " + err.Error()}
		}
		for _, t := range s.Tools {
			if t.Name == p.Name {
				text, err := t.Handler(p.Arguments)
				if err != nil {
					return callResult{
						Content: []textContent{{Type: "text", Text: "Error: " + err.Error()}},
						IsError: true,
					}, nil
				}
				return callResult{
					Content: []textContent{{Type: "text", Text: text}},
					IsError: false,
				}, nil
			}
		}
		return nil, &rpcError{Code: codeInvalidParams, Message: "unknown tool: " + p.Name}

	case "resources/list":
		return map[string]any{"resources": []any{}}, nil

	case "prompts/list":
		return map[string]any{"prompts": []any{}}, nil

	default:
		if strings.HasPrefix(req.Method, "notifications/") {
			return nil, nil
		}
		return nil, &rpcError{Code: codeMethodNotFound, Message: "method not found: " + req.Method}
	}
}

// Serve reads newline-delimited JSON-RPC messages from in and writes
// responses to out, until EOF.
func (s *MCPServer) Serve(in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	w := bufio.NewWriter(out)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		resp := s.Handle([]byte(line))
		if resp == nil {
			continue
		}
		data, err := json.Marshal(resp)
		if err != nil {
			log.Printf("marshal error: %v", err)
			continue
		}
		if _, err := fmt.Fprintf(w, "%s\n", data); err != nil {
			return err
		}
		if err := w.Flush(); err != nil {
			return err
		}
	}
	return scanner.Err()
}
