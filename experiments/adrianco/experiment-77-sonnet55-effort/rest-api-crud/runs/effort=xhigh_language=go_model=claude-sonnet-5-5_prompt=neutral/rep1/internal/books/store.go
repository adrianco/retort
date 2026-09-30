package books

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/url"

	_ "modernc.org/sqlite" // pure-Go SQLite driver, registers "sqlite"
)

// ErrNotFound is returned when no book has the requested ID.
var ErrNotFound = errors.New("book not found")

// MemoryPath opens a private in-memory database (handy for tests).
const MemoryPath = ":memory:"

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

// Store persists books in SQLite.
type Store struct {
	db *sql.DB
}

// Open opens (creating if needed) the SQLite database at path and applies the
// schema. Use MemoryPath for a throwaway in-memory database.
func Open(path string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn(path))
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	// SQLite allows a single writer at a time, and every connection to
	// ":memory:" is its own database, so one connection serialises access
	// and keeps both cases correct.
	db.SetMaxOpenConns(1)

	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("connect to database: %w", err)
	}
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema: %w", err)
	}
	return &Store{db: db}, nil
}

// dsn builds a SQLite URI so paths containing '?', '#' or spaces are safe.
func dsn(path string) string {
	q := url.Values{}
	q.Add("_pragma", "busy_timeout(5000)")

	u := url.URL{Scheme: "file", Opaque: MemoryPath}
	if path != MemoryPath {
		u = url.URL{Scheme: "file", Path: path}
		q.Add("_pragma", "journal_mode(WAL)")
	}
	u.RawQuery = q.Encode()
	return u.String()
}

// Close releases the database.
func (s *Store) Close() error { return s.db.Close() }

// Ping reports whether the database is reachable.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

// Create validates and inserts a new book.
func (s *Store) Create(ctx context.Context, in Input) (Book, error) {
	in, err := in.Clean()
	if err != nil {
		return Book{}, err
	}
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, in.ISBN)
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	return Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}, nil
}

// Get returns the book with the given ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	var b Book
	err := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book: %w", err)
	}
	return b, nil
}

// List returns all books ordered by ID. A non-empty author restricts the
// result to books by that author (case-insensitive exact match). The result is
// never nil.
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

	out := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("list books: %w", err)
		}
		out = append(out, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	return out, nil
}

// Update validates and replaces the book with the given ID, or returns
// ErrNotFound.
func (s *Store) Update(ctx context.Context, id int64, in Input) (Book, error) {
	in, err := in.Clean()
	if err != nil {
		return Book{}, err
	}
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		in.Title, in.Author, in.Year, in.ISBN, id)
	if err != nil {
		return Book{}, fmt.Errorf("update book: %w", err)
	}
	if err := requireAffected(res); err != nil {
		return Book{}, err
	}
	return Book{ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN}, nil
}

// Delete removes the book with the given ID, or returns ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	return requireAffected(res)
}

func requireAffected(res sql.Result) error {
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}
