package main

import (
	"database/sql"
	"errors"
	"fmt"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned when a book with the requested ID does not exist.
var ErrNotFound = errors.New("book not found")

// Book is the resource managed by this API.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

// Store wraps the SQLite database.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) the SQLite database at path and ensures the
// schema exists. Use ":memory:" for an in-memory database.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	// SQLite handles one writer at a time; serialize access through a single
	// connection to avoid SQLITE_BUSY errors under concurrent requests.
	db.SetMaxOpenConns(1)

	const schema = `
	CREATE TABLE IF NOT EXISTS books (
		id     INTEGER PRIMARY KEY AUTOINCREMENT,
		title  TEXT NOT NULL,
		author TEXT NOT NULL,
		year   INTEGER,
		isbn   TEXT
	);`
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("create schema: %w", err)
	}
	return &Store{db: db}, nil
}

// Close closes the underlying database.
func (s *Store) Close() error {
	return s.db.Close()
}

// CreateBook inserts a book and returns it with its assigned ID.
func (s *Store) CreateBook(b Book) (Book, error) {
	res, err := s.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		b.Title, b.Author, b.Year, b.ISBN,
	)
	if err != nil {
		return Book{}, err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, err
	}
	b.ID = id
	return b, nil
}

// ListBooks returns all books, optionally filtered by exact author match.
func (s *Store) ListBooks(author string) ([]Book, error) {
	query := "SELECT id, title, author, year, isbn FROM books"
	var args []any
	if author != "" {
		query += " WHERE author = ?"
		args = append(args, author)
	}
	query += " ORDER BY id"

	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

// GetBook returns the book with the given ID, or ErrNotFound.
func (s *Store) GetBook(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	return b, err
}

// UpdateBook replaces the book with the given ID, or returns ErrNotFound.
func (s *Store) UpdateBook(id int64, b Book) (Book, error) {
	res, err := s.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		b.Title, b.Author, b.Year, b.ISBN, id,
	)
	if err != nil {
		return Book{}, err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, err
	}
	if n == 0 {
		return Book{}, ErrNotFound
	}
	b.ID = id
	return b, nil
}

// DeleteBook removes the book with the given ID, or returns ErrNotFound.
func (s *Store) DeleteBook(id int64) error {
	res, err := s.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}
