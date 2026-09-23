package main

import (
	"errors"
	"fmt"
	"strings"
	"testing"
	"time"
)

func TestBookInputValidate(t *testing.T) {
	nextYear := time.Now().Year() + 1
	yearErr := fmt.Sprintf("must be between 1 and %d", nextYear)
	valid := BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: "978-0441013593"}
	with := func(edit func(*BookInput)) BookInput {
		in := valid
		edit(&in)
		return in
	}

	tests := []struct {
		name string
		in   BookInput
		want ValidationError // nil means valid
	}{
		{"all fields", valid, nil},
		{"only required fields", BookInput{Title: "Dune", Author: "Frank Herbert"}, nil},
		{"missing title", with(func(in *BookInput) { in.Title = "" }), ValidationError{"title": "is required"}},
		{"missing author", with(func(in *BookInput) { in.Author = "" }), ValidationError{"author": "is required"}},
		{"blank title and author", with(func(in *BookInput) { in.Title, in.Author = " \t", "\n" }),
			ValidationError{"title": "is required", "author": "is required"}},
		{"title at max length", with(func(in *BookInput) { in.Title = strings.Repeat("é", maxTitleLen) }), nil},
		{"title too long", with(func(in *BookInput) { in.Title = strings.Repeat("é", maxTitleLen+1) }),
			ValidationError{"title": "must be at most 500 characters"}},
		{"author too long", with(func(in *BookInput) { in.Author = strings.Repeat("a", maxAuthorLen+1) }),
			ValidationError{"author": "must be at most 300 characters"}},
		{"isbn too long", with(func(in *BookInput) { in.ISBN = strings.Repeat("9", maxISBNLen+1) }),
			ValidationError{"isbn": "must be at most 32 characters"}},
		{"year 1", with(func(in *BookInput) { in.Year = ptr(1) }), nil},
		{"year next year", with(func(in *BookInput) { in.Year = ptr(nextYear) }), nil},
		{"year zero", with(func(in *BookInput) { in.Year = ptr(0) }), ValidationError{"year": yearErr}},
		{"year negative", with(func(in *BookInput) { in.Year = ptr(-450) }), ValidationError{"year": yearErr}},
		{"year too far ahead", with(func(in *BookInput) { in.Year = ptr(nextYear + 1) }), ValidationError{"year": yearErr}},
		{"every field invalid", BookInput{Year: ptr(0), ISBN: strings.Repeat("9", maxISBNLen+1)},
			ValidationError{"title": "is required", "author": "is required", "year": yearErr, "isbn": "must be at most 32 characters"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.in.Validate()
			if tt.want == nil {
				if err != nil {
					t.Fatalf("Validate() = %v, want nil", err)
				}
				return
			}
			var got ValidationError
			if !errors.As(err, &got) {
				t.Fatalf("Validate() = %v, want a ValidationError", err)
			}
			assertEqual(t, got, tt.want)
		})
	}
}

func TestBookInputNormalize(t *testing.T) {
	in := BookInput{Title: "  Dune\n", Author: "\tFrank Herbert ", Year: ptr(1965), ISBN: " 978-0441013593 "}
	want := BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: "978-0441013593"}
	assertEqual(t, in.Normalize(), want)
}

func TestValidationErrorMessageIsSortedByField(t *testing.T) {
	err := ValidationError{"title": "is required", "author": "is required", "year": "must be between 1 and 2027"}
	want := "validation failed: author is required; title is required; year must be between 1 and 2027"
	if got := err.Error(); got != want {
		t.Errorf("Error() = %q, want %q", got, want)
	}
}
