// Package book defines the Book model and the rules client input must satisfy.
package book

import (
	"fmt"
	"regexp"
	"strings"
	"time"
	"unicode/utf8"
)

// Length limits, in characters, for the free-text fields.
const (
	MaxTitleLength  = 500
	MaxAuthorLength = 200
)

var (
	isbnPattern    = regexp.MustCompile(`^(?:[0-9]{9}[0-9X]|[0-9]{13})$`)
	isbnSeparators = strings.NewReplacer("-", "", " ", "")
)

// Book is a book in the collection, as stored and returned by the API.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Input is the client payload used to create or replace a book. Title and
// Author are required. Year is the publication year, where 0 means unknown.
// ISBN is optional, but must be well formed when present.
type Input struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ValidationError lists every rule an Input breaks, keyed by JSON field name.
type ValidationError struct {
	Fields map[string]string
}

func (e *ValidationError) Error() string {
	return "invalid book"
}

// Validate trims surrounding whitespace from the text fields and checks every
// rule. It returns the cleaned input, ready to store, or a *ValidationError
// naming each field that failed.
func (in Input) Validate() (Input, *ValidationError) {
	clean := Input{
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
		Year:   in.Year,
		ISBN:   strings.TrimSpace(in.ISBN),
	}

	fields := map[string]string{}
	switch n := utf8.RuneCountInString(clean.Title); {
	case n == 0:
		fields["title"] = "is required"
	case n > MaxTitleLength:
		fields["title"] = fmt.Sprintf("must be at most %d characters", MaxTitleLength)
	}
	switch n := utf8.RuneCountInString(clean.Author); {
	case n == 0:
		fields["author"] = "is required"
	case n > MaxAuthorLength:
		fields["author"] = fmt.Sprintf("must be at most %d characters", MaxAuthorLength)
	}
	// Allow next year too, for titles announced ahead of publication.
	maxYear := time.Now().Year() + 1
	if clean.Year < 0 || clean.Year > maxYear {
		fields["year"] = fmt.Sprintf("must be between 0 and %d", maxYear)
	}
	if clean.ISBN != "" && !validISBN(clean.ISBN) {
		fields["isbn"] = "must be an ISBN-10 or ISBN-13"
	}

	if len(fields) > 0 {
		return Input{}, &ValidationError{Fields: fields}
	}
	return clean, nil
}

// validISBN checks the shape of an ISBN-10 or ISBN-13, ignoring hyphens and
// spaces. It does not verify the check digit.
func validISBN(s string) bool {
	return isbnPattern.MatchString(strings.ToUpper(isbnSeparators.Replace(s)))
}
