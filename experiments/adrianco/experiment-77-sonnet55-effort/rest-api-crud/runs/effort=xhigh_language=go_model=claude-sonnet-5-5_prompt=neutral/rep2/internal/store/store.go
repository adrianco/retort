// Package store persists books in an embedded SQLite database.
package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	_ "modernc.org/sqlite" // pure-Go SQLite driver, registers "sqlite"
)

// ErrNotFound is returned when no book has the requested ID.
var ErrNotFound = errors.New("book not found")

// Book is a stored book. Year is nil when unknown.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year"`
	ISBN   string `json:"isbn"`
}

// Input holds the client-writable fields of a book.
type Input struct {
	Title  string
	Author string
	Year   *int
	ISBN   string
}

// Store is a SQLite-backed book repository. It is safe for concurrent use.
type Store struct {
	db *sql.DB
}

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT NOT NULL,
	author TEXT NOT NULL COLLATE NOCASE,
	year   INTEGER,
	isbn   TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
`

const columns = `id, title, author, year, isbn`

// Open opens (creating if necessary) the database at path and applies the
// schema. Use ":memory:" for a private in-memory database.
func Open(path string) (*Store, error) {
	if path == "" {
		return nil, errors.New("store: empty database path")
	}
	memory := path == ":memory:"

	dsn := "file::memory:?_pragma=busy_timeout(5000)"
	if !memory {
		// Escape the characters that are significant in a SQLite URI.
		escaped := strings.NewReplacer("%", "%25", "?", "%3f", "#", "%23").Replace(path)
		dsn = "file:" + escaped + "?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)"
	}

	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("store: open %q: %w", path, err)
	}
	if memory {
		// Every connection to ":memory:" is a separate database, so pin the
		// pool to one connection to keep the schema and data visible.
		db.SetMaxOpenConns(1)
	}
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("store: apply schema: %w", err)
	}
	return &Store{db: db}, nil
}

// Close releases the database.
func (s *Store) Close() error { return s.db.Close() }

// Ping verifies that the database is reachable.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

// Create inserts a book and returns it with its new ID.
func (s *Store) Create(ctx context.Context, in Input) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, in.ISBN)
	if err != nil {
		return Book{}, fmt.Errorf("store: create: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("store: create: %w", err)
	}
	return Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}, nil
}

// Get returns the book with the given ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	b, err := scan(s.db.QueryRowContext(ctx, `SELECT `+columns+` FROM books WHERE id = ?`, id))
	if err != nil {
		return Book{}, fmt.Errorf("store: get %d: %w", id, err)
	}
	return b, nil
}

// List returns all books ordered by ID. A non-empty author restricts the
// result to books by that author (ASCII case-insensitive exact match).
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT ` + columns + ` FROM books`
	var args []any
	if author != "" {
		query += ` WHERE author = ?`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("store: list: %w", err)
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		b, err := scan(rows)
		if err != nil {
			return nil, fmt.Errorf("store: list: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("store: list: %w", err)
	}
	return books, nil
}

// Update replaces the writable fields of a book and returns the result, or
// ErrNotFound.
func (s *Store) Update(ctx context.Context, id int64, in Input) (Book, error) {
	b, err := scan(s.db.QueryRowContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING `+columns,
		in.Title, in.Author, in.Year, in.ISBN, id))
	if err != nil {
		return Book{}, fmt.Errorf("store: update %d: %w", id, err)
	}
	return b, nil
}

// Delete removes a book, or returns ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("store: delete %d: %w", id, err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("store: delete %d: %w", id, err)
	}
	if n == 0 {
		return fmt.Errorf("store: delete %d: %w", id, ErrNotFound)
	}
	return nil
}

type scanner interface{ Scan(dest ...any) error }

// scan reads one row, mapping sql.ErrNoRows to ErrNotFound.
func scan(row scanner) (Book, error) {
	var (
		b    Book
		year sql.NullInt64
	)
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &year, &b.ISBN); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return Book{}, ErrNotFound
		}
		return Book{}, err
	}
	if year.Valid {
		y := int(year.Int64)
		b.Year = &y
	}
	return b, nil
}
