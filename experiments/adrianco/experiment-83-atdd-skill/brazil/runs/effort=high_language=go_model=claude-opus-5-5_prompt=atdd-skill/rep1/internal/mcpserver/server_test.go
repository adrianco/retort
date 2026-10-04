package mcpserver

import (
	"encoding/json"
	"errors"
	"strings"
	"testing"
)

func serve(t *testing.T, s *Server, lines ...string) []map[string]any {
	t.Helper()
	var out strings.Builder
	if err := s.Serve(strings.NewReader(strings.Join(lines, "\n")+"\n"), &out); err != nil {
		t.Fatal(err)
	}
	var replies []map[string]any
	for _, line := range strings.Split(strings.TrimSpace(out.String()), "\n") {
		if line == "" {
			continue
		}
		var m map[string]any
		if err := json.Unmarshal([]byte(line), &m); err != nil {
			t.Fatalf("reply is not JSON: %q", line)
		}
		replies = append(replies, m)
	}
	return replies
}

func testServer() *Server {
	s := New("test", "0", "")
	s.AddTool(Tool{Name: "echo", Description: "echo", InputSchema: map[string]any{"type": "object"},
		Handler: func(a Args) (Result, error) {
			if a.String("fail") != "" {
				return Result{}, errors.New("it failed")
			}
			return Result{Text: a.String("say"), Structured: map[string]any{"said": a.String("say")}}, nil
		}})
	return s
}

func TestServerAgreesTheClientsProtocolVersionWhenSupported(t *testing.T) {
	r := serve(t, testServer(), `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}`)
	if got := r[0]["result"].(map[string]any)["protocolVersion"]; got != "2024-11-05" {
		t.Errorf("protocol version = %v", got)
	}
}

func TestServerDoesNotReplyToNotifications(t *testing.T) {
	r := serve(t, testServer(), `{"jsonrpc":"2.0","method":"notifications/initialized"}`, `{"jsonrpc":"2.0","id":2,"method":"ping"}`)
	if len(r) != 1 || r[0]["id"].(float64) != 2 {
		t.Errorf("expected only the ping reply, got %v", r)
	}
}

func TestServerReportsMalformedJSONAndUnknownMethods(t *testing.T) {
	r := serve(t, testServer(), `{not json`, `{"jsonrpc":"2.0","id":3,"method":"nope"}`)
	codes := []float64{-32700, -32601}
	for i, reply := range r {
		if code := reply["error"].(map[string]any)["code"].(float64); code != codes[i] {
			t.Errorf("reply %d: code %v, want %v", i, code, codes[i])
		}
	}
}

func TestServerRejectsUnknownTools(t *testing.T) {
	r := serve(t, testServer(), `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"missing","arguments":{}}}`)
	if r[0]["error"] == nil {
		t.Errorf("expected an error, got %v", r[0])
	}
}

func TestToolFailuresReachTheLLMAsErrorResults(t *testing.T) {
	r := serve(t, testServer(), `{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"echo","arguments":{"fail":"yes"}}}`)
	result := r[0]["result"].(map[string]any)
	if result["isError"] != true || !strings.Contains(r[0]["result"].(map[string]any)["content"].([]any)[0].(map[string]any)["text"].(string), "it failed") {
		t.Errorf("expected an error result, got %v", result)
	}
}

func TestToolResultsCarryTextAndStructuredContent(t *testing.T) {
	r := serve(t, testServer(), `{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"echo","arguments":{"say":"olá"}}}`)
	result := r[0]["result"].(map[string]any)
	if result["structuredContent"].(map[string]any)["said"] != "olá" || result["isError"] != false {
		t.Errorf("unexpected result %v", result)
	}
}

func TestArgsAcceptNumbersWrittenAsText(t *testing.T) {
	a := Args{"season": "2019", "limit": 5.0, "seasons": "2018, 2019"}
	if n, _ := a.Int("season", 0); n != 2019 {
		t.Errorf("season = %d", n)
	}
	if n, _ := a.Int("limit", 0); n != 5 {
		t.Errorf("limit = %d", n)
	}
	if ns, _ := a.Ints("seasons"); len(ns) != 2 || ns[1] != 2019 {
		t.Errorf("seasons = %v", ns)
	}
}
