// e2e_test.go drives the real server the way an MCP client does: newline
// delimited JSON-RPC over a pipe, from initialize to tool calls, resources and
// prompts.
package soccerserver

import (
	"bufio"
	"context"
	"encoding/json"
	"io"
	"strings"
	"testing"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcp"
)

// client reads whole lines rather than decoding straight off the stream: the
// transport is newline delimited, and a json.Decoder stops at the closing
// brace, which would leave the server blocked writing the newline that
// follows a large response.
type client struct {
	t      *testing.T
	out    io.WriteCloser
	in     *bufio.Reader
	nextID int
}

func (c *client) request(method string, params any) map[string]any {
	c.t.Helper()
	c.nextID++
	msg := map[string]any{"jsonrpc": "2.0", "id": c.nextID, "method": method}
	if params != nil {
		msg["params"] = params
	}
	raw, _ := json.Marshal(msg)
	if _, err := c.out.Write(append(raw, '\n')); err != nil {
		c.t.Fatalf("writing %s: %v", method, err)
	}
	line, err := c.in.ReadBytes('\n')
	if err != nil {
		c.t.Fatalf("reading the response to %s: %v", method, err)
	}
	var resp map[string]any
	if err := json.Unmarshal(line, &resp); err != nil {
		c.t.Fatalf("the server wrote a non-JSON line for %s: %q", method, line)
	}
	if e, ok := resp["error"]; ok {
		c.t.Fatalf("%s failed: %v", method, e)
	}
	result, ok := resp["result"].(map[string]any)
	if !ok {
		c.t.Fatalf("%s returned %v", method, resp)
	}
	return result
}

func (c *client) notify(method string) {
	c.t.Helper()
	raw, _ := json.Marshal(map[string]any{"jsonrpc": "2.0", "method": method})
	if _, err := c.out.Write(append(raw, '\n')); err != nil {
		c.t.Fatalf("writing %s: %v", method, err)
	}
}

func TestEndToEndSession(t *testing.T) {
	srv := testServer(t)
	clientIn, serverOut := io.Pipe()
	serverIn, clientOut := io.Pipe()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	done := make(chan error, 1)
	go func() { done <- srv.Serve(ctx, serverIn, serverOut) }()

	c := &client{t: t, out: clientOut, in: bufio.NewReaderSize(clientIn, 1<<20)}

	// 1. Handshake.
	init := c.request("initialize", map[string]any{
		"protocolVersion": mcp.LatestVersion,
		"capabilities":    map[string]any{},
		"clientInfo":      map[string]any{"name": "e2e-test", "version": "1.0"},
	})
	if init["protocolVersion"] != mcp.LatestVersion {
		t.Errorf("negotiated %v", init["protocolVersion"])
	}
	serverInfo := init["serverInfo"].(map[string]any)
	if serverInfo["name"] != ServerName {
		t.Errorf("serverInfo = %v", serverInfo)
	}
	instructions, _ := init["instructions"].(string)
	if !strings.Contains(instructions, "Brazilian football") {
		t.Errorf("instructions = %q", instructions)
	}
	c.notify("notifications/initialized")

	// 2. Discover the tools.
	list := c.request("tools/list", nil)
	tools := list["tools"].([]any)
	if len(tools) < 15 {
		t.Fatalf("server advertises %d tools", len(tools))
	}
	names := map[string]bool{}
	for _, item := range tools {
		tool := item.(map[string]any)
		names[tool["name"].(string)] = true
		if tool["description"] == "" {
			t.Errorf("tool %v has no description", tool["name"])
		}
		if _, ok := tool["inputSchema"].(map[string]any); !ok {
			t.Errorf("tool %v has no input schema", tool["name"])
		}
	}
	for _, want := range []string{"search_matches", "head_to_head", "standings", "search_players", "graph_neighbors"} {
		if !names[want] {
			t.Errorf("tool %q is not advertised", want)
		}
	}

	// 3. Ask the questions from the specification.
	callTool := func(name string, args map[string]any) (string, bool) {
		result := c.request("tools/call", map[string]any{"name": name, "arguments": args})
		content := result["content"].([]any)
		first := content[0].(map[string]any)
		isError, _ := result["isError"].(bool)
		return first["text"].(string), isError
	}

	answer, isErr := callTool("standings", map[string]any{"competition": "brasileirao", "season": 2019})
	if isErr {
		t.Fatalf("standings failed: %s", answer)
	}
	for _, want := range []string{"Flamengo", "90 pts", "Champion"} {
		if !strings.Contains(answer, want) {
			t.Errorf("the 2019 table is missing %q:\n%s", want, answer)
		}
	}

	answer, isErr = callTool("head_to_head", map[string]any{"team_a": "Flamengo", "team_b": "Fluminense", "limit": 3})
	if isErr {
		t.Fatalf("head_to_head failed: %s", answer)
	}
	if !strings.Contains(answer, "Fla-Flu") {
		t.Errorf("head-to-head answer:\n%s", answer)
	}

	// 4. A tool error must arrive as a result, not as a protocol failure.
	answer, isErr = callTool("team_stats", map[string]any{"team": "Nonexistent United"})
	if !isErr {
		t.Errorf("an unknown club should be reported as a tool error, got:\n%s", answer)
	}

	// 5. Resources.
	resources := c.request("resources/list", nil)["resources"].([]any)
	if len(resources) < 4 {
		t.Errorf("server exposes %d resources", len(resources))
	}
	read := c.request("resources/read", map[string]any{"uri": "soccer://sample-questions"})
	contents := read["contents"].([]any)
	body := contents[0].(map[string]any)["text"].(string)
	if !strings.Contains(body, "Who won the 2019 Brasileirão?") {
		t.Errorf("sample questions resource:\n%s", body)
	}

	teams := c.request("resources/read", map[string]any{"uri": "soccer://teams"})
	teamsJSON := teams["contents"].([]any)[0].(map[string]any)["text"].(string)
	var parsed []map[string]any
	if err := json.Unmarshal([]byte(teamsJSON), &parsed); err != nil {
		t.Errorf("the teams resource is not valid JSON: %v", err)
	} else if len(parsed) < 100 {
		t.Errorf("the teams resource lists %d clubs", len(parsed))
	}

	// 6. Prompts.
	prompts := c.request("prompts/list", nil)["prompts"].([]any)
	if len(prompts) < 4 {
		t.Errorf("server exposes %d prompts", len(prompts))
	}
	prompt := c.request("prompts/get", map[string]any{
		"name": "season_review", "arguments": map[string]string{"competition": "brasileirao", "season": "2019"}})
	messages := prompt["messages"].([]any)
	msg := messages[0].(map[string]any)["content"].(map[string]any)["text"].(string)
	if !strings.Contains(msg, "season_summary") {
		t.Errorf("season_review prompt:\n%s", msg)
	}

	// 7. Completion of a club name.
	completion := c.request("completion/complete", map[string]any{
		"ref":      map[string]any{"type": "ref/prompt", "name": "club_dossier"},
		"argument": map[string]any{"name": "team", "value": "Fla"},
	})
	values := completion["completion"].(map[string]any)["values"].([]any)
	found := false
	for _, v := range values {
		if v == "Flamengo" {
			found = true
		}
	}
	if !found {
		t.Errorf("completion for \"Fla\" = %v", values)
	}

	// 8. Ping, then shut down cleanly.
	c.request("ping", nil)
	clientOut.Close()
	select {
	case err := <-done:
		if err != nil {
			t.Errorf("Serve returned %v", err)
		}
	case <-time.After(10 * time.Second):
		t.Error("the server did not stop when its input closed")
	}
}

// The graph resources and schema must describe what the graph actually holds.
func TestResourceContents(t *testing.T) {
	srv := testServer(t)
	for _, uri := range []string{"soccer://datasets", "soccer://teams", "soccer://competitions", "soccer://graph/schema", "soccer://sample-questions"} {
		raw, _ := json.Marshal(map[string]any{"jsonrpc": "2.0", "id": 1, "method": "resources/read",
			"params": map[string]any{"uri": uri}})
		reply, send := srv.HandleMessage(context.Background(), raw)
		if !send {
			t.Fatalf("%s produced no response", uri)
		}
		var resp struct {
			Result struct {
				Contents []mcp.ResourceContents `json:"contents"`
			} `json:"result"`
			Error *mcp.RPCError `json:"error"`
		}
		if err := json.Unmarshal(reply, &resp); err != nil {
			t.Fatalf("%s: %v", uri, err)
		}
		if resp.Error != nil {
			t.Fatalf("%s: %v", uri, resp.Error)
		}
		if len(resp.Result.Contents) != 1 || len(resp.Result.Contents[0].Text) < 50 {
			t.Errorf("%s returned %d contents", uri, len(resp.Result.Contents))
		}
	}
}
