package books

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"modernc.org/sqlite"
	sqlite3 "modernc.org/sqlite/lib"
)

// Errors returned by Store that callers are expected to branch on.
var (
	// ErrNotFound means no book has the requested ID.
	ErrNotFound = errors.New("book not found")
	// ErrDuplicateISBN means another book already carries that ISBN.
	ErrDuplicateISBN = errors.New("isbn already belongs to another book")
)

// InMemoryPath opens a private, throwaway database that lives only as long as
// the process. Handy for tests and for kicking the tyres on the API.
//
// The shared cache is what makes it usable through database/sql: without it
// every pooled connection would get its own empty database.
const InMemoryPath = "file::memory:?cache=shared"

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id         INTEGER PRIMARY KEY AUTOINCREMENT,
	title      TEXT    NOT NULL,
	author     TEXT    NOT NULL,
	year       INTEGER NOT NULL DEFAULT 0,
	isbn       TEXT,
	created_at TEXT    NOT NULL,
	updated_at TEXT    NOT NULL
);

-- Partial index: any number of books may have no ISBN (NULL), but a present
-- ISBN identifies exactly one book.
CREATE UNIQUE INDEX IF NOT EXISTS books_isbn_key ON books(isbn) WHERE isbn IS NOT NULL;

-- Supports the ?author= filter.
CREATE INDEX IF NOT EXISTS books_author_idx ON books(author COLLATE NOCASE);
`

const columns = `id, title, author, year, isbn, created_at, updated_at`

// Store is the SQLite-backed collection of books. It is safe for concurrent
// use by multiple goroutines.
type Store struct {
	db *sql.DB
}

// Open connects to the SQLite database at path, creating the file and the
// schema if they do not exist yet. Pass InMemoryPath for an ephemeral database.
//
// The caller owns the returned Store and must Close it.
func Open(ctx context.Context, path string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn(path))
	if err != nil {
		return nil, fmt.Errorf("open database %q: %w", path, err)
	}

	// SQLite serialises writers anyway; capping the pool at one connection
	// trades a little read concurrency for never having to reason about
	// SQLITE_BUSY. At the scale this service targets it costs nothing.
	db.SetMaxOpenConns(1)

	if err := db.PingContext(ctx); err != nil {
		db.Close()
		return nil, fmt.Errorf("connect to database %q: %w", path, err)
	}
	if _, err := db.ExecContext(ctx, schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema: %w", err)
	}
	return &Store{db: db}, nil
}

// dsn turns a filesystem path into a SQLite connection string carrying the
// pragmas we want on every connection. A path that is already a file: URI
// (such as InMemoryPath) is passed through with the pragmas appended.
func dsn(path string) string {
	pragmas := "_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)&_pragma=foreign_keys(1)"
	if strings.HasPrefix(path, "file:") {
		separator := "?"
		if strings.Contains(path, "?") {
			separator = "&"
		}
		return path + separator + pragmas
	}
	return "file:" + path + "?" + pragmas
}

// Close releases the database handle.
func (s *Store) Close() error { return s.db.Close() }

// Ping checks that the database is reachable. It backs the health endpoint.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

// Create stores a new book and returns it with its assigned ID and timestamps.
// The input is expected to have been validated already.
func (s *Store) Create(ctx context.Context, in Input) (Book, error) {
	now := time.Now().UTC()
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, nullableISBN(in.ISBN), formatTime(now), formatTime(now))
	if err != nil {
		return Book{}, translateError(err, "insert book")
	}

	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("read inserted book id: %w", err)
	}
	return Book{
		ID:        id,
		Title:     in.Title,
		Author:    in.Author,
		Year:      in.Year,
		ISBN:      in.ISBN,
		CreatedAt: now,
		UpdatedAt: now,
	}, nil
}

// Get returns the book with the given ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (Book, error) {
	row := s.db.QueryRowContext(ctx, `SELECT `+columns+` FROM books WHERE id = ?`, id)
	book, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("select book %d: %w", id, err)
	}
	return book, nil
}

// List returns every book, oldest ID first. A non-empty author restricts the
// result to books by that author, compared without regard to case or
// surrounding whitespace.
//
// The result is never nil, so it always marshals to a JSON array.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT ` + columns + ` FROM books`
	var args []any
	if author = strings.TrimSpace(author); author != "" {
		query += ` WHERE author = ? COLLATE NOCASE`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("select books: %w", err)
	}
	defer rows.Close()

	list := []Book{}
	for rows.Next() {
		book, err := scanBook(rows)
		if err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		list = append(list, book)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate books: %w", err)
	}
	return list, nil
}

// Update replaces every client-supplied field of the book with the given ID and
// returns the stored result. It reports ErrNotFound if no such book exists and
// ErrDuplicateISBN if the new ISBN is taken.
func (s *Store) Update(ctx context.Context, id int64, in Input) (Book, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return Book{}, fmt.Errorf("begin update: %w", err)
	}
	defer tx.Rollback() //nolint:errcheck // no-op once the tx is committed

	now := time.Now().UTC()
	res, err := tx.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?`,
		in.Title, in.Author, in.Year, nullableISBN(in.ISBN), formatTime(now), id)
	if err != nil {
		return Book{}, translateError(err, "update book")
	}

	// SQLite counts every row the WHERE clause matched, whether or not the
	// values actually changed, so zero rows means the book is gone.
	affected, err := res.RowsAffected()
	if err != nil {
		return Book{}, fmt.Errorf("count updated rows: %w", err)
	}
	if affected == 0 {
		return Book{}, ErrNotFound
	}

	// Re-read rather than reconstruct, so created_at comes from the row.
	book, err := scanBook(tx.QueryRowContext(ctx, `SELECT `+columns+` FROM books WHERE id = ?`, id))
	if err != nil {
		return Book{}, fmt.Errorf("select updated book %d: %w", id, err)
	}
	if err := tx.Commit(); err != nil {
		return Book{}, fmt.Errorf("commit update: %w", err)
	}
	return book, nil
}

// Delete removes the book with the given ID, or reports ErrNotFound.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	affected, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("count deleted rows: %w", err)
	}
	if affected == 0 {
		return ErrNotFound
	}
	return nil
}

// scanner is the shared surface of *sql.Row and *sql.Rows.
type scanner interface {
	Scan(dest ...any) error
}

func scanBook(row scanner) (Book, error) {
	var (
		book      Book
		isbn      sql.NullString
		createdAt string
		updatedAt string
	)
	if err := row.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &isbn, &createdAt, &updatedAt); err != nil {
		return Book{}, err
	}
	book.ISBN = isbn.String

	var err error
	if book.CreatedAt, err = parseTime(createdAt); err != nil {
		return Book{}, fmt.Errorf("book %d: created_at: %w", book.ID, err)
	}
	if book.UpdatedAt, err = parseTime(updatedAt); err != nil {
		return Book{}, fmt.Errorf("book %d: updated_at: %w", book.ID, err)
	}
	return book, nil
}

// nullableISBN maps the "no ISBN" empty string to SQL NULL, which is what lets
// the partial unique index tolerate many books without one.
func nullableISBN(isbn string) any {
	if isbn == "" {
		return nil
	}
	return isbn
}

func formatTime(t time.Time) string { return t.UTC().Format(time.RFC3339Nano) }

func parseTime(s string) (time.Time, error) {
	t, err := time.Parse(time.RFC3339Nano, s)
	if err != nil {
		return time.Time{}, fmt.Errorf("parse timestamp %q: %w", s, err)
	}
	return t.UTC(), nil
}

// translateError converts a driver-level uniqueness violation into
// ErrDuplicateISBN and wraps everything else with context.
func translateError(err error, operation string) error {
	var sqliteErr *sqlite.Error
	if errors.As(err, &sqliteErr) && sqliteErr.Code() == sqlite3.SQLITE_CONSTRAINT_UNIQUE {
		return ErrDuplicateISBN
	}
	return fmt.Errorf("%s: %w", operation, err)
}
