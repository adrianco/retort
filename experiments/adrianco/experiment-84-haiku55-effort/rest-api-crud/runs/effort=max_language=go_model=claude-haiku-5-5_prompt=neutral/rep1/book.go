package main

import (
	"fmt"
	"strings"
	"time"
	"unicode"
	"unicode/utf8"
)

const (
	minYear       = 1
	maxTextLength = 500 // in characters, for title and author
)

// Book is a book in the collection, as stored and returned by the API. Year and
// ISBN are optional: nil means the value is unknown.
type Book struct {
	ID     int64   `json:"id"`
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// bookInput is the JSON body accepted by POST and PUT.
type bookInput struct {
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// fieldErrors maps a JSON field name to a description of what is wrong with it.
type fieldErrors map[string]string

// toBook validates the input against the rules in the README and returns the
// Book it describes, with ID unset. The returned fieldErrors is empty when the
// input is valid. now determines the latest acceptable publication year, which
// is the next calendar year.
func (in bookInput) toBook(now time.Time) (Book, fieldErrors) {
	b := Book{
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
	}
	errs := fieldErrors{}

	if msg := checkRequiredText(b.Title); msg != "" {
		errs["title"] = msg
	}
	if msg := checkRequiredText(b.Author); msg != "" {
		errs["author"] = msg
	}

	if in.Year != nil {
		maxYear := now.Year() + 1 // allow forthcoming titles
		if *in.Year < minYear || *in.Year > maxYear {
			errs["year"] = fmt.Sprintf("must be between %d and %d", minYear, maxYear)
		} else {
			b.Year = in.Year
		}
	}

	// A blank ISBN counts as absent, so clients can send "" for "unknown".
	if in.ISBN != nil && strings.TrimSpace(*in.ISBN) != "" {
		if isbn, ok := normalizeISBN(*in.ISBN); ok {
			b.ISBN = &isbn
		} else {
			errs["isbn"] = "must be a valid ISBN-10 or ISBN-13"
		}
	}

	return b, errs
}

// checkRequiredText returns a problem description for a required text field,
// or "" if the value is acceptable. The value must already be trimmed.
func checkRequiredText(s string) string {
	switch {
	case s == "":
		return "is required"
	case utf8.RuneCountInString(s) > maxTextLength:
		return fmt.Sprintf("must be at most %d characters", maxTextLength)
	}
	return ""
}

// normalizeISBN removes spaces and hyphens, upper-cases letters (so a trailing x
// becomes X), and checks the ISBN-10 or ISBN-13 check digit. It returns the
// canonical form (10 characters, the last possibly X, or 13 digits) and whether
// the input is valid.
func normalizeISBN(raw string) (string, bool) {
	s := strings.Map(func(r rune) rune {
		if r == ' ' || r == '-' {
			return -1
		}
		return unicode.ToUpper(r)
	}, raw)

	switch len(s) {
	case 10:
		return s, isValidISBN10(s)
	case 13:
		return s, isValidISBN13(s)
	}
	return "", false
}

// isValidISBN10 checks that s is ten characters whose weighted sum is divisible
// by 11. Only the final character may be X, which stands for 10.
func isValidISBN10(s string) bool {
	sum := 0
	for i := range 10 {
		var digit int
		switch c := s[i]; {
		case c >= '0' && c <= '9':
			digit = int(c - '0')
		case c == 'X' && i == 9:
			digit = 10
		default:
			return false
		}
		sum += (10 - i) * digit
	}
	return sum%11 == 0
}

// isValidISBN13 checks that s is thirteen digits, starts with the 978 or 979
// Bookland prefix, and has a valid EAN-13 check digit.
func isValidISBN13(s string) bool {
	if !strings.HasPrefix(s, "978") && !strings.HasPrefix(s, "979") {
		return false
	}
	sum := 0
	for i := range 13 {
		c := s[i]
		if c < '0' || c > '9' {
			return false
		}
		digit := int(c - '0')
		if i%2 == 1 {
			sum += 3 * digit
		} else {
			sum += digit
		}
	}
	return sum%10 == 0
}
