// server.go is the transport and dispatch half of the MCP implementation: it
// reads newline delimited JSON-RPC messages from a reader, routes them to
// registered tool handlers, and writes responses to a writer. It is transport
// agnostic so tests can drive it over buffers instead of stdio.
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sort"
	"sync"
)

// Handler executes a tool call. Returning an error produces a tool result with
// isError set, which is what the MCP spec wants for recoverable failures so the
// model can see and react to the message.
type Handler func(args Args) (*CallToolResult, error)

// Server routes JSON-RPC messages to tool handlers.
type Server struct {
	info     Implementation
	instruct string

	mu       sync.RWMutex
	tools    map[string]Tool
	handlers map[string]Handler
}

// NewServer creates a server with the given identity and instructions.
func NewServer(name, version, instructions string) *Server {
	return &Server{
		info:     Implementation{Name: name, Version: version},
		instruct: instructions,
		tools:    map[string]Tool{},
		handlers: map[string]Handler{},
	}
}

// Register adds a tool and its handler.
func (s *Server) Register(t Tool, h Handler) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.tools[t.Name] = t
	s.handlers[t.Name] = h
}

// Tools returns the registered tools sorted by name.
func (s *Server) Tools() []Tool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]Tool, 0, len(s.tools))
	for _, t := range s.tools {
		out = append(out, t)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	return out
}

// Serve reads requests from r until EOF, writing responses to w.
func (s *Server) Serve(r io.Reader, w io.Writer) error {
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	enc := json.NewEncoder(w)

	for sc.Scan() {
		line := sc.Bytes()
		if len(trimSpace(line)) == 0 {
			continue
		}
		resp, send := s.HandleMessage(line)
		if !send {
			continue
		}
		if err := enc.Encode(resp); err != nil {
			return err
		}
	}
	return sc.Err()
}

func trimSpace(b []byte) []byte {
	i, j := 0, len(b)
	for i < j && (b[i] == ' ' || b[i] == '\t' || b[i] == '\r' || b[i] == '\n') {
		i++
	}
	for j > i && (b[j-1] == ' ' || b[j-1] == '\t' || b[j-1] == '\r' || b[j-1] == '\n') {
		j--
	}
	return b[i:j]
}

// HandleMessage processes a single raw JSON-RPC message. The second return
// value reports whether a response should be sent (notifications get none).
func (s *Server) HandleMessage(raw []byte) (*Response, bool) {
	var req Request
	if err := json.Unmarshal(raw, &req); err != nil {
		return &Response{JSONRPC: "2.0", ID: json.RawMessage("null"),
			Error: Errorf(CodeParseError, "invalid JSON: "+err.Error())}, true
	}
	notification := req.IsNotification()
	result, rpcErr := s.dispatch(&req)
	if notification {
		return nil, false
	}
	resp := &Response{JSONRPC: "2.0", ID: req.ID}
	if rpcErr != nil {
		resp.Error = rpcErr
	} else {
		resp.Result = result
	}
	return resp, true
}

// dispatch routes one request by method name.
func (s *Server) dispatch(req *Request) (any, *RPCError) {
	switch req.Method {
	case "initialize":
		return InitializeResult{
			ProtocolVersion: ProtocolVersion,
			Capabilities:    Capabilities{Tools: &ToolsCapability{}},
			ServerInfo:      s.info,
			Instructions:    s.instruct,
		}, nil

	case "notifications/initialized", "notifications/cancelled":
		return struct{}{}, nil

	case "ping":
		return struct{}{}, nil

	case "tools/list":
		return ListToolsResult{Tools: s.Tools()}, nil

	case "tools/call":
		var p CallToolParams
		if len(req.Params) > 0 {
			if err := json.Unmarshal(req.Params, &p); err != nil {
				return nil, Errorf(CodeInvalidParams, "invalid params: "+err.Error())
			}
		}
		s.mu.RLock()
		h, ok := s.handlers[p.Name]
		s.mu.RUnlock()
		if !ok {
			return nil, Errorf(CodeInvalidParams, fmt.Sprintf("unknown tool %q", p.Name))
		}
		res, err := h(Args(p.Arguments))
		if err != nil {
			// Tool level failures are reported in-band, per the MCP spec.
			return &CallToolResult{Content: []Content{TextContent(err.Error())}, IsError: true}, nil
		}
		return res, nil

	default:
		return nil, Errorf(CodeMethodNotFound, fmt.Sprintf("unknown method %q", req.Method))
	}
}
