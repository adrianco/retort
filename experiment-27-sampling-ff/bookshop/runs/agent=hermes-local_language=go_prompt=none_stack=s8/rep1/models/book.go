package models

import (
	"encoding/json"
	"fmt"
	"time"
)

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

// Validate checks that required fields are present.
func (r *CreateBookRequest) Validate() error {
	if r.Title == "" {
		return fmt.Errorf("title is required")
	}
	if r.Author == "" {
		return fmt.Errorf("author is required")
	}
	return nil
}

// ValidatePartial checks that at least one field is provided and required ones are valid.
func (r *UpdateBookRequest) ValidatePartial() error {
	if r.Title != nil && *r.Title == "" {
		return fmt.Errorf("title cannot be empty")
	}
	if r.Author != nil && *r.Author == "" {
		return fmt.Errorf("author cannot be empty")
	}
	return nil
}

// MarshalJSON customizes JSON output to use RFC3339 format for time fields.
func (b Book) MarshalJSON() ([]byte, error) {
	type Alias Book
	return json.Marshal(&struct {
		CreatedAt string `json:"created_at"`
		UpdatedAt string `json:"updated_at"`
		*Alias
	}{
		CreatedAt: b.CreatedAt.Format(time.RFC3339),
		UpdatedAt: b.UpdatedAt.Format(time.RFC3339),
		Alias:     (*Alias)(&b),
	})
}
