package main

import "testing"

func TestDefaultAddr(t *testing.T) {
	tests := []struct {
		name string
		env  map[string]string
		want string
	}{
		{"default", nil, ":8080"},
		{"PORT", map[string]string{"PORT": "9000"}, ":9000"},
		{"ADDR wins over PORT", map[string]string{"ADDR": "127.0.0.1:7000", "PORT": "9000"}, "127.0.0.1:7000"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			getenv := func(k string) string { return tc.env[k] }
			if got := defaultAddr(getenv); got != tc.want {
				t.Errorf("defaultAddr() = %q, want %q", got, tc.want)
			}
		})
	}
}
