// mcp.go — a minimal Model Context Protocol server (JSON-RPC 2.0 over stdio).
//
// Messages are newline-delimited JSON objects as defined by the MCP stdio
// transport. Supported methods: initialize, notifications/initialized, ping,
// tools/list, tools/call, plus empty resources/prompts listings so clients
// that probe for them get a valid answer. Batches are accepted.
package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"sync"
	"time"
)

const (
	serverName    = "brazilian-soccer-mcp"
	serverVersion = "1.0.0"
	// latestProtocol is offered when the client asks for a version we do not know.
	latestProtocol = "2025-06-18"
)

var supportedProtocols = map[string]bool{
	"2024-11-05": true, "2025-03-26": true, "2025-06-18": true,
}

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

// Server serves MCP requests against a Store.
type Server struct {
	store *Store
	tools []Tool
	mu    sync.Mutex // serialises writes
	// Log receives one line per tool call (nil to disable).
	Log io.Writer
}

// NewServer creates an MCP server.
func NewServer(s *Store) *Server { return &Server{store: s, tools: Tools()} }

// Serve reads requests from r and writes responses to w until EOF.
func (srv *Server) Serve(r io.Reader, w io.Writer) error {
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 1024*1024), 16*1024*1024)
	for sc.Scan() {
		line := bytes.TrimSpace(sc.Bytes())
		if len(line) == 0 {
			continue
		}
		out := srv.HandleMessage(line)
		if out == nil {
			continue
		}
		srv.mu.Lock()
		_, err := w.Write(append(out, '\n'))
		srv.mu.Unlock()
		if err != nil {
			return err
		}
	}
	return sc.Err()
}

// HandleMessage processes one JSON-RPC message (single or batch) and returns
// the encoded response, or nil when no response is due (notifications).
func (srv *Server) HandleMessage(msg []byte) []byte {
	if len(msg) > 0 && msg[0] == '[' {
		var batch []json.RawMessage
		if err := json.Unmarshal(msg, &batch); err != nil {
			return mustJSON(rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &rpcError{-32700, "parse error"}})
		}
		var outs []json.RawMessage
		for _, m := range batch {
			if resp := srv.handleOne(m); resp != nil {
				outs = append(outs, mustJSON(resp))
			}
		}
		if len(outs) == 0 {
			return nil
		}
		return mustJSON(outs)
	}
	resp := srv.handleOne(msg)
	if resp == nil {
		return nil
	}
	return mustJSON(resp)
}

func mustJSON(v any) []byte {
	b, err := json.Marshal(v)
	if err != nil {
		b, _ = json.Marshal(rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &rpcError{-32603, err.Error()}})
	}
	return b
}

func (srv *Server) handleOne(raw json.RawMessage) *rpcResponse {
	var req rpcRequest
	if err := json.Unmarshal(raw, &req); err != nil {
		return &rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &rpcError{-32700, "parse error: " + err.Error()}}
	}
	isNotification := len(req.ID) == 0 || string(req.ID) == "null"
	if req.Method == "" {
		if isNotification {
			return nil // a response from the client; nothing to do
		}
		return &rpcResponse{JSONRPC: "2.0", ID: req.ID, Error: &rpcError{-32600, "invalid request: missing method"}}
	}
	result, rerr := srv.dispatch(req)
	if isNotification {
		return nil
	}
	resp := &rpcResponse{JSONRPC: "2.0", ID: req.ID}
	if rerr != nil {
		resp.Error = rerr
	} else {
		resp.Result = result
	}
	return resp
}

func (srv *Server) dispatch(req rpcRequest) (any, *rpcError) {
	switch req.Method {
	case "initialize":
		var p struct {
			ProtocolVersion string `json:"protocolVersion"`
		}
		_ = json.Unmarshal(req.Params, &p)
		version := latestProtocol
		if supportedProtocols[p.ProtocolVersion] {
			version = p.ProtocolVersion
		}
		return map[string]any{
			"protocolVersion": version,
			"capabilities": map[string]any{
				"tools": map[string]any{"listChanged": false},
			},
			"serverInfo": map[string]any{"name": serverName, "version": serverVersion},
			"instructions": "Brazilian soccer knowledge base: Brasileirão (2003-2023), Série B/C (2014-2023), Copa do Brasil (2012-2023), " +
				"Copa Libertadores (2013-2022) and FIFA 19 players. Team names are normalised, so any common spelling works. " +
				"Start with search_matches, team_record, head_to_head, standings or search_players.",
		}, nil
	case "ping":
		return map[string]any{}, nil
	case "tools/list":
		return map[string]any{"tools": srv.tools}, nil
	case "resources/list":
		return map[string]any{"resources": []any{}}, nil
	case "resources/templates/list":
		return map[string]any{"resourceTemplates": []any{}}, nil
	case "prompts/list":
		return map[string]any{"prompts": []any{}}, nil
	case "tools/call":
		var p struct {
			Name      string `json:"name"`
			Arguments Args   `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			return nil, &rpcError{-32602, "invalid params: " + err.Error()}
		}
		known := false
		for _, t := range srv.tools {
			if t.Name == p.Name {
				known = true
			}
		}
		if !known {
			return nil, &rpcError{-32602, fmt.Sprintf("unknown tool %q", p.Name)}
		}
		start := time.Now()
		text, err := CallTool(srv.store, p.Name, p.Arguments)
		if srv.Log != nil {
			fmt.Fprintf(srv.Log, "tool %s %v in %s (error: %v)\n", p.Name, map[string]any(p.Arguments), time.Since(start), err)
		}
		if err != nil {
			return map[string]any{
				"content": []map[string]any{{"type": "text", "text": "Error: " + err.Error()}},
				"isError": true,
			}, nil
		}
		return map[string]any{
			"content": []map[string]any{{"type": "text", "text": text}},
			"isError": false,
		}, nil
	}
	if len(req.Method) > 14 && req.Method[:14] == "notifications/" {
		return nil, nil
	}
	return nil, &rpcError{-32601, "method not found: " + req.Method}
}
