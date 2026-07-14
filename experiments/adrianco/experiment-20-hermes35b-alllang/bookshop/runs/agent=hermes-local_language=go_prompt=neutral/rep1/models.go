package main

import "time"

// Book represents a book in the collection.
type Book struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      int       `json:"year"`
	ISBN      string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
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
	Title  *string `json:"title,omitempty"`
	Author *string `json:"author,omitempty"`
	Year   *int    `json:"year,omitempty"`
	ISBN   *string `json:"isbn,omitempty"`
}

// ErrorResponse represents a JSON error response.
type ErrorResponse struct {
	Error string `json:"error"`
}
