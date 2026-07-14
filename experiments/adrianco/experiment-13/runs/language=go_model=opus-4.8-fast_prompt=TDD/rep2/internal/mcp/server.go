// Package mcp implements a minimal Model Context Protocol server (JSON-RPC 2.0
// over newline-delimited stdio) that exposes the Brazilian-soccer knowledge
// base as a set of callable tools.
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"

	"brazilian-soccer-mcp/internal/soccer"
)

const protocolVersion = "2024-11-05"

// request is a JSON-RPC 2.0 request or notification. A notification has no ID.
type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// response is a JSON-RPC 2.0 response.
type response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  interface{}     `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// JSON-RPC standard error codes used here.
const (
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
)

// Server answers MCP requests against an in-memory knowledge base.
type Server struct {
	kb *soccer.KB
}

// New returns a Server backed by kb.
func New(kb *soccer.KB) *Server { return &Server{kb: kb} }

// Serve reads newline-delimited JSON-RPC messages from in and writes responses
// to out until in is exhausted. Notifications produce no response.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	dec := json.NewDecoder(bufio.NewReader(in))
	enc := json.NewEncoder(out)
	for {
		var req request
		if err := dec.Decode(&req); err != nil {
			if err == io.EOF {
				return nil
			}
			return err
		}
		resp, ok := s.handle(req)
		if !ok {
			continue
		}
		if err := enc.Encode(resp); err != nil {
			return err
		}
	}
}

// handle dispatches a single request. The bool result is false for
// notifications (which must not receive a response).
func (s *Server) handle(req request) (*response, bool) {
	switch req.Method {
	case "initialize":
		return s.reply(req, s.initializeResult()), true
	case "tools/list":
		return s.reply(req, map[string]any{"tools": toolDefinitions()}), true
	case "tools/call":
		return s.handleToolCall(req), true
	case "ping":
		return s.reply(req, map[string]any{}), true
	case "notifications/initialized", "notifications/cancelled":
		return nil, false // notifications: no response
	default:
		if len(req.ID) == 0 {
			return nil, false // unknown notification
		}
		return s.fail(req, codeMethodNotFound, "method not found: "+req.Method), true
	}
}

func (s *Server) initializeResult() map[string]any {
	return map[string]any{
		"protocolVersion": protocolVersion,
		"capabilities":    map[string]any{"tools": map[string]any{}},
		"serverInfo": map[string]any{
			"name":    "brazilian-soccer-mcp",
			"version": "1.0.0",
		},
	}
}

func (s *Server) reply(req request, result interface{}) *response {
	return &response{JSONRPC: "2.0", ID: req.ID, Result: result}
}

func (s *Server) fail(req request, code int, msg string) *response {
	return &response{JSONRPC: "2.0", ID: req.ID, Error: &rpcError{Code: code, Message: msg}}
}

// handleToolCall executes a tools/call request, returning the tool output as
// MCP text content. Tool-level failures are reported via isError content
// rather than a JSON-RPC error, per the MCP convention.
func (s *Server) handleToolCall(req request) *response {
	var call struct {
		Name      string          `json:"name"`
		Arguments json.RawMessage `json:"arguments"`
	}
	if err := json.Unmarshal(req.Params, &call); err != nil {
		return s.fail(req, codeInvalidParams, "invalid params: "+err.Error())
	}
	var args toolArgs
	if len(call.Arguments) > 0 {
		if err := json.Unmarshal(call.Arguments, &args); err != nil {
			return s.fail(req, codeInvalidParams, "invalid arguments: "+err.Error())
		}
	}
	text, err := s.dispatchTool(call.Name, args)
	if err != nil {
		return s.reply(req, toolError(err.Error()))
	}
	return s.reply(req, toolText(text))
}

// toolText wraps plain text in an MCP tool result.
func toolText(text string) map[string]any {
	return map[string]any{
		"content": []map[string]any{{"type": "text", "text": text}},
	}
}

// toolError wraps an error message in an MCP tool result flagged isError.
func toolError(msg string) map[string]any {
	return map[string]any{
		"content": []map[string]any{{"type": "text", "text": "Error: " + msg}},
		"isError": true,
	}
}

// dispatchTool routes a tool name and parsed arguments to its implementation.
func (s *Server) dispatchTool(name string, a toolArgs) (string, error) {
	switch name {
	case "search_matches":
		return s.toolSearchMatches(a)
	case "head_to_head":
		return s.toolHeadToHead(a)
	case "team_record":
		return s.toolTeamRecord(a)
	case "search_players":
		return s.toolSearchPlayers(a)
	case "standings":
		return s.toolStandings(a)
	case "competition_stats":
		return s.toolCompetitionStats(a)
	default:
		return "", fmt.Errorf("unknown tool: %s", name)
	}
}
