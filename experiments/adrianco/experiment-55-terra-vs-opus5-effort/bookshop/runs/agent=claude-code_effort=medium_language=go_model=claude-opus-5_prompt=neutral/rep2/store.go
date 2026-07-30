package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	_ "modernc.org/sqlite"
)

var (
	// ErrNotFound is returned when no book matches the requested ID.
	ErrNotFound = errors.New("book not found")
	// ErrDuplicateISBN is returned when an ISBN is already used by another book.
	ErrDuplicateISBN = errors.New("a book with that ISBN already exists")
)

// Store is the SQLite-backed persistence layer for books.
type Store struct {
	db *sql.DB
}

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT NOT NULL,
	author TEXT NOT NULL,
	year   INTEGER NOT NULL DEFAULT 0,
	isbn   TEXT
);
-- NULL isbn means "not supplied"; SQLite lets any number of NULLs coexist in a
-- unique index, so this enforces uniqueness only for books that have an ISBN.
CREATE UNIQUE INDEX IF NOT EXISTS books_isbn_unique ON books(isbn) WHERE isbn IS NOT NULL;
CREATE INDEX IF NOT EXISTS books_author ON books(author);
`

// OpenStore opens (creating if needed) the SQLite database at dsn and applies
// the schema. Use ":memory:" for an ephemeral database.
func OpenStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	// SQLite tolerates a single writer at a time. Capping the pool at one
	// connection keeps writes serialised and, for ":memory:", guarantees every
	// query sees the same database.
	db.SetMaxOpenConns(1)

	if _, err := db.Exec(`PRAGMA foreign_keys = ON`); err != nil {
		db.Close()
		return nil, fmt.Errorf("enable foreign keys: %w", err)
	}
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema: %w", err)
	}
	return &Store{db: db}, nil
}

// Close releases the underlying database handle.
func (s *Store) Close() error { return s.db.Close() }

// Ping verifies the database is reachable.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

// Create inserts b and returns it with the assigned ID.
func (s *Store) Create(ctx context.Context, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, nullableISBN(b.ISBN))
	if err != nil {
		return Book{}, translateErr(err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("read inserted id: %w", err)
	}
	b.ID = id
	return b, nil
}

// List returns all books ordered by ID. When author is non-empty only books by
// that author are returned, matched case-insensitively.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT id, title, author, year, COALESCE(isbn, '') FROM books`
	var args []any
	if author = strings.TrimSpace(author); author != "" {
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
			return nil, fmt.Errorf("scan book: %w", err)
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
		`SELECT id, title, author, year, COALESCE(isbn, '') FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book: %w", err)
	}
	return b, nil
}

// Update replaces every field of the book with the given ID, returning
// ErrNotFound if it does not exist.
func (s *Store) Update(ctx context.Context, id int64, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, nullableISBN(b.ISBN), id)
	if err != nil {
		return Book{}, translateErr(err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, fmt.Errorf("update book: %w", err)
	}
	if n == 0 {
		// Either the row is gone or the update was a no-op writing identical
		// values; a lookup distinguishes the two.
		if _, err := s.Get(ctx, id); err != nil {
			return Book{}, err
		}
	}
	b.ID = id
	return b, nil
}

// Delete removes the book with the given ID, returning ErrNotFound if it does
// not exist.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

// nullableISBN maps an empty ISBN to NULL so the unique index ignores it.
func nullableISBN(isbn string) any {
	if isbn == "" {
		return nil
	}
	return isbn
}

// translateErr converts driver-level constraint failures into domain errors.
func translateErr(err error) error {
	if err == nil {
		return nil
	}
	msg := err.Error()
	if strings.Contains(msg, "UNIQUE constraint failed") && strings.Contains(msg, "isbn") {
		return ErrDuplicateISBN
	}
	return fmt.Errorf("database error: %w", err)
}
