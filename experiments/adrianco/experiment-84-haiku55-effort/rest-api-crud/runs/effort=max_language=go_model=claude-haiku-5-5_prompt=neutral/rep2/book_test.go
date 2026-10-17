package main

import (
	"encoding/json"
	"reflect"
	"slices"
	"strings"
	"testing"
)

func intPtr(v int) *int       { return &v }
func strPtr(v string) *string { return &v }

// toJSON renders v the way the API would, for readable failure messages.
func toJSON(v any) string {
	b, _ := json.Marshal(v)
	return string(b)
}

func TestNormalize(t *testing.T) {
	t.Run("trims text fields", func(t *testing.T) {
		book := Book{Title: "  Dune \t", Author: "\nFrank Herbert "}
		book.normalize()
		if book.Title != "Dune" || book.Author != "Frank Herbert" {
			t.Errorf("normalize() gave title %q, author %q; want trimmed values", book.Title, book.Author)
		}
	})

	t.Run("trims ISBN", func(t *testing.T) {
		book := Book{ISBN: strPtr(" 978-0441172719 ")}
		book.normalize()
		if book.ISBN == nil || *book.ISBN != "978-0441172719" {
			t.Errorf("normalize() ISBN = %s; want \"978-0441172719\"", toJSON(book.ISBN))
		}
	})

	t.Run("blank ISBN becomes nil", func(t *testing.T) {
		book := Book{ISBN: strPtr("   ")}
		book.normalize()
		if book.ISBN != nil {
			t.Errorf("normalize() ISBN = %s; want null for a blank ISBN", toJSON(book.ISBN))
		}
	})
}

func TestValidate(t *testing.T) {
	maxYear := latestPublicationYear()

	tests := []struct {
		name       string
		book       Book
		wantFields []string // empty means the book should be accepted
	}{
		{
			name: "title and author only",
			book: Book{Title: "Dune", Author: "Frank Herbert"},
		},
		{
			name: "all fields",
			book: Book{Title: "Dune", Author: "Frank Herbert", Year: intPtr(1965), ISBN: strPtr("978-0441172719")},
		},
		{
			name:       "missing title",
			book:       Book{Author: "Frank Herbert"},
			wantFields: []string{"title"},
		},
		{
			name:       "missing author",
			book:       Book{Title: "Dune"},
			wantFields: []string{"author"},
		},
		{
			name:       "missing title and author",
			book:       Book{},
			wantFields: []string{"title", "author"},
		},
		{
			name: "title at the length limit counts characters, not bytes",
			book: Book{Title: strings.Repeat("é", maxTitleLength), Author: "A"},
		},
		{
			name:       "title over the length limit",
			book:       Book{Title: strings.Repeat("é", maxTitleLength+1), Author: "A"},
			wantFields: []string{"title"},
		},
		{
			name:       "author over the length limit",
			book:       Book{Title: "Dune", Author: strings.Repeat("a", maxAuthorLength+1)},
			wantFields: []string{"author"},
		},
		{
			name: "year 1 is accepted",
			book: Book{Title: "Dune", Author: "A", Year: intPtr(1)},
		},
		{
			name:       "year 0 is rejected",
			book:       Book{Title: "Dune", Author: "A", Year: intPtr(0)},
			wantFields: []string{"year"},
		},
		{
			name:       "negative year is rejected",
			book:       Book{Title: "Dune", Author: "A", Year: intPtr(-800)},
			wantFields: []string{"year"},
		},
		{
			name: "next year is accepted for forthcoming titles",
			book: Book{Title: "Dune", Author: "A", Year: intPtr(maxYear)},
		},
		{
			name:       "year beyond next year is rejected",
			book:       Book{Title: "Dune", Author: "A", Year: intPtr(maxYear + 1)},
			wantFields: []string{"year"},
		},
		{
			name: "ISBN-10 is accepted",
			book: Book{Title: "Dune", Author: "A", ISBN: strPtr("0441172717")},
		},
		{
			name: "ISBN-10 with X check digit is accepted",
			book: Book{Title: "Dune", Author: "A", ISBN: strPtr("044117271X")},
		},
		{
			name: "ISBN-10 with lowercase x check digit is accepted",
			book: Book{Title: "Dune", Author: "A", ISBN: strPtr("044117271x")},
		},
		{
			name: "ISBN-13 with hyphens is accepted",
			book: Book{Title: "Dune", Author: "A", ISBN: strPtr("978-0-441-17271-9")},
		},
		{
			name: "ISBN-13 with spaces is accepted",
			book: Book{Title: "Dune", Author: "A", ISBN: strPtr("978 0441172719")},
		},
		{
			name:       "ISBN with letters is rejected",
			book:       Book{Title: "Dune", Author: "A", ISBN: strPtr("not-an-isbn")},
			wantFields: []string{"isbn"},
		},
		{
			name:       "ISBN of the wrong length is rejected",
			book:       Book{Title: "Dune", Author: "A", ISBN: strPtr("978044117271")},
			wantFields: []string{"isbn"},
		},
		{
			name:       "X is only valid as the last ISBN-10 character",
			book:       Book{Title: "Dune", Author: "A", ISBN: strPtr("04411X2717")},
			wantFields: []string{"isbn"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := tt.book.validate(maxYear)

			if len(tt.wantFields) == 0 {
				if got != nil {
					t.Fatalf("validate() = %s; want no errors", toJSON(got))
				}
				return
			}

			gotFields := make([]string, 0, len(got))
			for field := range got {
				gotFields = append(gotFields, field)
			}
			slices.Sort(gotFields)
			wantFields := slices.Clone(tt.wantFields)
			slices.Sort(wantFields)
			if !reflect.DeepEqual(gotFields, wantFields) {
				t.Fatalf("validate() flagged fields %v (%s); want %v", gotFields, toJSON(got), wantFields)
			}
		})
	}
}
