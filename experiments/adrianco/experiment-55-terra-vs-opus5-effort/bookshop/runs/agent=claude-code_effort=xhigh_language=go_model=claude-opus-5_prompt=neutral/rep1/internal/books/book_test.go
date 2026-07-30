package books

import (
	"errors"
	"strings"
	"testing"
	"time"
)

// referenceNow pins "now" so the year bound is deterministic.
var referenceNow = time.Date(2026, time.July, 29, 12, 0, 0, 0, time.UTC)

func TestInputValidateAccepts(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name  string
		input Input
		want  Input
	}{
		{
			name:  "minimal book",
			input: Input{Title: "Untitled", Author: "Anon"},
			want:  Input{Title: "Untitled", Author: "Anon"},
		},
		{
			name:  "surrounding whitespace is trimmed",
			input: Input{Title: "  The Go Programming Language\t", Author: "\n Alan Donovan "},
			want:  Input{Title: "The Go Programming Language", Author: "Alan Donovan"},
		},
		{
			name:  "isbn is canonicalised",
			input: Input{Title: "T", Author: "A", ISBN: "978-0-306-40615-7"},
			want:  Input{Title: "T", Author: "A", ISBN: "9780306406157"},
		},
		{
			name:  "year zero means unknown",
			input: Input{Title: "T", Author: "A", Year: 0},
			want:  Input{Title: "T", Author: "A", Year: 0},
		},
		{
			name:  "next year is allowed for forthcoming titles",
			input: Input{Title: "T", Author: "A", Year: referenceNow.Year() + 1},
			want:  Input{Title: "T", Author: "A", Year: referenceNow.Year() + 1},
		},
		{
			name:  "titles may use the full length budget",
			input: Input{Title: strings.Repeat("x", MaxTitleLen), Author: strings.Repeat("y", MaxAuthorLen)},
			want:  Input{Title: strings.Repeat("x", MaxTitleLen), Author: strings.Repeat("y", MaxAuthorLen)},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			input := tc.input
			if err := input.Validate(referenceNow); err != nil {
				t.Fatalf("Validate(%+v) = %v, want nil", tc.input, err)
			}
			if input != tc.want {
				t.Errorf("Validate normalised to %+v, want %+v", input, tc.want)
			}
		})
	}
}

func TestInputValidateRejects(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		input      Input
		wantFields []string
	}{
		{
			name:       "missing title",
			input:      Input{Author: "Anon"},
			wantFields: []string{"title"},
		},
		{
			name:       "title of only whitespace",
			input:      Input{Title: "   \t\n ", Author: "Anon"},
			wantFields: []string{"title"},
		},
		{
			name:       "missing author",
			input:      Input{Title: "Untitled"},
			wantFields: []string{"author"},
		},
		{
			name:       "missing title and author are reported together",
			input:      Input{},
			wantFields: []string{"author", "title"},
		},
		{
			name:       "title too long",
			input:      Input{Title: strings.Repeat("x", MaxTitleLen+1), Author: "Anon"},
			wantFields: []string{"title"},
		},
		{
			name:       "author too long",
			input:      Input{Title: "T", Author: strings.Repeat("y", MaxAuthorLen+1)},
			wantFields: []string{"author"},
		},
		{
			name:       "year too far in the future",
			input:      Input{Title: "T", Author: "A", Year: referenceNow.Year() + 2},
			wantFields: []string{"year"},
		},
		{
			name:       "negative year",
			input:      Input{Title: "T", Author: "A", Year: -100},
			wantFields: []string{"year"},
		},
		{
			name:       "malformed isbn",
			input:      Input{Title: "T", Author: "A", ISBN: "not-an-isbn"},
			wantFields: []string{"isbn"},
		},
		{
			name:       "every field at once",
			input:      Input{Year: 9999, ISBN: "123"},
			wantFields: []string{"author", "isbn", "title", "year"},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			input := tc.input
			err := input.Validate(referenceNow)
			if err == nil {
				t.Fatalf("Validate(%+v) = nil, want a validation error", tc.input)
			}

			var validation *ValidationError
			if !errors.As(err, &validation) {
				t.Fatalf("Validate returned %T (%v), want *ValidationError", err, err)
			}
			if len(validation.Fields) != len(tc.wantFields) {
				t.Fatalf("reported fields %v, want exactly %v", validation.Fields, tc.wantFields)
			}
			for _, field := range tc.wantFields {
				message, ok := validation.Fields[field]
				if !ok {
					t.Errorf("no message reported for field %q; got %v", field, validation.Fields)
					continue
				}
				if message == "" {
					t.Errorf("field %q reported with an empty message", field)
				}
			}
		})
	}
}

// TestInputValidateUsesRuneLengths checks that the length limits count
// characters rather than bytes, so a title of accented or CJK text is not
// rejected at a third of the advertised limit.
func TestInputValidateUsesRuneLengths(t *testing.T) {
	t.Parallel()

	input := Input{Title: strings.Repeat("日", MaxTitleLen), Author: "著者"}
	if err := input.Validate(referenceNow); err != nil {
		t.Fatalf("Validate of a %d-rune title = %v, want nil", MaxTitleLen, err)
	}

	tooLong := Input{Title: strings.Repeat("日", MaxTitleLen+1), Author: "著者"}
	if err := tooLong.Validate(referenceNow); err == nil {
		t.Fatal("Validate of a title one rune over the limit = nil, want an error")
	}
}

func TestValidationErrorMessageListsFieldsInOrder(t *testing.T) {
	t.Parallel()

	err := &ValidationError{Fields: map[string]string{
		"title":  "title is required",
		"author": "author is required",
	}}
	const want = "invalid book: author: author is required; title: title is required"
	if got := err.Error(); got != want {
		t.Errorf("Error() = %q, want %q", got, want)
	}
}
