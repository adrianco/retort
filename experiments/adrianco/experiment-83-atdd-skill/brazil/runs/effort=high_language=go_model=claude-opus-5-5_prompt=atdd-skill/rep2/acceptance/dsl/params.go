// Params is the small toolkit the DSL uses to read "key: value" arguments
// with defaults, after Dave Farley's Params class. Test cases only state what
// they care about; everything else falls back to a sensible default.
package dsl

import (
	"strconv"

	"brsoccer/acceptance/drivers"
	"strings"
	"testing"
)

type Params struct {
	t      testing.TB
	values map[string]string
	order  []string
}

func NewParams(t testing.TB, args ...string) Params {
	t.Helper()
	p := Params{t: t, values: map[string]string{}}
	for _, arg := range args {
		key, value, ok := strings.Cut(arg, ":")
		if !ok {
			t.Fatalf("DSL argument %q should look like \"name: value\"", arg)
		}
		key = strings.ToLower(strings.TrimSpace(key))
		p.values[key] = strings.TrimSpace(value)
		p.order = append(p.order, key)
	}
	return p
}

func (p Params) Has(key string) bool {
	_, ok := p.values[key]
	return ok
}

func (p Params) Optional(key, def string) string {
	if v, ok := p.values[key]; ok {
		return v
	}
	return def
}

func (p Params) Required(key string) string {
	p.t.Helper()
	v, ok := p.values[key]
	if !ok {
		p.t.Fatalf("DSL argument %q is required", key)
	}
	return v
}

func (p Params) Int(key string, def int) int {
	p.t.Helper()
	v, ok := p.values[key]
	if !ok {
		return def
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		p.t.Fatalf("DSL argument %q should be a whole number, got %q", key, v)
	}
	return n
}

// Expectations returns every supplied key in the order given, for
// confirmations that check whichever facts the test case cares about.
func (p Params) Expectations() []drivers.Expectation {
	out := make([]drivers.Expectation, 0, len(p.order))
	for _, k := range p.order {
		out = append(out, drivers.Expectation{Fact: k, Value: p.values[k]})
	}
	return out
}

// Criteria returns the supplied arguments as query criteria.
func (p Params) Criteria() map[string]string {
	out := make(map[string]string, len(p.values))
	for k, v := range p.values {
		out[k] = v
	}
	return out
}
