package main

import (
	"fmt"
	"strings"
	"time"
	"unicode/utf8"
)

const (
	maxTextLength = 500 // maximum runes for title and author
	minYear       = 1
)

// BookInput is the JSON body accepted by POST /books and PUT /books/{id}.
// Year and ISBN are optional; omitting them or sending null leaves them unset.
type BookInput struct {
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// Book is a book as stored and returned by the API.
type Book struct {
	ID     int64   `json:"id"`
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// fieldErrors maps a JSON field name to a description of what is wrong with it.
type fieldErrors map[string]string

// validateBook trims and checks in. It returns the cleaned book (ID unset),
// or the per-field errors when the input is invalid. now determines the
// latest acceptable publication year.
func validateBook(in BookInput, now time.Time) (Book, fieldErrors) {
	errs := fieldErrors{}
	b := Book{
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
	}

	checkText(errs, "title", b.Title)
	checkText(errs, "author", b.Author)

	if in.Year != nil {
		maxYear := now.Year() + 1 // allow books announced for next year
		if *in.Year < minYear || *in.Year > maxYear {
			errs["year"] = fmt.Sprintf("must be between %d and %d", minYear, maxYear)
		} else {
			b.Year = in.Year
		}
	}

	if in.ISBN != nil {
		isbn := normalizeISBN(*in.ISBN)
		switch {
		case isbn == "": // blank is treated as "no ISBN"
		case !validISBN(isbn):
			errs["isbn"] = "must be a valid ISBN-10 or ISBN-13"
		default:
			b.ISBN = &isbn
		}
	}

	if len(errs) > 0 {
		return Book{}, errs
	}
	return b, nil
}

// checkText records an error for a required text field that is empty or too long.
func checkText(errs fieldErrors, field, value string) {
	switch {
	case value == "":
		errs[field] = "is required"
	case utf8.RuneCountInString(value) > maxTextLength:
		errs[field] = fmt.Sprintf("must be at most %d characters", maxTextLength)
	}
}

// normalizeISBN removes spaces and hyphens and upper-cases the ISBN-10 check character X.
func normalizeISBN(s string) string {
	return strings.ToUpper(strings.NewReplacer(" ", "", "-", "").Replace(strings.TrimSpace(s)))
}

// validISBN reports whether s, already normalized, is a valid ISBN-10 or ISBN-13.
func validISBN(s string) bool {
	switch len(s) {
	case 10:
		return validISBN10(s)
	case 13:
		return validISBN13(s)
	}
	return false
}

// validISBN10 checks the weighted sum (weights 10..1) is divisible by 11.
func validISBN10(s string) bool {
	sum := 0
	for i := range 10 {
		c := s[i]
		var d int
		switch {
		case c >= '0' && c <= '9':
			d = int(c - '0')
		case c == 'X' && i == 9:
			d = 10
		default:
			return false
		}
		sum += (10 - i) * d
	}
	return sum%11 == 0
}

// validISBN13 checks the 978/979 prefix and the alternating 1/3 weighted sum is divisible by 10.
func validISBN13(s string) bool {
	if !strings.HasPrefix(s, "978") && !strings.HasPrefix(s, "979") {
		return false
	}
	sum := 0
	for i := range 13 {
		c := s[i]
		if c < '0' || c > '9' {
			return false
		}
		d := int(c - '0')
		if i%2 == 0 {
			sum += d
		} else {
			sum += 3 * d
		}
	}
	return sum%10 == 0
}
