package main

import (
	"fmt"
	"strings"
	"time"
	"unicode/utf8"
)

// Field length limits, measured in characters (runes).
const (
	maxTitleLen  = 500
	maxAuthorLen = 200
	maxISBNLen   = 20 // an ISBN-13 with hyphens is 17 characters; leave a little slack
)

// Book is a book as stored and returned by the API.
type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      int       `json:"year"`
	ISBN      string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// BookInput is the client-supplied body for creating (POST) or replacing (PUT) a book.
// Title and author are required. Year and ISBN are optional; a year of 0 and an
// empty ISBN mean "unknown".
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Normalize trims surrounding whitespace from the text fields.
func (in *BookInput) Normalize() {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
}

// Validate checks a normalized input and returns a map of field name to problem.
// An empty map means the input is valid.
func (in BookInput) Validate() map[string]string {
	errs := map[string]string{}

	switch {
	case in.Title == "":
		errs["title"] = "title is required"
	case utf8.RuneCountInString(in.Title) > maxTitleLen:
		errs["title"] = fmt.Sprintf("title must be at most %d characters", maxTitleLen)
	}

	switch {
	case in.Author == "":
		errs["author"] = "author is required"
	case utf8.RuneCountInString(in.Author) > maxAuthorLen:
		errs["author"] = fmt.Sprintf("author must be at most %d characters", maxAuthorLen)
	}

	if maxYear := time.Now().Year() + 1; in.Year < 0 || in.Year > maxYear {
		errs["year"] = fmt.Sprintf("year must be between 1 and %d (or 0/omitted if unknown)", maxYear)
	}

	if in.ISBN != "" && !validISBNFormat(in.ISBN) {
		errs["isbn"] = "isbn must contain 10 or 13 digits (hyphens and spaces allowed; ISBN-10 may end in X)"
	}

	return errs
}

// validISBNFormat reports whether s is shaped like an ISBN-10 or ISBN-13, ignoring
// hyphens and spaces. It deliberately does not verify the check digit so that
// collections holding legacy or mistyped-but-real identifiers can still be stored.
func validISBNFormat(s string) bool {
	if len(s) > maxISBNLen {
		return false
	}
	digits := strings.NewReplacer("-", "", " ", "").Replace(s)
	switch len(digits) {
	case 13:
		return allDigits(digits)
	case 10:
		last := digits[9]
		return allDigits(digits[:9]) && (isDigit(last) || last == 'X' || last == 'x')
	default:
		return false
	}
}

func allDigits(s string) bool {
	for i := 0; i < len(s); i++ {
		if !isDigit(s[i]) {
			return false
		}
	}
	return true
}

func isDigit(b byte) bool { return b >= '0' && b <= '9' }
