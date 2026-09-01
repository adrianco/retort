// Package store provides SQLite-backed persistence for books.
package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned when a book with the requested ID does not exist.
var ErrNotFound = errors.New("book not found")

// ErrDuplicateISBN is returned when a book with the same ISBN already exists.
var ErrDuplicateISBN = errors.New("a book with this ISBN already exists")

// Book is the persisted representation of a book.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

// Store wraps a SQLite database handle.
type Store struct {
	db *sql.DB
}

// Open opens (or creates) the SQLite database at dsn and applies the schema.
// Use ":memory:" for an in-memory database (tests).
func Open(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	// SQLite handles one writer at a time; a single connection avoids
	// "database is locked" errors and keeps :memory: databases coherent.
	db.SetMaxOpenConns(1)

	s := &Store{db: db}
	if err := s.migrate(); err != nil {
		db.Close()
		return nil, err
	}
	return s, nil
}

func (s *Store) migrate() error {
	const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT NOT NULL,
	author TEXT NOT NULL,
	year   INTEGER,
	isbn   TEXT
);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
CREATE UNIQUE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn) WHERE isbn <> '';
`
	_, err := s.db.Exec(schema)
	if err != nil {
		return fmt.Errorf("migrate: %w", err)
	}
	return nil
}

// Close closes the underlying database.
func (s *Store) Close() error { return s.db.Close() }

// Ping verifies the database connection is alive.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

// Create inserts a new book and returns it with its assigned ID.
func (s *Store) Create(ctx context.Context, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, nullableInt(b.Year), b.ISBN)
	if err != nil {
		return Book{}, translateErr(err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("last insert id: %w", err)
	}
	b.ID = id
	return b, nil
}

// Get returns the book with the given ID.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id)
	return scanBook(row)
}

// List returns all books, optionally filtered by exact (case-insensitive) author.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	q := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author != "" {
		q += ` WHERE author = ? COLLATE NOCASE`
		args = append(args, author)
	}
	q += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, q, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		b, err := scanBook(rows)
		if err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

// Update replaces all mutable fields of the book with the given ID.
func (s *Store) Update(ctx context.Context, id int64, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, nullableInt(b.Year), b.ISBN, id)
	if err != nil {
		return Book{}, translateErr(err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, fmt.Errorf("rows affected: %w", err)
	}
	if n == 0 {
		return Book{}, ErrNotFound
	}
	b.ID = id
	return b, nil
}

// Delete removes the book with the given ID.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("rows affected: %w", err)
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
		b    Book
		year sql.NullInt64
		isbn sql.NullString
	)
	if err := sc.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return Book{}, ErrNotFound
		}
		return Book{}, fmt.Errorf("scan book: %w", err)
	}
	if year.Valid {
		y := int(year.Int64)
		b.Year = &y
	}
	b.ISBN = isbn.String
	return b, nil
}

func nullableInt(p *int) any {
	if p == nil {
		return nil
	}
	return *p
}

func translateErr(err error) error {
	if strings.Contains(err.Error(), "UNIQUE constraint failed") {
		return ErrDuplicateISBN
	}
	return fmt.Errorf("store: %w", err)
}
