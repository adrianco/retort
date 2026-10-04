package mcp

import (
	"fmt"
	"strconv"
	"strings"
)

// Args are a tool call's arguments, read leniently: language models send
// numbers as strings and lists as comma-separated text.
type Args map[string]any

func (a Args) String(key string) string {
	switch v := a[key].(type) {
	case nil:
		return ""
	case string:
		return strings.TrimSpace(v)
	case float64:
		return strconv.FormatFloat(v, 'f', -1, 64)
	default:
		return fmt.Sprint(v)
	}
}

func (a Args) Int(key string) (int, error) {
	switch v := a[key].(type) {
	case nil:
		return 0, nil
	case float64:
		return int(v), nil
	case string:
		if strings.TrimSpace(v) == "" {
			return 0, nil
		}
		n, err := strconv.Atoi(strings.TrimSpace(v))
		if err != nil {
			return 0, fmt.Errorf("%s should be a whole number, got %q", key, v)
		}
		return n, nil
	}
	return 0, fmt.Errorf("%s should be a whole number", key)
}

func (a Args) Bool(key string, def bool) bool {
	switch v := a[key].(type) {
	case bool:
		return v
	case string:
		if b, err := strconv.ParseBool(v); err == nil {
			return b
		}
	}
	return def
}

func (a Args) Ints(key string) ([]int, error) {
	var parts []string
	switch v := a[key].(type) {
	case nil:
		return nil, nil
	case []any:
		for _, x := range v {
			parts = append(parts, fmt.Sprint(x))
		}
	case float64:
		return []int{int(v)}, nil
	case string:
		parts = strings.FieldsFunc(v, func(r rune) bool { return r == ',' || r == ' ' || r == ';' })
	}
	var out []int
	for _, p := range parts {
		n, err := strconv.Atoi(strings.TrimSpace(p))
		if err != nil {
			return nil, fmt.Errorf("%s should be a list of years, got %q", key, p)
		}
		out = append(out, n)
	}
	return out, nil
}
