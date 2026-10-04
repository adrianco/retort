package mcpserver

import (
	"fmt"
	"strconv"
	"strings"
)

// Args are the arguments of a tool call. LLMs are not always careful
// about types, so numbers may arrive as strings and the reverse.
type Args map[string]any

// String returns a text argument, or "" when absent.
func (a Args) String(name string) string {
	switch v := a[name].(type) {
	case nil:
		return ""
	case string:
		return strings.TrimSpace(v)
	case float64:
		return strconv.FormatFloat(v, 'f', -1, 64)
	default:
		return strings.TrimSpace(fmt.Sprint(v))
	}
}

// Int returns a whole-number argument, or def when absent.
func (a Args) Int(name string, def int) (int, error) {
	switch v := a[name].(type) {
	case nil:
		return def, nil
	case float64:
		return int(v), nil
	case string:
		if strings.TrimSpace(v) == "" {
			return def, nil
		}
		n, err := strconv.Atoi(strings.TrimSpace(v))
		if err != nil {
			return 0, fmt.Errorf("%s should be a whole number, not %q", name, v)
		}
		return n, nil
	}
	return 0, fmt.Errorf("%s should be a whole number", name)
}

// Ints returns a list of whole numbers given as a list or as "2018,2019".
func (a Args) Ints(name string) ([]int, error) {
	var parts []string
	switch v := a[name].(type) {
	case nil:
		return nil, nil
	case []any:
		for _, x := range v {
			parts = append(parts, fmt.Sprint(x))
		}
	case float64:
		return []int{int(v)}, nil
	default:
		parts = strings.FieldsFunc(fmt.Sprint(v), func(r rune) bool { return r == ',' || r == ' ' || r == ';' })
	}
	var out []int
	for _, p := range parts {
		n, err := strconv.Atoi(strings.TrimSpace(p))
		if err != nil {
			return nil, fmt.Errorf("%s should be a list of years, not %q", name, p)
		}
		out = append(out, n)
	}
	return out, nil
}
