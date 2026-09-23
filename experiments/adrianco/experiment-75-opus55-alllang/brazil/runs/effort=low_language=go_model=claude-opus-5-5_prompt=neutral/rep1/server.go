package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
)

const protocolVersion = "2024-11-05"

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

// Server is a stdio MCP server over newline-delimited JSON-RPC.
type Server struct {
	db    *DB
	tools map[string]Tool
	list  []Tool
}

func NewServer(db *DB) *Server {
	s := &Server{db: db, tools: map[string]Tool{}, list: Tools()}
	for _, t := range s.list {
		s.tools[t.Name] = t
	}
	return s
}

// CallTool runs a tool by name and returns its text output.
func (s *Server) CallTool(name string, args Args) (string, error) {
	t, ok := s.tools[name]
	if !ok {
		return "", fmt.Errorf("unknown tool %q", name)
	}
	return t.handler(s.db, args)
}

// Handle processes one request; returns nil for notifications.
func (s *Server) Handle(req rpcRequest) *rpcResponse {
	resp := &rpcResponse{JSONRPC: "2.0", ID: req.ID}
	switch req.Method {
	case "initialize":
		resp.Result = map[string]any{
			"protocolVersion": protocolVersion,
			"capabilities":    map[string]any{"tools": map[string]any{}},
			"serverInfo":      map[string]any{"name": "brazilian-soccer-mcp", "version": "1.0.0"},
		}
	case "ping":
		resp.Result = map[string]any{}
	case "tools/list":
		resp.Result = map[string]any{"tools": s.list}
	case "tools/call":
		var p struct {
			Name      string `json:"name"`
			Arguments Args   `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &p); err != nil {
			resp.Error = &rpcError{-32602, "invalid params: " + err.Error()}
			break
		}
		if _, ok := s.tools[p.Name]; !ok {
			resp.Error = &rpcError{-32602, "unknown tool: " + p.Name}
			break
		}
		text, err := s.CallTool(p.Name, p.Arguments)
		isErr := err != nil
		if isErr {
			text = "Error: " + err.Error()
		}
		resp.Result = map[string]any{"content": []map[string]any{{"type": "text", "text": text}}, "isError": isErr}
	default:
		if len(req.ID) == 0 { // notification, e.g. notifications/initialized
			return nil
		}
		resp.Error = &rpcError{-32601, "method not found: " + req.Method}
	}
	if len(req.ID) == 0 {
		return nil
	}
	return resp
}

// Serve reads requests from r and writes responses to w until EOF.
func (s *Server) Serve(r io.Reader, w io.Writer) error {
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 1<<20), 16<<20)
	enc := json.NewEncoder(w)
	for sc.Scan() {
		line := sc.Bytes()
		if len(line) == 0 {
			continue
		}
		var req rpcRequest
		if err := json.Unmarshal(line, &req); err != nil {
			enc.Encode(rpcResponse{JSONRPC: "2.0", ID: json.RawMessage("null"), Error: &rpcError{-32700, "parse error"}})
			continue
		}
		if resp := s.Handle(req); resp != nil {
			if err := enc.Encode(resp); err != nil {
				return err
			}
		}
	}
	return sc.Err()
}

func main() {
	dir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV files")
	flag.Parse()
	log.SetOutput(os.Stderr)
	db, err := LoadDB(*dir)
	if err != nil {
		log.Fatalf("loading data: %v", err)
	}
	log.Printf("loaded %d matches, %d players", len(db.Matches), len(db.Players))
	if err := NewServer(db).Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatal(err)
	}
}
