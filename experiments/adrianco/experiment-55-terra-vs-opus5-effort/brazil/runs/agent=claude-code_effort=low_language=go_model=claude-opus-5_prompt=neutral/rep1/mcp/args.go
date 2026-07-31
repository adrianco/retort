// args.go provides tolerant accessors for tool arguments. LLM clients are
// inconsistent about JSON types (a season may arrive as 2019, 2019.0 or
// "2019"), so every getter accepts the reasonable spellings rather than
// failing the call.
package mcp

import (
	"fmt"
	"strconv"
	"strings"
)

// Args is a decoded tool argument object.
type Args map[string]any

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
	default:
		return strings.TrimSpace(fmt.Sprint(t))
	}
}

// RequireString returns a string argument or an error when it is missing.
func (a Args) RequireString(key string) (string, error) {
	s := a.String(key)
	if s == "" {
		return "", fmt.Errorf("missing required argument %q", key)
	}
	return s, nil
}

// Int returns an integer argument, falling back to def.
func (a Args) Int(key string, def int) int {
	v, ok := a[key]
	if !ok || v == nil {
		return def
	}
	switch t := v.(type) {
	case float64:
		return int(t)
	case int:
		return t
	case string:
		s := strings.TrimSpace(t)
		if s == "" {
			return def
		}
		if n, err := strconv.Atoi(s); err == nil {
			return n
		}
		if f, err := strconv.ParseFloat(s, 64); err == nil {
			return int(f)
		}
	}
	return def
}

// Bool returns a boolean argument, falling back to def.
func (a Args) Bool(key string, def bool) bool {
	v, ok := a[key]
	if !ok || v == nil {
		return def
	}
	switch t := v.(type) {
	case bool:
		return t
	case string:
		if b, err := strconv.ParseBool(strings.TrimSpace(t)); err == nil {
			return b
		}
	case float64:
		return t != 0
	}
	return def
}
