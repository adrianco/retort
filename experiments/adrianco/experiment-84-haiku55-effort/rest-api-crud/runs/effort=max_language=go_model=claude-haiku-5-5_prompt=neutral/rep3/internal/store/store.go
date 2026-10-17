// Package store persists books in an embedded SQLite database.
package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/url"
	"strings"

	"bookapi/internal/book"

	_ "modernc.org/sqlite" // registers the "sqlite" driver; pure Go, so no cgo
)

// ErrNotFound is returned when no book has the requested ID.
var ErrNotFound = errors.New("book not found")

// AUTOINCREMENT keeps a deleted book's ID from being reused by a later book.
const schema = `CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT    NOT NULL,
	author TEXT    NOT NULL,
	year   INTEGER NOT NULL DEFAULT 0,
	isbn   TEXT    NOT NULL DEFAULT ''
)`

// Store is a book repository backed by a SQLite database file.
type Store struct {
	db *sql.DB
}

// uriPathEscaper escapes the characters that SQLite reads as URI syntax inside
// a file: DSN, so that the path reaches the file system unchanged.
var uriPathEscaper = strings.NewReplacer("%", "%25", "?", "%3F", "#", "%23")

// Open opens the SQLite database at path, creating the file and schema if needed.
func Open(path string) (*Store, error) {
	// The pragmas are applied to every new connection the driver opens.
	dsn := "file:" + uriPathEscaper.Replace(path) + "?" + url.Values{
		"_pragma": {"busy_timeout(5000)", "journal_mode(WAL)"},
	}.Encode()

	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	// SQLite permits one writer at a time. A single connection keeps the
	// pool from competing for the write lock.
	db.SetMaxOpenConns(1)

	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("create schema: %w", err)
	}
	return &Store{db: db}, nil
}

// Close releases the database.
func (s *Store) Close() error {
	return s.db.Close()
}

// Ping reports whether the database is reachable.
func (s *Store) Ping(ctx context.Context) error {
	return s.db.PingContext(ctx)
}

// Create stores a new book and returns it with its assigned ID.
func (s *Store) Create(ctx context.Context, in book.Input) (book.Book, error) {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, in.ISBN)
	if err != nil {
		return book.Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return book.Book{}, fmt.Errorf("read new book id: %w", err)
	}
	return toBook(id, in), nil
}

// Get returns the book with the given ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (book.Book, error) {
	var b book.Book
	err := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return book.Book{}, ErrNotFound
	}
	if err != nil {
		return book.Book{}, fmt.Errorf("get book %d: %w", id, err)
	}
	return b, nil
}

// List returns books ordered by ID. A non-empty author limits the result to
// books whose author contains it, ignoring case.
func (s *Store) List(ctx context.Context, author string) ([]book.Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author != "" {
		query += ` WHERE instr(lower(author), lower(?)) > 0`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	// Start from an empty slice so an empty result encodes as [] rather than null.
	books := []book.Book{}
	for rows.Next() {
		var b book.Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate books: %w", err)
	}
	return books, nil
}

// Update replaces every field of the book with the given ID, or returns
// ErrNotFound.
func (s *Store) Update(ctx context.Context, id int64, in book.Input) (book.Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		in.Title, in.Author, in.Year, in.ISBN, id)
	if err != nil {
		return book.Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return book.Book{}, fmt.Errorf("count updated rows: %w", err)
	}
	if n == 0 {
		return book.Book{}, ErrNotFound
	}
	return toBook(id, in), nil
}

// Delete removes the book with the given ID, or returns ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("count deleted rows: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

func toBook(id int64, in book.Input) book.Book {
	return book.Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
}
