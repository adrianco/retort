package main

import (
	"errors"
	"strings"
	"testing"
	"time"
)

// ptr returns a pointer to v, for building the optional fields of a BookInput.
func ptr[T any](v T) *T { return &v }

// referenceNow anchors the year validation so the tests do not drift with the
// real clock.
var referenceNow = time.Date(2024, time.March, 14, 15, 9, 26, 0, time.UTC)

func TestBookInputValidate(t *testing.T) {
	tests := []struct {
		name     string
		input    BookInput
		problems []string // exact list expected; nil means the input is valid
	}{
		{
			name:  "all fields present",
			input: BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(1965), ISBN: ptr("9780441013593")},
		},
		{
			name:  "optional fields omitted",
			input: BookInput{Title: "Dune", Author: "Frank Herbert"},
		},
		{
			name:     "title missing",
			input:    BookInput{Author: "Frank Herbert"},
			problems: []string{"title is required"},
		},
		{
			name:     "author missing",
			input:    BookInput{Title: "Dune"},
			problems: []string{"author is required"},
		},
		{
			name:     "title and author blank after trimming",
			input:    BookInput{Title: "   ", Author: "\t\n"},
			problems: []string{"title is required", "author is required"},
		},
		{
			name:     "title too long",
			input:    BookInput{Title: strings.Repeat("x", maxTitleLen+1), Author: "Frank Herbert"},
			problems: []string{"title must be at most 500 characters"},
		},
		{
			name:     "author too long",
			input:    BookInput{Title: "Dune", Author: strings.Repeat("x", maxAuthorLen+1)},
			problems: []string{"author must be at most 300 characters"},
		},
		{
			name:     "year zero",
			input:    BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(0)},
			problems: []string{"year must be between 1 and 2029"},
		},
		{
			name:     "year negative",
			input:    BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(-1965)},
			problems: []string{"year must be between 1 and 2029"},
		},
		{
			name:     "year too far in the future",
			input:    BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(referenceNow.Year() + futureYearSlack + 1)},
			problems: []string{"year must be between 1 and 2029"},
		},
		{
			name:  "year just inside the future slack",
			input: BookInput{Title: "Dune", Author: "Frank Herbert", Year: ptr(referenceNow.Year() + futureYearSlack)},
		},
		{
			name:     "isbn wrong length",
			input:    BookInput{Title: "Dune", Author: "Frank Herbert", ISBN: ptr("12345")},
			problems: []string{"isbn must be 10 or 13 digits (a trailing X is allowed on ISBN-10); hyphens and spaces are ignored"},
		},
		{
			name:     "isbn non numeric",
			input:    BookInput{Title: "Dune", Author: "Frank Herbert", ISBN: ptr("abcdefghij")},
			problems: []string{"isbn must be 10 or 13 digits (a trailing X is allowed on ISBN-10); hyphens and spaces are ignored"},
		},
		{
			name: "every field wrong at once",
			input: BookInput{
				Title:  "",
				Author: "",
				Year:   ptr(0),
				ISBN:   ptr("nope"),
			},
			problems: []string{
				"title is required",
				"author is required",
				"year must be between 1 and 2029",
				"isbn must be 10 or 13 digits (a trailing X is allowed on ISBN-10); hyphens and spaces are ignored",
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			in := tt.input
			in.Clean()
			err := in.Validate(referenceNow)

			if len(tt.problems) == 0 {
				if err != nil {
					t.Fatalf("Validate() = %v, want nil", err)
				}
				return
			}

			var valErr *ValidationError
			if err == nil {
				t.Fatalf("Validate() = nil, want problems %v", tt.problems)
			}
			if !errors.As(err, &valErr) {
				t.Fatalf("Validate() = %v (%T), want *ValidationError", err, err)
			}
			if got, want := strings.Join(valErr.Problems, " | "), strings.Join(tt.problems, " | "); got != want {
				t.Errorf("problems:\n got %s\nwant %s", got, want)
			}
		})
	}
}

func TestBookInputCleanTrimsAndNormalizes(t *testing.T) {
	tests := []struct {
		name       string
		input      BookInput
		wantTitle  string
		wantAuthor string
		wantISBN   *string
	}{
		{
			name:       "surrounding whitespace is trimmed",
			input:      BookInput{Title: "  Dune  ", Author: "\tFrank Herbert\n"},
			wantTitle:  "Dune",
			wantAuthor: "Frank Herbert",
		},
		{
			name:       "isbn separators are stripped",
			input:      BookInput{Title: "Dune", Author: "Frank Herbert", ISBN: ptr("978-0-441-01359-3")},
			wantTitle:  "Dune",
			wantAuthor: "Frank Herbert",
			wantISBN:   ptr("9780441013593"),
		},
		{
			name:       "isbn-10 check character is upper-cased",
			input:      BookInput{Title: "Dune", Author: "Frank Herbert", ISBN: ptr("0 8044 2957 x")},
			wantTitle:  "Dune",
			wantAuthor: "Frank Herbert",
			wantISBN:   ptr("080442957X"),
		},
		{
			name:       "empty isbn becomes absent",
			input:      BookInput{Title: "Dune", Author: "Frank Herbert", ISBN: ptr("   ")},
			wantTitle:  "Dune",
			wantAuthor: "Frank Herbert",
			wantISBN:   nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			in := tt.input
			in.Clean()

			if in.Title != tt.wantTitle {
				t.Errorf("Title = %q, want %q", in.Title, tt.wantTitle)
			}
			if in.Author != tt.wantAuthor {
				t.Errorf("Author = %q, want %q", in.Author, tt.wantAuthor)
			}
			switch {
			case tt.wantISBN == nil && in.ISBN != nil:
				t.Errorf("ISBN = %q, want nil", *in.ISBN)
			case tt.wantISBN != nil && in.ISBN == nil:
				t.Errorf("ISBN = nil, want %q", *tt.wantISBN)
			case tt.wantISBN != nil && *in.ISBN != *tt.wantISBN:
				t.Errorf("ISBN = %q, want %q", *in.ISBN, *tt.wantISBN)
			}
			if err := in.Validate(referenceNow); err != nil {
				t.Errorf("cleaned input should validate, got %v", err)
			}
		})
	}
}
