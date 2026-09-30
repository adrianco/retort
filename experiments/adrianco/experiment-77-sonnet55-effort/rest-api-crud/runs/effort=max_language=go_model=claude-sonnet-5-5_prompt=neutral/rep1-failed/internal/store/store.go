// Package store persists books in an SQLite database.
package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"time"

	_ "modernc.org/sqlite" // registers the pure-Go "sqlite" driver

	"bookapi/internal/book"
)

// Memory selects a private in-memory database instead of a file. Its contents
// disappear when the Store is closed.
const Memory = ":memory:"

// BusyTimeout is how long a statement waits for a lock held by another process
// (the sqlite3 shell, say) before it fails with "database is locked". SQLite
// does this wait itself, so a cancelled context cannot cut it short.
const BusyTimeout = 5 * time.Second

// AUTOINCREMENT guarantees that the id of a deleted book is never reused. The
// NOCASE index backs the case-insensitive author filter.
const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT    NOT NULL,
	author TEXT    NOT NULL,
	year   INTEGER NOT NULL DEFAULT 0,
	isbn   TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS books_author_nocase ON books (author COLLATE NOCASE);
`

const selectBook = `SELECT id, title, author, year, isbn FROM books`

// Store is a book repository backed by SQLite. It is safe for concurrent use.
type Store struct {
	db *sql.DB
}

// Open opens the database at path, creating the file and its schema when they
// do not exist yet. Use Memory for a throwaway in-memory database.
func Open(path string) (*Store, error) {
	if path != Memory {
		if err := checkDir(filepath.Dir(path)); err != nil {
			return nil, err
		}
	}
	db, err := sql.Open("sqlite", dsn(path))
	if err != nil {
		return nil, fmt.Errorf("open database %q: %w", path, err)
	}
	// SQLite allows a single writer at a time. Funnelling all access through
	// one connection avoids "database is locked" errors between pooled
	// connections, and keeps an in-memory database (which is private to the
	// connection that created it) coherent.
	db.SetMaxOpenConns(1)
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("initialise database %q: %w", path, err)
	}
	return &Store{db: db}, nil
}

// checkDir reports a missing directory clearly; SQLite itself only says
// "out of memory" in that case.
func checkDir(dir string) error {
	info, err := os.Stat(dir)
	switch {
	case err != nil:
		return fmt.Errorf("database directory: %w", err)
	case !info.IsDir():
		return fmt.Errorf("database directory: %s is not a directory", dir)
	}
	return nil
}

// dsn converts a filesystem path into an SQLite "file:" URI. Escaping keeps
// characters such as '?' and '#' in the path from being read as URI syntax.
// busy_timeout makes a connection wait up to BusyTimeout for a lock held by
// another process instead of failing immediately.
func dsn(path string) string {
	escaped := (&url.URL{Path: path}).EscapedPath()
	return fmt.Sprintf("file:%s?_pragma=busy_timeout(%d)", escaped, BusyTimeout.Milliseconds())
}

// Close releases the database.
func (s *Store) Close() error {
	return s.db.Close()
}

// Ping verifies that the database answers queries and that the books table
// can be read. The driver's own ping is a bare "select 1", which would keep
// succeeding after the table was dropped or the file was damaged.
func (s *Store) Ping(ctx context.Context) error {
	var populated int
	if err := s.db.QueryRowContext(ctx, `SELECT EXISTS (SELECT 1 FROM books)`).Scan(&populated); err != nil {
		return fmt.Errorf("ping: %w", err)
	}
	return nil
}

// Create stores a new book and returns it with its assigned id.
func (s *Store) Create(ctx context.Context, in book.Input) (book.Book, error) {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, in.ISBN)
	if err != nil {
		return book.Book{}, fmt.Errorf("create book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return book.Book{}, fmt.Errorf("create book: %w", err)
	}
	return book.Book{ID: id, Input: in}, nil
}

// Get returns the book with the given id, or book.ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (book.Book, error) {
	b, err := scanBook(s.db.QueryRowContext(ctx, selectBook+` WHERE id = ?`, id))
	if errors.Is(err, sql.ErrNoRows) {
		err = book.ErrNotFound
	}
	if err != nil {
		return book.Book{}, fmt.Errorf("get book %d: %w", id, err)
	}
	return b, nil
}

// List returns the books ordered by id. A non-empty author restricts the
// result to books by that author, compared case-insensitively.
func (s *Store) List(ctx context.Context, author string) ([]book.Book, error) {
	query := selectBook
	var args []any
	if author != "" {
		query += ` WHERE author COLLATE NOCASE = ?`
		args = append(args, author)
	}
	rows, err := s.db.QueryContext(ctx, query+` ORDER BY id`, args...)
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

// Update replaces every field of the book with the given id and returns the
// result, or book.ErrNotFound.
func (s *Store) Update(ctx context.Context, id int64, in book.Input) (book.Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		in.Title, in.Author, in.Year, in.ISBN, id)
	if err == nil {
		err = checkAffected(res)
	}
	if err != nil {
		return book.Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	return book.Book{ID: id, Input: in}, nil
}

// Delete removes the book with the given id, or returns book.ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err == nil {
		err = checkAffected(res)
	}
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	return nil
}

// checkAffected turns "no row matched" into book.ErrNotFound.
func checkAffected(res sql.Result) error {
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return book.ErrNotFound
	}
	return nil
}

// scanner is satisfied by both *sql.Row and *sql.Rows.
type scanner interface {
	Scan(dest ...any) error
}

func scanBook(s scanner) (book.Book, error) {
	var b book.Book
	err := s.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}
