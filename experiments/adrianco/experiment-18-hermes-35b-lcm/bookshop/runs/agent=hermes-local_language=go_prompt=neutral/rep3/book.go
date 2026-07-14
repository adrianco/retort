package main

import "time"

// Book represents a book in the collection.
type Book struct {
	ID        int64      `json:"id"`
	Title     string     `json:"title"`
	Author    string     `json:"author"`
	Year      int        `json:"year"`
	ISBN      string     `json:"isbn"`
	CreatedAt time.Time  `json:"created_at"`
	UpdatedAt time.Time  `json:"updated_at"`
}

// CreateBookRequest represents the request body for creating a book.
type CreateBookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// UpdateBookRequest represents the request body for updating a book.
type UpdateBookRequest struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// ValidationError holds a single validation error message.
type ValidationError struct {
	Field   string `json:"field"`
	Message string `json:"message"`
}

// ErrorResponse is returned when validation or other errors occur.
type ErrorResponse struct {
	Error       string           `json:"error"`
	Validations []ValidationError `json:"validations,omitempty"`
}

// SuccessResponse is returned on successful creation.
type SuccessResponse struct {
	Message string `json:"message"`
	Book    Book   `json:"book"`
}
