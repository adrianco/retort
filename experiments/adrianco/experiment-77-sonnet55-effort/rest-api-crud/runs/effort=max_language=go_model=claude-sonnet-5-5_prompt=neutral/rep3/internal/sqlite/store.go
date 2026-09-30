// Package sqlite persists books in an embedded SQLite database. It uses the
// pure-Go modernc.org/sqlite driver, so no C toolchain is needed to build it.
package sqlite

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	_ "modernc.org/sqlite" // registers the "sqlite" database/sql driver

	"bookapi/internal/book"
)

// The CHECK constraints are a backstop for the validation in package book.
// AUTOINCREMENT guarantees that the ID of a deleted book is never handed out
// again.
const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT NOT NULL CHECK (length(trim(title)) > 0),
	author TEXT NOT NULL CHECK (length(trim(author)) > 0),
	year   INTEGER,
	isbn   TEXT
);
CREATE INDEX IF NOT EXISTS books_author_idx ON books (author COLLATE NOCASE);
`

const columns = "id, title, author, year, isbn"

// Store keeps books in a SQLite database. It is safe for concurrent use.
type Store struct {
	db *sql.DB
}

// Open opens (creating it if necessary) the SQLite database file at path and
// makes sure the schema exists. The special path ":memory:" gives a private,
// in-memory database that disappears on Close.
func Open(path string) (*Store, error) {
	if path == "" {
		return nil, errors.New("database path must not be empty")
	}
	db, err := sql.Open("sqlite", dsn(path))
	if err != nil {
		return nil, fmt.Errorf("open database %q: %w", path, err)
	}
	// SQLite allows a single writer at a time. One connection serialises all
	// access, so requests never fail with SQLITE_BUSY against each other, and
	// it keeps an in-memory database alive and shared by every request.
	db.SetMaxOpenConns(1)

	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("initialise database %q: %w", path, err)
	}
	return &Store{db: db}, nil
}

// dsn turns a file path into a driver DSN. The path is placed in a "file:" URI,
// so the characters that URI syntax would otherwise interpret are escaped. In
// particular a '?' must not let a path smuggle extra parameters into the DSN.
// _busy_timeout is one of the driver's validated shorthand parameters, and it
// makes a write wait for a lock held by another process instead of failing.
func dsn(path string) string {
	escaped := strings.NewReplacer("%", "%25", "?", "%3f", "#", "%23").Replace(path)
	scheme := "file:"
	if strings.HasPrefix(escaped, "/") {
		// Spell out the empty authority: "file://x/y" would read x as a host name.
		scheme = "file://"
	}
	return scheme + escaped + "?_busy_timeout=5000"
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
	row := s.db.QueryRowContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING `+columns,
		in.Title, in.Author, in.Year, in.ISBN)
	b, err := scanBook(row)
	if err != nil {
		return book.Book{}, fmt.Errorf("create book: %w", err)
	}
	return b, nil
}

// Get returns the book with the given ID, or book.ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (book.Book, error) {
	row := s.db.QueryRowContext(ctx, `SELECT `+columns+` FROM books WHERE id = ?`, id)
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return book.Book{}, book.ErrNotFound
	}
	if err != nil {
		return book.Book{}, fmt.Errorf("get book %d: %w", id, err)
	}
	return b, nil
}

// List returns all books ordered by ID. A non-empty author restricts the result
// to books whose author equals it, ignoring ASCII case.
func (s *Store) List(ctx context.Context, author string) ([]book.Book, error) {
	query, args := `SELECT `+columns+` FROM books ORDER BY id`, []any(nil)
	if author != "" {
		query = `SELECT ` + columns + ` FROM books WHERE author = ? COLLATE NOCASE ORDER BY id`
		args = []any{author}
	}

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	var books []book.Book
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

// Update replaces every writable field of the book with the given ID and
// returns the stored result, or book.ErrNotFound.
func (s *Store) Update(ctx context.Context, id int64, in book.Input) (book.Book, error) {
	row := s.db.QueryRowContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING `+columns,
		in.Title, in.Author, in.Year, in.ISBN, id)
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return book.Book{}, book.ErrNotFound
	}
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
		return book.ErrNotFound
	}
	return nil
}

// rowScanner is the part of *sql.Row and *sql.Rows that scanBook needs.
type rowScanner interface {
	Scan(dest ...any) error
}

func scanBook(row rowScanner) (book.Book, error) {
	var b book.Book
	err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}
