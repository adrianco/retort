// Package mcp implements a minimal, dependency-free MCP (Model Context
// Protocol) server over stdio.
//
// Context: MCP clients (Claude Desktop, Claude Code, etc.) speak JSON-RPC
// 2.0 with newline-delimited JSON messages on stdin/stdout. This file
// implements the transport and the protocol handshake (initialize,
// notifications/initialized, ping, tools/list, tools/call); tool
// registration is generic so the Brazilian soccer tools plug in from
// tools.go. Logging goes to stderr, which MCP reserves for diagnostics.
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
)

const protocolVersion = "2024-11-05"

// JSON-RPC 2.0 message envelope (request, response, or notification).
type rpcMessage struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method,omitempty"`
	Params  json.RawMessage `json:"params,omitempty"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

const (
	codeParseError     = -32700
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
	codeInternalError  = -32603
)

// Tool is one MCP tool: JSON schema plus a handler that returns text.
type Tool struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     func(args map[string]any) (string, error)
}

// Server is a stdio MCP server with a fixed tool set.
type Server struct {
	Name    string
	Version string
	Tools   []Tool
	logger  *log.Logger
}

func NewServer(name, version string, tools []Tool, logger *log.Logger) *Server {
	if logger == nil {
		logger = log.New(io.Discard, "", 0)
	}
	return &Server{Name: name, Version: version, Tools: tools, logger: logger}
}

func (s *Server) tool(name string) *Tool {
	for i := range s.Tools {
		if s.Tools[i].Name == name {
			return &s.Tools[i]
		}
	}
	return nil
}

// Serve reads newline-delimited JSON-RPC messages from in and writes
// responses to out until in is exhausted.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 0, 1024*1024), 16*1024*1024)
	enc := json.NewEncoder(out)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var msg rpcMessage
		if err := json.Unmarshal(line, &msg); err != nil {
			s.logger.Printf("parse error: %v", err)
			_ = enc.Encode(rpcMessage{JSONRPC: "2.0", Error: &rpcError{codeParseError, "parse error"}})
			continue
		}
		resp := s.handle(&msg)
		if resp != nil {
			if err := enc.Encode(resp); err != nil {
				return err
			}
		}
	}
	return scanner.Err()
}

// handle dispatches one message; nil return means no response (notification).
func (s *Server) handle(msg *rpcMessage) *rpcMessage {
	isNotification := len(msg.ID) == 0
	reply := func(result any) *rpcMessage {
		if isNotification {
			return nil
		}
		return &rpcMessage{JSONRPC: "2.0", ID: msg.ID, Result: result}
	}
	replyErr := func(code int, format string, a ...any) *rpcMessage {
		if isNotification {
			return nil
		}
		return &rpcMessage{JSONRPC: "2.0", ID: msg.ID, Error: &rpcError{code, fmt.Sprintf(format, a...)}}
	}

	switch msg.Method {
	case "initialize":
		return reply(map[string]any{
			"protocolVersion": protocolVersion,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": s.Name, "version": s.Version},
		})
	case "notifications/initialized", "notifications/cancelled":
		return nil
	case "ping":
		return reply(map[string]any{})
	case "tools/list":
		tools := make([]map[string]any, 0, len(s.Tools))
		for _, t := range s.Tools {
			tools = append(tools, map[string]any{
				"name":        t.Name,
				"description": t.Description,
				"inputSchema": t.InputSchema,
			})
		}
		return reply(map[string]any{"tools": tools})
	case "tools/call":
		var params struct {
			Name      string         `json:"name"`
			Arguments map[string]any `json:"arguments"`
		}
		if err := json.Unmarshal(msg.Params, &params); err != nil {
			return replyErr(codeInvalidParams, "invalid params: %v", err)
		}
		t := s.tool(params.Name)
		if t == nil {
			return replyErr(codeInvalidParams, "unknown tool %q", params.Name)
		}
		s.logger.Printf("tools/call %s %v", params.Name, params.Arguments)
		text, err := t.Handler(params.Arguments)
		result := map[string]any{
			"content": []map[string]any{{"type": "text", "text": text}},
		}
		if err != nil {
			result["content"] = []map[string]any{{"type": "text", "text": "Error: " + err.Error()}}
			result["isError"] = true
		}
		return reply(result)
	default:
		return replyErr(codeMethodNotFound, "method %q not found", msg.Method)
	}
}
