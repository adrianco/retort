package main

import (
	"errors"
	"testing"
)

func TestNormalizeISBN(t *testing.T) {
	tests := map[string]string{
		"978-0-441-17271-9": "9780441172719",
		" 0 306 40615 2 ":   "0306406152",
		"030640615x":        "030640615X",
		"":                  "",
	}
	for in, want := range tests {
		if got := normalizeISBN(in); got != want {
			t.Errorf("normalizeISBN(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestValidate(t *testing.T) {
	tests := []struct {
		name   string
		in     BookInput
		fields []string // empty means valid
	}{
		{"minimal valid", BookInput{Title: "T", Author: "A"}, nil},
		{"full valid", BookInput{Title: "T", Author: "A", Year: 1999, ISBN: "0306406152"}, nil},
		{"isbn-10 with X", BookInput{Title: "T", Author: "A", ISBN: "030640615X"}, nil},
		{"isbn-13", BookInput{Title: "T", Author: "A", ISBN: "9780306406157"}, nil},
		{"missing title", BookInput{Author: "A"}, []string{"title"}},
		{"missing author", BookInput{Title: "T"}, []string{"author"}},
		{"year too small", BookInput{Title: "T", Author: "A", Year: 999}, []string{"year"}},
		{"year too large", BookInput{Title: "T", Author: "A", Year: 10000}, []string{"year"}},
		{"negative year", BookInput{Title: "T", Author: "A", Year: -1}, []string{"year"}},
		{"isbn wrong length", BookInput{Title: "T", Author: "A", ISBN: "12345"}, []string{"isbn"}},
		{"isbn-13 with letters", BookInput{Title: "T", Author: "A", ISBN: "978030640615X"}, []string{"isbn"}},
		{"all invalid", BookInput{}, []string{"title", "author"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.in.normalize().Validate()
			if len(tt.fields) == 0 {
				if err != nil {
					t.Fatalf("unexpected error: %v", err)
				}
				return
			}
			var verrs ValidationErrors
			if !errors.As(err, &verrs) {
				t.Fatalf("error = %v, want ValidationErrors", err)
			}
			for _, f := range tt.fields {
				if _, ok := verrs[f]; !ok {
					t.Errorf("no error for field %q; got %v", f, verrs)
				}
			}
			if len(verrs) != len(tt.fields) {
				t.Errorf("got errors for %v, want only %v", verrs, tt.fields)
			}
		})
	}
}
