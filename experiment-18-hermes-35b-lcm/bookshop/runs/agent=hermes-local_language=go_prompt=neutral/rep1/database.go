package main

import (
	"database/sql"
	"errors"
	"fmt"

	_ "github.com/mattn/go-sqlite3"
)

var ErrNotFound = errors.New("record not found")

// BookStore provides CRUD operations backed by SQLite.
type BookStore struct {
	db *sql.DB
}

// NewBookStore creates a new BookStore and initializes the SQLite database.
func NewBookStore(dsn string) (*BookStore, error) {
	db, err := sql.Open("sqlite3", dsn)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	// Enable WAL mode and foreign keys
	if _, err := db.Exec("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;"); err != nil {
		return nil, fmt.Errorf("pragma: %w", err)
	}

	// Create the books table
	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL
	);`
	if _, err := db.Exec(createTable); err != nil {
		return nil, fmt.Errorf("create table: %w", err)
	}

	return &BookStore{db: db}, nil
}

// Close closes the database connection.
func (s *BookStore) Close() error {
	return s.db.Close()
}

// CreateBook inserts a book and returns the created book with generated ID.
func (s *BookStore) CreateBook(title, author string, year int, isbn string) (*Book, error) {
	result, err := s.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		title, author, year, isbn,
	)
	if err != nil {
		return nil, fmt.Errorf("insert book: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("get last insert id: %w", err)
	}

	return &Book{
		ID:     int(id),
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}, nil
}

// GetAllBooks returns all books, optionally filtered by author.
func (s *BookStore) GetAllBooks(authorFilter string) ([]Book, error) {
	var rows *sql.Rows
	var err error

	if authorFilter != "" {
		rows, err = s.db.Query(
			"SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id",
			authorFilter,
		)
	} else {
		rows, err = s.db.Query("SELECT id, title, author, year, isbn FROM books ORDER BY id")
	}
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate rows: %w", err)
	}
	return books, nil
}

// GetBookByID returns a book by its ID.
func (s *BookStore) GetBookByID(id int) (*Book, error) {
	var b Book
	err := s.db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("query book: %w", err)
	}
	return &b, nil
}

// UpdateBook updates an existing book by ID.
func (s *BookStore) UpdateBook(id int, title, author string, year int, isbn string) (*Book, error) {
	// Verify the book exists
	_, err := s.GetBookByID(id)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			return nil, ErrNotFound
		}
		return nil, err
	}

	_, err = s.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		title, author, year, isbn, id,
	)
	if err != nil {
		return nil, fmt.Errorf("update book: %w", err)
	}

	return &Book{
		ID:     id,
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}, nil
}

// DeleteBook deletes a book by ID.
func (s *BookStore) DeleteBook(id int) error {
	// Verify the book exists first
	if _, err := s.GetBookByID(id); err != nil {
		return err
	}

	_, err := s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	return nil
}
