package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func runServerOnce(t *testing.T, requests string) []map[string]any {
	t.Helper()
	store := buildFixtureStore(t)
	server := NewServer(store, BuildToolRegistry())

	var out bytes.Buffer
	var errOut bytes.Buffer
	if err := server.Run(strings.NewReader(requests), &out, &errOut); err != nil {
		t.Fatalf("server.Run returned error: %v", err)
	}

	var responses []map[string]any
	dec := json.NewDecoder(&out)
	for dec.More() {
		var m map[string]any
		if err := dec.Decode(&m); err != nil {
			t.Fatalf("decoding response: %v", err)
		}
		responses = append(responses, m)
	}
	return responses
}

func Test_GivenAnInitializeRequest_WhenHandled_ThenTheServerRespondsWithItsProtocolVersion(t *testing.T) {
	// Given a well-formed MCP "initialize" request
	req := `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}` + "\n"

	// When the server handles it
	responses := runServerOnce(t, req)

	// Then it responds with a result containing the protocol version
	if len(responses) != 1 {
		t.Fatalf("got %d responses, want 1", len(responses))
	}
	result, ok := responses[0]["result"].(map[string]any)
	if !ok {
		t.Fatalf("response has no result: %+v", responses[0])
	}
	if result["protocolVersion"] == "" {
		t.Error("expected a non-empty protocolVersion")
	}
}

func Test_GivenANotification_WhenHandled_ThenNoResponseIsSent(t *testing.T) {
	// Given a notification (no "id" field), per JSON-RPC 2.0
	req := `{"jsonrpc":"2.0","method":"notifications/initialized"}` + "\n"

	// When the server handles it
	responses := runServerOnce(t, req)

	// Then no response is written at all
	if len(responses) != 0 {
		t.Errorf("got %d responses for a notification, want 0", len(responses))
	}
}

func Test_GivenAToolsListRequest_WhenHandled_ThenEveryRegisteredToolIsReturned(t *testing.T) {
	// Given a "tools/list" request
	req := `{"jsonrpc":"2.0","id":2,"method":"tools/list"}` + "\n"

	// When the server handles it
	responses := runServerOnce(t, req)

	// Then the response lists every tool the registry knows about
	result := responses[0]["result"].(map[string]any)
	tools := result["tools"].([]any)
	if len(tools) != len(BuildToolRegistry().List()) {
		t.Errorf("got %d tools, want %d", len(tools), len(BuildToolRegistry().List()))
	}
}

func Test_GivenAToolsCallRequestForAKnownTool_WhenHandled_ThenTextContentIsReturned(t *testing.T) {
	// Given a "tools/call" request for the head_to_head tool
	req := `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo","team_b":"Fluminense"}}}` + "\n"

	// When the server handles it
	responses := runServerOnce(t, req)

	// Then the response contains a text content block
	result := responses[0]["result"].(map[string]any)
	content := result["content"].([]any)
	if len(content) == 0 {
		t.Fatal("expected at least one content block")
	}
	block := content[0].(map[string]any)
	if block["type"] != "text" || block["text"] == "" {
		t.Errorf("got content block %+v, want non-empty text", block)
	}
}

func Test_GivenAToolsCallRequestForAnUnknownTool_WhenHandled_ThenAnErrorResponseIsReturned(t *testing.T) {
	// Given a "tools/call" request naming a tool that doesn't exist
	req := `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"does_not_exist","arguments":{}}}` + "\n"

	// When the server handles it
	responses := runServerOnce(t, req)

	// Then the response is a JSON-RPC error, not a result
	if responses[0]["error"] == nil {
		t.Errorf("expected an error response, got %+v", responses[0])
	}
}

func Test_GivenAnUnknownMethod_WhenHandled_ThenAMethodNotFoundErrorIsReturned(t *testing.T) {
	// Given a request for a method the server doesn't implement
	req := `{"jsonrpc":"2.0","id":5,"method":"totally/bogus"}` + "\n"

	// When the server handles it
	responses := runServerOnce(t, req)

	// Then it responds with a JSON-RPC "method not found" error
	errObj, ok := responses[0]["error"].(map[string]any)
	if !ok {
		t.Fatalf("expected an error object, got %+v", responses[0])
	}
	if int(errObj["code"].(float64)) != codeMethodNotFound {
		t.Errorf("got error code %v, want %d", errObj["code"], codeMethodNotFound)
	}
}
