package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	_ "modernc.org/sqlite" // registers the pure-Go "sqlite" database/sql driver
)

// ErrNotFound is returned when no book has the requested ID.
var ErrNotFound = errors.New("book not found")

// schema creates the books table if it does not already exist.
//
// AUTOINCREMENT stops SQLite from reusing the IDs of deleted books, so a stale
// /books/{id} URL can never point at a different book.
//
// author_lower is the author lowercased by Go, so that the ?author= filter is
// case-insensitive for all letters; SQLite's own LIKE and lower() only fold
// ASCII, which would miss matches such as "émile" against "Émile Zola".
const schema = `
CREATE TABLE IF NOT EXISTS books (
	id           INTEGER PRIMARY KEY AUTOINCREMENT,
	title        TEXT    NOT NULL CHECK (title <> ''),
	author       TEXT    NOT NULL CHECK (author <> ''),
	author_lower TEXT    NOT NULL,
	year         INTEGER,
	isbn         TEXT
)`

// bookColumns are the columns read by scanBook, in order.
const bookColumns = `id, title, author, year, isbn`

// Store keeps books in a SQLite database. It is safe for concurrent use.
type Store struct {
	db *sql.DB
}

// OpenStore opens the SQLite database at path, creating the file and schema if
// needed. The path ":memory:" gives a private database that is lost on Close.
func OpenStore(ctx context.Context, path string) (*Store, error) {
	// busy_timeout makes a writer wait for another's lock instead of failing
	// at once; WAL lets reads proceed while a write is in progress.
	db, err := sql.Open("sqlite", path+"?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)")
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	if path == ":memory:" {
		// Each connection to ":memory:" has its own separate database, so
		// the pool must never open a second one.
		db.SetMaxOpenConns(1)
	}
	if _, err := db.ExecContext(ctx, schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("open database %s: %w", path, err)
	}
	return &Store{db: db}, nil
}

// Close closes the database.
func (s *Store) Close() error {
	return s.db.Close()
}

// Ping checks that the database can be reached.
func (s *Store) Ping(ctx context.Context) error {
	return s.db.PingContext(ctx)
}

// Create adds b to the collection, ignoring b.ID, and returns it as stored,
// with its newly assigned ID.
func (s *Store) Create(ctx context.Context, b Book) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`INSERT INTO books (title, author, author_lower, year, isbn)
		 VALUES (?, ?, ?, ?, ?)
		 RETURNING `+bookColumns,
		b.Title, b.Author, strings.ToLower(b.Author), b.Year, b.ISBN)
	created, err := scanBook(row)
	if err != nil {
		return Book{}, fmt.Errorf("create book: %w", err)
	}
	return created, nil
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

// List returns the books in the order they were added. If author is not
// empty, only books whose author contains it, ignoring case, are returned.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT ` + bookColumns + ` FROM books`
	var args []any
	if author != "" {
		// instr rather than LIKE, so that % and _ in the filter match literally.
		query += ` WHERE instr(author_lower, ?) > 0`
		args = append(args, strings.ToLower(author))
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	books := []Book{} // not nil, so that no books encodes as [] rather than null
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

// Update replaces all fields of the book whose ID is b.ID and returns it as
// stored, or returns ErrNotFound.
func (s *Store) Update(ctx context.Context, b Book) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`UPDATE books SET title = ?, author = ?, author_lower = ?, year = ?, isbn = ?
		 WHERE id = ?
		 RETURNING `+bookColumns,
		b.Title, b.Author, strings.ToLower(b.Author), b.Year, b.ISBN, b.ID)
	updated, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("update book %d: %w", b.ID, err)
	}
	return updated, nil
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

// scanBook reads a Book from a row holding bookColumns. NULL year and isbn
// columns become nil pointers.
func scanBook(row interface{ Scan(dest ...any) error }) (Book, error) {
	var b Book
	err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}
