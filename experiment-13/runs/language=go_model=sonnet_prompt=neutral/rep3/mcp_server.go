package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
)

// MCP JSON-RPC 2.0 types

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  interface{}     `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// MCP capability types

type serverInfo struct {
	Name    string `json:"name"`
	Version string `json:"version"`
}

type initResult struct {
	ProtocolVersion string       `json:"protocolVersion"`
	Capabilities    capabilities `json:"capabilities"`
	ServerInfo      serverInfo   `json:"serverInfo"`
}

type capabilities struct {
	Tools toolsCap `json:"tools"`
}

type toolsCap struct {
	ListChanged bool `json:"listChanged"`
}

type toolsListResult struct {
	Tools []toolDef `json:"tools"`
}

type toolDef struct {
	Name        string      `json:"name"`
	Description string      `json:"description"`
	InputSchema inputSchema `json:"inputSchema"`
}

type inputSchema struct {
	Type       string              `json:"type"`
	Properties map[string]property `json:"properties"`
	Required   []string            `json:"required,omitempty"`
}

type property struct {
	Type        string `json:"type"`
	Description string `json:"description"`
}

type toolCallResult struct {
	Content []contentItem `json:"content"`
}

type contentItem struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

// Server runs the MCP stdio server
type Server struct {
	db     *Database
	reader *bufio.Reader
	writer io.Writer
}

func NewServer(db *Database) *Server {
	return &Server{
		db:     db,
		reader: bufio.NewReader(os.Stdin),
		writer: os.Stdout,
	}
}

func (s *Server) Run() error {
	for {
		line, err := s.reader.ReadString('\n')
		if err == io.EOF {
			return nil
		}
		if err != nil {
			return err
		}
		if len(line) == 0 || line == "\n" {
			continue
		}

		var req rpcRequest
		if err := json.Unmarshal([]byte(line), &req); err != nil {
			s.sendError(nil, -32700, "parse error")
			continue
		}

		s.handleRequest(req)
	}
}

func (s *Server) handleRequest(req rpcRequest) {
	// Notifications have no id and need no response
	if req.ID == nil {
		return
	}

	switch req.Method {
	case "initialize":
		s.sendResult(req.ID, initResult{
			ProtocolVersion: "2024-11-05",
			Capabilities:    capabilities{Tools: toolsCap{ListChanged: false}},
			ServerInfo:      serverInfo{Name: "brazilian-soccer-mcp", Version: "1.0.0"},
		})
	case "ping":
		s.sendResult(req.ID, map[string]interface{}{})
	case "tools/list":
		s.sendResult(req.ID, toolsListResult{Tools: allTools()})
	case "tools/call":
		s.handleToolCall(req)
	default:
		s.sendError(req.ID, -32601, fmt.Sprintf("method not found: %s", req.Method))
	}
}

func (s *Server) handleToolCall(req rpcRequest) {
	var params struct {
		Name      string                 `json:"name"`
		Arguments map[string]interface{} `json:"arguments"`
	}
	if err := json.Unmarshal(req.Params, &params); err != nil {
		s.sendError(req.ID, -32602, "invalid params")
		return
	}

	text, err := dispatchTool(s.db, params.Name, params.Arguments)
	if err != nil {
		s.sendError(req.ID, -32603, err.Error())
		return
	}

	s.sendResult(req.ID, toolCallResult{
		Content: []contentItem{{Type: "text", Text: text}},
	})
}

func (s *Server) sendResult(id json.RawMessage, result interface{}) {
	resp := rpcResponse{JSONRPC: "2.0", ID: id, Result: result}
	s.writeJSON(resp)
}

func (s *Server) sendError(id json.RawMessage, code int, msg string) {
	resp := rpcResponse{JSONRPC: "2.0", ID: id, Error: &rpcError{Code: code, Message: msg}}
	s.writeJSON(resp)
}

func (s *Server) writeJSON(v interface{}) {
	b, err := json.Marshal(v)
	if err != nil {
		return
	}
	fmt.Fprintf(s.writer, "%s\n", b)
}
