package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"sync/atomic"
	"time"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned when a book ID does not exist.
var ErrNotFound = errors.New("book not found")

// memDBSeq names in-memory databases uniquely; see OpenStore.
var memDBSeq atomic.Int64

// Store is the SQLite-backed persistence layer for books.
type Store struct {
	db  *sql.DB
	now func() time.Time
}

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id         INTEGER PRIMARY KEY AUTOINCREMENT,
	title      TEXT    NOT NULL,
	author     TEXT    NOT NULL,
	year       INTEGER NOT NULL DEFAULT 0,
	isbn       TEXT    NOT NULL DEFAULT '',
	created_at TEXT    NOT NULL,
	updated_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS books_author_idx ON books (author COLLATE NOCASE);
`

// OpenStore opens (creating if necessary) the SQLite database at path and
// applies the schema. Use ":memory:" for an ephemeral database.
func OpenStore(path string) (*Store, error) {
	dsn := path
	if path == ":memory:" {
		// A plain ":memory:" DSN gives every pooled connection its own
		// private database; a shared-cache URI keeps them consistent. The
		// name is unique per call so concurrent stores stay isolated.
		dsn = fmt.Sprintf("file:memdb%d?mode=memory&cache=shared", memDBSeq.Add(1))
	}
	dsn += joiner(dsn) + "_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)&_pragma=foreign_keys(1)"

	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	// SQLite allows a single writer. Serialising access here trades a little
	// read concurrency for the guarantee that we never surface SQLITE_BUSY,
	// and keeps the shared in-memory database alive for the pool's lifetime.
	db.SetMaxOpenConns(1)

	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("connect sqlite: %w", err)
	}
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema: %w", err)
	}
	return &Store{db: db, now: time.Now}, nil
}

func joiner(dsn string) string {
	for _, c := range dsn {
		if c == '?' {
			return "&"
		}
	}
	return "?"
}

// Close releases the database handle.
func (s *Store) Close() error { return s.db.Close() }

// Ping verifies the database is reachable.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

// Create inserts a new book and returns it with its assigned ID.
func (s *Store) Create(ctx context.Context, in BookInput) (Book, error) {
	ts := s.timestamp()
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at)
		 VALUES (?, ?, ?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, in.ISBN, ts, ts)
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	return Book{
		ID: id, Title: in.Title, Author: in.Author, Year: in.Year, ISBN: in.ISBN,
		CreatedAt: mustParseTime(ts), UpdatedAt: mustParseTime(ts),
	}, nil
}

// List returns all books ordered by ID. When author is non-empty only books
// by that author are returned, compared case-insensitively.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT id, title, author, year, isbn, created_at, updated_at FROM books`
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

	// Non-nil so an empty result marshals as [] rather than null.
	books := []Book{}
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

// Get returns the book with the given ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn, created_at, updated_at
		 FROM books WHERE id = ?`, id)
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book %d: %w", id, err)
	}
	return b, nil
}

// Update replaces every client-owned field of an existing book and returns the
// stored result. It returns ErrNotFound if the ID does not exist.
func (s *Store) Update(ctx context.Context, id int64, in BookInput) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ?
		 WHERE id = ?`,
		in.Title, in.Author, in.Year, in.ISBN, s.timestamp(), id)
	if err != nil {
		return Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	if n == 0 {
		return Book{}, ErrNotFound
	}
	return s.Get(ctx, id)
}

// Delete removes a book, returning ErrNotFound if it did not exist.
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

// scanner covers both *sql.Row and *sql.Rows.
type scanner interface{ Scan(dest ...any) error }

func scanBook(sc scanner) (Book, error) {
	var (
		b                    Book
		createdAt, updatedAt string
	)
	if err := sc.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &createdAt, &updatedAt); err != nil {
		return Book{}, err
	}
	b.CreatedAt = mustParseTime(createdAt)
	b.UpdatedAt = mustParseTime(updatedAt)
	return b, nil
}

// timestamp renders the current time in a lexicographically sortable,
// timezone-explicit form.
func (s *Store) timestamp() string {
	return s.now().UTC().Format(time.RFC3339Nano)
}

// mustParseTime tolerates unparsable values by returning the zero time: a
// malformed timestamp is not worth failing a request over.
func mustParseTime(v string) time.Time {
	t, err := time.Parse(time.RFC3339Nano, v)
	if err != nil {
		return time.Time{}
	}
	return t
}
