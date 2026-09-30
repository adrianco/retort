// Package store persists books in an embedded SQLite database.
package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	_ "modernc.org/sqlite" // pure-Go driver (no CGO); registers itself as "sqlite"

	"bookapi/internal/book"
)

// AUTOINCREMENT guarantees an ID is never handed out twice, even after the
// book that held it is deleted. The NOCASE index backs the author filter.
const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT    NOT NULL CHECK (length(trim(title)) > 0),
	author TEXT    NOT NULL CHECK (length(trim(author)) > 0),
	year   INTEGER NOT NULL DEFAULT 0,
	isbn   TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books (author COLLATE NOCASE);
`

const (
	columns     = "id, title, author, year, isbn"
	openTimeout = 10 * time.Second

	// The driver consumes these options itself and strips them from the path
	// before handing it to SQLite. WAL lets other processes (for example the
	// sqlite3 shell) read the file while the server writes to it.
	connOptions = "?_busy_timeout=5000&_journal_mode=WAL"
)

// Store is a book store backed by a SQLite database. It is safe for
// concurrent use.
type Store struct {
	db *sql.DB
}

// Open opens the SQLite database at path, creating the file and the schema if
// they do not exist. Use ":memory:" for a throwaway in-memory database.
func Open(path string) (*Store, error) {
	if path == "" {
		return nil, errors.New("database path is required")
	}
	if strings.Contains(path, "?") {
		// The driver would take everything after the '?' for connection options.
		return nil, fmt.Errorf("database path %q must not contain '?'", path)
	}

	db, err := sql.Open("sqlite", path+connOptions)
	if err != nil {
		return nil, fmt.Errorf("open database %q: %w", path, err)
	}
	// SQLite allows a single writer at a time, so extra connections would only
	// contend for its lock. A single connection also keeps ":memory:" usable:
	// every connection would otherwise get its own private, empty database.
	db.SetMaxOpenConns(1)

	ctx, cancel := context.WithTimeout(context.Background(), openTimeout)
	defer cancel()
	if _, err := db.ExecContext(ctx, schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("initialise database %q: %w", path, err)
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
	b, err := scanOne(s.db.QueryRowContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING `+columns,
		in.Title, in.Author, in.Year, in.ISBN))
	if err != nil {
		return book.Book{}, fmt.Errorf("create book: %w", err)
	}
	return b, nil
}

// Get returns the book with the given ID, or book.ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (book.Book, error) {
	b, err := scanOne(s.db.QueryRowContext(ctx,
		`SELECT `+columns+` FROM books WHERE id = ?`, id))
	if err != nil {
		return book.Book{}, fmt.Errorf("get book %d: %w", id, err)
	}
	return b, nil
}

// List returns all books ordered by ID. A non-empty author restricts the
// result to books by that author, compared case-insensitively (for ASCII
// letters). The result is never nil.
func (s *Store) List(ctx context.Context, author string) ([]book.Book, error) {
	query := `SELECT ` + columns + ` FROM books`
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

	books := []book.Book{}
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

// Update replaces all client-controlled fields of the book with the given ID
// and returns the result, or book.ErrNotFound.
func (s *Store) Update(ctx context.Context, id int64, in book.Input) (book.Book, error) {
	b, err := scanOne(s.db.QueryRowContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING `+columns,
		in.Title, in.Author, in.Year, in.ISBN, id))
	if err != nil {
		return book.Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	return b, nil
}

// Delete removes the book with the given ID, or returns book.ErrNotFound.
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
		return fmt.Errorf("delete book %d: %w", id, book.ErrNotFound)
	}
	return nil
}

// scanner is implemented by both *sql.Row and *sql.Rows.
type scanner interface {
	Scan(dest ...any) error
}

func scanBook(s scanner) (book.Book, error) {
	var b book.Book
	err := s.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

// scanOne reads the single book a query returned, mapping "no rows" to
// book.ErrNotFound.
func scanOne(row *sql.Row) (book.Book, error) {
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return book.Book{}, book.ErrNotFound
	}
	return b, err
}
