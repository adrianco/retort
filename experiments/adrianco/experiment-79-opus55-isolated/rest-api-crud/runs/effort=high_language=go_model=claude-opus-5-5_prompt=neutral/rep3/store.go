package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	_ "modernc.org/sqlite" // pure-Go SQLite driver, registered as "sqlite"
)

// ErrNotFound is returned when a book with the requested ID does not exist.
var ErrNotFound = errors.New("book not found")

// Book is a single entry in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

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

// Store persists books in a SQLite database.
type Store struct {
	db *sql.DB
}

// OpenStore opens (creating if necessary) the SQLite database at path and
// ensures the schema exists. Use ":memory:" for a throwaway in-memory database.
func OpenStore(ctx context.Context, path string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn(path))
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	if path == ":memory:" {
		// Every connection to ":memory:" gets its own private database, so the
		// pool must never grow beyond one.
		db.SetMaxOpenConns(1)
	}
	if _, err := db.ExecContext(ctx, schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("initialise schema: %w", err)
	}
	return &Store{db: db}, nil
}

// dsn builds a connection string whose pragmas apply to every pooled
// connection, not just the first one.
func dsn(path string) string {
	if path == ":memory:" {
		return path
	}
	// The path is embedded in a URI, so escape the characters that would
	// otherwise end it early.
	escaped := strings.NewReplacer("%", "%25", "?", "%3f", "#", "%23").Replace(path)
	return "file:" + escaped + "?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)"
}

// Close releases the underlying database handle.
func (s *Store) Close() error {
	return s.db.Close()
}

// Ping reports whether the database is reachable.
func (s *Store) Ping(ctx context.Context) error {
	return s.db.PingContext(ctx)
}

// Create inserts b and returns it with its newly assigned ID.
func (s *Store) Create(ctx context.Context, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	b.ID = id
	return b, nil
}

// List returns all books ordered by ID. A non-empty author restricts the
// result to books by that author (case-insensitive exact match).
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
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
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

// Update replaces every field of the book with the given ID, or returns
// ErrNotFound if there is no such book.
func (s *Store) Update(ctx context.Context, id int64, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id)
	if err != nil {
		return Book{}, fmt.Errorf("update book: %w", err)
	}
	if err := requireOneRow(res); err != nil {
		return Book{}, err
	}
	b.ID = id
	return b, nil
}

// Delete removes the book with the given ID, or returns ErrNotFound if there
// is no such book.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	return requireOneRow(res)
}

func requireOneRow(res sql.Result) error {
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}
