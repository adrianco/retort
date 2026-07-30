package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
	"unicode"
)

// Book is a single entry in the collection.
type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      int       `json:"year"`
	ISBN      string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// BookInput is the client-supplied representation of a book. It is
// deliberately separate from Book so that server-owned fields (ID,
// timestamps) can never be set by a request body.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

const (
	maxTitleLen  = 500
	maxAuthorLen = 200
	// Gutenberg's press predates any book worth cataloguing here.
	minYear = 1450
	// Allow a little slack for forthcoming titles.
	maxYearSlack = 5
)

// ValidationError reports one message per offending field.
type ValidationError map[string]string

func (v ValidationError) Error() string {
	fields := make([]string, 0, len(v))
	for f := range v {
		fields = append(fields, f)
	}
	sort.Strings(fields)
	parts := make([]string, 0, len(fields))
	for _, f := range fields {
		parts = append(parts, fmt.Sprintf("%s: %s", f, v[f]))
	}
	return "validation failed (" + strings.Join(parts, "; ") + ")"
}

// Normalize trims surrounding whitespace so that " " is not accepted as a
// title and so stored values compare predictably.
func (in *BookInput) Normalize() {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
}

// Validate reports every problem with the input at once, so a client does not
// have to fix errors one round trip at a time. Title and author are required;
// year and isbn are optional but must be well formed when present.
func (in BookInput) Validate(now time.Time) error {
	errs := ValidationError{}

	switch {
	case in.Title == "":
		errs["title"] = "is required"
	case len(in.Title) > maxTitleLen:
		errs["title"] = fmt.Sprintf("must be at most %d characters", maxTitleLen)
	}

	switch {
	case in.Author == "":
		errs["author"] = "is required"
	case len(in.Author) > maxAuthorLen:
		errs["author"] = fmt.Sprintf("must be at most %d characters", maxAuthorLen)
	}

	if maxYear := now.Year() + maxYearSlack; in.Year != 0 && (in.Year < minYear || in.Year > maxYear) {
		errs["year"] = fmt.Sprintf("must be between %d and %d, or omitted", minYear, maxYear)
	}

	if in.ISBN != "" && !validISBN(in.ISBN) {
		errs["isbn"] = "must be a 10- or 13-digit ISBN"
	}

	if len(errs) == 0 {
		return nil
	}
	return errs
}

// validISBN checks the shape of an ISBN-10/13 (digits, with an optional
// trailing X on ISBN-10) ignoring the usual hyphen and space separators. The
// check digit is not verified: catalogues are full of legitimately mistyped
// ISBNs and rejecting them is not this service's job.
func validISBN(isbn string) bool {
	var digits []rune
	for i, r := range isbn {
		switch {
		case unicode.IsDigit(r):
			digits = append(digits, r)
		case (r == 'X' || r == 'x') && i == len(isbn)-1:
			digits = append(digits, r)
		case r == '-' || r == ' ':
			// separator
		default:
			return false
		}
	}
	switch len(digits) {
	case 10:
		return true
	case 13:
		// The X check digit only exists in ISBN-10.
		return unicode.IsDigit(digits[12])
	default:
		return false
	}
}
