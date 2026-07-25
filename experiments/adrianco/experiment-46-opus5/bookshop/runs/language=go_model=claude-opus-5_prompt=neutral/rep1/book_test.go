package main

import (
	"strings"
	"testing"
	"time"
)

func TestNormalizeISBN(t *testing.T) {
	tests := []struct {
		name    string
		in      string
		want    string
		wantErr string
	}{
		{name: "empty means no isbn", in: ""},
		{name: "whitespace only means no isbn", in: "  -- "},
		{name: "isbn13 with separators", in: "978-0-13-419044-0", want: "9780134190440"},
		{name: "isbn13 plain", in: "9780441013593", want: "9780441013593"},
		{name: "isbn10", in: "0-13-110362-8", want: "0131103628"},
		{name: "isbn10 with X check digit", in: "080442957X", want: "080442957X"},
		{name: "isbn10 lowercase x is upcased", in: "080442957x", want: "080442957X"},
		{name: "isbn13 bad check digit", in: "9780134190441", wantErr: "ISBN-13 check digit"},
		{name: "isbn10 bad check digit", in: "0131103627", wantErr: "ISBN-10 check digit"},
		{name: "X in the wrong position", in: "X131103628", wantErr: "ISBN-10 check digit"},
		{name: "X is not allowed in isbn13", in: "978013419044X", wantErr: "ISBN-13 check digit"},
		{name: "too short", in: "12345", wantErr: "must have 10 or 13 digits"},
		{name: "too long", in: "12345678901234", wantErr: "must have 10 or 13 digits"},
		{name: "letters rejected", in: "97801341904a0", wantErr: "invalid character"},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := normalizeISBN(tc.in)
			if tc.wantErr != "" {
				if err == nil {
					t.Fatalf("normalizeISBN(%q) = %q, want error containing %q", tc.in, got, tc.wantErr)
				}
				if !strings.Contains(err.Error(), tc.wantErr) {
					t.Errorf("error = %q, want it to contain %q", err, tc.wantErr)
				}
				return
			}
			if err != nil {
				t.Fatalf("normalizeISBN(%q): unexpected error %v", tc.in, err)
			}
			if got != tc.want {
				t.Errorf("normalizeISBN(%q) = %q, want %q", tc.in, got, tc.want)
			}
		})
	}
}

func TestPayloadValidate(t *testing.T) {
	now := time.Date(2024, 6, 1, 0, 0, 0, 0, time.UTC)
	str := func(s string) *string { return &s }
	num := func(i int) *int { return &i }

	tests := []struct {
		name         string
		payload      bookPayload
		want         BookInput
		wantProblems []string
	}{
		{
			name:    "trims and normalizes",
			payload: bookPayload{Title: str(" Dune\t"), Author: str(" Frank Herbert "), Year: num(1965), ISBN: str("978-0-441-01359-3")},
			want:    BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"},
		},
		{
			name:    "optional fields default to zero",
			payload: bookPayload{Title: str("Dune"), Author: str("Frank Herbert")},
			want:    BookInput{Title: "Dune", Author: "Frank Herbert"},
		},
		{
			name:    "year zero means unknown",
			payload: bookPayload{Title: str("T"), Author: str("A"), Year: num(0)},
			want:    BookInput{Title: "T", Author: "A"},
		},
		{
			name:    "next year is allowed for upcoming releases",
			payload: bookPayload{Title: str("T"), Author: str("A"), Year: num(2025)},
			want:    BookInput{Title: "T", Author: "A", Year: 2025},
		},
		{
			name:         "two years out is rejected",
			payload:      bookPayload{Title: str("T"), Author: str("A"), Year: num(2026)},
			wantProblems: []string{"year must be 0 (unknown) or between 1 and 2025"},
		},
		{
			name:         "missing title and author are reported together",
			payload:      bookPayload{},
			wantProblems: []string{"title is required", "author is required"},
		},
		{
			name:         "blank strings count as missing",
			payload:      bookPayload{Title: str("   "), Author: str("\n")},
			wantProblems: []string{"title is required", "author is required"},
		},
		{
			name:         "over-long title",
			payload:      bookPayload{Title: str(strings.Repeat("a", maxTitleLen+1)), Author: str("A")},
			wantProblems: []string{"title must be at most 512 characters"},
		},
		{
			name:         "over-long author",
			payload:      bookPayload{Title: str("T"), Author: str(strings.Repeat("a", maxAuthorLen+1))},
			wantProblems: []string{"author must be at most 256 characters"},
		},
		{
			name:         "every problem is collected in one pass",
			payload:      bookPayload{Year: num(-1), ISBN: str("nope")},
			wantProblems: []string{"title is required", "author is required", "year must be", "isbn"},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, problems := tc.payload.validate(now)

			if len(problems) != len(tc.wantProblems) {
				t.Fatalf("problems = %v, want %d of %v", problems, len(tc.wantProblems), tc.wantProblems)
			}
			for i, want := range tc.wantProblems {
				if !strings.Contains(problems[i], want) {
					t.Errorf("problems[%d] = %q, want it to contain %q", i, problems[i], want)
				}
			}
			if len(tc.wantProblems) == 0 && got != tc.want {
				t.Errorf("input = %+v, want %+v", got, tc.want)
			}
		})
	}
}
