// Package book defines the book domain type and the rules for validating
// client-supplied book data. It has no dependencies on HTTP or storage.
package book

import (
	"fmt"
	"strings"
	"time"
	"unicode/utf8"
)

const (
	maxTitleLen  = 500
	maxAuthorLen = 200

	// minYear is roughly the date of the earliest surviving written works.
	minYear = -3000
)

// Book is a book as stored in the collection.
type Book struct {
	ID     int64   `json:"id"`
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// Input is the client-supplied data for creating or replacing a book.
// Year and ISBN are optional; nil means "not recorded".
type Input struct {
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// FieldErrors maps a JSON field name to a description of what is wrong with it.
type FieldErrors map[string]string

// Normalize returns a copy of in with surrounding whitespace removed from text
// fields, and the ISBN stripped of hyphens and spaces. An empty ISBN becomes nil.
// Normalize never fails; Validate reports anything that is still wrong.
func (in Input) Normalize() Input {
	out := Input{
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
		Year:   in.Year,
	}
	if in.ISBN != nil {
		isbn := strings.ToUpper(strings.NewReplacer("-", "", " ", "").Replace(strings.TrimSpace(*in.ISBN)))
		if isbn != "" {
			out.ISBN = &isbn
		}
	}
	return out
}

// Validate checks a normalized Input and returns the problems found, or nil
// if the input is acceptable. Call Normalize first.
func (in Input) Validate() FieldErrors {
	errs := FieldErrors{}

	switch {
	case in.Title == "":
		errs["title"] = "is required"
	case utf8.RuneCountInString(in.Title) > maxTitleLen:
		errs["title"] = fmt.Sprintf("must be at most %d characters", maxTitleLen)
	}

	switch {
	case in.Author == "":
		errs["author"] = "is required"
	case utf8.RuneCountInString(in.Author) > maxAuthorLen:
		errs["author"] = fmt.Sprintf("must be at most %d characters", maxAuthorLen)
	}

	if in.Year != nil {
		if maxYear := time.Now().Year() + 1; *in.Year < minYear || *in.Year > maxYear {
			errs["year"] = fmt.Sprintf("must be between %d and %d", minYear, maxYear)
		}
	}

	if in.ISBN != nil && !validISBN(*in.ISBN) {
		errs["isbn"] = "must be a valid ISBN-10 or ISBN-13"
	}

	if len(errs) == 0 {
		return nil
	}
	return errs
}

// validISBN reports whether s (already stripped of hyphens and spaces) is a
// valid ISBN-10 or ISBN-13, including the check digit.
func validISBN(s string) bool {
	switch len(s) {
	case 10:
		return validISBN10(s)
	case 13:
		return validISBN13(s)
	default:
		return false
	}
}

// validISBN10 checks that the weighted sum of the digits (weights 10 down to 1)
// is divisible by 11. The final character may be 'X', meaning 10.
func validISBN10(s string) bool {
	sum := 0
	for i := 0; i < 10; i++ {
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
		sum += d * (10 - i)
	}
	return sum%11 == 0
}

// validISBN13 checks that the digits weighted alternately 1 and 3 sum to a
// multiple of 10.
func validISBN13(s string) bool {
	sum := 0
	for i := 0; i < 13; i++ {
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
