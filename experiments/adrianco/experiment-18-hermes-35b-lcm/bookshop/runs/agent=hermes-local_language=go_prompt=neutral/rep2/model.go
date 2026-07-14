package main

import "time"

// Book represents a book in the collection.
type Book struct {
	ID        int       `json:"id"`
	Title     string    `json:"title"`
	Author    string    `json:"author"`
	Year      int       `json:"year"`
	ISBN      string    `json:"isbn"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// CreateBookRequest represents the input for creating a book.
type CreateBookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// UpdateBookRequest represents the input for updating a book.
type UpdateBookRequest struct {
	Title  *string `json:"title,omitempty"`
	Author *string `json:"author,omitempty"`
	Year   *int    `json:"year,omitempty"`
	ISBN   *string `json:"isbn,omitempty"`
}

// ValidationError represents a field validation error.
type ValidationError struct {
	Field   string `json:"field"`
	Message string `json:"message"`
}

// ErrorResponse represents a JSON error response.
type ErrorResponse struct {
	Error       string           `json:"error"`
	Validation  []ValidationError `json:"validation,omitempty"`
}

// HealthResponse represents the health check response.
type HealthResponse struct {
	Status  string `json:"status"`
	Timestamp string `json:"timestamp"`
}
