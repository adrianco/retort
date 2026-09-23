package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	_ "modernc.org/sqlite" // pure-Go SQLite driver (no cgo), registers as "sqlite"
)

// ErrNotFound is returned when a book with the requested ID does not exist.
var ErrNotFound = errors.New("book not found")

// AUTOINCREMENT guarantees IDs of deleted books are never reused, so a stale
// /books/{id} URL keeps returning 404 instead of silently pointing at a new book.
const schema = `
CREATE TABLE IF NOT EXISTS books (
	id         INTEGER PRIMARY KEY AUTOINCREMENT,
	title      TEXT    NOT NULL,
	author     TEXT    NOT NULL,
	year       INTEGER NOT NULL DEFAULT 0,
	isbn       TEXT    NOT NULL DEFAULT '',
	created_at TEXT    NOT NULL,
	updated_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
`

const bookColumns = `id, title, author, year, isbn, created_at, updated_at`

// Store persists books in a SQLite database.
type Store struct {
	db *sql.DB
}

// OpenStore opens (creating if necessary) the SQLite database at path and applies
// the schema. Use ":memory:" for a throwaway in-memory database.
func OpenStore(path string) (*Store, error) {
	// busy_timeout makes concurrent writers wait for the lock instead of failing
	// with SQLITE_BUSY; WAL lets readers proceed while a write is in progress.
	dsn := path + "?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)&_pragma=synchronous(NORMAL)"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	if path == ":memory:" {
		// Every connection to ":memory:" is a separate, empty database, so pin the
		// pool to a single long-lived connection.
		db.SetMaxOpenConns(1)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if _, err := db.ExecContext(ctx, schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema to %s: %w", path, err)
	}
	return &Store{db: db}, nil
}

// Close releases the database.
func (s *Store) Close() error { return s.db.Close() }

// Ping verifies the database is reachable.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

// Create inserts a new book and returns it with its assigned ID and timestamps.
func (s *Store) Create(ctx context.Context, in BookInput) (Book, error) {
	now := timestamp()
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, in.ISBN, formatTime(now), formatTime(now))
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	return Book{
		ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN,
		CreatedAt: now, UpdatedAt: now,
	}, nil
}

// List returns all books ordered by ID. If author is non-empty, only books whose
// author matches it exactly (ignoring ASCII case) are returned. The result is
// never nil, so it always encodes as a JSON array.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT ` + bookColumns + ` FROM books`
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
			return nil, fmt.Errorf("list books: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	return books, nil
}

// Get returns the book with the given ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	row := s.db.QueryRowContext(ctx, `SELECT `+bookColumns+` FROM books WHERE id = ?`, id)
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book %d: %w", id, err)
	}
	return b, nil
}

// Update replaces the editable fields of the book with the given ID and returns
// the updated book, or ErrNotFound. The creation timestamp is preserved.
func (s *Store) Update(ctx context.Context, id int64, in BookInput) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ?
		 WHERE id = ? RETURNING `+bookColumns,
		in.Title, in.Author, in.Year, in.ISBN, formatTime(timestamp()), id)
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	return b, nil
}

// Delete removes the book with the given ID, or returns ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

type scanner interface {
	Scan(dest ...any) error
}

func scanBook(sc scanner) (Book, error) {
	var (
		b                Book
		created, updated string
	)
	if err := sc.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &created, &updated); err != nil {
		return Book{}, err
	}
	var err error
	if b.CreatedAt, err = time.Parse(time.RFC3339Nano, created); err != nil {
		return Book{}, fmt.Errorf("parse created_at: %w", err)
	}
	if b.UpdatedAt, err = time.Parse(time.RFC3339Nano, updated); err != nil {
		return Book{}, fmt.Errorf("parse updated_at: %w", err)
	}
	return b, nil
}

// timestamp returns the current UTC time at millisecond precision, so values
// round-trip through the database unchanged.
func timestamp() time.Time { return time.Now().UTC().Truncate(time.Millisecond) }

func formatTime(t time.Time) string { return t.Format(time.RFC3339Nano) }
