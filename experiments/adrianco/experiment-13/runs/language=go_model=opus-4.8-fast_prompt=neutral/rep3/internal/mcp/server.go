// server.go wires the JSON-RPC transport to the MCP method handlers
// (initialize, tools/list, tools/call, ping) and the tool registry.
package mcp

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"sync"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// protocolVersion is the MCP revision this server speaks.
const protocolVersion = "2024-11-05"

// Tool is an MCP tool exposed to the client.
type Tool struct {
	Name        string                 `json:"name"`
	Description string                 `json:"description"`
	InputSchema map[string]interface{} `json:"inputSchema"`
	// handler executes the tool and returns the text answer.
	handler func(args map[string]interface{}) (string, error) `json:"-"`
}

// Server is an MCP server backed by the soccer knowledge graph.
type Server struct {
	name    string
	version string
	db      *soccer.DB

	tools   []Tool
	toolIdx map[string]Tool

	mu  sync.Mutex // serializes writes to the output stream
	out io.Writer
}

// NewServer builds a server over the given database and registers all tools.
func NewServer(db *soccer.DB, name, version string) *Server {
	s := &Server{name: name, version: version, db: db, toolIdx: map[string]Tool{}}
	s.registerTools()
	return s
}

func (s *Server) addTool(t Tool) {
	s.tools = append(s.tools, t)
	s.toolIdx[t.Name] = t
}

// Tools returns the registered tool definitions (used in tests).
func (s *Server) Tools() []Tool { return s.tools }

// Serve runs the stdio JSON-RPC loop until ctx is cancelled or in reaches EOF.
func (s *Server) Serve(ctx context.Context, in io.Reader, out io.Writer) error {
	s.out = out
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 0, 64*1024), 8*1024*1024) // allow large messages

	for scanner.Scan() {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		s.handleLine(line)
	}
	return scanner.Err()
}

func (s *Server) handleLine(line []byte) {
	var req request
	if err := json.Unmarshal(line, &req); err != nil {
		s.write(response{JSONRPC: "2.0", Error: newError(codeParseError, "parse error: "+err.Error())})
		return
	}
	result, rerr := s.Dispatch(req.Method, req.Params)
	if req.isNotification() {
		return // notifications get no response
	}
	resp := response{JSONRPC: "2.0", ID: req.ID}
	if rerr != nil {
		resp.Error = rerr
	} else {
		resp.Result = result
	}
	s.write(resp)
}

func (s *Server) write(resp response) {
	s.mu.Lock()
	defer s.mu.Unlock()
	b, err := json.Marshal(resp)
	if err != nil {
		return
	}
	b = append(b, '\n')
	_, _ = s.out.Write(b)
}

// Dispatch routes a single JSON-RPC method call. Exported so tests can drive
// the server without a transport.
func (s *Server) Dispatch(method string, params json.RawMessage) (interface{}, *rpcError) {
	switch method {
	case "initialize":
		return s.handleInitialize(), nil
	case "notifications/initialized", "initialized":
		return nil, nil
	case "ping":
		return map[string]interface{}{}, nil
	case "tools/list":
		return map[string]interface{}{"tools": s.tools}, nil
	case "tools/call":
		return s.handleToolsCall(params)
	default:
		return nil, newError(codeMethodNotFound, "unknown method: "+method)
	}
}

func (s *Server) handleInitialize() map[string]interface{} {
	return map[string]interface{}{
		"protocolVersion": protocolVersion,
		"capabilities": map[string]interface{}{
			"tools": map[string]interface{}{},
		},
		"serverInfo": map[string]interface{}{
			"name":    s.name,
			"version": s.version,
		},
	}
}

func (s *Server) handleToolsCall(params json.RawMessage) (interface{}, *rpcError) {
	var p struct {
		Name      string                 `json:"name"`
		Arguments map[string]interface{} `json:"arguments"`
	}
	if err := json.Unmarshal(params, &p); err != nil {
		return nil, newError(codeInvalidParams, "invalid params: "+err.Error())
	}
	tool, ok := s.toolIdx[p.Name]
	if !ok {
		return nil, newError(codeMethodNotFound, "unknown tool: "+p.Name)
	}
	if p.Arguments == nil {
		p.Arguments = map[string]interface{}{}
	}
	text, err := tool.handler(p.Arguments)
	if err != nil {
		// Tool-level errors are reported via the result envelope (isError),
		// per MCP conventions, so the LLM can see the message.
		return toolResult(fmt.Sprintf("Error: %v", err), true), nil
	}
	return toolResult(text, false), nil
}

// CallTool invokes a tool directly by name (used in tests).
func (s *Server) CallTool(name string, args map[string]interface{}) (string, error) {
	tool, ok := s.toolIdx[name]
	if !ok {
		return "", fmt.Errorf("unknown tool: %s", name)
	}
	if args == nil {
		args = map[string]interface{}{}
	}
	return tool.handler(args)
}

// toolResult builds the MCP tools/call result envelope.
func toolResult(text string, isErr bool) map[string]interface{} {
	return map[string]interface{}{
		"content": []map[string]interface{}{
			{"type": "text", "text": text},
		},
		"isError": isErr,
	}
}
