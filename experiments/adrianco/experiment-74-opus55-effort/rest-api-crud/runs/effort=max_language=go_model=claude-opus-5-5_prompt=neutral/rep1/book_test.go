package main

import (
	"encoding/json"
	"reflect"
	"strings"
	"testing"
)

func TestBookInputValidate(t *testing.T) {
	const maxYear = 2027
	tests := []struct {
		name     string
		in       BookInput
		want     Book
		wantErrs FieldErrors
	}{
		{
			name: "all fields",
			in:   BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: "978-0-441-17271-9"},
			want: Book{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: ptr("978-0-441-17271-9")},
		},
		{
			name: "only the required fields",
			in:   BookInput{Title: "Dune", Author: "Frank Herbert"},
			want: Book{Title: "Dune", Author: "Frank Herbert"},
		},
		{
			name: "surrounding whitespace is trimmed",
			in:   BookInput{Title: "  Dune\n", Author: "\tFrank Herbert ", ISBN: " 0441172717 "},
			want: Book{Title: "Dune", Author: "Frank Herbert", ISBN: ptr("0441172717")},
		},
		{
			name: "blank isbn means no isbn",
			in:   BookInput{Title: "Dune", Author: "Frank Herbert", ISBN: "   "},
			want: Book{Title: "Dune", Author: "Frank Herbert"},
		},
		{
			name: "earliest year",
			in:   BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(1)},
			want: Book{Title: "Dune", Author: "Frank Herbert", Year: ptr(1)},
		},
		{
			name: "latest year",
			in:   BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(maxYear)},
			want: Book{Title: "Dune", Author: "Frank Herbert", Year: ptr(maxYear)},
		},
		{
			name: "length limits count characters, not bytes",
			in:   BookInput{Title: strings.Repeat("é", maxTitleLen), Author: strings.Repeat("é", maxAuthorLen)},
			want: Book{Title: strings.Repeat("é", maxTitleLen), Author: strings.Repeat("é", maxAuthorLen)},
		},
		{
			name:     "missing title and author",
			in:       BookInput{},
			wantErrs: FieldErrors{"title": "is required", "author": "is required"},
		},
		{
			name:     "blank title",
			in:       BookInput{Title: " \t ", Author: "Frank Herbert"},
			wantErrs: FieldErrors{"title": "is required"},
		},
		{
			name:     "blank author",
			in:       BookInput{Title: "Dune", Author: "\n"},
			wantErrs: FieldErrors{"author": "is required"},
		},
		{
			name:     "title too long",
			in:       BookInput{Title: strings.Repeat("a", maxTitleLen+1), Author: "Frank Herbert"},
			wantErrs: FieldErrors{"title": "must be at most 500 characters"},
		},
		{
			name:     "author too long",
			in:       BookInput{Title: "Dune", Author: strings.Repeat("a", maxAuthorLen+1)},
			wantErrs: FieldErrors{"author": "must be at most 255 characters"},
		},
		{
			name:     "year zero",
			in:       BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(0)},
			wantErrs: FieldErrors{"year": "must be between 1 and 2027"},
		},
		{
			name:     "negative year",
			in:       BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(-800)},
			wantErrs: FieldErrors{"year": "must be between 1 and 2027"},
		},
		{
			name:     "year after the latest allowed",
			in:       BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(maxYear + 1)},
			wantErrs: FieldErrors{"year": "must be between 1 and 2027"},
		},
		{
			name:     "malformed isbn",
			in:       BookInput{Title: "Dune", Author: "Frank Herbert", ISBN: "0441-1727"},
			wantErrs: FieldErrors{"isbn": "must be an ISBN-10 or ISBN-13, optionally separated by hyphens or spaces"},
		},
		{
			name: "every invalid field is reported",
			in:   BookInput{Title: "", Author: " ", Year: ptr(0), ISBN: "none"},
			wantErrs: FieldErrors{
				"title":  "is required",
				"author": "is required",
				"year":   "must be between 1 and 2027",
				"isbn":   "must be an ISBN-10 or ISBN-13, optionally separated by hyphens or spaces",
			},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, errs := tt.in.Validate(maxYear)
			if !reflect.DeepEqual(errs, tt.wantErrs) {
				t.Errorf("errors = %v, want %v", errs, tt.wantErrs)
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("book = %s, want %s", toJSON(got), toJSON(tt.want))
			}
		})
	}
}

func TestValidISBN(t *testing.T) {
	valid := []string{
		"0441172717",
		"0-441-17271-7",
		"080442957X",
		"080442957x",
		"9780441172719",
		"978-0-441-17271-9",
		"978 0 441 17271 9",
		"1234567890", // wrong check digit, accepted on purpose (see validISBN)
	}
	for _, s := range valid {
		if !validISBN(s) {
			t.Errorf("validISBN(%q) = false, want true", s)
		}
	}

	invalid := []string{
		"",
		"044117271",      // 9 digits
		"04411727170",    // 11 digits
		"978044117271",   // 12 digits
		"97804411727190", // 14 digits
		"X441172717",     // X is only allowed as the last character
		"978044117271X",  // ... of an ISBN-10
		"044117271?",
		"abcdefghij",
		"ISBN 0441172717",
		"0441172717\n",
	}
	for _, s := range invalid {
		if validISBN(s) {
			t.Errorf("validISBN(%q) = true, want false", s)
		}
	}
}

// ptr returns a pointer to v.
func ptr[T any](v T) *T { return &v }

// toJSON renders v for test failure messages, showing the values behind
// pointers rather than their addresses.
func toJSON(v any) string {
	b, err := json.Marshal(v)
	if err != nil {
		return err.Error()
	}
	return string(b)
}
