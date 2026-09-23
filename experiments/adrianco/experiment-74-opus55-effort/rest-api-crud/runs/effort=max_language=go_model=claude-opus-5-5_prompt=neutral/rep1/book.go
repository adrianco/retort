package main

import (
	"fmt"
	"strings"
	"unicode/utf8"
)

// Maximum lengths of the free-text fields, in characters.
const (
	maxTitleLen  = 500
	maxAuthorLen = 255
)

// Book is a book in the collection, both as stored and as returned by the API.
// Year and ISBN are optional and encode as JSON null when unknown.
type Book struct {
	ID     int64   `json:"id"`
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// BookInput is the request body for creating (POST) or replacing (PUT) a book.
// Unknown fields, including read-only ones such as "id", are ignored.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year"`
	ISBN   string `json:"isbn"`
}

// FieldErrors maps a JSON field name to a description of what is wrong with it.
type FieldErrors map[string]string

// Validate checks every field of in and, if all are valid, returns the
// normalized Book it describes: surrounding whitespace is trimmed and an empty
// ISBN means "no ISBN". The returned Book has no ID. Otherwise it returns the
// problem with each invalid field. Years later than maxYear are rejected.
func (in BookInput) Validate(maxYear int) (Book, FieldErrors) {
	b := Book{
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
		Year:   in.Year,
	}
	errs := FieldErrors{}

	checkText(errs, "title", b.Title, maxTitleLen)
	checkText(errs, "author", b.Author, maxAuthorLen)

	if in.Year != nil && (*in.Year < 1 || *in.Year > maxYear) {
		errs["year"] = fmt.Sprintf("must be between 1 and %d", maxYear)
	}

	if isbn := strings.TrimSpace(in.ISBN); isbn != "" {
		if validISBN(isbn) {
			b.ISBN = &isbn
		} else {
			errs["isbn"] = "must be an ISBN-10 or ISBN-13, optionally separated by hyphens or spaces"
		}
	}

	if len(errs) > 0 {
		return Book{}, errs
	}
	return b, nil
}

// checkText records an error in errs if the required field is empty or longer
// than maxLen characters.
func checkText(errs FieldErrors, field, value string, maxLen int) {
	switch {
	case value == "":
		errs[field] = "is required"
	case utf8.RuneCountInString(value) > maxLen:
		errs[field] = fmt.Sprintf("must be at most %d characters", maxLen)
	}
}

var isbnSeparators = strings.NewReplacer("-", "", " ", "")

// validISBN reports whether s has the shape of an ISBN-10 (nine digits followed
// by a digit or X) or an ISBN-13 (thirteen digits), ignoring hyphens and spaces.
// Check digits are deliberately not verified: books with misprinted ISBNs
// exist, and a collection should still be able to record them.
func validISBN(s string) bool {
	s = isbnSeparators.Replace(s)
	switch len(s) {
	case 13:
		return allDigits(s)
	case 10:
		last := s[9]
		return allDigits(s[:9]) && (isDigit(last) || last == 'X' || last == 'x')
	default:
		return false
	}
}

func allDigits(s string) bool {
	for i := range len(s) {
		if !isDigit(s[i]) {
			return false
		}
	}
	return true
}

func isDigit(c byte) bool { return '0' <= c && c <= '9' }
