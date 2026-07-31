// world.go holds the state a scenario builds up as its steps run: the loaded
// graph, a live MCP session, and the result of the most recent tool call.
//
// Steps talk to the server through the real protocol, so a passing scenario
// proves the whole path works - argument schema, handler, formatter and JSON-RPC
// encoding - not just the Go query functions underneath.
package bdd

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcpserver"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// World is the per-scenario context.
type World struct {
	Graph   *soccer.Graph
	Session *mcp.ClientSession

	// Set by the most recent tool call.
	Tool       string
	Text       string
	Structured map[string]any
	CallErr    error
	Elapsed    time.Duration
}

// NewWorld connects a client to a server sharing the given graph.
func NewWorld(ctx context.Context, graph *soccer.Graph) (*World, error) {
	srv := mcpserver.NewWithGraph(graph)
	serverTransport, clientTransport := mcp.NewInMemoryTransports()
	if _, err := srv.MCP().Connect(ctx, serverTransport, nil); err != nil {
		return nil, err
	}
	client := mcp.NewClient(&mcp.Implementation{Name: "bdd-runner", Version: mcpserver.Version}, nil)
	session, err := client.Connect(ctx, clientTransport, nil)
	if err != nil {
		return nil, err
	}
	return &World{Graph: graph, Session: session}, nil
}

// Close ends the session.
func (w *World) Close() {
	if w.Session != nil {
		w.Session.Close()
	}
}

// Call runs a tool and records the outcome. A tool that reports an error stores
// it in CallErr rather than failing the scenario, so that a "Then the call
// should fail" step can assert on it.
func (w *World) Call(tool string, args map[string]any) {
	w.Tool, w.Text, w.Structured, w.CallErr = tool, "", nil, nil
	start := time.Now()
	res, err := w.Session.CallTool(context.Background(), &mcp.CallToolParams{Name: tool, Arguments: args})
	w.Elapsed = time.Since(start)
	if err != nil {
		w.CallErr = err
		return
	}
	var parts []string
	for _, c := range res.Content {
		if text, ok := c.(*mcp.TextContent); ok {
			parts = append(parts, text.Text)
		}
	}
	w.Text = strings.Join(parts, "\n")
	if res.IsError {
		w.CallErr = fmt.Errorf("%s", w.Text)
		return
	}
	if res.StructuredContent != nil {
		raw, err := json.Marshal(res.StructuredContent)
		if err != nil {
			w.CallErr = err
			return
		}
		if err := json.Unmarshal(raw, &w.Structured); err != nil {
			w.CallErr = err
		}
	}
}

// ok returns an error when the last call failed, so assertion steps do not have
// to repeat the check.
func (w *World) ok() error {
	if w.CallErr != nil {
		return fmt.Errorf("the %s call failed: %v", w.Tool, w.CallErr)
	}
	return nil
}

// list reads an array field out of the structured payload.
func (w *World) list(field string) ([]map[string]any, error) {
	if err := w.ok(); err != nil {
		return nil, err
	}
	raw, ok := w.Structured[field]
	if !ok {
		return nil, fmt.Errorf("the %s result has no %q field (fields: %s)", w.Tool, field, strings.Join(keysOf(w.Structured), ", "))
	}
	items, ok := raw.([]any)
	if !ok {
		return nil, fmt.Errorf("field %q of the %s result is not a list", field, w.Tool)
	}
	out := make([]map[string]any, 0, len(items))
	for _, item := range items {
		m, ok := item.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("field %q contains a non-object entry", field)
		}
		out = append(out, m)
	}
	return out, nil
}

// number reads a numeric field out of the structured payload.
func (w *World) number(field string) (float64, error) {
	if err := w.ok(); err != nil {
		return 0, err
	}
	raw, ok := w.Structured[field]
	if !ok {
		return 0, fmt.Errorf("the %s result has no %q field", w.Tool, field)
	}
	n, ok := raw.(float64)
	if !ok {
		return 0, fmt.Errorf("field %q of the %s result is not a number", field, w.Tool)
	}
	return n, nil
}

// text reads a string field out of the structured payload.
func (w *World) text(field string) (string, error) {
	if err := w.ok(); err != nil {
		return "", err
	}
	raw, ok := w.Structured[field]
	if !ok {
		return "", fmt.Errorf("the %s result has no %q field", w.Tool, field)
	}
	s, ok := raw.(string)
	if !ok {
		return "", fmt.Errorf("field %q of the %s result is not a string", field, w.Tool)
	}
	return s, nil
}

func keysOf(m map[string]any) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	return out
}

// str returns the string value of a nested field, or "" when absent.
func str(m map[string]any, field string) string {
	if v, ok := m[field].(string); ok {
		return v
	}
	return ""
}

// num returns the numeric value of a nested field, or 0 when absent.
func num(m map[string]any, field string) float64 {
	if v, ok := m[field].(float64); ok {
		return v
	}
	return 0
}
