package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
)

const (
	mcpProtocolVersion = "2024-11-05"
	serverName         = "brazilian-soccer-mcp"
	serverVersion      = "1.0.0"
)

// Tool describes an MCP tool: its name, human-readable description, and the
// JSON Schema its arguments must satisfy.
type Tool struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	InputSchema json.RawMessage `json:"inputSchema"`
}

// ToolHandler executes a tool call against the Store and returns the
// human-readable text response.
type ToolHandler func(store *Store, args json.RawMessage) (string, error)

type toolDef struct {
	Tool
	Handler ToolHandler
}

// ToolRegistry holds every tool the server exposes, keyed by name.
type ToolRegistry struct {
	order  []string
	byName map[string]toolDef
}

func NewToolRegistry() *ToolRegistry {
	return &ToolRegistry{byName: make(map[string]toolDef)}
}

func (tr *ToolRegistry) Register(t Tool, h ToolHandler) {
	tr.order = append(tr.order, t.Name)
	tr.byName[t.Name] = toolDef{Tool: t, Handler: h}
}

func (tr *ToolRegistry) List() []Tool {
	tools := make([]Tool, 0, len(tr.order))
	for _, name := range tr.order {
		tools = append(tools, tr.byName[name].Tool)
	}
	return tools
}

type initializeResult struct {
	ProtocolVersion string            `json:"protocolVersion"`
	Capabilities    map[string]any    `json:"capabilities"`
	ServerInfo      map[string]string `json:"serverInfo"`
}

type toolsListResult struct {
	Tools []Tool `json:"tools"`
}

type callToolParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

type content struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type callToolResult struct {
	Content []content `json:"content"`
	IsError bool      `json:"isError"`
}

// Server implements the MCP stdio JSON-RPC transport: newline-delimited
// JSON-RPC 2.0 messages on stdin/stdout.
type Server struct {
	store    *Store
	registry *ToolRegistry
}

func NewServer(store *Store, registry *ToolRegistry) *Server {
	return &Server{store: store, registry: registry}
}

// Run reads JSON-RPC requests from r, dispatches them, and writes responses
// to w until r reaches EOF. Log output (never protocol traffic) goes to
// errOut.
func (s *Server) Run(r io.Reader, w io.Writer, errOut io.Writer) error {
	logger := log.New(errOut, "", log.LstdFlags)
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var req rpcRequest
		if err := json.Unmarshal(line, &req); err != nil {
			writeMessage(w, newError(nil, codeParseError, "parse error: "+err.Error()))
			continue
		}
		resp, hasResp := s.handle(req)
		if !hasResp {
			continue
		}
		if err := writeMessage(w, resp); err != nil {
			logger.Printf("write error: %v", err)
		}
	}
	return scanner.Err()
}

func (s *Server) handle(req rpcRequest) (rpcResponse, bool) {
	switch req.Method {
	case "initialize":
		return newResult(req.ID, initializeResult{
			ProtocolVersion: mcpProtocolVersion,
			Capabilities:    map[string]any{"tools": map[string]any{}},
			ServerInfo:      map[string]string{"name": serverName, "version": serverVersion},
		}), !req.isNotification()

	case "notifications/initialized", "notifications/cancelled":
		return rpcResponse{}, false

	case "ping":
		return newResult(req.ID, map[string]any{}), !req.isNotification()

	case "tools/list":
		return newResult(req.ID, toolsListResult{Tools: s.registry.List()}), !req.isNotification()

	case "tools/call":
		return s.handleToolsCall(req)

	default:
		if req.isNotification() {
			return rpcResponse{}, false
		}
		return newError(req.ID, codeMethodNotFound, fmt.Sprintf("method not found: %s", req.Method)), true
	}
}

func (s *Server) handleToolsCall(req rpcRequest) (rpcResponse, bool) {
	var params callToolParams
	if err := json.Unmarshal(req.Params, &params); err != nil {
		return newError(req.ID, codeInvalidParams, "invalid params: "+err.Error()), !req.isNotification()
	}

	tool, ok := s.registry.byName[params.Name]
	if !ok {
		return newError(req.ID, codeInvalidParams, "unknown tool: "+params.Name), !req.isNotification()
	}

	text, err := tool.Handler(s.store, params.Arguments)
	if err != nil {
		result := callToolResult{
			Content: []content{{Type: "text", Text: err.Error()}},
			IsError: true,
		}
		return newResult(req.ID, result), !req.isNotification()
	}

	result := callToolResult{Content: []content{{Type: "text", Text: text}}}
	return newResult(req.ID, result), !req.isNotification()
}

func writeMessage(w io.Writer, resp rpcResponse) error {
	data, err := json.Marshal(resp)
	if err != nil {
		return err
	}
	data = append(data, '\n')
	_, err = w.Write(data)
	return err
}
