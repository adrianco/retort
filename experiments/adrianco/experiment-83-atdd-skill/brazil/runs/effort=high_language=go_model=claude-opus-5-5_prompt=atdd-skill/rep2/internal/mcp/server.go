// Package mcp is a minimal Model Context Protocol server: JSON-RPC 2.0
// messages, one per line, over stdin/stdout, offering tools.
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync"
)

// Tool is one capability offered to the client.
type Tool struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     func(Args) (text string, structured any, err error)
}

// Server dispatches MCP requests to tools.
type Server struct {
	Name, Version, Instructions string
	tools                       []Tool
	byName                      map[string]Tool
	mu                          sync.Mutex
}

func NewServer(name, version, instructions string) *Server {
	return &Server{Name: name, Version: version, Instructions: instructions, byName: map[string]Tool{}}
}

func (s *Server) AddTool(t Tool) {
	s.tools = append(s.tools, t)
	s.byName[t.Name] = t
}

// SupportedVersions are the MCP protocol revisions this server speaks.
var SupportedVersions = []string{"2025-06-18", "2025-03-26", "2024-11-05"}

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

type response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

// Serve reads requests until in is closed.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	reader := bufio.NewReaderSize(in, 1<<20)
	w := bufio.NewWriter(out)
	for {
		line, err := reader.ReadBytes('\n')
		if len(line) > 0 {
			if resp := s.Handle(line); resp != nil {
				b, _ := json.Marshal(resp)
				w.Write(append(b, '\n'))
				w.Flush()
			}
		}
		if err == io.EOF {
			return nil
		}
		if err != nil {
			return err
		}
	}
}

// Handle processes one message and returns the response, or nil for a
// notification.
func (s *Server) Handle(line []byte) *response {
	var req request
	if err := json.Unmarshal(line, &req); err != nil {
		if len(trimSpace(line)) == 0 {
			return nil
		}
		return &response{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &rpcError{-32700, "parse error"}}
	}
	if len(req.ID) == 0 || string(req.ID) == "null" {
		return nil // notifications get no reply
	}
	result, rerr := s.dispatch(req)
	resp := &response{JSONRPC: "2.0", ID: req.ID}
	if rerr != nil {
		resp.Error = rerr
	} else {
		resp.Result = result
	}
	return resp
}

func trimSpace(b []byte) []byte {
	for len(b) > 0 && (b[0] == ' ' || b[0] == '\n' || b[0] == '\r' || b[0] == '\t') {
		b = b[1:]
	}
	return b
}

func (s *Server) dispatch(req request) (any, *rpcError) {
	switch req.Method {
	case "initialize":
		var p struct {
			ProtocolVersion string `json:"protocolVersion"`
		}
		json.Unmarshal(req.Params, &p)
		version := SupportedVersions[0]
		for _, v := range SupportedVersions {
			if v == p.ProtocolVersion {
				version = v
			}
		}
		return map[string]any{
			"protocolVersion": version,
			"capabilities":    map[string]any{"tools": map[string]any{"listChanged": false}},
			"serverInfo":      map[string]any{"name": s.Name, "version": s.Version},
			"instructions":    s.Instructions,
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
			return nil, &rpcError{-32602, "invalid params"}
		}
		t, ok := s.byName[p.Name]
		if !ok {
			return nil, &rpcError{-32602, fmt.Sprintf("unknown tool %q", p.Name)}
		}
		return s.call(t, p.Arguments), nil
	case "resources/list":
		return map[string]any{"resources": []any{}}, nil
	case "prompts/list":
		return map[string]any{"prompts": []any{}}, nil
	}
	return nil, &rpcError{-32601, fmt.Sprintf("method %q not found", req.Method)}
}

func (s *Server) call(t Tool, args map[string]any) (result map[string]any) {
	defer func() {
		if r := recover(); r != nil {
			result = errorResult(fmt.Sprintf("internal error in %s: %v", t.Name, r))
		}
	}()
	s.mu.Lock()
	defer s.mu.Unlock()
	text, structured, err := t.Handler(Args(args))
	if err != nil {
		return errorResult(err.Error())
	}
	res := map[string]any{"content": []map[string]any{{"type": "text", "text": text}}}
	if structured != nil {
		// structuredContent must be a JSON object.
		b, _ := json.Marshal(structured)
		var obj map[string]any
		if json.Unmarshal(b, &obj) == nil {
			res["structuredContent"] = obj
		}
	}
	return res
}

func errorResult(msg string) map[string]any {
	return map[string]any{"content": []map[string]any{{"type": "text", "text": msg}}, "isError": true}
}
