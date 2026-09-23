package main

import (
	"fmt"
	"strings"
	"time"
	"unicode/utf8"
)

const (
	maxTitleLen  = 500
	maxAuthorLen = 200
	maxISBNLen   = 32
)

// BookInput is the request payload for creating or updating a book.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ValidationErrors maps a field name to a human-readable problem.
type ValidationErrors map[string]string

// Normalize trims surrounding whitespace from all string fields.
func (in *BookInput) Normalize() {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	in.ISBN = strings.TrimSpace(in.ISBN)
}

// Validate checks the input and returns any field errors (nil if valid).
// Title and author are required; year and isbn are optional.
func (in BookInput) Validate() ValidationErrors {
	errs := ValidationErrors{}

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
		errs["year"] = fmt.Sprintf("year must be between 0 and %d", maxYear)
	}

	if utf8.RuneCountInString(in.ISBN) > maxISBNLen {
		errs["isbn"] = fmt.Sprintf("isbn must be at most %d characters", maxISBNLen)
	}

	if len(errs) == 0 {
		return nil
	}
	return errs
}
