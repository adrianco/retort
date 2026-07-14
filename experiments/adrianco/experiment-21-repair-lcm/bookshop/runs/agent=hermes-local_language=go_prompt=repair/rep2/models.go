package main

import "errors"

// Book represents a book in the collection.
type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// CreateBookRequest holds the fields for creating a book.
type CreateBookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// UpdateBookRequest holds the fields for updating a book.
// Zero values mean the field is not being updated; use pointers for explicit updates.
type UpdateBookRequest struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// ErrorResponse is a standard error response JSON body.
type ErrorResponse struct {
	Error string `json:"error"`
}

// ErrNotFound is returned when a requested resource does not exist.
var ErrNotFound = errors.New("resource not found")
