// server.go implements the JSON-RPC dispatch loop and the MCP methods:
// initialize, ping, tools/list, tools/call, resources/list, resources/read,
// prompts/list, prompts/get, completion/complete and logging/setLevel.
package mcp

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"sort"
	"strings"
	"sync"
)

// Server is an MCP server. Register tools, resources and prompts, then call
// Serve with a transport (usually stdin/stdout).
type Server struct {
	Name         string
	Title        string
	Version      string
	Instructions string

	// Logf receives diagnostics. Anything written to stdout would corrupt the
	// protocol stream, so this must go to stderr or a file.
	Logf func(format string, args ...any)

	mu          sync.RWMutex
	tools       map[string]*Tool
	toolOrder   []string
	resources   map[string]*Resource
	resOrder    []string
	prompts     map[string]*Prompt
	promptOrder []string
	complete    CompletionFunc

	initialized bool
	clientInfo  Implementation
	negotiated  string

	writeMu sync.Mutex
}

// NewServer creates a server with the given identity.
func NewServer(name, version string) *Server {
	return &Server{
		Name:      name,
		Version:   version,
		tools:     map[string]*Tool{},
		resources: map[string]*Resource{},
		prompts:   map[string]*Prompt{},
		Logf:      func(string, ...any) {},
	}
}

// AddTool registers a tool. Registering the same name twice replaces it.
func (s *Server) AddTool(t *Tool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.tools[t.Name]; !exists {
		s.toolOrder = append(s.toolOrder, t.Name)
	}
	s.tools[t.Name] = t
}

// AddResource registers a readable resource.
func (s *Server) AddResource(r *Resource) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.resources[r.URI]; !exists {
		s.resOrder = append(s.resOrder, r.URI)
	}
	s.resources[r.URI] = r
}

// AddPrompt registers a prompt template.
func (s *Server) AddPrompt(p *Prompt) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, exists := s.prompts[p.Name]; !exists {
		s.promptOrder = append(s.promptOrder, p.Name)
	}
	s.prompts[p.Name] = p
}

// SetCompletion installs the completion provider used by completion/complete.
func (s *Server) SetCompletion(fn CompletionFunc) { s.complete = fn }

// Tools returns the registered tools in registration order.
func (s *Server) Tools() []*Tool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]*Tool, 0, len(s.toolOrder))
	for _, name := range s.toolOrder {
		out = append(out, s.tools[name])
	}
	return out
}

// Tool returns one registered tool.
func (s *Server) Tool(name string) *Tool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.tools[name]
}

// CallTool invokes a tool directly, bypassing the transport. It is what the
// CLI mode and the tests use.
func (s *Server) CallTool(name string, args Args) (*ToolResult, error) {
	tool := s.Tool(name)
	if tool == nil {
		return nil, fmt.Errorf("unknown tool %q", name)
	}
	if args == nil {
		args = Args{}
	}
	// The same validation the protocol path applies, so the CLI and the tests
	// cannot accept arguments a client could not send.
	if err := validate(tool.InputSchema, args); err != nil {
		return ErrorResult("invalid arguments for %s: %v", name, err), nil
	}
	return s.runTool(tool, args)
}

// ---------------------------------------------------------------------------
// Transport
// ---------------------------------------------------------------------------

// Serve reads newline delimited JSON-RPC messages from in and writes responses
// to out until the input is exhausted or the context is cancelled.
func (s *Server) Serve(ctx context.Context, in io.Reader, out io.Writer) error {
	reader := bufio.NewReaderSize(in, 1<<20)
	writer := bufio.NewWriter(out)
	defer writer.Flush()

	for {
		if err := ctx.Err(); err != nil {
			return nil
		}
		line, err := readMessage(reader)
		if err != nil {
			if errors.Is(err, io.EOF) {
				return nil
			}
			return err
		}
		if len(bytes.TrimSpace(line)) == 0 {
			continue
		}
		reply, send := s.HandleMessage(ctx, line)
		if !send {
			continue
		}
		if err := s.write(writer, reply); err != nil {
			return err
		}
	}
}

func readMessage(r *bufio.Reader) ([]byte, error) {
	var buf []byte
	for {
		chunk, err := r.ReadBytes('\n')
		buf = append(buf, chunk...)
		if err == nil {
			return buf, nil
		}
		if errors.Is(err, io.EOF) {
			if len(bytes.TrimSpace(buf)) > 0 {
				return buf, nil
			}
			return nil, io.EOF
		}
		return nil, err
	}
}

// write emits one message, terminator included, as a single write so that a
// reader never sees a response without its newline.
func (s *Server) write(w *bufio.Writer, payload []byte) error {
	s.writeMu.Lock()
	defer s.writeMu.Unlock()
	if _, err := w.Write(append(payload, '\n')); err != nil {
		return err
	}
	return w.Flush()
}

// HandleMessage processes one raw message and returns the raw reply. The
// second result is false when nothing should be written (notifications, or a
// batch that contained only notifications).
func (s *Server) HandleMessage(ctx context.Context, raw []byte) ([]byte, bool) {
	trimmed := bytes.TrimSpace(raw)
	if len(trimmed) == 0 {
		return nil, false
	}
	// JSON-RPC batch (used by MCP revision 2025-03-26).
	if trimmed[0] == '[' {
		var batch []json.RawMessage
		if err := json.Unmarshal(trimmed, &batch); err != nil {
			return marshal(newError(nil, Errorf(CodeParseError, "invalid JSON: %v", err))), true
		}
		if len(batch) == 0 {
			return marshal(newError(nil, Errorf(CodeInvalidRequest, "empty batch"))), true
		}
		var replies []*Response
		for _, item := range batch {
			if resp := s.handleOne(ctx, item); resp != nil {
				replies = append(replies, resp)
			}
		}
		if len(replies) == 0 {
			return nil, false
		}
		return marshal(replies), true
	}
	resp := s.handleOne(ctx, trimmed)
	if resp == nil {
		return nil, false
	}
	return marshal(resp), true
}

func marshal(v any) []byte {
	b, err := json.Marshal(v)
	if err != nil {
		b, _ = json.Marshal(newError(nil, Errorf(CodeInternalError, "failed to encode response: %v", err)))
	}
	return b
}

func (s *Server) handleOne(ctx context.Context, raw []byte) *Response {
	var req Request
	if err := json.Unmarshal(raw, &req); err != nil {
		return newError(nil, Errorf(CodeParseError, "invalid JSON: %v", err))
	}
	// A notification never gets a reply, not even when it is malformed:
	// JSON-RPC 2.0 forbids responding to a message that carries no id.
	if req.IsNotification() {
		if req.JSONRPC == "2.0" && req.Method != "" {
			s.handleNotification(req)
		} else {
			s.Logf("ignoring malformed notification %q", req.Method)
		}
		return nil
	}
	if req.JSONRPC != "2.0" {
		return newError(req.ID, Errorf(CodeInvalidRequest, "jsonrpc must be %q", "2.0"))
	}
	if req.Method == "" {
		return newError(req.ID, Errorf(CodeInvalidRequest, "missing method"))
	}
	if req.HasNullID() {
		return newError(json.RawMessage("null"),
			Errorf(CodeInvalidRequest, "the request id must not be null (MCP forbids it); use a string or a number"))
	}

	result, rpcErr := s.dispatch(ctx, req)
	if rpcErr != nil {
		return newError(req.ID, rpcErr)
	}
	return newResponse(req.ID, result)
}

func (s *Server) handleNotification(req Request) {
	switch req.Method {
	case "notifications/initialized":
		s.mu.Lock()
		s.initialized = true
		s.mu.Unlock()
	case "notifications/cancelled":
		// Requests are served synchronously, so there is nothing to cancel.
	default:
		s.Logf("ignoring notification %s", req.Method)
	}
}

func (s *Server) dispatch(ctx context.Context, req Request) (any, *RPCError) {
	switch req.Method {
	case "initialize":
		return s.handleInitialize(req)
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		return s.handleToolsList()
	case "tools/call":
		return s.handleToolsCall(ctx, req)
	case "resources/list":
		return s.handleResourcesList()
	case "resources/templates/list":
		return map[string]any{"resourceTemplates": []any{}}, nil
	case "resources/read":
		return s.handleResourcesRead(req)
	case "prompts/list":
		return s.handlePromptsList()
	case "prompts/get":
		return s.handlePromptsGet(req)
	case "completion/complete":
		return s.handleComplete(req)
	case "logging/setLevel":
		return map[string]any{}, nil
	}
	return nil, Errorf(CodeMethodNotFound, "unknown method %q", req.Method)
}

func (s *Server) handleInitialize(req Request) (any, *RPCError) {
	var p initializeParams
	if len(req.Params) > 0 {
		if err := json.Unmarshal(req.Params, &p); err != nil {
			return nil, Errorf(CodeInvalidParams, "invalid initialize params: %v", err)
		}
	}
	version := LatestVersion
	for _, v := range supportedVersions {
		if v == p.ProtocolVersion {
			version = v
			break
		}
	}
	s.mu.Lock()
	s.clientInfo = p.ClientInfo
	s.negotiated = version
	s.mu.Unlock()
	s.Logf("initialize from %s %s (protocol %s -> %s)", p.ClientInfo.Name, p.ClientInfo.Version, p.ProtocolVersion, version)

	// No "logging" capability: logging/setLevel is accepted for tolerance, but
	// this server never emits log notifications, so it must not claim it.
	caps := map[string]any{
		"tools":       map[string]any{"listChanged": false},
		"resources":   map[string]any{"subscribe": false, "listChanged": false},
		"prompts":     map[string]any{"listChanged": false},
		"completions": map[string]any{},
	}
	return initializeResult{
		ProtocolVersion: version,
		Capabilities:    caps,
		ServerInfo:      Implementation{Name: s.Name, Title: s.Title, Version: s.Version},
		Instructions:    s.Instructions,
	}, nil
}

func (s *Server) handleToolsList() (any, *RPCError) {
	return map[string]any{"tools": s.Tools()}, nil
}

type callToolParams struct {
	Name      string `json:"name"`
	Arguments Args   `json:"arguments"`
}

func (s *Server) handleToolsCall(ctx context.Context, req Request) (any, *RPCError) {
	var p callToolParams
	if err := json.Unmarshal(req.Params, &p); err != nil {
		return nil, Errorf(CodeInvalidParams, "invalid tools/call params: %v", err)
	}
	if p.Name == "" {
		return nil, Errorf(CodeInvalidParams, "tools/call requires a tool name")
	}
	tool := s.Tool(p.Name)
	if tool == nil {
		return nil, Errorf(CodeInvalidParams, "unknown tool %q (call tools/list for the catalogue)", p.Name)
	}
	if p.Arguments == nil {
		p.Arguments = Args{}
	}
	if err := validate(tool.InputSchema, p.Arguments); err != nil {
		return ErrorResult("invalid arguments for %s: %v", p.Name, err), nil
	}
	if err := ctx.Err(); err != nil {
		return nil, Errorf(CodeInternalError, "server shutting down")
	}
	result, err := s.runTool(tool, p.Arguments)
	if err != nil {
		return ErrorResult("%s failed: %v", p.Name, err), nil
	}
	return result, nil
}

// runTool isolates a tool call from panics so that one bad query cannot take
// the server down mid-session.
func (s *Server) runTool(tool *Tool, args Args) (result *ToolResult, err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("internal error: %v", r)
			s.Logf("tool %s panicked: %v", tool.Name, r)
		}
	}()
	return tool.Handler(args)
}

// validate checks required arguments, types and enum membership. It is
// deliberately forgiving about numbers arriving as strings.
func validate(schema *Schema, args Args) error {
	if schema == nil {
		return nil
	}
	for _, req := range schema.Required {
		if !args.Has(req) {
			return fmt.Errorf("missing required argument %q", req)
		}
	}
	var unknown []string
	for key, value := range args {
		prop, ok := schema.Properties[key]
		if !ok {
			unknown = append(unknown, key)
			continue
		}
		if value == nil {
			continue
		}
		switch prop.Type {
		case "integer", "number":
			if _, err := (Args{key: value}).Int(key, 0); err != nil {
				return err
			}
		case "boolean":
			if _, err := (Args{key: value}).Bool(key, false); err != nil {
				return err
			}
		case "array":
			switch value.(type) {
			case []any, []string, string:
			default:
				return fmt.Errorf("argument %q must be an array", key)
			}
		}
		if len(prop.Enum) > 0 {
			got := (Args{key: value}).String(key)
			if got == "" {
				continue
			}
			allowed := false
			for _, e := range prop.Enum {
				if strings.EqualFold(e, got) {
					allowed = true
					break
				}
			}
			if !allowed {
				return fmt.Errorf("argument %q must be one of %s, got %q", key, strings.Join(prop.Enum, ", "), got)
			}
		}
	}
	if len(unknown) > 0 {
		sort.Strings(unknown)
		known := make([]string, 0, len(schema.Properties))
		for name := range schema.Properties {
			known = append(known, name)
		}
		sort.Strings(known)
		return fmt.Errorf("unknown argument(s) %s; supported: %s", strings.Join(unknown, ", "), strings.Join(known, ", "))
	}
	return nil
}

func (s *Server) handleResourcesList() (any, *RPCError) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]*Resource, 0, len(s.resOrder))
	for _, uri := range s.resOrder {
		out = append(out, s.resources[uri])
	}
	return map[string]any{"resources": out}, nil
}

func (s *Server) handleResourcesRead(req Request) (any, *RPCError) {
	var p struct {
		URI string `json:"uri"`
	}
	if err := json.Unmarshal(req.Params, &p); err != nil {
		return nil, Errorf(CodeInvalidParams, "invalid resources/read params: %v", err)
	}
	s.mu.RLock()
	res := s.resources[p.URI]
	s.mu.RUnlock()
	if res == nil {
		return nil, Errorf(CodeInvalidParams, "unknown resource %q", p.URI)
	}
	text, err := res.Reader()
	if err != nil {
		return nil, Errorf(CodeInternalError, "reading %s: %v", p.URI, err)
	}
	mime := res.MIMEType
	if mime == "" {
		mime = "text/plain"
	}
	return map[string]any{
		"contents": []ResourceContents{{URI: res.URI, MIMEType: mime, Text: text}},
	}, nil
}

func (s *Server) handlePromptsList() (any, *RPCError) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]*Prompt, 0, len(s.promptOrder))
	for _, name := range s.promptOrder {
		out = append(out, s.prompts[name])
	}
	return map[string]any{"prompts": out}, nil
}

func (s *Server) handlePromptsGet(req Request) (any, *RPCError) {
	var p struct {
		Name      string            `json:"name"`
		Arguments map[string]string `json:"arguments"`
	}
	if err := json.Unmarshal(req.Params, &p); err != nil {
		return nil, Errorf(CodeInvalidParams, "invalid prompts/get params: %v", err)
	}
	s.mu.RLock()
	prompt := s.prompts[p.Name]
	s.mu.RUnlock()
	if prompt == nil {
		return nil, Errorf(CodeInvalidParams, "unknown prompt %q", p.Name)
	}
	for _, arg := range prompt.Arguments {
		if arg.Required && strings.TrimSpace(p.Arguments[arg.Name]) == "" {
			return nil, Errorf(CodeInvalidParams, "prompt %q requires argument %q", p.Name, arg.Name)
		}
	}
	desc, text, err := prompt.Render(p.Arguments)
	if err != nil {
		return nil, Errorf(CodeInternalError, "rendering prompt %q: %v", p.Name, err)
	}
	return getPromptResult{
		Description: desc,
		Messages:    []PromptMessage{{Role: "user", Content: TextContent(text)}},
	}, nil
}

func (s *Server) handleComplete(req Request) (any, *RPCError) {
	var p struct {
		Ref struct {
			Type string `json:"type"`
			Name string `json:"name"`
			URI  string `json:"uri"`
		} `json:"ref"`
		Argument struct {
			Name  string `json:"name"`
			Value string `json:"value"`
		} `json:"argument"`
	}
	if err := json.Unmarshal(req.Params, &p); err != nil {
		return nil, Errorf(CodeInvalidParams, "invalid completion/complete params: %v", err)
	}
	var values []string
	if s.complete != nil {
		ref := p.Ref.Name
		if ref == "" {
			ref = p.Ref.URI
		}
		values = s.complete(ref, p.Argument.Name, p.Argument.Value)
	}
	const maxValues = 100
	total := len(values)
	hasMore := false
	if total > maxValues {
		values, hasMore = values[:maxValues], true
	}
	if values == nil {
		values = []string{}
	}
	return map[string]any{
		"completion": map[string]any{"values": values, "total": total, "hasMore": hasMore},
	}, nil
}
