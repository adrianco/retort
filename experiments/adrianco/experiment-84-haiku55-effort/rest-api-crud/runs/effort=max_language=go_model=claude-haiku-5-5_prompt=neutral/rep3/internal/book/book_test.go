package book

import (
	"fmt"
	"maps"
	"strings"
	"testing"
	"time"
)

func TestValidate(t *testing.T) {
	maxYear := time.Now().Year() + 1
	yearMsg := fmt.Sprintf("must be between 0 and %d", maxYear)

	tests := []struct {
		name    string
		in      Input
		wantErr map[string]string // nil means the input should be accepted
	}{
		{
			name: "title and author only",
			in:   Input{Title: "The Hobbit", Author: "J.R.R. Tolkien"},
		},
		{
			name: "all fields",
			in:   Input{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0-441-17271-9"},
		},
		{
			name:    "missing title and author",
			in:      Input{Year: 1965},
			wantErr: map[string]string{"title": "is required", "author": "is required"},
		},
		{
			name:    "whitespace-only title counts as missing",
			in:      Input{Title: "   \t", Author: "Frank Herbert"},
			wantErr: map[string]string{"title": "is required"},
		},
		{
			name:    "whitespace-only author counts as missing",
			in:      Input{Title: "Dune", Author: " "},
			wantErr: map[string]string{"author": "is required"},
		},
		{
			name:    "title over the length limit",
			in:      Input{Title: strings.Repeat("t", MaxTitleLength+1), Author: "Someone"},
			wantErr: map[string]string{"title": fmt.Sprintf("must be at most %d characters", MaxTitleLength)},
		},
		{
			name: "title at the length limit",
			in:   Input{Title: strings.Repeat("t", MaxTitleLength), Author: "Someone"},
		},
		{
			name:    "author over the length limit",
			in:      Input{Title: "Dune", Author: strings.Repeat("a", MaxAuthorLength+1)},
			wantErr: map[string]string{"author": fmt.Sprintf("must be at most %d characters", MaxAuthorLength)},
		},
		{
			name: "length counts characters, not bytes",
			in:   Input{Title: strings.Repeat("é", MaxTitleLength), Author: "Someone"},
		},
		{
			name: "year zero means unknown",
			in:   Input{Title: "Dune", Author: "Frank Herbert", Year: 0},
		},
		{
			name: "next year is allowed for forthcoming titles",
			in:   Input{Title: "Dune", Author: "Frank Herbert", Year: maxYear},
		},
		{
			name:    "negative year",
			in:      Input{Title: "Dune", Author: "Frank Herbert", Year: -1},
			wantErr: map[string]string{"year": yearMsg},
		},
		{
			name:    "year too far in the future",
			in:      Input{Title: "Dune", Author: "Frank Herbert", Year: maxYear + 1},
			wantErr: map[string]string{"year": yearMsg},
		},
		{
			name:    "malformed isbn",
			in:      Input{Title: "Dune", Author: "Frank Herbert", ISBN: "not-an-isbn"},
			wantErr: map[string]string{"isbn": "must be an ISBN-10 or ISBN-13"},
		},
		{
			name: "several problems are all reported",
			in:   Input{Year: -5, ISBN: "123"},
			wantErr: map[string]string{
				"title":  "is required",
				"author": "is required",
				"year":   yearMsg,
				"isbn":   "must be an ISBN-10 or ISBN-13",
			},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			_, verr := tc.in.Validate()
			if tc.wantErr == nil {
				if verr != nil {
					t.Fatalf("Validate() failed: %v", verr.Fields)
				}
				return
			}
			if verr == nil {
				t.Fatalf("Validate() accepted the input; want failures %v", tc.wantErr)
			}
			if !maps.Equal(verr.Fields, tc.wantErr) {
				t.Errorf("Validate() failures = %v; want %v", verr.Fields, tc.wantErr)
			}
		})
	}
}

func TestValidateISBN(t *testing.T) {
	tests := []struct {
		isbn  string
		valid bool
	}{
		{"0306406152", true},
		{"030640615X", true},
		{"030640615x", true},
		{"0-306-40615-2", true},
		{"9780306406157", true},
		{"978-0-306-40615-7", true},
		{"978 0 306 40615 7", true},
		{"", true}, // optional, so an empty value is not checked
		{"030640615", false},
		{"03064061522", false},
		{"978030640615X", false}, // X is only valid as the ISBN-10 check digit
		{"97803064061570", false},
		{"abcdefghij", false},
	}

	for _, tc := range tests {
		t.Run(tc.isbn, func(t *testing.T) {
			_, verr := Input{Title: "t", Author: "a", ISBN: tc.isbn}.Validate()
			gotValid := verr == nil || verr.Fields["isbn"] == ""
			if gotValid != tc.valid {
				t.Errorf("isbn %q: valid = %v; want %v (failures %v)", tc.isbn, gotValid, tc.valid, verr)
			}
		})
	}
}

func TestValidateTrimsWhitespace(t *testing.T) {
	clean, verr := Input{
		Title:  "  Dune  ",
		Author: "\tFrank Herbert\n",
		Year:   1965,
		ISBN:   " 9780441172719 ",
	}.Validate()
	if verr != nil {
		t.Fatalf("Validate() failed: %v", verr.Fields)
	}
	want := Input{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"}
	if clean != want {
		t.Errorf("Validate() = %+v; want %+v", clean, want)
	}
}
