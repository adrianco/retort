// Context: method dispatch for the MCP server. Maps JSON-RPC method names to
// handlers and shapes the MCP-specific result payloads (initialize result,
// tools/list, tools/call content blocks).
package mcp

import "encoding/json"

// dispatch routes a request to the appropriate handler, returning either a
// result value or an RPC error.
func (s *Server) dispatch(req *Request) (interface{}, *RPCError) {
	switch req.Method {
	case "initialize":
		return s.handleInitialize(), nil
	case "notifications/initialized", "initialized":
		return nil, nil
	case "ping":
		return map[string]interface{}{}, nil
	case "tools/list":
		return s.handleToolsList(), nil
	case "tools/call":
		return s.handleToolsCall(req.Params)
	default:
		return nil, errf(CodeMethodNotFound, "method not found: %s", req.Method)
	}
}

func (s *Server) handleInitialize() interface{} {
	return map[string]interface{}{
		"protocolVersion": ProtocolVersion,
		"capabilities": map[string]interface{}{
			"tools": map[string]interface{}{},
		},
		"serverInfo": map[string]interface{}{
			"name":    s.name,
			"version": s.version,
		},
	}
}

func (s *Server) handleToolsList() interface{} {
	// Return tools without the (non-serializable) handler field.
	type listed struct {
		Name        string                 `json:"name"`
		Description string                 `json:"description"`
		InputSchema map[string]interface{} `json:"inputSchema"`
	}
	out := make([]listed, 0, len(s.tools))
	for _, t := range s.tools {
		out = append(out, listed{t.Name, t.Description, t.InputSchema})
	}
	return map[string]interface{}{"tools": out}
}

// callParams is the params object for tools/call.
type callParams struct {
	Name      string                 `json:"name"`
	Arguments map[string]interface{} `json:"arguments"`
}

func (s *Server) handleToolsCall(raw json.RawMessage) (interface{}, *RPCError) {
	var p callParams
	if err := json.Unmarshal(raw, &p); err != nil {
		return nil, errf(CodeInvalidParams, "invalid params: %v", err)
	}
	tool, ok := s.byName[p.Name]
	if !ok {
		return nil, errf(CodeMethodNotFound, "unknown tool: %s", p.Name)
	}
	if p.Arguments == nil {
		p.Arguments = map[string]interface{}{}
	}
	text, err := tool.Handler(p.Arguments)
	if err != nil {
		// MCP convention: tool errors are reported as result content with
		// isError=true rather than as protocol-level errors.
		return toolResult(err.Error(), true), nil
	}
	return toolResult(text, false), nil
}

// toolResult builds an MCP tools/call result with a single text content block.
func toolResult(text string, isErr bool) interface{} {
	return map[string]interface{}{
		"content": []map[string]interface{}{
			{"type": "text", "text": text},
		},
		"isError": isErr,
	}
}
