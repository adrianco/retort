package main

import (
	"errors"
	"strings"
)

// Book is a single entry in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput is the client-supplied payload for create and update.
// Pointers let us tell "field omitted" from "field set to zero value".
type BookInput struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// ErrValidation wraps any problem with the request body itself.
var ErrValidation = errors.New("validation failed")

// ValidationError lists the fields that failed validation.
type ValidationError struct {
	Fields map[string]string
}

func (e *ValidationError) Error() string {
	parts := make([]string, 0, len(e.Fields))
	for f, msg := range e.Fields {
		parts = append(parts, f+": "+msg)
	}
	return "validation failed (" + strings.Join(parts, ", ") + ")"
}

func (e *ValidationError) Unwrap() error { return ErrValidation }

// currentYearUpperBound is generous on purpose: we only want to reject
// obvious nonsense such as a negative or five-digit year.
const minYear, maxYear = 0, 2200

// toBook validates the input as a complete book (POST / PUT semantics).
func (in BookInput) toBook() (Book, error) {
	ve := &ValidationError{Fields: map[string]string{}}

	title := ""
	if in.Title != nil {
		title = strings.TrimSpace(*in.Title)
	}
	if title == "" {
		ve.Fields["title"] = "is required"
	}

	author := ""
	if in.Author != nil {
		author = strings.TrimSpace(*in.Author)
	}
	if author == "" {
		ve.Fields["author"] = "is required"
	}

	year := 0
	if in.Year != nil {
		year = *in.Year
		if year < minYear || year > maxYear {
			ve.Fields["year"] = "must be between 0 and 2200"
		}
	}

	isbn := ""
	if in.ISBN != nil {
		isbn = strings.TrimSpace(*in.ISBN)
	}

	if len(ve.Fields) > 0 {
		return Book{}, ve
	}
	return Book{Title: title, Author: author, Year: year, ISBN: isbn}, nil
}
