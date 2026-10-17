package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	_ "modernc.org/sqlite" // registers the "sqlite" database/sql driver
)

// ErrNotFound is returned when no book has the requested ID.
var ErrNotFound = errors.New("book not found")

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT NOT NULL,
	author TEXT NOT NULL,
	year   INTEGER,
	isbn   TEXT
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
`

// Store persists books in an SQLite database.
type Store struct {
	db *sql.DB
}

// OpenStore opens the SQLite database at path, creating it if needed, and applies the schema.
func OpenStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path+"?_pragma=busy_timeout(5000)")
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	// SQLite permits only one writer at a time, so a single connection avoids lock contention.
	db.SetMaxOpenConns(1)
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema: %w", err)
	}
	return &Store{db: db}, nil
}

// Close releases the database.
func (s *Store) Close() error {
	return s.db.Close()
}

// Ping verifies the database is reachable.
func (s *Store) Ping(ctx context.Context) error {
	return s.db.PingContext(ctx)
}

// Create inserts b and returns it with its assigned ID.
func (s *Store) Create(ctx context.Context, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, optional(b.Year), optional(b.ISBN))
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("read new book id: %w", err)
	}
	b.ID = id
	return b, nil
}

// Get returns the book with the given ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id)
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book: %w", err)
	}
	return b, nil
}

// List returns books in ID order. When author is non-empty, only books whose
// author matches it case-insensitively are returned. The result is never nil.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author != "" {
		query += ` WHERE author = ? COLLATE NOCASE`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		b, err := scanBook(rows)
		if err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate books: %w", err)
	}
	return books, nil
}

// Update replaces every field of the book with the given ID and returns the
// stored result, or ErrNotFound.
func (s *Store) Update(ctx context.Context, id int64, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, optional(b.Year), optional(b.ISBN), id)
	if err != nil {
		return Book{}, fmt.Errorf("update book: %w", err)
	}
	if err := requireAffected(res); err != nil {
		return Book{}, err
	}
	b.ID = id
	return b, nil
}

// Delete removes the book with the given ID, or returns ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	return requireAffected(res)
}

// requireAffected returns ErrNotFound if the statement matched no rows.
func requireAffected(res sql.Result) error {
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("count affected rows: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

// optional maps a nil pointer to SQL NULL and otherwise returns the pointed-to value.
func optional[T any](p *T) any {
	if p == nil {
		return nil
	}
	return *p
}

// rowScanner is satisfied by both *sql.Row and *sql.Rows.
type rowScanner interface {
	Scan(dest ...any) error
}

// scanBook reads one book row, leaving Year and ISBN nil when the column is NULL.
func scanBook(row rowScanner) (Book, error) {
	var (
		b    Book
		year sql.NullInt64
		isbn sql.NullString
	)
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn); err != nil {
		return Book{}, err
	}
	if year.Valid {
		y := int(year.Int64)
		b.Year = &y
	}
	if isbn.Valid {
		s := isbn.String
		b.ISBN = &s
	}
	return b, nil
}
