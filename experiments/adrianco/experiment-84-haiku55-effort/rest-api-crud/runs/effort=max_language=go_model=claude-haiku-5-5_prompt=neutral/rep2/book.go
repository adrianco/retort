package main

import (
	"fmt"
	"regexp"
	"strings"
	"time"
	"unicode/utf8"
)

const (
	maxTitleLength  = 500
	maxAuthorLength = 200
)

var (
	isbnSeparators = strings.NewReplacer("-", "", " ", "")
	isbnPattern    = regexp.MustCompile(`^(?:[0-9]{9}[0-9Xx]|[0-9]{13})$`)
)

// Book is one entry in the collection. Year and ISBN are optional: nil is
// sent as null and stored as NULL.
type Book struct {
	ID     int64   `json:"id"`
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// fieldErrors maps a JSON field name to the reason its value was rejected.
type fieldErrors map[string]string

// normalize trims surrounding whitespace from the text fields. A blank ISBN is
// set to nil so that "no ISBN" has exactly one representation.
func (b *Book) normalize() {
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	if b.ISBN != nil {
		isbn := strings.TrimSpace(*b.ISBN)
		if isbn == "" {
			b.ISBN = nil
		} else {
			b.ISBN = &isbn
		}
	}
}

// validate returns the rules b breaks, keyed by field name, or nil if b is
// acceptable. It expects a normalized book. A year must be between 1 and maxYear.
func (b Book) validate(maxYear int) fieldErrors {
	errs := fieldErrors{}

	if b.Title == "" {
		errs["title"] = "is required"
	} else if utf8.RuneCountInString(b.Title) > maxTitleLength {
		errs["title"] = fmt.Sprintf("must be at most %d characters", maxTitleLength)
	}

	if b.Author == "" {
		errs["author"] = "is required"
	} else if utf8.RuneCountInString(b.Author) > maxAuthorLength {
		errs["author"] = fmt.Sprintf("must be at most %d characters", maxAuthorLength)
	}

	if b.Year != nil && (*b.Year < 1 || *b.Year > maxYear) {
		errs["year"] = fmt.Sprintf("must be between 1 and %d", maxYear)
	}

	if b.ISBN != nil && !isISBNFormat(*b.ISBN) {
		errs["isbn"] = "must be an ISBN-10 or ISBN-13"
	}

	if len(errs) == 0 {
		return nil
	}
	return errs
}

// latestPublicationYear is the largest year a book may have. It is next year,
// so that forthcoming titles can be recorded.
func latestPublicationYear() int {
	return time.Now().Year() + 1
}

// isISBNFormat reports whether s is an ISBN-10 or ISBN-13 once hyphens and
// spaces are removed. It checks the shape only; the check digit is not verified.
func isISBNFormat(s string) bool {
	return isbnPattern.MatchString(isbnSeparators.Replace(s))
}
