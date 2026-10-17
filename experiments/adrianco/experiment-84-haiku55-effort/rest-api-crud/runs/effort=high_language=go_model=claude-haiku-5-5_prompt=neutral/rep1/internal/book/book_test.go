package book

import (
	"errors"
	"strings"
	"testing"
)

const testYear = 2026

func TestValidate(t *testing.T) {
	tests := []struct {
		name       string
		in         Book
		wantFields []string // empty means the book should be valid
		wantISBN   string   // expected normalized ISBN when valid
		wantTitle  string
	}{
		{
			name:      "minimal valid book",
			in:        Book{Title: "Dune", Author: "Frank Herbert"},
			wantTitle: "Dune",
		},
		{
			name: "all fields valid",
			in:   Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0-306-40615-7"},
		},
		{
			name:       "missing title",
			in:         Book{Author: "Frank Herbert"},
			wantFields: []string{"title"},
		},
		{
			name:       "missing author",
			in:         Book{Title: "Dune"},
			wantFields: []string{"author"},
		},
		{
			name:       "whitespace-only title and author are rejected",
			in:         Book{Title: "   \t", Author: "  \n "},
			wantFields: []string{"title", "author"},
		},
		{
			name:      "surrounding whitespace is trimmed",
			in:        Book{Title: "  Dune  ", Author: " Frank Herbert "},
			wantTitle: "Dune",
		},
		{
			name:       "title over max length",
			in:         Book{Title: strings.Repeat("a", MaxTitleLen+1), Author: "A"},
			wantFields: []string{"title"},
		},
		{
			name: "title at max length is allowed",
			in:   Book{Title: strings.Repeat("a", MaxTitleLen), Author: "A"},
		},
		{
			name:       "author over max length",
			in:         Book{Title: "T", Author: strings.Repeat("é", MaxAuthorLen+1)},
			wantFields: []string{"author"},
		},
		{
			name:       "year before minimum",
			in:         Book{Title: "T", Author: "A", Year: 999},
			wantFields: []string{"year"},
		},
		{
			name:       "negative year",
			in:         Book{Title: "T", Author: "A", Year: -1},
			wantFields: []string{"year"},
		},
		{
			name:       "year too far in the future",
			in:         Book{Title: "T", Author: "A", Year: testYear + 2},
			wantFields: []string{"year"},
		},
		{
			name: "year next year is allowed",
			in:   Book{Title: "T", Author: "A", Year: testYear + 1},
		},
		{
			name:       "isbn wrong checksum",
			in:         Book{Title: "T", Author: "A", ISBN: "978-0-306-40615-8"},
			wantFields: []string{"isbn"},
		},
		{
			name:       "isbn wrong length",
			in:         Book{Title: "T", Author: "A", ISBN: "12345"},
			wantFields: []string{"isbn"},
		},
		{
			name:       "isbn with letters",
			in:         Book{Title: "T", Author: "A", ISBN: "abcdefghij"},
			wantFields: []string{"isbn"},
		},
		{
			name:     "valid isbn-10",
			in:       Book{Title: "T", Author: "A", ISBN: "0-306-40615-2"},
			wantISBN: "0306406152",
		},
		{
			name:     "isbn-10 with X check digit is accepted lowercase too",
			in:       Book{Title: "T", Author: "A", ISBN: "0-8044-2957-x"},
			wantISBN: "080442957X",
		},
		{
			name:     "isbn-13 is normalized by stripping hyphens",
			in:       Book{Title: "T", Author: "A", ISBN: "978-0-306-40615-7"},
			wantISBN: "9780306406157",
		},
		{
			name:       "several problems are reported together",
			in:         Book{Year: 1, ISBN: "bad"},
			wantFields: []string{"title", "author", "year", "isbn"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			b := tt.in
			err := validateAt(&b, testYear)

			if len(tt.wantFields) == 0 {
				if err != nil {
					t.Fatalf("validateAt() error = %v, want nil", err)
				}
				if tt.wantTitle != "" && b.Title != tt.wantTitle {
					t.Errorf("Title = %q, want %q", b.Title, tt.wantTitle)
				}
				if tt.wantISBN != "" && b.ISBN != tt.wantISBN {
					t.Errorf("ISBN = %q, want %q", b.ISBN, tt.wantISBN)
				}
				return
			}

			var ve *ValidationError
			if !errors.As(err, &ve) {
				t.Fatalf("validateAt() error = %v, want *ValidationError", err)
			}
			if len(ve.Details) != len(tt.wantFields) {
				t.Errorf("Details = %v, want fields %v", ve.Details, tt.wantFields)
			}
			for _, f := range tt.wantFields {
				if ve.Details[f] == "" {
					t.Errorf("Details missing field %q: %v", f, ve.Details)
				}
			}
		})
	}
}

func TestValidateUsesCurrentYear(t *testing.T) {
	b := Book{Title: "T", Author: "A", Year: 2100}
	if err := Validate(&b); err == nil {
		t.Fatal("Validate() accepted year 2100, which is beyond next year")
	}
}
