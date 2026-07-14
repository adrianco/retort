package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"strings"
)

// Request is a JSON-RPC 2.0 request or notification.
type Request struct {
	JSONRPC string          `json:"jsonrpc"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
	ID      json.RawMessage `json:"id,omitempty"`
}

// Response is a JSON-RPC 2.0 response.
type Response struct {
	JSONRPC string          `json:"jsonrpc"`
	Result  interface{}     `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
	ID      json.RawMessage `json:"id,omitempty"`
}

// RPCError is a JSON-RPC 2.0 error object.
type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// Server holds all server state.
type Server struct {
	db *Database
}

func newServer(db *Database) *Server {
	return &Server{db: db}
}

func main() {
	log.SetOutput(os.Stderr)
	log.SetFlags(log.Ltime)

	dataDir := os.Getenv("DATA_DIR")
	if dataDir == "" {
		dataDir = "./data/kaggle"
	}

	log.Printf("Loading database from %s", dataDir)
	db, err := loadDatabase(dataDir)
	if err != nil {
		log.Fatalf("Failed to load database: %v", err)
	}
	log.Printf("Loaded %d matches, %d players", len(db.Matches), len(db.Players))

	srv := newServer(db)
	srv.serve(os.Stdin, os.Stdout)
}

func (s *Server) serve(in io.Reader, out io.Writer) {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 4*1024*1024), 4*1024*1024)

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}

		var req Request
		if err := json.Unmarshal([]byte(line), &req); err != nil {
			log.Printf("Failed to parse request: %v", err)
			continue
		}

		resp := s.handle(&req)
		if resp == nil {
			continue
		}

		data, err := json.Marshal(resp)
		if err != nil {
			log.Printf("Failed to marshal response: %v", err)
			continue
		}
		fmt.Fprintf(out, "%s\n", data)
	}

	if err := scanner.Err(); err != nil {
		log.Printf("stdin read error: %v", err)
	}
}

func isNotification(req *Request) bool {
	return req.ID == nil || string(req.ID) == "null"
}

func (s *Server) handle(req *Request) *Response {
	log.Printf("→ %s", req.Method)

	switch req.Method {
	case "initialize":
		return &Response{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result:  s.handleInitialize(),
		}

	case "notifications/initialized", "initialized":
		return nil // notification, no response

	case "tools/list":
		return &Response{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result:  s.handleToolsList(),
		}

	case "tools/call":
		result, err := s.handleToolCall(req.Params)
		if err != nil {
			return &Response{
				JSONRPC: "2.0",
				ID:      req.ID,
				Error:   &RPCError{Code: -32603, Message: err.Error()},
			}
		}
		return &Response{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result:  result,
		}

	case "ping":
		return &Response{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result:  map[string]interface{}{},
		}

	default:
		if isNotification(req) {
			return nil
		}
		return &Response{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error:   &RPCError{Code: -32601, Message: fmt.Sprintf("method not found: %s", req.Method)},
		}
	}
}
