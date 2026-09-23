package main

import (
	"fmt"
	"maps"
	"slices"
	"strings"
	"time"
	"unicode/utf8"
)

// Maximum field lengths, in characters. They guard against junk input rather
// than encode bibliographic rules.
const (
	maxTitleLen  = 500
	maxAuthorLen = 300
	maxISBNLen   = 32
)

// Book is a book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year"` // null when unknown
	ISBN   string `json:"isbn"` // empty when unknown
}

// BookInput holds the client-supplied fields of a book: the request body of
// POST /books and PUT /books/{id}.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year"`
	ISBN   string `json:"isbn"`
}

// Normalize returns a copy of in with surrounding whitespace trimmed from its
// text fields, so stored values are clean and blank values count as missing.
func (in BookInput) Normalize() BookInput {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
	return in
}

// Validate reports every problem with in at once. Title and author are
// required; year and ISBN are optional.
func (in BookInput) Validate() error {
	errs := ValidationError{}
	requireText(errs, "title", in.Title, maxTitleLen)
	requireText(errs, "author", in.Author, maxAuthorLen)
	if utf8.RuneCountInString(in.ISBN) > maxISBNLen {
		errs["isbn"] = fmt.Sprintf("must be at most %d characters", maxISBNLen)
	}
	if in.Year != nil {
		// Next year is allowed so that announced books can be catalogued.
		if maxYear := time.Now().Year() + 1; *in.Year < 1 || *in.Year > maxYear {
			errs["year"] = fmt.Sprintf("must be between 1 and %d", maxYear)
		}
	}
	if len(errs) > 0 {
		return errs
	}
	return nil
}

func requireText(errs ValidationError, field, value string, maxLen int) {
	switch {
	case strings.TrimSpace(value) == "":
		errs[field] = "is required"
	case utf8.RuneCountInString(value) > maxLen:
		errs[field] = fmt.Sprintf("must be at most %d characters", maxLen)
	}
}

// book returns the Book described by in, with the given ID.
func (in BookInput) book(id int64) Book {
	return Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
}

// ValidationError maps JSON field names to what is wrong with their values.
type ValidationError map[string]string

func (e ValidationError) Error() string {
	problems := make([]string, 0, len(e))
	for _, field := range slices.Sorted(maps.Keys(e)) {
		problems = append(problems, field+" "+e[field])
	}
	return "validation failed: " + strings.Join(problems, "; ")
}
