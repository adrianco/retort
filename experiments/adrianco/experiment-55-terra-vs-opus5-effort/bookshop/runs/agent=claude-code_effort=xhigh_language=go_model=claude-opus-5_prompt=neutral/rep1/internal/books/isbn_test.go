package books

import "testing"

func TestNormalizeISBN(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name  string
		input string
		want  string
		valid bool
	}{
		{name: "empty means unset", input: "", want: "", valid: true},
		{name: "whitespace means unset", input: "  \t ", want: "", valid: true},
		{name: "isbn-10 plain", input: "0306406152", want: "0306406152", valid: true},
		{name: "isbn-10 hyphenated", input: "0-306-40615-2", want: "0306406152", valid: true},
		{name: "isbn-10 spaced", input: "0 306 40615 2", want: "0306406152", valid: true},
		{name: "isbn-10 check digit X", input: "043942089X", want: "043942089X", valid: true},
		{name: "isbn-10 lowercase x is upcased", input: "043942089x", want: "043942089X", valid: true},
		{name: "isbn-13 plain", input: "9780306406157", want: "9780306406157", valid: true},
		{name: "isbn-13 hyphenated", input: "978-0-306-40615-7", want: "9780306406157", valid: true},

		{name: "isbn-10 bad check digit", input: "0306406153"},
		{name: "isbn-13 bad check digit", input: "9780306406158"},
		{name: "too short", input: "12345"},
		{name: "too long", input: "97803064061570"},
		{name: "eleven digits", input: "03064061520"},
		{name: "letters", input: "abcdefghij"},
		{name: "X in the middle of an isbn-10", input: "04394X089X"},
		{name: "X in an isbn-13", input: "97803064061X"},
		{name: "punctuation", input: "0306406152!"},
		{name: "only separators", input: "---"},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			got, err := NormalizeISBN(tc.input)
			if tc.valid {
				if err != nil {
					t.Fatalf("NormalizeISBN(%q) returned error %v, want it accepted", tc.input, err)
				}
				if got != tc.want {
					t.Errorf("NormalizeISBN(%q) = %q, want %q", tc.input, got, tc.want)
				}
				return
			}
			if err == nil {
				t.Fatalf("NormalizeISBN(%q) = %q with no error, want it rejected", tc.input, got)
			}
		})
	}
}

// TestNormalizeISBNIsIdempotent guards the property the uniqueness index relies
// on: every spelling of an ISBN collapses to one canonical form that is itself
// stable.
func TestNormalizeISBNIsIdempotent(t *testing.T) {
	t.Parallel()

	for _, spelling := range []string{"0306406152", "0-306-40615-2", "0 306-40615 2"} {
		once, err := NormalizeISBN(spelling)
		if err != nil {
			t.Fatalf("NormalizeISBN(%q): %v", spelling, err)
		}
		twice, err := NormalizeISBN(once)
		if err != nil {
			t.Fatalf("NormalizeISBN(%q): %v", once, err)
		}
		if once != twice {
			t.Errorf("normalising %q twice gave %q then %q", spelling, once, twice)
		}
		if once != "0306406152" {
			t.Errorf("NormalizeISBN(%q) = %q, want canonical 0306406152", spelling, once)
		}
	}
}
