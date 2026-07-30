package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"runtime"
	"strings"
	"time"

	_ "modernc.org/sqlite" // pure-Go SQLite driver, registered as "sqlite"
)

var (
	// ErrNotFound means the requested book id does not exist.
	ErrNotFound = errors.New("book not found")
	// ErrDuplicateISBN means a write would have given two books the same ISBN.
	ErrDuplicateISBN = errors.New("a book with that isbn already exists")
)

// SQLite extended result codes for constraint violations. Checked numerically
// so the mapping does not depend on the driver's error message wording.
const (
	sqliteConstraintPrimaryKey = 1555
	sqliteConstraintUnique     = 2067
)

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id         INTEGER PRIMARY KEY AUTOINCREMENT,
	title      TEXT    NOT NULL,
	author     TEXT    NOT NULL,
	year       INTEGER,
	isbn       TEXT,
	created_at TEXT    NOT NULL,
	updated_at TEXT    NOT NULL
);

-- Partial index so that ISBNs are unique among the books that have one, while
-- any number of books may have no ISBN at all.
CREATE UNIQUE INDEX IF NOT EXISTS books_isbn_unique ON books(isbn) WHERE isbn IS NOT NULL;

-- Matches the collation used by the ?author= filter.
CREATE INDEX IF NOT EXISTS books_author_idx ON books(author COLLATE NOCASE);
`

const bookColumns = `id, title, author, year, isbn, created_at, updated_at`

// Store persists books in a SQLite database.
type Store struct {
	db *sql.DB
	// now is the clock used for created_at/updated_at. Tests replace it to get
	// deterministic timestamps.
	now func() time.Time
}

// OpenStore opens the SQLite database at path, creating the file and the
// schema if they do not exist. Pass ":memory:" for an ephemeral database that
// lives only as long as the Store.
func OpenStore(path string) (*Store, error) {
	// busy_timeout lets concurrent writers wait their turn instead of failing
	// immediately with SQLITE_BUSY.
	const pragmas = "_pragma=busy_timeout(5000)&_pragma=foreign_keys(on)"

	inMemory := path == ":memory:"
	dsn := "file:" + path + "?" + pragmas
	if inMemory {
		dsn = "file::memory:?" + pragmas
	} else {
		// WAL keeps readers from blocking the writer. It is a no-op for
		// in-memory databases, so it is only requested for real files.
		dsn += "&_pragma=journal_mode(WAL)"
	}

	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open sqlite database %q: %w", path, err)
	}

	if inMemory {
		// Each new connection to ":memory:" gets its own private database, so
		// the pool has to be pinned to one connection to behave like one DB.
		db.SetMaxOpenConns(1)
	} else {
		db.SetMaxOpenConns(max(4, runtime.NumCPU()))
		db.SetMaxIdleConns(max(4, runtime.NumCPU()))
		db.SetConnMaxIdleTime(5 * time.Minute)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := db.PingContext(ctx); err != nil {
		db.Close()
		return nil, fmt.Errorf("connect to sqlite database %q: %w", path, err)
	}
	if _, err := db.ExecContext(ctx, schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema: %w", err)
	}

	return &Store{db: db, now: time.Now}, nil
}

// Close releases the database handle.
func (s *Store) Close() error { return s.db.Close() }

// Ping reports whether the database is reachable. It backs GET /health.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

// Create inserts a new book and returns it with its assigned id and
// timestamps. The input is expected to have been cleaned and validated.
func (s *Store) Create(ctx context.Context, in BookInput) (*Book, error) {
	now := s.now().UTC()
	stamp := formatTime(now)

	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)`,
		in.Title, in.Author, nullableInt(in.Year), nullableString(in.ISBN), stamp, stamp)
	if err != nil {
		if isUniqueViolation(err) {
			return nil, ErrDuplicateISBN
		}
		return nil, fmt.Errorf("insert book: %w", err)
	}

	id, err := res.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("read inserted book id: %w", err)
	}

	return &Book{
		ID:        id,
		Title:     in.Title,
		Author:    in.Author,
		Year:      in.Year,
		ISBN:      in.ISBN,
		CreatedAt: now,
		UpdatedAt: now,
	}, nil
}

// Get returns the book with the given id, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id int64) (*Book, error) {
	row := s.db.QueryRowContext(ctx, `SELECT `+bookColumns+` FROM books WHERE id = ?`, id)
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("get book %d: %w", id, err)
	}
	return b, nil
}

// List returns every book ordered by id. If author is non-empty the result is
// restricted to books by that author, compared case-insensitively.
func (s *Store) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT ` + bookColumns + ` FROM books`
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

	// Never nil: an empty collection must marshal to [] rather than null.
	books := []Book{}
	for rows.Next() {
		b, err := scanBook(rows)
		if err != nil {
			return nil, fmt.Errorf("list books: %w", err)
		}
		books = append(books, *b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	return books, nil
}

// Update replaces every client-settable field of an existing book and returns
// the stored result, or ErrNotFound if the id does not exist. PUT semantics:
// fields the client omitted are cleared, not preserved.
func (s *Store) Update(ctx context.Context, id int64, in BookInput) (*Book, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("begin update transaction: %w", err)
	}
	defer func() { _ = tx.Rollback() }() // no-op once Commit has succeeded

	res, err := tx.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?`,
		in.Title, in.Author, nullableInt(in.Year), nullableString(in.ISBN), formatTime(s.now().UTC()), id)
	if err != nil {
		if isUniqueViolation(err) {
			return nil, ErrDuplicateISBN
		}
		return nil, fmt.Errorf("update book %d: %w", id, err)
	}
	affected, err := res.RowsAffected()
	if err != nil {
		return nil, fmt.Errorf("update book %d: %w", id, err)
	}
	if affected == 0 {
		return nil, ErrNotFound
	}

	// Re-read inside the transaction so the response reflects exactly what was
	// committed, including the untouched created_at.
	b, err := scanBook(tx.QueryRowContext(ctx, `SELECT `+bookColumns+` FROM books WHERE id = ?`, id))
	if err != nil {
		return nil, fmt.Errorf("reload book %d after update: %w", id, err)
	}
	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit update of book %d: %w", id, err)
	}
	return b, nil
}

// Delete removes a book, or returns ErrNotFound if it was never there.
func (s *Store) Delete(ctx context.Context, id int64) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	affected, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	if affected == 0 {
		return ErrNotFound
	}
	return nil
}

// rowScanner is the part of *sql.Row and *sql.Rows that scanBook needs.
type rowScanner interface {
	Scan(dest ...any) error
}

func scanBook(row rowScanner) (*Book, error) {
	var (
		b       Book
		year    sql.NullInt64
		isbn    sql.NullString
		created string
		updated string
	)
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn, &created, &updated); err != nil {
		return nil, err
	}
	if year.Valid {
		v := int(year.Int64)
		b.Year = &v
	}
	if isbn.Valid {
		v := isbn.String
		b.ISBN = &v
	}

	var err error
	if b.CreatedAt, err = parseTime(created); err != nil {
		return nil, fmt.Errorf("book %d: created_at: %w", b.ID, err)
	}
	if b.UpdatedAt, err = parseTime(updated); err != nil {
		return nil, fmt.Errorf("book %d: updated_at: %w", b.ID, err)
	}
	return &b, nil
}

// Timestamps are stored as RFC 3339 text in UTC: it round-trips exactly, sorts
// lexicographically, and does not depend on the driver's date handling.
func formatTime(t time.Time) string { return t.UTC().Format(time.RFC3339Nano) }

func parseTime(s string) (time.Time, error) {
	t, err := time.Parse(time.RFC3339Nano, s)
	if err != nil {
		return time.Time{}, fmt.Errorf("parse timestamp %q: %w", s, err)
	}
	return t.UTC(), nil
}

// nullableInt and nullableString convert optional fields into arguments the
// driver stores as SQL NULL when unset.
func nullableInt(p *int) any {
	if p == nil {
		return nil
	}
	return int64(*p)
}

func nullableString(p *string) any {
	if p == nil {
		return nil
	}
	return *p
}

// isUniqueViolation reports whether err is SQLite refusing a duplicate key.
// The driver's error type is matched structurally rather than by name so this
// survives a driver swap, with a message check as a last resort.
func isUniqueViolation(err error) bool {
	var coded interface{ Code() int }
	if errors.As(err, &coded) {
		switch coded.Code() {
		case sqliteConstraintUnique, sqliteConstraintPrimaryKey:
			return true
		}
	}
	return strings.Contains(err.Error(), "UNIQUE constraint failed")
}
