// Context:
//   - BDD-style (Given/When/Then) tests for the MCP protocol layer. They verify
//     the JSON-RPC handshake (initialize), tool discovery (tools/list), tool
//     invocation (tools/call) and a full line-delimited stdio round trip — all
//     without external dependencies or a real client.
//   - A small real store is loaded from the bundled CSVs so the tool handlers
//     run against genuine data; tests skip cleanly if the data is absent.
package mcpserver

import (
	"bufio"
	"encoding/json"
	"strings"
	"testing"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

const testDataDir = "../../data/kaggle"

func testServer(t *testing.T) *Server {
	t.Helper()
	store, err := soccer.Load(testDataDir)
	if err != nil {
		t.Fatalf("loading data: %v", err)
	}
	if len(store.Matches) == 0 {
		t.Skip("no data available")
	}
	return NewServer(store)
}

func TestInitialize_ReturnsCapabilities(t *testing.T) {
	// Given an MCP server
	s := testServer(t)

	// When dispatching an initialize request
	res, rpcErr := s.dispatch(&request{Method: "initialize"})

	// Then it succeeds and advertises the tools capability and server info
	if rpcErr != nil {
		t.Fatalf("initialize error: %v", rpcErr)
	}
	m := res.(map[string]any)
	if m["protocolVersion"] != protocolVersion {
		t.Errorf("unexpected protocol version: %v", m["protocolVersion"])
	}
	caps := m["capabilities"].(map[string]any)
	if _, ok := caps["tools"]; !ok {
		t.Error("expected tools capability")
	}
}

func TestToolsList_AllToolsHaveSchemas(t *testing.T) {
	// Given an MCP server
	s := testServer(t)

	// When listing tools
	res, _ := s.dispatch(&request{Method: "tools/list"})
	tools := res.(map[string]any)["tools"].([]map[string]any)

	// Then every expected tool is present with a name, description and schema
	want := []string{
		"search_matches", "head_to_head", "team_stats", "search_players",
		"competition_standings", "competition_stats", "list_competitions",
	}
	got := map[string]bool{}
	for _, tl := range tools {
		got[tl["name"].(string)] = true
		if tl["description"] == "" {
			t.Errorf("tool %v missing description", tl["name"])
		}
		if _, ok := tl["inputSchema"].(map[string]any); !ok {
			t.Errorf("tool %v missing inputSchema", tl["name"])
		}
	}
	for _, name := range want {
		if !got[name] {
			t.Errorf("missing tool %q", name)
		}
	}
}

// callTool is a helper that invokes a tool and returns its text content.
func callTool(t *testing.T, s *Server, name string, args map[string]any) (string, bool) {
	t.Helper()
	argBytes, _ := json.Marshal(args)
	params, _ := json.Marshal(toolCallParams{Name: name, Arguments: argBytes})
	res, rpcErr := s.dispatch(&request{Method: "tools/call", Params: params})
	if rpcErr != nil {
		t.Fatalf("tools/call %s error: %v", name, rpcErr)
	}
	m := res.(map[string]any)
	content := m["content"].([]map[string]any)
	return content[0]["text"].(string), m["isError"].(bool)
}

func TestToolsCall_SearchPlayers(t *testing.T) {
	// Given an MCP server
	s := testServer(t)

	// When calling search_players for Brazilians
	text, isErr := callTool(t, s, "search_players", map[string]any{
		"nationality": "Brazil", "limit": 5,
	})

	// Then it succeeds and the top result is Neymar
	if isErr {
		t.Fatalf("unexpected error result: %s", text)
	}
	if !strings.Contains(text, "Neymar") {
		t.Errorf("expected Neymar in result, got:\n%s", text)
	}
}

func TestToolsCall_Standings2019(t *testing.T) {
	// Given an MCP server
	s := testServer(t)

	// When requesting the 2019 Série A standings
	text, isErr := callTool(t, s, "competition_standings", map[string]any{
		"competition": "Série A", "season": 2019,
	})

	// Then Flamengo is reported as champion
	if isErr {
		t.Fatalf("unexpected error: %s", text)
	}
	if !strings.Contains(text, "Flamengo") || !strings.Contains(text, "Champion: Flamengo") {
		t.Errorf("expected Flamengo champion, got:\n%s", text)
	}
}

func TestToolsCall_MissingRequiredArg(t *testing.T) {
	// Given an MCP server
	s := testServer(t)

	// When calling head_to_head without the required teams
	text, isErr := callTool(t, s, "head_to_head", map[string]any{})

	// Then the call returns an error result (not a protocol failure)
	if !isErr {
		t.Errorf("expected isError=true for missing args, got:\n%s", text)
	}
}

func TestToolsCall_UnknownTool(t *testing.T) {
	// Given an MCP server
	s := testServer(t)

	// When calling a tool that does not exist
	params, _ := json.Marshal(toolCallParams{Name: "nope"})
	_, rpcErr := s.dispatch(&request{Method: "tools/call", Params: params})

	// Then a JSON-RPC error is returned
	if rpcErr == nil {
		t.Fatal("expected an error for unknown tool")
	}
}

func TestServe_StdioRoundTrip(t *testing.T) {
	// Given an MCP server and a stream of newline-delimited JSON-RPC requests
	s := testServer(t)
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`, // notification: no reply
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_competitions","arguments":{}}}`,
	}, "\n") + "\n"

	// When served over the streams
	var out strings.Builder
	if err := s.Serve(strings.NewReader(input), &out); err != nil {
		t.Fatalf("serve: %v", err)
	}

	// Then exactly three responses come back (the notification produced none),
	// matched to their request ids, with no errors.
	scanner := bufio.NewScanner(strings.NewReader(out.String()))
	var ids []float64
	for scanner.Scan() {
		var resp struct {
			ID    float64                   `json:"id"`
			Error *struct{ Message string } `json:"error"`
		}
		if err := json.Unmarshal(scanner.Bytes(), &resp); err != nil {
			t.Fatalf("bad response line %q: %v", scanner.Text(), err)
		}
		if resp.Error != nil {
			t.Errorf("unexpected error in response: %v", resp.Error.Message)
		}
		ids = append(ids, resp.ID)
	}
	if len(ids) != 3 {
		t.Fatalf("expected 3 responses, got %d:\n%s", len(ids), out.String())
	}
	if ids[0] != 1 || ids[1] != 2 || ids[2] != 3 {
		t.Errorf("unexpected response ids: %v", ids)
	}
}
