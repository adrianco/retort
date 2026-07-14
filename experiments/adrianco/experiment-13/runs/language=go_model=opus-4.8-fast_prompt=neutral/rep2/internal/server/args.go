// Package server wires the soccer knowledge base to the MCP transport: it
// defines the tool set, parses tool arguments, and formats query results into
// the human-readable answer style shown in TASK.md.
//
// Context: argument helpers. JSON numbers arrive as float64 and booleans/strings
// may be missing; these helpers read tool arguments defensively so a sloppy
// caller (or LLM) gets sensible behavior instead of a panic.
package server

import "fmt"

func argString(args map[string]interface{}, key string) string {
	v, ok := args[key]
	if !ok || v == nil {
		return ""
	}
	switch t := v.(type) {
	case string:
		return t
	case float64:
		return trimFloat(t)
	case bool:
		return fmt.Sprintf("%v", t)
	default:
		return fmt.Sprintf("%v", t)
	}
}

func argInt(args map[string]interface{}, key string) int {
	v, ok := args[key]
	if !ok || v == nil {
		return 0
	}
	switch t := v.(type) {
	case float64:
		return int(t)
	case int:
		return t
	case string:
		var n int
		_, _ = fmt.Sscanf(t, "%d", &n)
		return n
	default:
		return 0
	}
}

func argBool(args map[string]interface{}, key string) bool {
	v, ok := args[key]
	if !ok || v == nil {
		return false
	}
	switch t := v.(type) {
	case bool:
		return t
	case string:
		return t == "true" || t == "1" || t == "yes"
	case float64:
		return t != 0
	default:
		return false
	}
}

func trimFloat(f float64) string {
	if f == float64(int64(f)) {
		return fmt.Sprintf("%d", int64(f))
	}
	return fmt.Sprintf("%g", f)
}
