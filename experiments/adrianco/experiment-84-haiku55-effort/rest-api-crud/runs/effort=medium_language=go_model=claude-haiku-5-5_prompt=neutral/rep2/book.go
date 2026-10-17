package main

import (
	"fmt"
	"strings"
	"time"
)

// Book is a single entry in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the writable portion of a Book, used for create and update requests.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ValidationErrors maps field names to a human-readable problem description.
type ValidationErrors map[string]string

func (v ValidationErrors) Error() string {
	return fmt.Sprintf("validation failed: %d field(s) invalid", len(v))
}

// Normalize trims surrounding whitespace from string fields.
func (in BookInput) Normalize() BookInput {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
	return in
}

// Validate checks a BookInput. Title and author are required; year is optional
// but must be a plausible publication year when given; ISBN is optional.
func (in BookInput) Validate() error {
	errs := ValidationErrors{}
	if in.Title == "" {
		errs["title"] = "is required"
	}
	if in.Author == "" {
		errs["author"] = "is required"
	}
	if in.Year != 0 && (in.Year < 1 || in.Year > time.Now().Year()+1) {
		errs["year"] = fmt.Sprintf("must be between 1 and %d", time.Now().Year()+1)
	}
	if in.ISBN != "" && !validISBN(in.ISBN) {
		errs["isbn"] = "must be 10 or 13 characters (digits, optional trailing X for ISBN-10)"
	}
	if len(errs) > 0 {
		return errs
	}
	return nil
}

// validISBN performs a shape check only (length and characters), not a checksum.
// Hyphens and spaces are permitted as separators.
func validISBN(s string) bool {
	var digits []rune
	for _, r := range s {
		switch {
		case r == '-' || r == ' ':
			continue
		case r >= '0' && r <= '9':
			digits = append(digits, r)
		case r == 'X' && len(digits) == 9:
			digits = append(digits, r)
		default:
			return false
		}
	}
	return len(digits) == 10 || len(digits) == 13
}
