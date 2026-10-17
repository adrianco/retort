package main

import (
	"errors"
	"testing"
)

func TestBookInputValidate(t *testing.T) {
	tests := []struct {
		name    string
		in      BookInput
		wantErr bool
		field   string
	}{
		{"valid full", BookInput{Title: "Dune", Author: "Herbert", Year: 1965, ISBN: "9780441013593"}, false, ""},
		{"valid minimal", BookInput{Title: "Dune", Author: "Herbert"}, false, ""},
		{"valid isbn10 with X", BookInput{Title: "T", Author: "A", ISBN: "043942089X"}, false, ""},
		{"valid isbn with hyphens", BookInput{Title: "T", Author: "A", ISBN: "978-0-441-01359-3"}, false, ""},
		{"missing title", BookInput{Author: "A"}, true, "title"},
		{"missing author", BookInput{Title: "T"}, true, "author"},
		{"negative year", BookInput{Title: "T", Author: "A", Year: -1}, true, "year"},
		{"far future year", BookInput{Title: "T", Author: "A", Year: 99999}, true, "year"},
		{"isbn wrong length", BookInput{Title: "T", Author: "A", ISBN: "12345"}, true, "isbn"},
		{"isbn bad char", BookInput{Title: "T", Author: "A", ISBN: "97804410135aa"}, true, "isbn"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.in.Validate()
			if (err != nil) != tt.wantErr {
				t.Fatalf("Validate() err = %v, wantErr %v", err, tt.wantErr)
			}
			if tt.wantErr {
				var verrs ValidationErrors
				if !errors.As(err, &verrs) {
					t.Fatalf("error is %T, want ValidationErrors", err)
				}
				if _, ok := verrs[tt.field]; !ok {
					t.Fatalf("expected field %q in %v", tt.field, verrs)
				}
			}
		})
	}
}

func TestNormalizeTrimsWhitespace(t *testing.T) {
	got := BookInput{Title: "  Dune ", Author: "\tHerbert\n", ISBN: " 9780441013593 "}.Normalize()
	if got.Title != "Dune" || got.Author != "Herbert" || got.ISBN != "9780441013593" {
		t.Fatalf("Normalize() = %+v", got)
	}
}
