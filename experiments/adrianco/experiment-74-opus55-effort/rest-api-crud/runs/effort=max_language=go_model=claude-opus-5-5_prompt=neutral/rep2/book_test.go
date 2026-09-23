package main

import (
	"errors"
	"reflect"
	"strings"
	"testing"
)

// ptr returns a pointer to v, for filling in optional fields.
func ptr[T any](v T) *T { return &v }

func TestBookInputNormalize(t *testing.T) {
	in := BookInput{Title: "  Dune \n", Author: "\tFrank Herbert ", Year: ptr(1965), ISBN: ptr(" 978-0441172719 ")}
	in.Normalize()
	assertEqual(t, in, BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: ptr("978-0441172719")})

	blankISBN := BookInput{Title: "Dune", Author: "Frank Herbert", ISBN: ptr("   ")}
	blankISBN.Normalize()
	assertEqual(t, blankISBN, BookInput{Title: "Dune", Author: "Frank Herbert"})
}

func TestBookInputValidate(t *testing.T) {
	const currentYear = 2026
	// dune returns a valid input, modified by change.
	dune := func(change func(*BookInput)) BookInput {
		in := BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: ptr("978-0441172719")}
		change(&in)
		return in
	}
	yearError := ValidationError{{"year", "must be between 1 and 2027"}}

	tests := []struct {
		name string
		in   BookInput
		want ValidationError // nil if the input is valid
	}{
		{"all fields", dune(func(*BookInput) {}), nil},
		{"required fields only", BookInput{Title: "Dune", Author: "Frank Herbert"}, nil},
		{"missing title", dune(func(b *BookInput) { b.Title = "" }), ValidationError{{"title", "is required"}}},
		{"blank author", dune(func(b *BookInput) { b.Author = " \t " }), ValidationError{{"author", "is required"}}},
		{"missing title and author", BookInput{}, ValidationError{{"title", "is required"}, {"author", "is required"}}},
		{"longest title", dune(func(b *BookInput) { b.Title = strings.Repeat("é", maxTitleLength) }), nil},
		{
			"title too long",
			dune(func(b *BookInput) { b.Title = strings.Repeat("a", maxTitleLength+1) }),
			ValidationError{{"title", "must be at most 500 characters"}},
		},
		{
			"author too long",
			dune(func(b *BookInput) { b.Author = strings.Repeat("a", maxAuthorLength+1) }),
			ValidationError{{"author", "must be at most 300 characters"}},
		},
		{
			"isbn too long",
			dune(func(b *BookInput) { b.ISBN = ptr(strings.Repeat("9", maxISBNLength+1)) }),
			ValidationError{{"isbn", "must be at most 32 characters"}},
		},
		{"year 1", dune(func(b *BookInput) { b.Year = ptr(1) }), nil},
		{"next year", dune(func(b *BookInput) { b.Year = ptr(currentYear + 1) }), nil},
		{"year after next", dune(func(b *BookInput) { b.Year = ptr(currentYear + 2) }), yearError},
		{"year 0", dune(func(b *BookInput) { b.Year = ptr(0) }), yearError},
		{"negative year", dune(func(b *BookInput) { b.Year = ptr(-500) }), yearError},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.in.Validate(currentYear)
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
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("Validate() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestValidationErrorMessage(t *testing.T) {
	err := ValidationError{{"title", "is required"}, {"year", "must be between 1 and 2027"}}
	want := "validation failed: title is required; year must be between 1 and 2027"
	if got := err.Error(); got != want {
		t.Errorf("Error() = %q, want %q", got, want)
	}
}
