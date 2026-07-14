// Context: tests the JSON-RPC/MCP transport in isolation using in-memory pipes.
// A registered echo-style tool lets us assert the full request/response cycle:
// initialize, tools/list, tools/call (success + error), notifications (no
// response), and unknown methods.
package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"strings"
	"testing"
)

// run feeds the given newline-delimited requests through a server and returns
// the decoded responses in order.
func run(t *testing.T, tools []Tool, requests ...string) []Response {
	t.Helper()
	in := strings.NewReader(strings.Join(requests, "\n") + "\n")
	var out strings.Builder
	s := NewServer("test", "0.0.1", in, &out)
	for _, tool := range tools {
		s.Register(tool)
	}
	if err := s.Serve(); err != nil {
		t.Fatalf("Serve: %v", err)
	}
	var resps []Response
	sc := bufio.NewScanner(strings.NewReader(out.String()))
	for sc.Scan() {
		if len(sc.Bytes()) == 0 {
			continue
		}
		var r Response
		if err := json.Unmarshal(sc.Bytes(), &r); err != nil {
			t.Fatalf("decode response %q: %v", sc.Text(), err)
		}
		resps = append(resps, r)
	}
	return resps
}

func echoTool() Tool {
	return Tool{
		Name:        "echo",
		Description: "echoes the text argument",
		InputSchema: map[string]interface{}{"type": "object"},
		Handler: func(args map[string]interface{}) (string, error) {
			if args["fail"] == true {
				return "", fmt.Errorf("boom")
			}
			return fmt.Sprintf("echo: %v", args["text"]), nil
		},
	}
}

func TestInitializeAndList(t *testing.T) {
	resps := run(t, []Tool{echoTool()},
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}`,
	)
	if len(resps) != 2 {
		t.Fatalf("got %d responses, want 2", len(resps))
	}
	init := resps[0].Result.(map[string]interface{})
	if init["protocolVersion"] != ProtocolVersion {
		t.Errorf("protocolVersion = %v, want %v", init["protocolVersion"], ProtocolVersion)
	}
	list := resps[1].Result.(map[string]interface{})
	tools := list["tools"].([]interface{})
	if len(tools) != 1 {
		t.Fatalf("tools listed = %d, want 1", len(tools))
	}
	if tools[0].(map[string]interface{})["name"] != "echo" {
		t.Errorf("tool name = %v, want echo", tools[0])
	}
}

func TestToolCallSuccess(t *testing.T) {
	resps := run(t, []Tool{echoTool()},
		`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"echo","arguments":{"text":"hi"}}}`,
	)
	res := resps[0].Result.(map[string]interface{})
	if res["isError"] != false {
		t.Errorf("isError = %v, want false", res["isError"])
	}
	content := res["content"].([]interface{})
	text := content[0].(map[string]interface{})["text"]
	if text != "echo: hi" {
		t.Errorf("text = %v, want 'echo: hi'", text)
	}
}

func TestToolCallError(t *testing.T) {
	resps := run(t, []Tool{echoTool()},
		`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"echo","arguments":{"fail":true}}}`,
	)
	res := resps[0].Result.(map[string]interface{})
	if res["isError"] != true {
		t.Errorf("isError = %v, want true (tool errors surface as result content)", res["isError"])
	}
}

func TestUnknownToolAndMethod(t *testing.T) {
	resps := run(t, []Tool{echoTool()},
		`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"nope","arguments":{}}}`,
		`{"jsonrpc":"2.0","id":2,"method":"bogus/method"}`,
	)
	if resps[0].Error == nil || resps[0].Error.Code != CodeMethodNotFound {
		t.Errorf("unknown tool: expected method-not-found, got %+v", resps[0])
	}
	if resps[1].Error == nil || resps[1].Error.Code != CodeMethodNotFound {
		t.Errorf("unknown method: expected method-not-found, got %+v", resps[1])
	}
}

func TestNotificationProducesNoResponse(t *testing.T) {
	// A notification (no id) plus a request; only the request should respond.
	resps := run(t, []Tool{echoTool()},
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":9,"method":"ping"}`,
	)
	if len(resps) != 1 {
		t.Fatalf("got %d responses, want 1 (notification must be silent)", len(resps))
	}
	if string(resps[0].ID) != "9" {
		t.Errorf("response id = %s, want 9", resps[0].ID)
	}
}

func TestParseError(t *testing.T) {
	resps := run(t, nil, `{not valid json`)
	if len(resps) != 1 || resps[0].Error == nil || resps[0].Error.Code != CodeParseError {
		t.Errorf("expected parse error, got %+v", resps)
	}
}
