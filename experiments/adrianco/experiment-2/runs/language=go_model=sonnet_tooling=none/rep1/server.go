// Package main - Brazilian Soccer MCP Server
// server.go: MCP (Model Context Protocol) server implementation using JSON-RPC 2.0
// over stdio with Content-Length framing (LSP-style transport).
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"strconv"
	"strings"
)

// MCPServer handles the MCP protocol for the Brazilian soccer data.
type MCPServer struct {
	db *Database
}

// NewMCPServer creates a new MCP server with the given database.
func NewMCPServer(db *Database) *MCPServer {
	return &MCPServer{db: db}
}

// jsonRPCRequest represents a JSON-RPC 2.0 request.
type jsonRPCRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      interface{}     `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// jsonRPCResponse represents a JSON-RPC 2.0 response.
type jsonRPCResponse struct {
	JSONRPC string      `json:"jsonrpc"`
	ID      interface{} `json:"id,omitempty"`
	Result  interface{} `json:"result,omitempty"`
	Error   *rpcError   `json:"error,omitempty"`
}

// rpcError represents a JSON-RPC error object.
type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// Serve reads JSON-RPC messages from r and writes responses to w.
// Supports both Content-Length framing (LSP-style) and newline-delimited JSON.
func (s *MCPServer) Serve(r io.Reader, w io.Writer) error {
	reader := bufio.NewReader(r)
	writer := bufio.NewWriter(w)

	for {
		msg, err := readMessage(reader)
		if err == io.EOF {
			return nil
		}
		if err != nil {
			log.Printf("Error reading message: %v", err)
			continue
		}

		var req jsonRPCRequest
		if err := json.Unmarshal(msg, &req); err != nil {
			log.Printf("Error parsing JSON-RPC request: %v", err)
			continue
		}

		resp := s.handleRequest(&req)

		// Notifications (no id) don't get responses, unless it's an error
		if req.ID == nil && resp == nil {
			continue
		}
		if resp == nil {
			continue
		}

		data, err := json.Marshal(resp)
		if err != nil {
			log.Printf("Error marshaling response: %v", err)
			continue
		}

		if err := writeMessage(writer, data); err != nil {
			return fmt.Errorf("error writing response: %w", err)
		}
	}
}

// readMessage reads a single JSON-RPC message, supporting both
// Content-Length framing and newline-delimited JSON.
func readMessage(r *bufio.Reader) ([]byte, error) {
	// Peek to see if we're dealing with Content-Length headers or raw JSON
	b, err := r.Peek(1)
	if err != nil {
		return nil, err
	}

	if b[0] == '{' || b[0] == '[' {
		// Newline-delimited JSON
		line, err := r.ReadString('\n')
		if err != nil && err != io.EOF {
			return nil, err
		}
		line = strings.TrimSpace(line)
		if line == "" {
			return nil, io.EOF
		}
		return []byte(line), nil
	}

	// Content-Length framing
	contentLength := 0
	for {
		line, err := r.ReadString('\n')
		if err != nil {
			return nil, err
		}
		line = strings.TrimRight(line, "\r\n")
		if line == "" {
			break // empty line signals end of headers
		}
		if strings.HasPrefix(strings.ToLower(line), "content-length:") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				contentLength, _ = strconv.Atoi(strings.TrimSpace(parts[1]))
			}
		}
	}

	if contentLength <= 0 {
		return nil, fmt.Errorf("invalid or missing Content-Length")
	}

	buf := make([]byte, contentLength)
	_, err = io.ReadFull(r, buf)
	if err != nil {
		return nil, err
	}
	return buf, nil
}

// writeMessage writes a JSON message with Content-Length framing.
func writeMessage(w *bufio.Writer, data []byte) error {
	header := fmt.Sprintf("Content-Length: %d\r\n\r\n", len(data))
	if _, err := w.WriteString(header); err != nil {
		return err
	}
	if _, err := w.Write(data); err != nil {
		return err
	}
	return w.Flush()
}

// handleRequest dispatches a JSON-RPC request to the appropriate handler.
func (s *MCPServer) handleRequest(req *jsonRPCRequest) *jsonRPCResponse {
	switch req.Method {
	case "initialize":
		return s.handleInitialize(req)
	case "initialized":
		// Notification, no response
		return nil
	case "ping":
		return &jsonRPCResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result:  map[string]interface{}{},
		}
	case "tools/list":
		return s.handleToolsList(req)
	case "tools/call":
		return s.handleToolsCall(req)
	default:
		return &jsonRPCResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error: &rpcError{
				Code:    -32601,
				Message: fmt.Sprintf("method not found: %s", req.Method),
			},
		}
	}
}

// handleInitialize handles the MCP initialize request.
func (s *MCPServer) handleInitialize(req *jsonRPCRequest) *jsonRPCResponse {
	return &jsonRPCResponse{
		JSONRPC: "2.0",
		ID:      req.ID,
		Result: map[string]interface{}{
			"protocolVersion": "2024-11-05",
			"capabilities": map[string]interface{}{
				"tools": map[string]interface{}{},
			},
			"serverInfo": map[string]interface{}{
				"name":    "brazilian-soccer-mcp",
				"version": "1.0.0",
			},
		},
	}
}

// handleToolsList returns the list of available tools.
func (s *MCPServer) handleToolsList(req *jsonRPCRequest) *jsonRPCResponse {
	defs := GetToolDefinitions()
	tools := make([]map[string]interface{}, len(defs))
	for i, d := range defs {
		tools[i] = map[string]interface{}{
			"name":        d.Name,
			"description": d.Description,
			"inputSchema": d.InputSchema,
		}
	}
	return &jsonRPCResponse{
		JSONRPC: "2.0",
		ID:      req.ID,
		Result: map[string]interface{}{
			"tools": tools,
		},
	}
}

// handleToolsCall dispatches a tool call and returns the result.
func (s *MCPServer) handleToolsCall(req *jsonRPCRequest) *jsonRPCResponse {
	var callParams struct {
		Name      string                 `json:"name"`
		Arguments map[string]interface{} `json:"arguments"`
	}
	if req.Params != nil {
		if err := json.Unmarshal(req.Params, &callParams); err != nil {
			return &jsonRPCResponse{
				JSONRPC: "2.0",
				ID:      req.ID,
				Error: &rpcError{
					Code:    -32602,
					Message: fmt.Sprintf("invalid params: %v", err),
				},
			}
		}
	}

	result, err := DispatchTool(s.db, callParams.Name, callParams.Arguments)
	if err != nil {
		return &jsonRPCResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result: map[string]interface{}{
				"content": []map[string]interface{}{
					{"type": "text", "text": fmt.Sprintf("Error: %v", err)},
				},
				"isError": true,
			},
		}
	}

	return &jsonRPCResponse{
		JSONRPC: "2.0",
		ID:      req.ID,
		Result: map[string]interface{}{
			"content": []map[string]interface{}{
				{"type": "text", "text": result},
			},
		},
	}
}
