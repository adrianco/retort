// Package store persists books in an embedded SQLite database.
package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	"bookapi/internal/book"

	_ "modernc.org/sqlite" // registers the pure-Go "sqlite" driver
)

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT    NOT NULL,
	author TEXT    NOT NULL,
	year   INTEGER NOT NULL DEFAULT 0,
	isbn   TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
`

// Store is a SQLite-backed book repository. It is safe for concurrent use.
type Store struct {
	db *sql.DB
}

// Open opens (creating if necessary) the SQLite database at path and applies
// the schema. Use ":memory:" for a private in-memory database.
func Open(path string) (*Store, error) {
	if path == "" {
		return nil, errors.New("store: database path is empty")
	}
	db, err := sql.Open("sqlite", dsn(path))
	if err != nil {
		return nil, fmt.Errorf("store: open %q: %w", path, err)
	}
	if path == ":memory:" {
		// Every connection to :memory: is a separate database, so pin to one.
		db.SetMaxOpenConns(1)
	}
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("store: apply schema to %q: %w", path, err)
	}
	return &Store{db: db}, nil
}

// dsn builds a driver DSN that waits on locks instead of failing, and uses
// write-ahead logging for on-disk databases so readers don't block the writer.
func dsn(path string) string {
	pragmas := "?_pragma=busy_timeout(5000)"
	if path == ":memory:" {
		return "file::memory:" + pragmas
	}
	escaped := strings.NewReplacer("%", "%25", "?", "%3f", "#", "%23").Replace(path)
	return "file:" + escaped + pragmas + "&_pragma=journal_mode(WAL)"
}

// Close releases the database handle.
func (s *Store) Close() error { return s.db.Close() }

// Ping verifies the database is reachable.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

// Create inserts a new book and returns it with its assigned ID.
func (s *Store) Create(ctx context.Context, in book.Input) (book.Book, error) {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, in.ISBN)
	if err != nil {
		return book.Book{}, fmt.Errorf("store: insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return book.Book{}, fmt.Errorf("store: read new book id: %w", err)
	}
	return fromInput(id, in), nil
}

// Get returns the book with the given ID, or book.ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (book.Book, error) {
	var b book.Book
	err := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return book.Book{}, book.ErrNotFound
	}
	if err != nil {
		return book.Book{}, fmt.Errorf("store: get book %d: %w", id, err)
	}
	return b, nil
}

// List returns all books ordered by ID. If author is non-empty, only books by
// that author are returned (case-insensitive exact match). The result is never
// nil.
func (s *Store) List(ctx context.Context, author string) ([]book.Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author != "" {
		query += ` WHERE author = ? COLLATE NOCASE`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("store: list books: %w", err)
	}
	defer rows.Close()

	books := []book.Book{}
	for rows.Next() {
		var b book.Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("store: scan book: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("store: list books: %w", err)
	}
	return books, nil
}

// Update replaces the book with the given ID, or returns book.ErrNotFound.
func (s *Store) Update(ctx context.Context, id int64, in book.Input) (book.Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		in.Title, in.Author, in.Year, in.ISBN, id)
	if err != nil {
		return book.Book{}, fmt.Errorf("store: update book %d: %w", id, err)
	}
	if err := requireAffected(res, id); err != nil {
		return book.Book{}, err
	}
	return fromInput(id, in), nil
}

// Delete removes the book with the given ID, or returns book.ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("store: delete book %d: %w", id, err)
	}
	return requireAffected(res, id)
}

func requireAffected(res sql.Result, id int64) error {
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("store: rows affected for book %d: %w", id, err)
	}
	if n == 0 {
		return book.ErrNotFound
	}
	return nil
}

func fromInput(id int64, in book.Input) book.Book {
	return book.Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}
}
