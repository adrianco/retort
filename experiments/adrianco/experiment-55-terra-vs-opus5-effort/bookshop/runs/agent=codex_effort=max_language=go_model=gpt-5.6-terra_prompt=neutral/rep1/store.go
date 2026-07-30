package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned when a requested book does not exist.
var ErrNotFound = errors.New("book not found")

// Book is the persistent representation returned by the API.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookInput contains the fields clients can set when creating or updating a
// book. ID is intentionally omitted because it is assigned by SQLite.
type BookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Store provides SQLite-backed persistence for books.
type Store struct {
	db *sql.DB
}

// OpenStore opens (and, if needed, creates) a SQLite database at dsn.
func OpenStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	// A single connection avoids transient "database is locked" errors for a
	// small embedded service and also makes SQLite's in-memory DSNs predictable.
	db.SetMaxOpenConns(1)

	store := &Store{db: db}
	if err := store.migrate(context.Background()); err != nil {
		db.Close()
		return nil, err
	}
	return store, nil
}

func (s *Store) migrate(ctx context.Context) error {
	_, err := s.db.ExecContext(ctx, `
		CREATE TABLE IF NOT EXISTS books (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT NOT NULL,
			author TEXT NOT NULL,
			year INTEGER NOT NULL DEFAULT 0,
			isbn TEXT NOT NULL DEFAULT ''
		)
	`)
	if err != nil {
		return fmt.Errorf("create books table: %w", err)
	}
	return nil
}

// Close releases the database connection.
func (s *Store) Close() error {
	return s.db.Close()
}

// Create inserts a book and returns it with its generated ID.
func (s *Store) Create(ctx context.Context, input BookInput) (Book, error) {
	result, err := s.db.ExecContext(
		ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		input.Title,
		input.Author,
		input.Year,
		input.ISBN,
	)
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("get inserted book ID: %w", err)
	}
	return Book{ID: id, Title: input.Title, Author: input.Author, Year: input.Year, ISBN: input.ISBN}, nil
}

// List returns all books, optionally limited to an exact author match.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	args := make([]any, 0, 1)
	if author != "" {
		query += ` WHERE author = ?`
		args = append(args, author)
	}
	query += ` ORDER BY id ASC`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	books := make([]Book, 0)
	for rows.Next() {
		book, err := scanBook(rows)
		if err != nil {
			return nil, err
		}
		books = append(books, book)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate books: %w", err)
	}
	return books, nil
}

// Get returns one book by ID.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	row := s.db.QueryRowContext(ctx, `
		SELECT id, title, author, year, isbn
		FROM books
		WHERE id = ?
	`, id)
	book, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book: %w", err)
	}
	return book, nil
}

// Update replaces the editable fields of a book and returns the new value.
func (s *Store) Update(ctx context.Context, id int64, input BookInput) (Book, error) {
	result, err := s.db.ExecContext(ctx, `
		UPDATE books
		SET title = ?, author = ?, year = ?, isbn = ?
		WHERE id = ?
	`, input.Title, input.Author, input.Year, input.ISBN, id)
	if err != nil {
		return Book{}, fmt.Errorf("update book: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return Book{}, fmt.Errorf("check updated book: %w", err)
	}
	if rowsAffected == 0 {
		return Book{}, ErrNotFound
	}
	return Book{ID: id, Title: input.Title, Author: input.Author, Year: input.Year, ISBN: input.ISBN}, nil
}

// Delete removes a book by ID.
func (s *Store) Delete(ctx context.Context, id int64) error {
	result, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("check deleted book: %w", err)
	}
	if rowsAffected == 0 {
		return ErrNotFound
	}
	return nil
}

type scanner interface {
	Scan(dest ...any) error
}

func scanBook(s scanner) (Book, error) {
	var book Book
	if err := s.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
		return Book{}, err
	}
	return book, nil
}
