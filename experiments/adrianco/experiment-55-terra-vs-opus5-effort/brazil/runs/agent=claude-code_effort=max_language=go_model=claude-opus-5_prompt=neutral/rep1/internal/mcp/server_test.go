package mcp

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"strings"
	"testing"
	"time"
)

// testServer is a small server with one of everything.
func testServer() *Server {
	s := NewServer("test-server", "9.9.9")
	s.Title = "Test Server"
	s.Instructions = "instructions for the model"
	s.AddTool(&Tool{
		Name:        "echo",
		Title:       "Echo",
		Description: "Echo a message back.",
		InputSchema: Object(map[string]*Prop{
			"message": Str("Text to echo."),
			"times":   Int("How many times."),
			"shout":   Bool("Upper-case the answer."),
			"mode":    Enum("Rendering mode.", "plain", "fancy"),
			"tags":    StrArray("Tags."),
		}, "message"),
		Handler: func(args Args) (*ToolResult, error) {
			times, err := args.Int("times", 1)
			if err != nil {
				return ErrorResult("%v", err), nil
			}
			shout, _ := args.Bool("shout", false)
			msg := args.String("message")
			if shout {
				msg = strings.ToUpper(msg)
			}
			return TextWithData(strings.TrimSpace(strings.Repeat(msg+" ", times)),
				map[string]any{"message": msg, "times": times, "tags": args.Strings("tags")}), nil
		},
	})
	s.AddTool(&Tool{
		Name:        "boom",
		Description: "Always fails.",
		InputSchema: Object(map[string]*Prop{}),
		Handler: func(Args) (*ToolResult, error) {
			return nil, fmt.Errorf("exploded")
		},
	})
	s.AddTool(&Tool{
		Name:        "panic",
		Description: "Panics.",
		InputSchema: Object(map[string]*Prop{}),
		Handler: func(Args) (*ToolResult, error) {
			panic("kaboom")
		},
	})
	s.AddResource(&Resource{
		URI: "test://doc", Name: "doc", Description: "A document.", MIMEType: "text/plain",
		Reader: func() (string, error) { return "hello resource", nil },
	})
	s.AddResource(&Resource{
		URI: "test://broken", Name: "broken",
		Reader: func() (string, error) { return "", fmt.Errorf("cannot read") },
	})
	s.AddPrompt(&Prompt{
		Name:        "greet",
		Description: "Greet somebody.",
		Arguments:   []PromptArgument{{Name: "who", Required: true}},
		Render: func(args map[string]string) (string, string, error) {
			return "greeting", "Say hello to " + args["who"], nil
		},
	})
	s.SetCompletion(func(ref, argument, value string) []string {
		if argument == "who" {
			return []string{"world", "worldcup"}
		}
		return nil
	})
	return s
}

// call sends one request and decodes the response.
func call(t *testing.T, s *Server, method string, params any) (json.RawMessage, *RPCError) {
	t.Helper()
	req := map[string]any{"jsonrpc": "2.0", "id": 1, "method": method}
	if params != nil {
		req["params"] = params
	}
	raw, _ := json.Marshal(req)
	reply, send := s.HandleMessage(context.Background(), raw)
	if !send {
		t.Fatalf("%s produced no response", method)
	}
	var resp struct {
		JSONRPC string          `json:"jsonrpc"`
		ID      json.RawMessage `json:"id"`
		Result  json.RawMessage `json:"result"`
		Error   *RPCError       `json:"error"`
	}
	if err := json.Unmarshal(reply, &resp); err != nil {
		t.Fatalf("decoding the response to %s: %v (%s)", method, err, reply)
	}
	if resp.JSONRPC != "2.0" {
		t.Errorf("response to %s has jsonrpc %q", method, resp.JSONRPC)
	}
	if string(resp.ID) != "1" {
		t.Errorf("response to %s has id %s", method, resp.ID)
	}
	return resp.Result, resp.Error
}

func TestInitializeNegotiatesTheProtocolVersion(t *testing.T) {
	s := testServer()
	for _, want := range supportedVersions {
		result, rpcErr := call(t, s, "initialize", map[string]any{
			"protocolVersion": want,
			"capabilities":    map[string]any{},
			"clientInfo":      map[string]any{"name": "test-client", "version": "1"},
		})
		if rpcErr != nil {
			t.Fatalf("initialize: %v", rpcErr)
		}
		var got initializeResult
		if err := json.Unmarshal(result, &got); err != nil {
			t.Fatal(err)
		}
		if got.ProtocolVersion != want {
			t.Errorf("negotiated %q, want %q", got.ProtocolVersion, want)
		}
		if got.ServerInfo.Name != "test-server" || got.ServerInfo.Version != "9.9.9" {
			t.Errorf("serverInfo = %+v", got.ServerInfo)
		}
		if got.Instructions == "" {
			t.Error("instructions should be sent to the client")
		}
		for _, capability := range []string{"tools", "resources", "prompts"} {
			if _, ok := got.Capabilities[capability]; !ok {
				t.Errorf("capability %q is missing", capability)
			}
		}
	}

	// An unknown version falls back to the newest one we speak.
	result, _ := call(t, s, "initialize", map[string]any{"protocolVersion": "1999-01-01"})
	var got initializeResult
	json.Unmarshal(result, &got)
	if got.ProtocolVersion != LatestVersion {
		t.Errorf("unknown version negotiated %q, want %q", got.ProtocolVersion, LatestVersion)
	}
}

func TestNotificationsGetNoResponse(t *testing.T) {
	s := testServer()
	for _, method := range []string{"notifications/initialized", "notifications/cancelled", "notifications/unknown"} {
		raw, _ := json.Marshal(map[string]any{"jsonrpc": "2.0", "method": method})
		if reply, send := s.HandleMessage(context.Background(), raw); send {
			t.Errorf("%s produced a response: %s", method, reply)
		}
	}
}

func TestPing(t *testing.T) {
	s := testServer()
	result, rpcErr := call(t, s, "ping", nil)
	if rpcErr != nil {
		t.Fatalf("ping: %v", rpcErr)
	}
	if strings.TrimSpace(string(result)) != "{}" {
		t.Errorf("ping returned %s", result)
	}
}

func TestToolsList(t *testing.T) {
	s := testServer()
	result, rpcErr := call(t, s, "tools/list", nil)
	if rpcErr != nil {
		t.Fatalf("tools/list: %v", rpcErr)
	}
	var got struct {
		Tools []struct {
			Name        string `json:"name"`
			Description string `json:"description"`
			InputSchema struct {
				Type       string              `json:"type"`
				Properties map[string]struct{} `json:"properties"`
				Required   []string            `json:"required"`
			} `json:"inputSchema"`
		} `json:"tools"`
	}
	if err := json.Unmarshal(result, &got); err != nil {
		t.Fatal(err)
	}
	if len(got.Tools) != 3 {
		t.Fatalf("listed %d tools, want 3", len(got.Tools))
	}
	first := got.Tools[0]
	if first.Name != "echo" || first.Description == "" {
		t.Errorf("first tool = %+v", first)
	}
	if first.InputSchema.Type != "object" || len(first.InputSchema.Properties) != 5 {
		t.Errorf("schema = %+v", first.InputSchema)
	}
	if len(first.InputSchema.Required) != 1 || first.InputSchema.Required[0] != "message" {
		t.Errorf("required = %v", first.InputSchema.Required)
	}
}

func callTool(t *testing.T, s *Server, name string, args map[string]any) (*ToolResult, *RPCError) {
	t.Helper()
	result, rpcErr := call(t, s, "tools/call", map[string]any{"name": name, "arguments": args})
	if rpcErr != nil {
		return nil, rpcErr
	}
	var tr ToolResult
	if err := json.Unmarshal(result, &tr); err != nil {
		t.Fatalf("decoding tool result: %v (%s)", err, result)
	}
	return &tr, nil
}

func TestToolsCall(t *testing.T) {
	s := testServer()
	tr, rpcErr := callTool(t, s, "echo", map[string]any{"message": "hi", "times": 2})
	if rpcErr != nil {
		t.Fatalf("tools/call: %v", rpcErr)
	}
	if tr.IsError {
		t.Fatalf("unexpected error result: %+v", tr)
	}
	if len(tr.Content) != 1 || tr.Content[0].Type != "text" || tr.Content[0].Text != "hi hi" {
		t.Errorf("content = %+v", tr.Content)
	}
	if tr.StructuredContent == nil {
		t.Error("structured content is missing")
	}
}

func TestToolsCallCoercesArgumentTypes(t *testing.T) {
	s := testServer()
	// An LLM often sends numbers and booleans as strings.
	tr, _ := callTool(t, s, "echo", map[string]any{"message": "hi", "times": "3", "shout": "true"})
	if tr.IsError {
		t.Fatalf("string arguments were rejected: %+v", tr)
	}
	if tr.Content[0].Text != "HI HI HI" {
		t.Errorf("content = %q", tr.Content[0].Text)
	}
}

func TestToolsCallValidation(t *testing.T) {
	s := testServer()
	cases := []struct {
		name string
		args map[string]any
		want string
	}{
		{"missing required", map[string]any{}, "missing required argument"},
		{"unknown argument", map[string]any{"message": "x", "nope": 1}, "unknown argument"},
		{"bad integer", map[string]any{"message": "x", "times": "many"}, "must be an integer"},
		{"bad enum", map[string]any{"message": "x", "mode": "sideways"}, "must be one of"},
		{"bad array", map[string]any{"message": "x", "tags": 5}, "must be an array"},
	}
	for _, c := range cases {
		tr, rpcErr := callTool(t, s, "echo", c.args)
		if rpcErr != nil {
			t.Errorf("%s: unexpected protocol error %v", c.name, rpcErr)
			continue
		}
		if !tr.IsError {
			t.Errorf("%s: expected an error result, got %+v", c.name, tr)
			continue
		}
		if !strings.Contains(tr.Content[0].Text, c.want) {
			t.Errorf("%s: message %q does not mention %q", c.name, tr.Content[0].Text, c.want)
		}
	}
}

func TestToolsCallUnknownToolIsAProtocolError(t *testing.T) {
	s := testServer()
	_, rpcErr := call(t, s, "tools/call", map[string]any{"name": "nope"})
	if rpcErr == nil {
		t.Fatal("unknown tool should be a protocol error")
	}
	if rpcErr.Code != CodeInvalidParams {
		t.Errorf("code = %d, want %d", rpcErr.Code, CodeInvalidParams)
	}
}

// A failing tool reports through the result, not the protocol, so the model
// can read the failure.
func TestFailingToolReportsInTheResult(t *testing.T) {
	s := testServer()
	tr, rpcErr := callTool(t, s, "boom", map[string]any{})
	if rpcErr != nil {
		t.Fatalf("tool failure leaked as a protocol error: %v", rpcErr)
	}
	if !tr.IsError || !strings.Contains(tr.Content[0].Text, "exploded") {
		t.Errorf("result = %+v", tr)
	}
}

func TestPanickingToolIsContained(t *testing.T) {
	s := testServer()
	tr, rpcErr := callTool(t, s, "panic", map[string]any{})
	if rpcErr != nil {
		t.Fatalf("panic leaked as a protocol error: %v", rpcErr)
	}
	if !tr.IsError || !strings.Contains(tr.Content[0].Text, "internal error") {
		t.Errorf("result = %+v", tr)
	}
	// The server still works afterwards.
	if _, rpcErr := call(t, s, "ping", nil); rpcErr != nil {
		t.Errorf("server broke after a panic: %v", rpcErr)
	}
}

func TestResources(t *testing.T) {
	s := testServer()
	result, rpcErr := call(t, s, "resources/list", nil)
	if rpcErr != nil {
		t.Fatalf("resources/list: %v", rpcErr)
	}
	var list struct {
		Resources []Resource `json:"resources"`
	}
	json.Unmarshal(result, &list)
	if len(list.Resources) != 2 {
		t.Fatalf("listed %d resources", len(list.Resources))
	}

	result, rpcErr = call(t, s, "resources/read", map[string]any{"uri": "test://doc"})
	if rpcErr != nil {
		t.Fatalf("resources/read: %v", rpcErr)
	}
	var read struct {
		Contents []ResourceContents `json:"contents"`
	}
	json.Unmarshal(result, &read)
	if len(read.Contents) != 1 || read.Contents[0].Text != "hello resource" {
		t.Errorf("contents = %+v", read.Contents)
	}
	if read.Contents[0].MIMEType != "text/plain" {
		t.Errorf("mime type = %q", read.Contents[0].MIMEType)
	}

	if _, rpcErr := call(t, s, "resources/read", map[string]any{"uri": "test://missing"}); rpcErr == nil {
		t.Error("reading an unknown resource should fail")
	}
	if _, rpcErr := call(t, s, "resources/read", map[string]any{"uri": "test://broken"}); rpcErr == nil {
		t.Error("a resource that cannot be read should fail")
	}
	if _, rpcErr := call(t, s, "resources/templates/list", nil); rpcErr != nil {
		t.Errorf("resources/templates/list: %v", rpcErr)
	}
}

func TestPrompts(t *testing.T) {
	s := testServer()
	result, rpcErr := call(t, s, "prompts/list", nil)
	if rpcErr != nil {
		t.Fatalf("prompts/list: %v", rpcErr)
	}
	var list struct {
		Prompts []Prompt `json:"prompts"`
	}
	json.Unmarshal(result, &list)
	if len(list.Prompts) != 1 || list.Prompts[0].Name != "greet" {
		t.Fatalf("prompts = %+v", list.Prompts)
	}

	result, rpcErr = call(t, s, "prompts/get", map[string]any{"name": "greet", "arguments": map[string]string{"who": "Brazil"}})
	if rpcErr != nil {
		t.Fatalf("prompts/get: %v", rpcErr)
	}
	var got getPromptResult
	json.Unmarshal(result, &got)
	if len(got.Messages) != 1 || !strings.Contains(got.Messages[0].Content.Text, "Brazil") {
		t.Errorf("prompt = %+v", got)
	}
	if got.Messages[0].Role != "user" {
		t.Errorf("role = %q", got.Messages[0].Role)
	}

	if _, rpcErr := call(t, s, "prompts/get", map[string]any{"name": "greet"}); rpcErr == nil {
		t.Error("a missing required prompt argument should fail")
	}
	if _, rpcErr := call(t, s, "prompts/get", map[string]any{"name": "nope"}); rpcErr == nil {
		t.Error("an unknown prompt should fail")
	}
}

func TestCompletion(t *testing.T) {
	s := testServer()
	result, rpcErr := call(t, s, "completion/complete", map[string]any{
		"ref":      map[string]any{"type": "ref/prompt", "name": "greet"},
		"argument": map[string]any{"name": "who", "value": "wor"},
	})
	if rpcErr != nil {
		t.Fatalf("completion/complete: %v", rpcErr)
	}
	var got struct {
		Completion struct {
			Values  []string `json:"values"`
			Total   int      `json:"total"`
			HasMore bool     `json:"hasMore"`
		} `json:"completion"`
	}
	json.Unmarshal(result, &got)
	if len(got.Completion.Values) != 2 || got.Completion.Total != 2 {
		t.Errorf("completion = %+v", got.Completion)
	}
}

func TestProtocolErrors(t *testing.T) {
	s := testServer()
	cases := []struct {
		name string
		raw  string
		code int
	}{
		{"invalid json", `{"jsonrpc":`, CodeParseError},
		{"wrong version", `{"jsonrpc":"1.0","id":1,"method":"ping"}`, CodeInvalidRequest},
		{"no method", `{"jsonrpc":"2.0","id":1}`, CodeInvalidRequest},
		{"unknown method", `{"jsonrpc":"2.0","id":1,"method":"does/not/exist"}`, CodeMethodNotFound},
		{"bad params", `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":"nope"}`, CodeInvalidParams},
		{"no tool name", `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{}}`, CodeInvalidParams},
	}
	for _, c := range cases {
		reply, send := s.HandleMessage(context.Background(), []byte(c.raw))
		if !send {
			t.Errorf("%s: no response", c.name)
			continue
		}
		var resp Response
		if err := json.Unmarshal(reply, &resp); err != nil {
			t.Errorf("%s: undecodable response %s", c.name, reply)
			continue
		}
		if resp.Error == nil {
			t.Errorf("%s: expected an error, got %s", c.name, reply)
			continue
		}
		if resp.Error.Code != c.code {
			t.Errorf("%s: code = %d, want %d (%s)", c.name, resp.Error.Code, c.code, resp.Error.Message)
		}
	}
}

func TestBatchRequests(t *testing.T) {
	s := testServer()
	batch := `[{"jsonrpc":"2.0","id":1,"method":"ping"},{"jsonrpc":"2.0","method":"notifications/initialized"},{"jsonrpc":"2.0","id":2,"method":"tools/list"}]`
	reply, send := s.HandleMessage(context.Background(), []byte(batch))
	if !send {
		t.Fatal("batch produced no response")
	}
	var responses []Response
	if err := json.Unmarshal(reply, &responses); err != nil {
		t.Fatalf("batch response is not an array: %s", reply)
	}
	if len(responses) != 2 {
		t.Errorf("batch returned %d responses, want 2 (the notification gets none)", len(responses))
	}

	// A batch of only notifications gets no reply at all.
	if _, send := s.HandleMessage(context.Background(), []byte(`[{"jsonrpc":"2.0","method":"notifications/initialized"}]`)); send {
		t.Error("a batch of notifications should produce no response")
	}
	if _, send := s.HandleMessage(context.Background(), []byte(`[]`)); !send {
		t.Error("an empty batch is an invalid request and needs a response")
	}
}

// TestServeOverPipes drives a whole session the way a client would.
func TestServeOverPipes(t *testing.T) {
	s := testServer()
	clientIn, serverOut := io.Pipe()
	serverIn, clientOut := io.Pipe()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	done := make(chan error, 1)
	go func() { done <- s.Serve(ctx, serverIn, serverOut) }()

	send := func(v any) {
		raw, _ := json.Marshal(v)
		if _, err := clientOut.Write(append(raw, '\n')); err != nil {
			t.Errorf("write: %v", err)
		}
	}
	// Whole lines, not a streaming decoder: the transport is newline
	// delimited and a decoder would leave the trailing newline unread.
	reader := bufio.NewReaderSize(clientIn, 1<<20)
	receive := func() map[string]any {
		line, err := reader.ReadBytes('\n')
		if err != nil {
			t.Fatalf("read: %v", err)
		}
		var msg map[string]any
		if err := json.Unmarshal(line, &msg); err != nil {
			t.Fatalf("the server wrote a non-JSON line: %q", line)
		}
		return msg
	}

	send(map[string]any{"jsonrpc": "2.0", "id": 1, "method": "initialize",
		"params": map[string]any{"protocolVersion": LatestVersion, "clientInfo": map[string]any{"name": "pipe-client", "version": "1"}}})
	init := receive()
	if init["error"] != nil {
		t.Fatalf("initialize failed: %v", init["error"])
	}

	send(map[string]any{"jsonrpc": "2.0", "method": "notifications/initialized"})

	send(map[string]any{"jsonrpc": "2.0", "id": 2, "method": "tools/call",
		"params": map[string]any{"name": "echo", "arguments": map[string]any{"message": "over the wire"}}})
	call := receive()
	result, ok := call["result"].(map[string]any)
	if !ok {
		t.Fatalf("tools/call returned %v", call)
	}
	content := result["content"].([]any)
	first := content[0].(map[string]any)
	if first["text"] != "over the wire" {
		t.Errorf("text = %v", first["text"])
	}

	clientOut.Close()
	select {
	case err := <-done:
		if err != nil {
			t.Errorf("Serve returned %v", err)
		}
	case <-time.After(5 * time.Second):
		t.Error("Serve did not stop when the input closed")
	}
}

func TestServeIgnoresBlankLines(t *testing.T) {
	s := testServer()
	in := strings.NewReader("\n\n{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\"}\n\n")
	var out strings.Builder
	if err := s.Serve(context.Background(), in, &out); err != nil {
		t.Fatalf("Serve: %v", err)
	}
	if strings.Count(strings.TrimSpace(out.String()), "\n") != 0 {
		t.Errorf("expected exactly one response line, got:\n%s", out.String())
	}
	if !strings.Contains(out.String(), `"result"`) {
		t.Errorf("no result in %s", out.String())
	}
}

func TestCallToolDirectly(t *testing.T) {
	s := testServer()
	result, err := s.CallTool("echo", Args{"message": "direct"})
	if err != nil {
		t.Fatalf("CallTool: %v", err)
	}
	if result.Content[0].Text != "direct" {
		t.Errorf("text = %q", result.Content[0].Text)
	}
	if _, err := s.CallTool("missing", nil); err == nil {
		t.Error("calling an unknown tool should fail")
	}
}

func TestArgsAccessors(t *testing.T) {
	args := Args{
		"str": " padded ", "num": float64(7), "numstr": "8", "flag": true, "flagstr": "false",
		"list": []any{"a", "b"}, "csv": "c, d", "empty": "", "nilvalue": nil,
	}
	if args.String("str") != "padded" {
		t.Errorf("String = %q", args.String("str"))
	}
	if !args.Has("str") || args.Has("empty") || args.Has("nilvalue") || args.Has("absent") {
		t.Error("Has is wrong")
	}
	if n, err := args.Int("num", 0); err != nil || n != 7 {
		t.Errorf("Int = %d, %v", n, err)
	}
	if n, err := args.Int("numstr", 0); err != nil || n != 8 {
		t.Errorf("Int from string = %d, %v", n, err)
	}
	if n, err := args.Int("absent", 42); err != nil || n != 42 {
		t.Errorf("Int default = %d, %v", n, err)
	}
	if _, err := args.Int("str", 0); err == nil {
		t.Error("Int should reject text")
	}
	if b, err := args.Bool("flag", false); err != nil || !b {
		t.Errorf("Bool = %v, %v", b, err)
	}
	if b, err := args.Bool("flagstr", true); err != nil || b {
		t.Errorf("Bool from string = %v, %v", b, err)
	}
	if got := args.Strings("list"); len(got) != 2 || got[0] != "a" {
		t.Errorf("Strings = %v", got)
	}
	if got := args.Strings("csv"); len(got) != 2 || got[1] != "d" {
		t.Errorf("Strings from csv = %v", got)
	}
	if _, err := args.RequireString("absent"); err == nil {
		t.Error("RequireString should fail when absent")
	}
	ints, err := (Args{"nums": []any{float64(1), "2"}}).Ints("nums")
	if err != nil || len(ints) != 2 || ints[1] != 2 {
		t.Errorf("Ints = %v, %v", ints, err)
	}
	if _, err := (Args{"nums": []any{"x"}}).Ints("nums"); err == nil {
		t.Error("Ints should reject text")
	}
}

// JSON-RPC 2.0 forbids answering a message that carries no id, even when that
// message is itself malformed.
func TestMalformedNotificationsGetNoResponse(t *testing.T) {
	s := testServer()
	for _, raw := range []string{
		`{"method":"notifications/initialized"}`,
		`{"jsonrpc":"1.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0"}`,
		`{"jsonrpc":"2.0","id":null,"method":"notifications/initialized"}`,
	} {
		if reply, send := s.HandleMessage(context.Background(), []byte(raw)); send {
			t.Errorf("%s produced a response: %s", raw, reply)
		}
	}
}

// A request with an explicit null id is invalid under MCP, and answering is
// more useful than leaving the client waiting forever.
func TestNullIDRequestIsRejected(t *testing.T) {
	s := testServer()
	reply, send := s.HandleMessage(context.Background(), []byte(`{"jsonrpc":"2.0","id":null,"method":"ping"}`))
	if !send {
		t.Fatal("a request with a null id was silently dropped")
	}
	var resp Response
	if err := json.Unmarshal(reply, &resp); err != nil {
		t.Fatal(err)
	}
	if resp.Error == nil || resp.Error.Code != CodeInvalidRequest {
		t.Errorf("response = %s", reply)
	}
}

// The direct call path must validate exactly like the protocol path, so the
// CLI cannot accept arguments a client could not send.
func TestCallToolValidatesArguments(t *testing.T) {
	s := testServer()
	cases := []struct {
		args map[string]any
		want string
	}{
		{map[string]any{}, "missing required argument"},
		{map[string]any{"message": "x", "mesage": "typo"}, "unknown argument"},
		{map[string]any{"message": "x", "mode": "sideways"}, "must be one of"},
		{map[string]any{"message": "x", "times": "many"}, "must be an integer"},
	}
	for _, c := range cases {
		result, err := s.CallTool("echo", c.args)
		if err != nil {
			t.Errorf("CallTool(%v): %v", c.args, err)
			continue
		}
		if !result.IsError || !strings.Contains(result.Content[0].Text, c.want) {
			t.Errorf("CallTool(%v) = %+v, want an error mentioning %q", c.args, result, c.want)
		}
	}
	// A panic is contained on the direct path too: the caller gets an error
	// instead of a crashed process.
	if result, err := s.CallTool("panic", nil); err == nil && (result == nil || !result.IsError) {
		t.Errorf("a panicking tool called directly should report a failure: %v %+v", err, result)
	}
}
