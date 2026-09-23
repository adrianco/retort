package main

import (
	"fmt"
	"strings"
	"unicode/utf8"
)

// Length limits for text fields, in characters. They comfortably fit real
// bibliographic data while keeping individual records small.
const (
	maxTitleLength  = 500
	maxAuthorLength = 300
	maxISBNLength   = 32
)

// minYear is the earliest accepted publication year.
const minYear = 1

// Book is a book in the collection, as stored and as returned by the API.
// Year and ISBN are optional and encode as JSON null when unknown.
type Book struct {
	ID     int64   `json:"id"`
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// BookInput is the request body for creating or replacing a book. It has no
// ID: the store assigns IDs, and updates take the ID from the URL.
type BookInput struct {
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// Normalize trims surrounding whitespace from the text fields and drops a
// blank ISBN, so that stored values are canonical.
func (in *BookInput) Normalize() {
	in.Title = strings.TrimSpace(in.Title)
	in.Author = strings.TrimSpace(in.Author)
	if in.ISBN != nil {
		isbn := strings.TrimSpace(*in.ISBN)
		if isbn == "" {
			in.ISBN = nil
		} else {
			in.ISBN = &isbn
		}
	}
}

// Validate reports every problem with the input as a ValidationError, or nil
// if there are none. Title and author are required. A year, if given, must lie
// between minYear and currentYear+1, since books published late in a year are
// often dated the next one.
func (in BookInput) Validate(currentYear int) error {
	var errs ValidationError
	checkText := func(field, value string, maxLength int) {
		switch {
		case strings.TrimSpace(value) == "":
			errs.add(field, "is required")
		case utf8.RuneCountInString(value) > maxLength:
			errs.add(field, fmt.Sprintf("must be at most %d characters", maxLength))
		}
	}
	checkText("title", in.Title, maxTitleLength)
	checkText("author", in.Author, maxAuthorLength)
	if in.Year != nil && (*in.Year < minYear || *in.Year > currentYear+1) {
		errs.add("year", fmt.Sprintf("must be between %d and %d", minYear, currentYear+1))
	}
	if in.ISBN != nil && utf8.RuneCountInString(*in.ISBN) > maxISBNLength {
		errs.add("isbn", fmt.Sprintf("must be at most %d characters", maxISBNLength))
	}
	if len(errs) > 0 {
		return errs
	}
	return nil
}

// FieldError is a problem with one field of a request body.
type FieldError struct {
	Field   string
	Message string
}

// ValidationError lists the problems found in a request body, in field order.
type ValidationError []FieldError

func (e *ValidationError) add(field, message string) {
	*e = append(*e, FieldError{Field: field, Message: message})
}

func (e ValidationError) Error() string {
	problems := make([]string, len(e))
	for i, fe := range e {
		problems[i] = fe.Field + " " + fe.Message
	}
	return "validation failed: " + strings.Join(problems, "; ")
}
