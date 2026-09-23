package main

import (
	"fmt"
	"strings"
	"time"
	"unicode/utf8"
)

// Field length limits enforced on input.
const (
	maxTitleLen  = 500
	maxAuthorLen = 200
)

// Book is a single entry in the collection. Year and ISBN are optional and
// are serialized as null when not set.
type Book struct {
	ID     int64   `json:"id"`
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// BookInput is the request body accepted by POST /books and PUT /books/{id}.
type BookInput struct {
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// Validate checks the input and returns a normalized Book (without an ID).
// If any field is invalid, it returns a map of field name to problem.
// now is used to bound the publication year.
func (in BookInput) Validate(now time.Time) (Book, map[string]string) {
	errs := make(map[string]string)
	b := Book{
		Title:  strings.TrimSpace(in.Title),
		Author: strings.TrimSpace(in.Author),
	}

	switch {
	case b.Title == "":
		errs["title"] = "is required"
	case utf8.RuneCountInString(b.Title) > maxTitleLen:
		errs["title"] = fmt.Sprintf("must be at most %d characters", maxTitleLen)
	}

	switch {
	case b.Author == "":
		errs["author"] = "is required"
	case utf8.RuneCountInString(b.Author) > maxAuthorLen:
		errs["author"] = fmt.Sprintf("must be at most %d characters", maxAuthorLen)
	}

	if in.Year != nil {
		maxYear := now.Year() + 1
		if *in.Year < 1 || *in.Year > maxYear {
			errs["year"] = fmt.Sprintf("must be between 1 and %d", maxYear)
		} else {
			y := *in.Year
			b.Year = &y
		}
	}

	if in.ISBN != nil {
		// An empty ISBN is treated the same as an omitted one.
		if isbn := strings.TrimSpace(*in.ISBN); isbn != "" {
			if !validISBNFormat(isbn) {
				errs["isbn"] = "must be a 10 or 13 digit ISBN (hyphens and spaces allowed)"
			} else {
				b.ISBN = &isbn
			}
		}
	}

	if len(errs) > 0 {
		return Book{}, errs
	}
	return b, nil
}

// validISBNFormat reports whether s looks like an ISBN-10 or ISBN-13 once
// hyphens and spaces are removed. ISBN-10 may end in X as its check digit.
// Check digits are deliberately not verified so that catalog data with
// transcription quirks can still be stored.
func validISBNFormat(s string) bool {
	digits := strings.NewReplacer("-", "", " ", "").Replace(s)
	switch len(digits) {
	case 10:
		return allDigits(digits[:9]) && (allDigits(digits[9:]) || digits[9] == 'X' || digits[9] == 'x')
	case 13:
		return allDigits(digits)
	default:
		return false
	}
}

func allDigits(s string) bool {
	for i := 0; i < len(s); i++ {
		if s[i] < '0' || s[i] > '9' {
			return false
		}
	}
	return true
}
