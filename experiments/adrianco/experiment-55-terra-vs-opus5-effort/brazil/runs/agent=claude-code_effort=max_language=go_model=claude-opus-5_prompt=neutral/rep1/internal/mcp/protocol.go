// Package mcp is a dependency-free implementation of the Model Context
// Protocol server role over the stdio transport: newline delimited JSON-RPC
// 2.0 on stdin/stdout, with tools, resources, prompts and completions.
//
// protocol.go holds the wire types and the small JSON Schema builder used to
// describe tool arguments.
package mcp

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
)

// Protocol versions this server understands, newest first.
var supportedVersions = []string{"2025-06-18", "2025-03-26", "2024-11-05"}

// LatestVersion is the protocol revision the server prefers.
const LatestVersion = "2025-06-18"

// JSON-RPC error codes (the standard set plus the MCP additions).
const (
	CodeParseError     = -32700
	CodeInvalidRequest = -32600
	CodeMethodNotFound = -32601
	CodeInvalidParams  = -32602
	CodeInternalError  = -32603
)

// Request is an incoming JSON-RPC request or notification.
type Request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

// IsNotification reports whether no response must be sent. Only an absent id
// makes a message a notification; a literal null id is an invalid request,
// except from clients that spell their notifications that way.
func (r *Request) IsNotification() bool {
	if len(r.ID) == 0 {
		return true
	}
	return r.HasNullID() && strings.HasPrefix(r.Method, "notifications/")
}

// HasNullID reports whether the message carried an explicit null id.
func (r *Request) HasNullID() bool { return string(r.ID) == "null" }

// Response is an outgoing JSON-RPC response.
type Response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
}

// RPCError is a JSON-RPC error object.
type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

func (e *RPCError) Error() string { return fmt.Sprintf("%d: %s", e.Code, e.Message) }

// Errorf builds an RPCError.
func Errorf(code int, format string, args ...any) *RPCError {
	return &RPCError{Code: code, Message: fmt.Sprintf(format, args...)}
}

func newResponse(id json.RawMessage, result any) *Response {
	if len(id) == 0 {
		id = json.RawMessage("null")
	}
	return &Response{JSONRPC: "2.0", ID: id, Result: result}
}

func newError(id json.RawMessage, err *RPCError) *Response {
	if len(id) == 0 {
		id = json.RawMessage("null")
	}
	return &Response{JSONRPC: "2.0", ID: id, Error: err}
}

// ---------------------------------------------------------------------------
// Initialize
// ---------------------------------------------------------------------------

// Implementation identifies a client or server.
type Implementation struct {
	Name    string `json:"name"`
	Title   string `json:"title,omitempty"`
	Version string `json:"version"`
}

type initializeParams struct {
	ProtocolVersion string         `json:"protocolVersion"`
	Capabilities    map[string]any `json:"capabilities"`
	ClientInfo      Implementation `json:"clientInfo"`
}

type initializeResult struct {
	ProtocolVersion string         `json:"protocolVersion"`
	Capabilities    map[string]any `json:"capabilities"`
	ServerInfo      Implementation `json:"serverInfo"`
	Instructions    string         `json:"instructions,omitempty"`
}

// ---------------------------------------------------------------------------
// Tools
// ---------------------------------------------------------------------------

// Content is one block of tool or prompt output.
type Content struct {
	Type string `json:"type"`
	Text string `json:"text,omitempty"`
}

// TextContent builds a text block.
func TextContent(text string) Content { return Content{Type: "text", Text: text} }

// ToolResult is what a tool returns.
type ToolResult struct {
	Content           []Content `json:"content"`
	StructuredContent any       `json:"structuredContent,omitempty"`
	IsError           bool      `json:"isError,omitempty"`
}

// Text builds a successful text result.
func Text(text string) *ToolResult {
	return &ToolResult{Content: []Content{TextContent(text)}}
}

// TextWithData builds a successful result carrying both prose and structured
// data, which is what every tool in this server returns.
func TextWithData(text string, data any) *ToolResult {
	return &ToolResult{Content: []Content{TextContent(text)}, StructuredContent: data}
}

// Errorf builds a failed tool result. Tool failures are reported inside the
// result (rather than as protocol errors) so the model can read and react to
// them, as the MCP specification requires.
func ErrorResult(format string, args ...any) *ToolResult {
	return &ToolResult{Content: []Content{TextContent(fmt.Sprintf(format, args...))}, IsError: true}
}

// Tool is a callable exposed to the client.
type Tool struct {
	Name        string  `json:"name"`
	Title       string  `json:"title,omitempty"`
	Description string  `json:"description"`
	InputSchema *Schema `json:"inputSchema"`
	Handler     Handler `json:"-"`
}

// Handler executes a tool call.
type Handler func(args Args) (*ToolResult, error)

// ---------------------------------------------------------------------------
// JSON Schema (only the subset needed to describe tool arguments)
// ---------------------------------------------------------------------------

// Schema is a JSON Schema object description.
type Schema struct {
	Type                 string           `json:"type"`
	Properties           map[string]*Prop `json:"properties,omitempty"`
	Required             []string         `json:"required,omitempty"`
	AdditionalProperties *bool            `json:"additionalProperties,omitempty"`
}

// Prop is a property inside a Schema.
type Prop struct {
	Type        string   `json:"type,omitempty"`
	Description string   `json:"description,omitempty"`
	Enum        []string `json:"enum,omitempty"`
	Default     any      `json:"default,omitempty"`
	Items       *Prop    `json:"items,omitempty"`
	Minimum     *float64 `json:"minimum,omitempty"`
	Maximum     *float64 `json:"maximum,omitempty"`
}

// Object builds a schema from name/property pairs, in a stable order.
func Object(props map[string]*Prop, required ...string) *Schema {
	no := false
	return &Schema{Type: "object", Properties: props, Required: required, AdditionalProperties: &no}
}

// Str describes a string argument.
func Str(desc string) *Prop { return &Prop{Type: "string", Description: desc} }

// Int describes an integer argument.
func Int(desc string) *Prop { return &Prop{Type: "integer", Description: desc} }

// IntRange describes a bounded integer argument.
func IntRange(desc string, min, max float64) *Prop {
	return &Prop{Type: "integer", Description: desc, Minimum: &min, Maximum: &max}
}

// Bool describes a boolean argument.
func Bool(desc string) *Prop { return &Prop{Type: "boolean", Description: desc} }

// Enum describes a string argument restricted to a set of values.
func Enum(desc string, values ...string) *Prop {
	return &Prop{Type: "string", Description: desc, Enum: values}
}

// StrArray describes an array-of-strings argument.
func StrArray(desc string) *Prop {
	return &Prop{Type: "array", Description: desc, Items: &Prop{Type: "string"}}
}

// IntArray describes an array-of-integers argument.
func IntArray(desc string) *Prop {
	return &Prop{Type: "array", Description: desc, Items: &Prop{Type: "integer"}}
}

// ---------------------------------------------------------------------------
// Arguments
// ---------------------------------------------------------------------------

// Args is a decoded tool argument object with forgiving accessors: numbers may
// arrive as strings and vice versa, which is what happens when an LLM fills in
// the arguments.
type Args map[string]any

// Has reports whether a key was supplied with a non-empty value.
func (a Args) Has(key string) bool {
	v, ok := a[key]
	if !ok || v == nil {
		return false
	}
	if s, isStr := v.(string); isStr {
		return strings.TrimSpace(s) != ""
	}
	return true
}

// String returns a string argument, or "" when absent.
func (a Args) String(key string) string {
	v, ok := a[key]
	if !ok || v == nil {
		return ""
	}
	switch t := v.(type) {
	case string:
		return strings.TrimSpace(t)
	case float64:
		return strconv.FormatFloat(t, 'f', -1, 64)
	case bool:
		return strconv.FormatBool(t)
	}
	return fmt.Sprint(v)
}

// RequireString returns a string argument or an error when it is missing.
func (a Args) RequireString(key string) (string, error) {
	s := a.String(key)
	if s == "" {
		return "", fmt.Errorf("missing required argument %q", key)
	}
	return s, nil
}

// Int returns an integer argument, or def when absent.
func (a Args) Int(key string, def int) (int, error) {
	v, ok := a[key]
	if !ok || v == nil {
		return def, nil
	}
	switch t := v.(type) {
	case float64:
		return int(t), nil
	case int:
		return t, nil
	case string:
		s := strings.TrimSpace(t)
		if s == "" {
			return def, nil
		}
		n, err := strconv.Atoi(s)
		if err != nil {
			return def, fmt.Errorf("argument %q must be an integer, got %q", key, t)
		}
		return n, nil
	}
	return def, fmt.Errorf("argument %q must be an integer", key)
}

// Bool returns a boolean argument, or def when absent.
func (a Args) Bool(key string, def bool) (bool, error) {
	v, ok := a[key]
	if !ok || v == nil {
		return def, nil
	}
	switch t := v.(type) {
	case bool:
		return t, nil
	case string:
		s := strings.TrimSpace(strings.ToLower(t))
		if s == "" {
			return def, nil
		}
		b, err := strconv.ParseBool(s)
		if err != nil {
			return def, fmt.Errorf("argument %q must be a boolean, got %q", key, t)
		}
		return b, nil
	}
	return def, fmt.Errorf("argument %q must be a boolean", key)
}

// Strings returns an array argument, accepting a comma separated string too.
func (a Args) Strings(key string) []string {
	v, ok := a[key]
	if !ok || v == nil {
		return nil
	}
	switch t := v.(type) {
	case []any:
		out := make([]string, 0, len(t))
		for _, item := range t {
			if s := strings.TrimSpace(fmt.Sprint(item)); s != "" {
				out = append(out, s)
			}
		}
		return out
	case []string:
		return t
	case string:
		var out []string
		for _, part := range strings.Split(t, ",") {
			if s := strings.TrimSpace(part); s != "" {
				out = append(out, s)
			}
		}
		return out
	}
	return nil
}

// Ints returns an integer array argument.
func (a Args) Ints(key string) ([]int, error) {
	var out []int
	for _, s := range a.Strings(key) {
		n, err := strconv.Atoi(strings.TrimSpace(s))
		if err != nil {
			f, ferr := strconv.ParseFloat(strings.TrimSpace(s), 64)
			if ferr != nil {
				return nil, fmt.Errorf("argument %q must contain integers, got %q", key, s)
			}
			n = int(f)
		}
		out = append(out, n)
	}
	return out, nil
}

// ---------------------------------------------------------------------------
// Resources and prompts
// ---------------------------------------------------------------------------

// Resource is a readable document exposed by the server.
type Resource struct {
	URI         string                 `json:"uri"`
	Name        string                 `json:"name"`
	Title       string                 `json:"title,omitempty"`
	Description string                 `json:"description,omitempty"`
	MIMEType    string                 `json:"mimeType,omitempty"`
	Reader      func() (string, error) `json:"-"`
}

// ResourceContents is one document returned by resources/read.
type ResourceContents struct {
	URI      string `json:"uri"`
	MIMEType string `json:"mimeType,omitempty"`
	Text     string `json:"text"`
}

// PromptArgument describes one prompt parameter.
type PromptArgument struct {
	Name        string `json:"name"`
	Description string `json:"description,omitempty"`
	Required    bool   `json:"required,omitempty"`
}

// Prompt is a reusable prompt template.
type Prompt struct {
	Name        string                                               `json:"name"`
	Title       string                                               `json:"title,omitempty"`
	Description string                                               `json:"description,omitempty"`
	Arguments   []PromptArgument                                     `json:"arguments,omitempty"`
	Render      func(args map[string]string) (string, string, error) `json:"-"` // description, text
}

// PromptMessage is one message of a rendered prompt.
type PromptMessage struct {
	Role    string  `json:"role"`
	Content Content `json:"content"`
}

type getPromptResult struct {
	Description string          `json:"description,omitempty"`
	Messages    []PromptMessage `json:"messages"`
}

// CompletionFunc supplies argument completions for prompts and resources.
type CompletionFunc func(ref, argument, value string) []string
