package book

import (
	"errors"
	"strings"
	"testing"
)

func TestCleanTrimsAndAccepts(t *testing.T) {
	got, err := Input{Title: "  Dune ", Author: "\tFrank Herbert\n", Year: 1965, ISBN: " 978-0441172719 "}.Clean()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	want := Input{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441172719"}
	if got != want {
		t.Errorf("got %+v, want %+v", got, want)
	}
}

func TestCleanOptionalFields(t *testing.T) {
	if _, err := (Input{Title: "T", Author: "A"}).Clean(); err != nil {
		t.Errorf("year and isbn should be optional, got %v", err)
	}
}

func TestCleanRejectsInvalid(t *testing.T) {
	tests := []struct {
		name  string
		in    Input
		field string
	}{
		{"missing title", Input{Author: "A"}, "title"},
		{"blank title", Input{Title: "   ", Author: "A"}, "title"},
		{"missing author", Input{Title: "T"}, "author"},
		{"blank author", Input{Title: "T", Author: "\t"}, "author"},
		{"long title", Input{Title: strings.Repeat("x", MaxTitleLen+1), Author: "A"}, "title"},
		{"long author", Input{Title: "T", Author: strings.Repeat("x", MaxAuthorLen+1)}, "author"},
		{"negative year", Input{Title: "T", Author: "A", Year: -1}, "year"},
		{"huge year", Input{Title: "T", Author: "A", Year: MaxYear + 1}, "year"},
		{"long isbn", Input{Title: "T", Author: "A", ISBN: strings.Repeat("1", MaxISBNLen+1)}, "isbn"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			_, err := tc.in.Clean()
			var verr ValidationError
			if !errors.As(err, &verr) {
				t.Fatalf("want ValidationError, got %v", err)
			}
			if _, ok := verr[tc.field]; !ok {
				t.Errorf("want problem on %q, got %v", tc.field, verr)
			}
		})
	}
}

func TestCleanReportsAllProblems(t *testing.T) {
	_, err := Input{}.Clean()
	var verr ValidationError
	if !errors.As(err, &verr) || len(verr) != 2 {
		t.Fatalf("want title and author problems, got %v", err)
	}
	if got, want := err.Error(), "validation failed: author is required; title is required"; got != want {
		t.Errorf("Error() = %q, want %q", got, want)
	}
}

func TestCleanCountsRunesNotBytes(t *testing.T) {
	title := strings.Repeat("é", MaxTitleLen) // 2 bytes each, exactly at the limit
	if _, err := (Input{Title: title, Author: "A"}).Clean(); err != nil {
		t.Errorf("title of %d runes should be accepted: %v", MaxTitleLen, err)
	}
}
