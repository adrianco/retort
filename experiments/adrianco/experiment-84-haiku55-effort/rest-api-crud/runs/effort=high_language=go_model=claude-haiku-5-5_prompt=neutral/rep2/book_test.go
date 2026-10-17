package main

import (
	"errors"
	"testing"
	"time"
)

func TestBookFieldsValidate(t *testing.T) {
	nextYear := time.Now().Year() + 1

	tests := []struct {
		name       string
		fields     BookFields
		wantFields []string // names of fields expected to be invalid; nil means valid
	}{
		{
			name:   "complete book is valid",
			fields: BookFields{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "0306406152"},
		},
		{
			name:   "title and author only is valid",
			fields: BookFields{Title: "Dune", Author: "Frank Herbert"},
		},
		{
			name:       "missing title",
			fields:     BookFields{Author: "Frank Herbert"},
			wantFields: []string{"title"},
		},
		{
			name:       "missing author",
			fields:     BookFields{Title: "Dune"},
			wantFields: []string{"author"},
		},
		{
			name:       "missing title and author",
			fields:     BookFields{},
			wantFields: []string{"title", "author"},
		},
		{
			name:       "negative year",
			fields:     BookFields{Title: "Dune", Author: "Frank Herbert", Year: -5},
			wantFields: []string{"year"},
		},
		{
			name:       "year beyond next year",
			fields:     BookFields{Title: "Dune", Author: "Frank Herbert", Year: nextYear + 1},
			wantFields: []string{"year"},
		},
		{
			name:   "year of next year is allowed for forthcoming books",
			fields: BookFields{Title: "Dune", Author: "Frank Herbert", Year: nextYear},
		},
		{
			name:       "isbn with bad length",
			fields:     BookFields{Title: "Dune", Author: "Frank Herbert", ISBN: "12345"},
			wantFields: []string{"isbn"},
		},
		{
			name:       "isbn-13 with bad check digit",
			fields:     BookFields{Title: "Dune", Author: "Frank Herbert", ISBN: "9780306406158"},
			wantFields: []string{"isbn"},
		},
		{
			name:       "isbn-10 with bad check digit",
			fields:     BookFields{Title: "Dune", Author: "Frank Herbert", ISBN: "0306406153"},
			wantFields: []string{"isbn"},
		},
		{
			name:   "valid isbn-13 with hyphens",
			fields: BookFields{Title: "Dune", Author: "Frank Herbert", ISBN: "978-0-306-40615-7"},
		},
		{
			name:   "valid isbn-10 ending in X",
			fields: BookFields{Title: "Dune", Author: "Frank Herbert", ISBN: "0-8044-2957-X"},
		},
		{
			name:       "isbn-10 with X in a non-final position",
			fields:     BookFields{Title: "Dune", Author: "Frank Herbert", ISBN: "X306406152"},
			wantFields: []string{"isbn"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.fields.Validate()
			if tt.wantFields == nil {
				if err != nil {
					t.Fatalf("Validate() = %v, want nil", err)
				}
				return
			}

			var verr ValidationError
			if !errors.As(err, &verr) {
				t.Fatalf("Validate() = %v, want ValidationError", err)
			}
			if len(verr) != len(tt.wantFields) {
				t.Fatalf("invalid fields = %v, want %v", verr, tt.wantFields)
			}
			for _, field := range tt.wantFields {
				if _, ok := verr[field]; !ok {
					t.Errorf("field %q not reported invalid; got %v", field, verr)
				}
			}
		})
	}
}

func TestBookFieldsNormalizeTrimsWhitespace(t *testing.T) {
	f := BookFields{Title: "  Dune ", Author: "\tFrank Herbert\n", ISBN: " 0306406152 "}
	f.Normalize()

	if f.Title != "Dune" || f.Author != "Frank Herbert" || f.ISBN != "0306406152" {
		t.Fatalf("Normalize() = %+v, want trimmed fields", f)
	}
}

func TestBookFieldsWhitespaceOnlyTitleIsRejected(t *testing.T) {
	f := BookFields{Title: "   ", Author: "Frank Herbert"}
	f.Normalize()

	if err := f.Validate(); err == nil {
		t.Fatal("Validate() = nil for whitespace-only title, want error")
	}
}
