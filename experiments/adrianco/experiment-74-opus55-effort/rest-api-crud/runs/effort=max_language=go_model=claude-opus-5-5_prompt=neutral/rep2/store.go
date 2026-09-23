package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"

	_ "modernc.org/sqlite" // pure-Go SQLite driver, registered as "sqlite"
)

// ErrNotFound reports that no book has the requested ID.
var ErrNotFound = errors.New("book not found")

// schema creates the books table. AUTOINCREMENT stops the IDs of deleted books
// from being handed out again, and STRICT makes SQLite enforce column types.
const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT    NOT NULL CHECK (title <> ''),
	author TEXT    NOT NULL CHECK (author <> ''),
	year   INTEGER,
	isbn   TEXT
) STRICT`

// bookColumns lists the columns in the order scanBook reads them.
const bookColumns = "id, title, author, year, isbn"

// Store keeps books in a SQLite database. It is safe for concurrent use.
type Store struct {
	db *sql.DB
}

// OpenStore opens the SQLite database at path, creating the file and schema if
// needed. The path ":memory:" gives a private database that lasts as long as
// the Store.
func OpenStore(ctx context.Context, path string) (*Store, error) {
	// The pragmas apply to every pooled connection: WAL lets reads proceed
	// during a write, and busy_timeout makes a writer wait for the write lock
	// instead of failing at once with SQLITE_BUSY.
	db, err := sql.Open("sqlite", path+"?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)")
	if err != nil {
		return nil, fmt.Errorf("open database %s: %w", path, err)
	}
	if path == ":memory:" {
		// Every connection to ":memory:" gets its own empty database, so all
		// queries must share one connection.
		db.SetMaxOpenConns(1)
	}
	if err := db.PingContext(ctx); err != nil {
		db.Close()
		return nil, fmt.Errorf("open database %s: %w", path, err)
	}
	if _, err := db.ExecContext(ctx, schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("create schema: %w", err)
	}
	return &Store{db: db}, nil
}

// Close closes the database.
func (s *Store) Close() error {
	return s.db.Close()
}

// Ping checks that the database is reachable.
func (s *Store) Ping(ctx context.Context) error {
	return s.db.PingContext(ctx)
}

// CreateBook adds a book and returns it with its newly assigned ID.
func (s *Store) CreateBook(ctx context.Context, in BookInput) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING `+bookColumns,
		in.Title, in.Author, in.Year, in.ISBN)
	book, err := scanBook(row)
	if err != nil {
		return Book{}, fmt.Errorf("create book: %w", err)
	}
	return book, nil
}

// GetBook returns the book with the given ID, or an error wrapping ErrNotFound.
func (s *Store) GetBook(ctx context.Context, id int64) (Book, error) {
	row := s.db.QueryRowContext(ctx, `SELECT `+bookColumns+` FROM books WHERE id = ?`, id)
	book, err := scanBook(row)
	if err != nil {
		return Book{}, fmt.Errorf("get book %d: %w", id, err)
	}
	return book, nil
}

// ListBooks returns the books in ID order. A non-empty author restricts the
// result to books whose author contains it, ignoring case (for ASCII letters,
// as SQLite's lower() does).
func (s *Store) ListBooks(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT ` + bookColumns + ` FROM books`
	var args []any
	if author != "" {
		// instr rather than LIKE, so that % and _ in the filter match literally.
		query += ` WHERE instr(lower(author), lower(?)) > 0`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	books := []Book{} // an empty collection encodes as [], not null
	for rows.Next() {
		book, err := scanBook(rows)
		if err != nil {
			return nil, fmt.Errorf("list books: %w", err)
		}
		books = append(books, book)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	return books, nil
}

// UpdateBook replaces every field of the book with the given ID and returns
// the result, or an error wrapping ErrNotFound.
func (s *Store) UpdateBook(ctx context.Context, id int64, in BookInput) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING `+bookColumns,
		in.Title, in.Author, in.Year, in.ISBN, id)
	book, err := scanBook(row)
	if err != nil {
		return Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	return book, nil
}

// DeleteBook removes the book with the given ID, or returns an error wrapping
// ErrNotFound.
func (s *Store) DeleteBook(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	if n == 0 {
		return fmt.Errorf("delete book %d: %w", id, ErrNotFound)
	}
	return nil
}

// scanner is the Scan method shared by *sql.Row and *sql.Rows.
type scanner interface {
	Scan(dest ...any) error
}

// scanBook reads one row of bookColumns, mapping sql.ErrNoRows to ErrNotFound.
func scanBook(sc scanner) (Book, error) {
	var b Book
	if err := sc.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return Book{}, ErrNotFound
		}
		return Book{}, err
	}
	return b, nil
}
