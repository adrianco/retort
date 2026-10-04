package dsl

import (
	"strconv"
	"strings"
	"testing"
)

// Params holds the "name: value" arguments passed to a DSL method, so that
// specs only state the values they care about and the DSL fills in the rest.
type Params map[string]string

func parseParams(t testing.TB, args ...string) Params {
	t.Helper()
	p := Params{}
	for _, arg := range args {
		key, value, ok := strings.Cut(arg, ":")
		if !ok {
			t.Fatalf("DSL argument %q should be written as \"name: value\"", arg)
		}
		p[strings.ToLower(strings.TrimSpace(key))] = strings.TrimSpace(value)
	}
	return p
}

// Get returns the named value, or the default when the spec did not give one.
func (p Params) Get(key, def string) string {
	if v, ok := p[key]; ok {
		return v
	}
	return def
}

func (p Params) Has(key string) bool {
	_, ok := p[key]
	return ok
}

// Int returns the named value as a number, or the default.
func (p Params) Int(t testing.TB, key string, def int) int {
	t.Helper()
	v, ok := p[key]
	if !ok {
		return def
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		t.Fatalf("DSL argument %q should be a whole number, got %q", key, v)
	}
	return n
}

// Pair reads values written as "a-b", such as a score of "2-1".
func (p Params) Pair(t testing.TB, key string, defA, defB int) (int, int, bool) {
	t.Helper()
	v, ok := p[key]
	if !ok {
		return defA, defB, false
	}
	a, b, found := strings.Cut(v, "-")
	x, errA := strconv.Atoi(strings.TrimSpace(a))
	y, errB := strconv.Atoi(strings.TrimSpace(b))
	if !found || errA != nil || errB != nil {
		t.Fatalf("DSL argument %q should be written like \"2-1\", got %q", key, v)
	}
	return x, y, true
}

// List splits a comma-separated value.
func (p Params) List(key string) []string {
	var out []string
	for _, item := range strings.Split(p[key], ",") {
		if s := strings.TrimSpace(item); s != "" {
			out = append(out, s)
		}
	}
	return out
}
