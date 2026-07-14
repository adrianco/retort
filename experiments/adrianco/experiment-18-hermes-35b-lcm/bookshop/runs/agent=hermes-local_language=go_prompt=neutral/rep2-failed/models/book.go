package models

import (
	"errors"
	"fmt"
	"strconv"
)

// Book represents a book in the collection.
type Book struct {
	ID     string `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// CreateBookRequest represents the JSON body for creating a book.
type CreateBookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// UpdateBookRequest represents the JSON body for updating a book.
type UpdateBookRequest struct {
	Title  *string `json:"title"`
	Author *string `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

// Validate checks that required fields are present.
func (r CreateBookRequest) Validate() error {
	if r.Title == "" {
		return errors.New("title is required")
	}
	if r.Author == "" {
		return errors.New("author is required")
	}
	if r.Year <= 0 {
		return fmt.Errorf("year must be a positive integer, got %d", r.Year)
	}
	return nil
}

// ValidatePartial checks required fields when updating.
func (r UpdateBookRequest) ValidatePartial() error {
	if r.Title != nil && *r.Title == "" {
		return errors.New("title cannot be empty")
	}
	if r.Author != nil && *r.Author == "" {
		return errors.New("author cannot be empty")
	}
	if r.Year != nil && *r.Year <= 0 {
		return errors.New("year must be a positive integer")
	}
	return nil
}

// Apply updates a Book with non-nil fields from the request.
func (r UpdateBookRequest) Apply(b *Book) {
	if r.Title != nil {
		b.Title = *r.Title
	}
	if r.Author != nil {
		b.Author = *r.Author
	}
	if r.Year != nil {
		b.Year = *r.Year
	}
	if r.ISBN != nil {
		b.ISBN = *r.ISBN
	}
}

// BookStore defines the interface for book persistence.
type BookStore interface {
	Create(book *Book) error
	GetByID(id string) (*Book, error)
	List(authorFilter string) ([]Book, error)
	Update(id string, req UpdateBookRequest) (*Book, error)
	Delete(id string) error
}

// ToBookFromDB converts a database row to a Book model.
func ToBookFromDB(id string, title, author string, year int, isbn string) *Book {
	bookID, _ := strconv.ParseInt(id, 10, 64)
	return &Book{
		ID:     fmt.Sprintf("%d", bookID),
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}
}
