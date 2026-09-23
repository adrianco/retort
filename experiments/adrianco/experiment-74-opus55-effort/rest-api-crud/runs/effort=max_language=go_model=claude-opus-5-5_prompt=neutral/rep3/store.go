package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	_ "modernc.org/sqlite" // pure-Go SQLite driver, registered as "sqlite"
)

// ErrNotFound is returned when no book has the requested ID.
var ErrNotFound = errors.New("book not found")

// AUTOINCREMENT guarantees that the ID of a deleted book is never handed out
// again, so a stale /books/{id} URL cannot silently point at a different book.
const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT    NOT NULL,
	author TEXT    NOT NULL,
	year   INTEGER,
	isbn   TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS books_author_idx ON books (author COLLATE NOCASE);
`

const selectBooks = `SELECT id, title, author, year, isbn FROM books`

// Store persists books in a SQLite database. It is safe for concurrent use.
type Store struct {
	db *sql.DB
}

// OpenStore opens the SQLite database at path, creating the file and schema
// if they do not exist. Pass ":memory:" for a throwaway in-memory database.
func OpenStore(path string) (*Store, error) {
	// WAL lets other processes (such as the sqlite3 shell) read the file
	// while we write, and busy_timeout makes lock conflicts with them wait
	// instead of failing immediately with SQLITE_BUSY.
	dsn := path + "?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)&_pragma=synchronous(NORMAL)"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	// SQLite allows only one writer at a time. A single connection turns
	// contention between our own requests into cheap queueing inside
	// database/sql instead of SQLite's sleep-and-retry busy handler. It is
	// also required for ":memory:", where each new connection would open a
	// separate, empty database.
	db.SetMaxOpenConns(1)
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("initialize schema: %w", err)
	}
	return &Store{db: db}, nil
}

// Close closes the underlying database.
func (s *Store) Close() error {
	return s.db.Close()
}

// Ping checks that the database is reachable.
func (s *Store) Ping(ctx context.Context) error {
	return s.db.PingContext(ctx)
}

// Create inserts a new book and returns it with its assigned ID.
func (s *Store) Create(ctx context.Context, in BookInput) (Book, error) {
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
	return in.book(id), nil
}

// Get returns the book with the given ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	b, err := scanBook(s.db.QueryRowContext(ctx, selectBooks+` WHERE id = ?`, id))
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book %d: %w", id, err)
	}
	return b, nil
}

// List returns all books ordered by ID. A non-empty author restricts the
// result to that author's books, compared case-insensitively. The returned
// slice is never nil, so it always encodes as a JSON array.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query, args := selectBooks, []any{}
	if author != "" {
		query += ` WHERE author = ? COLLATE NOCASE`
		args = append(args, author)
	}
	rows, err := s.db.QueryContext(ctx, query+` ORDER BY id`, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

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

// Update replaces every field of the book with the given ID and returns the
// result, or ErrNotFound.
func (s *Store) Update(ctx context.Context, id int64, in BookInput) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		in.Title, in.Author, in.Year, in.ISBN, id)
	if err := checkAffected(res, err); err != nil {
		return Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	return in.book(id), nil
}

// Delete removes the book with the given ID, or returns ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err := checkAffected(res, err); err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	return nil
}

// scanBook reads a row whose columns are those selected by selectBooks.
func scanBook(row interface{ Scan(dest ...any) error }) (Book, error) {
	var b Book
	err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	return b, err
}

// checkAffected turns the outcome of a single-row UPDATE or DELETE into an
// error, reporting ErrNotFound when no row matched. SQLite counts matched
// rows even when an UPDATE leaves their values unchanged.
func checkAffected(res sql.Result, err error) error {
	if err != nil {
		return err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}
