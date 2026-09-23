package main

import (
	"strings"
	"testing"
	"time"
)

func TestBookInputNormalize(t *testing.T) {
	in := BookInput{Title: "  Dune \n", Author: "\tFrank Herbert ", ISBN: " 978-0441172719 "}
	in.Normalize()
	want := BookInput{Title: "Dune", Author: "Frank Herbert", ISBN: "978-0441172719"}
	if in != want {
		t.Fatalf("Normalize() = %+v, want %+v", in, want)
	}
}

func TestBookInputValidate(t *testing.T) {
	valid := BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0-441-17271-9"}
	nextYear := time.Now().Year() + 1

	tests := []struct {
		name       string
		modify     func(*BookInput)
		wantFields []string // fields expected to be reported as invalid
	}{
		{"valid full input", func(*BookInput) {}, nil},
		{"year and isbn are optional", func(in *BookInput) { in.Year, in.ISBN = 0, "" }, nil},
		{"missing title", func(in *BookInput) { in.Title = "" }, []string{"title"}},
		{"missing author", func(in *BookInput) { in.Author = "" }, []string{"author"}},
		{"missing title and author", func(in *BookInput) { in.Title, in.Author = "", "" }, []string{"title", "author"}},
		{"title too long", func(in *BookInput) { in.Title = strings.Repeat("a", maxTitleLen+1) }, []string{"title"}},
		{"title at limit counts runes not bytes", func(in *BookInput) { in.Title = strings.Repeat("é", maxTitleLen) }, nil},
		{"author too long", func(in *BookInput) { in.Author = strings.Repeat("a", maxAuthorLen+1) }, []string{"author"}},
		{"negative year", func(in *BookInput) { in.Year = -1 }, []string{"year"}},
		{"next year allowed (forthcoming books)", func(in *BookInput) { in.Year = nextYear }, nil},
		{"year too far in future", func(in *BookInput) { in.Year = nextYear + 1 }, []string{"year"}},
		{"isbn-10", func(in *BookInput) { in.ISBN = "0441172717" }, nil},
		{"isbn-10 ending in X", func(in *BookInput) { in.ISBN = "0-8044-2957-X" }, nil},
		{"isbn-13 with spaces", func(in *BookInput) { in.ISBN = "978 0 441 17271 9" }, nil},
		{"isbn wrong length", func(in *BookInput) { in.ISBN = "12345" }, []string{"isbn"}},
		{"isbn with letters", func(in *BookInput) { in.ISBN = "97804411727AB" }, []string{"isbn"}},
		{"isbn-13 may not end in X", func(in *BookInput) { in.ISBN = "978044117271X" }, []string{"isbn"}},
		{"isbn padded with separators", func(in *BookInput) { in.ISBN = "0-4-4-1-1-7-2-7-1-7-----" }, []string{"isbn"}},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			in := valid
			tc.modify(&in)
			got := in.Validate()
			if len(got) != len(tc.wantFields) {
				t.Fatalf("Validate() = %v, want errors for %v", got, tc.wantFields)
			}
			for _, f := range tc.wantFields {
				if got[f] == "" {
					t.Errorf("Validate() = %v, missing error for %q", got, f)
				}
			}
		})
	}
}
