package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/url"
	"strings"
	"time"

	"modernc.org/sqlite"
	sqlite3 "modernc.org/sqlite/lib"
)

// Sentinel errors the HTTP layer maps onto status codes.
var (
	ErrNotFound      = errors.New("book not found")
	ErrDuplicateISBN = errors.New("a book with this isbn already exists")
)

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id         INTEGER PRIMARY KEY AUTOINCREMENT,
	title      TEXT NOT NULL,
	author     TEXT NOT NULL,
	year       INTEGER NOT NULL DEFAULT 0,
	isbn       TEXT NOT NULL DEFAULT '',
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL
);

-- ISBN is optional, so only non-empty values participate in the unique index.
CREATE UNIQUE INDEX IF NOT EXISTS books_isbn_unique ON books(isbn) WHERE isbn <> '';

CREATE INDEX IF NOT EXISTS books_author_idx ON books(author COLLATE NOCASE);
`

// Store persists books in SQLite.
type Store struct {
	db *sql.DB
}

// OpenStore opens (and migrates) the database at path. Use ":memory:" for an
// ephemeral database, which is what the tests do.
func OpenStore(path string) (*Store, error) {
	dsn := dsnFor(path)
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}

	// A single connection keeps writers from tripping over each other and, for
	// an in-memory database, guarantees every query sees the same schema.
	db.SetMaxOpenConns(1)

	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("migrate: %w", err)
	}
	return &Store{db: db}, nil
}

// dsnFor turns a file path into a DSN with the pragmas we want. An in-memory
// database gets a shared cache so it survives for the lifetime of the pool.
func dsnFor(path string) string {
	params := url.Values{}
	params.Set("_pragma", "busy_timeout(5000)")
	params.Add("_pragma", "foreign_keys(1)")

	if path == ":memory:" || path == "" {
		params.Add("_pragma", "journal_mode(MEMORY)")
		return ":memory:?" + params.Encode()
	}
	params.Add("_pragma", "journal_mode(WAL)")
	return "file:" + path + "?" + params.Encode()
}

func (s *Store) Close() error { return s.db.Close() }

// Ping verifies the database is reachable; used by the health check.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

const bookColumns = "id, title, author, year, isbn, created_at, updated_at"

// Create inserts a book and returns it with its generated ID and timestamps.
func (s *Store) Create(ctx context.Context, in BookInput) (Book, error) {
	now := timestamp()
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, in.ISBN, now, now)
	if err != nil {
		if isUniqueViolation(err) {
			return Book{}, ErrDuplicateISBN
		}
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	return Book{
		ID:        id,
		Title:     in.Title,
		Author:    in.Author,
		Year:      in.Year,
		ISBN:      in.ISBN,
		CreatedAt: now,
		UpdatedAt: now,
	}, nil
}

// List returns books ordered by ID. A non-empty author filters on an exact,
// case-insensitive author match.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT ` + bookColumns + ` FROM books`
	var args []any
	if author = strings.TrimSpace(author); author != "" {
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
			return nil, fmt.Errorf("list books: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	return books, nil
}

// Get returns a single book, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	row := s.db.QueryRowContext(ctx, `SELECT `+bookColumns+` FROM books WHERE id = ?`, id)
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book: %w", err)
	}
	return b, nil
}

// Update replaces every mutable field of an existing book.
func (s *Store) Update(ctx context.Context, id int64, in BookInput) (Book, error) {
	now := timestamp()
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?`,
		in.Title, in.Author, in.Year, in.ISBN, now, id)
	if err != nil {
		if isUniqueViolation(err) {
			return Book{}, ErrDuplicateISBN
		}
		return Book{}, fmt.Errorf("update book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, fmt.Errorf("update book: %w", err)
	}
	if n == 0 {
		return Book{}, ErrNotFound
	}
	// Re-read so the response carries the stored created_at.
	return s.Get(ctx, id)
}

// Delete removes a book, or reports ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

// scanner covers both *sql.Row and *sql.Rows.
type scanner interface {
	Scan(dest ...any) error
}

func scanBook(s scanner) (Book, error) {
	var b Book
	err := s.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt)
	return b, err
}

func timestamp() string {
	return time.Now().UTC().Format(time.RFC3339Nano)
}

// isUniqueViolation reports whether err is SQLite's UNIQUE constraint failure.
func isUniqueViolation(err error) bool {
	var serr *sqlite.Error
	if errors.As(err, &serr) {
		return serr.Code() == sqlite3.SQLITE_CONSTRAINT_UNIQUE
	}
	return false
}
