// Package mcpserver is a minimal Model Context Protocol server: JSON-RPC
// 2.0 messages, one per line, over standard input and output, offering
// tools to an LLM host.
package mcpserver

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"slices"
	"strings"
	"sync"
)

// Result is what a tool gives back: text for the LLM to read, and the
// same answer as structured data.
type Result struct {
	Text       string
	Structured any
}

// Tool is one capability offered to the LLM.
type Tool struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     func(args Args) (Result, error)
}

// Server answers MCP requests.
type Server struct {
	name, version, instructions string
	tools                       []Tool
	byName                      map[string]Tool
	out                         io.Writer
	mu                          sync.Mutex
}

var supportedVersions = []string{"2025-06-18", "2025-03-26", "2024-11-05"}

func New(name, version, instructions string) *Server {
	return &Server{name: name, version: version, instructions: instructions, byName: map[string]Tool{}}
}

func (s *Server) AddTool(t Tool) {
	s.tools = append(s.tools, t)
	s.byName[t.Name] = t
}

type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

const (
	parseError     = -32700
	invalidRequest = -32600
	methodNotFound = -32601
	invalidParams  = -32602
)

// Serve answers requests from in until it is closed.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	s.out = out
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 1024*1024), 16*1024*1024)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var req request
		if err := json.Unmarshal(line, &req); err != nil {
			s.send(json.RawMessage("null"), nil, &rpcError{parseError, "invalid JSON: " + err.Error()})
			continue
		}
		s.handle(req)
	}
	return scanner.Err()
}

func (s *Server) handle(req request) {
	isNotification := len(req.ID) == 0
	if req.JSONRPC != "2.0" || req.Method == "" {
		if !isNotification {
			s.send(req.ID, nil, &rpcError{invalidRequest, "not a JSON-RPC 2.0 request"})
		}
		return
	}
	result, err := s.dispatch(req)
	if isNotification {
		return
	}
	s.send(req.ID, result, err)
}

func (s *Server) dispatch(req request) (any, *rpcError) {
	switch req.Method {
	case "initialize":
		var p struct {
			ProtocolVersion string `json:"protocolVersion"`
		}
		_ = json.Unmarshal(req.Params, &p)
		version := supportedVersions[0]
		if slices.Contains(supportedVersions, p.ProtocolVersion) {
			version = p.ProtocolVersion
		}
		return map[string]any{
			"protocolVersion": version,
			"capabilities":    map[string]any{"tools": map[string]any{"listChanged": false}},
			"serverInfo":      map[string]any{"name": s.name, "version": s.version},
			"instructions":    s.instructions,
		}, nil
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		tools := make([]map[string]any, 0, len(s.tools))
		for _, t := range s.tools {
			tools = append(tools, map[string]any{"name": t.Name, "description": t.Description, "inputSchema": t.InputSchema})
		}
		return map[string]any{"tools": tools}, nil
	case "tools/call":
		var p struct {
			Name      string         `json:"name"`
			Arguments map[string]any `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			return nil, &rpcError{invalidParams, "invalid tool call: " + err.Error()}
		}
		tool, ok := s.byName[p.Name]
		if !ok {
			return nil, &rpcError{invalidParams, fmt.Sprintf("unknown tool %q", p.Name)}
		}
		return s.call(tool, p.Arguments), nil
	case "resources/list":
		return map[string]any{"resources": []any{}}, nil
	case "prompts/list":
		return map[string]any{"prompts": []any{}}, nil
	}
	if strings.HasPrefix(req.Method, "notifications/") {
		return nil, nil
	}
	return nil, &rpcError{methodNotFound, fmt.Sprintf("method %q not supported", req.Method)}
}

// call runs a tool. Failures are reported to the LLM as an error result,
// so that it can explain them or try again, rather than as a protocol error.
func (s *Server) call(tool Tool, args map[string]any) (result map[string]any) {
	defer func() {
		if r := recover(); r != nil {
			result = errorResult(fmt.Sprintf("internal error in %s: %v", tool.Name, r))
		}
	}()
	res, err := tool.Handler(Args(args))
	if err != nil {
		return errorResult(err.Error())
	}
	result = map[string]any{"content": []map[string]any{{"type": "text", "text": res.Text}}, "isError": false}
	if res.Structured != nil {
		result["structuredContent"] = res.Structured
	}
	return result
}

func errorResult(msg string) map[string]any {
	return map[string]any{"content": []map[string]any{{"type": "text", "text": msg}}, "isError": true}
}

func (s *Server) send(id json.RawMessage, result any, rpcErr *rpcError) {
	msg := map[string]any{"jsonrpc": "2.0", "id": id}
	if rpcErr != nil {
		msg["error"] = rpcErr
	} else {
		msg["result"] = result
	}
	data, err := json.Marshal(msg)
	if err != nil {
		data, _ = json.Marshal(map[string]any{"jsonrpc": "2.0", "id": id, "error": rpcError{-32603, "could not encode answer: " + err.Error()}})
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	_, _ = s.out.Write(append(data, '\n'))
}
