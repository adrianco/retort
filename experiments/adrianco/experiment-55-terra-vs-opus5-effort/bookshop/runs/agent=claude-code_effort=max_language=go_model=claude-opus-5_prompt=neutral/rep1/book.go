package main

import (
	"fmt"
	"strings"
	"time"
	"unicode/utf8"
)

// Book is one record in the collection, in the shape it is both stored in and
// returned from the API. Year and ISBN are optional, so they are pointers: a
// missing value marshals to JSON null rather than to 0 or "".
type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      *int      `json:"year"`
	ISBN      *string   `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// BookInput is the client-supplied half of a book: the fields accepted by
// POST /books and PUT /books/{id}. Pointers again distinguish "field absent"
// from "field set to the zero value", which matters because PUT replaces the
// whole record — omitting isbn clears it.
type BookInput struct {
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

const (
	maxTitleLen  = 500
	maxAuthorLen = 300
	// minYear is deliberately permissive; the point is to reject 0 and
	// negatives, not to adjudicate the history of printing.
	minYear = 1
	// futureYearSlack allows for books announced ahead of publication.
	futureYearSlack = 5
)

// ValidationError collects every problem with an input so the client can fix
// them all in one round trip instead of discovering them one at a time.
type ValidationError struct {
	Problems []string
}

func (e *ValidationError) Error() string {
	return "invalid book: " + strings.Join(e.Problems, "; ")
}

// Clean trims and canonicalises the input in place. It runs before Validate,
// so validation sees exactly the values that will be persisted.
func (in *BookInput) Clean() {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	if in.ISBN != nil {
		// An explicitly empty ISBN means "this book has none", which is stored
		// as NULL so it does not collide with other ISBN-less books.
		if normalized := normalizeISBN(*in.ISBN); normalized == "" {
			in.ISBN = nil
		} else {
			in.ISBN = &normalized
		}
	}
}

// Validate reports everything wrong with the input. now supplies the upper
// bound for the year check; it is a parameter so tests do not depend on the
// wall clock.
func (in *BookInput) Validate(now time.Time) error {
	var problems []string

	switch {
	case in.Title == "":
		problems = append(problems, "title is required")
	case utf8.RuneCountInString(in.Title) > maxTitleLen:
		problems = append(problems, fmt.Sprintf("title must be at most %d characters", maxTitleLen))
	}

	switch {
	case in.Author == "":
		problems = append(problems, "author is required")
	case utf8.RuneCountInString(in.Author) > maxAuthorLen:
		problems = append(problems, fmt.Sprintf("author must be at most %d characters", maxAuthorLen))
	}

	if in.Year != nil {
		maxYear := now.UTC().Year() + futureYearSlack
		if *in.Year < minYear || *in.Year > maxYear {
			problems = append(problems, fmt.Sprintf("year must be between %d and %d", minYear, maxYear))
		}
	}

	if in.ISBN != nil && !validISBNFormat(*in.ISBN) {
		problems = append(problems, "isbn must be 10 or 13 digits (a trailing X is allowed on ISBN-10); hyphens and spaces are ignored")
	}

	if len(problems) > 0 {
		return &ValidationError{Problems: problems}
	}
	return nil
}

// normalizeISBN strips the separators people type by hand and upper-cases the
// ISBN-10 check character, so "0-306-40615-2" and "030640615 2" are one ISBN.
// Anything else is left alone for validISBNFormat to reject.
func normalizeISBN(s string) string {
	var b strings.Builder
	b.Grow(len(s))
	for _, r := range s {
		switch r {
		case ' ', '-', '\t', '\n', '\r':
			continue
		}
		b.WriteRune(r)
	}
	return strings.ToUpper(b.String())
}

// validISBNFormat checks shape only — length and alphabet — and deliberately
// does not verify the check digit. Catalogues are full of ISBNs that fail the
// checksum, and rejecting them would lose real data over a typo.
func validISBNFormat(s string) bool {
	switch len(s) {
	case 10:
		for i, r := range s {
			if r >= '0' && r <= '9' {
				continue
			}
			if i == 9 && r == 'X' {
				continue
			}
			return false
		}
		return true
	case 13:
		for _, r := range s {
			if r < '0' || r > '9' {
				return false
			}
		}
		return true
	default:
		return false
	}
}
