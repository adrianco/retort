package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/url"
	"strings"
	"time"

	"modernc.org/sqlite"
	sqlite3 "modernc.org/sqlite/lib"
)

var (
	// ErrNotFound is returned when no book has the requested ID.
	ErrNotFound = errors.New("book not found")
	// ErrISBNTaken is returned when a write would duplicate an ISBN that
	// another book already carries.
	ErrISBNTaken = errors.New("isbn already in use")
)

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id         INTEGER PRIMARY KEY AUTOINCREMENT,
	title      TEXT    NOT NULL,
	author     TEXT    NOT NULL,
	year       INTEGER,
	isbn       TEXT    UNIQUE,
	created_at TEXT    NOT NULL,
	updated_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS books_author_nocase ON books (author COLLATE NOCASE);
`

// columns is shared by every read so the scan order can never drift from the
// select list.
const columns = `id, title, author, year, isbn, created_at, updated_at`

// timeLayout stores timestamps as sortable UTC text. Nanosecond precision
// keeps updated_at strictly increasing even for updates issued back to back.
const timeLayout = "2006-01-02T15:04:05.000000000Z"

// Store is the SQLite-backed persistence layer for the collection.
type Store struct {
	db *sql.DB
	// now is injectable so tests can pin timestamps.
	now func() time.Time
}

// OpenStore opens (creating if needed) the database at path and applies the
// schema. The path may be a filename or ":memory:" for an ephemeral database.
func OpenStore(ctx context.Context, path string) (*Store, error) {
	inMemory := isMemoryPath(path)

	db, err := sql.Open("sqlite", buildDSN(path, inMemory))
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", path, err)
	}

	if inMemory {
		// Each pooled connection to ":memory:" would get its own private
		// database, so an in-memory store must be single-connection.
		db.SetMaxOpenConns(1)
	} else {
		// WAL lets readers proceed during a write; the cap plus the busy
		// timeout below keeps the writer contention bounded.
		db.SetMaxOpenConns(8)
	}
	db.SetMaxIdleConns(2)
	db.SetConnMaxIdleTime(5 * time.Minute)

	if err := db.PingContext(ctx); err != nil {
		db.Close()
		return nil, fmt.Errorf("connect %s: %w", path, err)
	}
	if _, err := db.ExecContext(ctx, schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema: %w", err)
	}

	return &Store{db: db, now: time.Now}, nil
}

// isMemoryPath reports whether path names an in-memory database, in any of the
// spellings SQLite accepts (":memory:", "file::memory:", "?mode=memory").
func isMemoryPath(path string) bool {
	return strings.Contains(path, ":memory:") || strings.Contains(path, "mode=memory")
}

func buildDSN(path string, inMemory bool) string {
	pragmas := []string{"busy_timeout(5000)", "foreign_keys(1)"}
	if !inMemory {
		// journal_mode is persisted in the file, so it is pointless (and
		// unsupported) for an in-memory database.
		pragmas = append(pragmas, "journal_mode(WAL)", "synchronous(NORMAL)")
	}

	q := url.Values{}
	for _, p := range pragmas {
		q.Add("_pragma", p)
	}

	// The path may already carry driver options (`file:books.db?_txlock=...`),
	// in which case these are appended rather than starting a second query.
	sep := "?"
	if strings.Contains(path, "?") {
		sep = "&"
	}
	return path + sep + q.Encode()
}

// Close releases the underlying connection pool.
func (s *Store) Close() error { return s.db.Close() }

// Ping verifies the database is reachable; it backs the health endpoint.
func (s *Store) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

// ListFilter narrows the result of List. A zero ListFilter selects every book.
type ListFilter struct {
	// Author, when set, matches the whole author field case-insensitively.
	Author string
}

// Create inserts b and returns it with the assigned ID and timestamps.
func (s *Store) Create(ctx context.Context, b Book) (Book, error) {
	// UTC also strips the monotonic reading, so the value formats and
	// compares consistently.
	now := s.now().UTC()
	ts := now.Format(timeLayout)

	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)`,
		b.Title, b.Author, nullYear(b.Year), nullISBN(b.ISBN), ts, ts)
	if err != nil {
		if isUniqueViolation(err) {
			return Book{}, ErrISBNTaken
		}
		return Book{}, fmt.Errorf("insert book: %w", err)
	}

	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}

	b.ID = id
	b.CreatedAt = now
	b.UpdatedAt = now
	return b, nil
}

// List returns the books matching f, oldest first.
func (s *Store) List(ctx context.Context, f ListFilter) ([]Book, error) {
	query := `SELECT ` + columns + ` FROM books`
	var args []any
	if f.Author != "" {
		// NOCASE matches the index declared on the same expression.
		query += ` WHERE author = ? COLLATE NOCASE`
		args = append(args, f.Author)
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list books: %w", err)
	}
	defer rows.Close()

	// Never nil: the handler encodes this directly and `[]` is a friendlier
	// empty result than `null`.
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
	b, err := scanBook(s.db.QueryRowContext(ctx, `SELECT `+columns+` FROM books WHERE id = ?`, id))
	switch {
	case errors.Is(err, sql.ErrNoRows):
		return Book{}, ErrNotFound
	case err != nil:
		return Book{}, fmt.Errorf("get book %d: %w", id, err)
	}
	return b, nil
}

// Update replaces every client-supplied field of the book with the given ID.
// created_at is preserved and updated_at is advanced. It returns ErrNotFound
// if the book does not exist, or ErrISBNTaken if another book already has the
// new ISBN.
func (s *Store) Update(ctx context.Context, id int64, b Book) (Book, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	// Rollback after a successful Commit is a no-op, so this needs no flag.
	defer tx.Rollback()

	// Read created_at inside the transaction: it doubles as the existence
	// check and as the value the response must echo back.
	var createdAt string
	err = tx.QueryRowContext(ctx, `SELECT created_at FROM books WHERE id = ?`, id).Scan(&createdAt)
	switch {
	case errors.Is(err, sql.ErrNoRows):
		return Book{}, ErrNotFound
	case err != nil:
		return Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	created, err := time.Parse(timeLayout, createdAt)
	if err != nil {
		return Book{}, fmt.Errorf("update book %d: parse created_at: %w", id, err)
	}

	now := s.now().UTC()
	if _, err := tx.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?`,
		b.Title, b.Author, nullYear(b.Year), nullISBN(b.ISBN), now.Format(timeLayout), id); err != nil {
		if isUniqueViolation(err) {
			return Book{}, ErrISBNTaken
		}
		return Book{}, fmt.Errorf("update book %d: %w", id, err)
	}
	if err := tx.Commit(); err != nil {
		return Book{}, fmt.Errorf("update book %d: %w", id, err)
	}

	b.ID = id
	b.CreatedAt = created
	b.UpdatedAt = now
	return b, nil
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

// rowScanner is satisfied by both *sql.Row and *sql.Rows.
type rowScanner interface {
	Scan(dest ...any) error
}

func scanBook(row rowScanner) (Book, error) {
	var (
		b       Book
		year    sql.NullInt64
		isbn    sql.NullString
		created string
		updated string
	)
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &year, &isbn, &created, &updated); err != nil {
		return Book{}, err
	}
	if year.Valid {
		y := int(year.Int64)
		b.Year = &y
	}
	b.ISBN = isbn.String

	var err error
	if b.CreatedAt, err = time.Parse(timeLayout, created); err != nil {
		return Book{}, fmt.Errorf("parse created_at %q: %w", created, err)
	}
	if b.UpdatedAt, err = time.Parse(timeLayout, updated); err != nil {
		return Book{}, fmt.Errorf("parse updated_at %q: %w", updated, err)
	}
	return b, nil
}

func nullYear(year *int) any {
	if year == nil {
		return nil
	}
	return *year
}

// nullISBN maps an absent ISBN to NULL rather than "". SQLite's UNIQUE index
// ignores NULLs, so any number of books may have no ISBN while the ones that
// do stay unique.
func nullISBN(isbn string) any {
	if isbn == "" {
		return nil
	}
	return isbn
}

// isUniqueViolation reports whether err is the UNIQUE constraint on
// books.isbn, the only unique index a client request can collide with. The
// driver enables extended result codes when it opens a connection, so the
// specific constraint kind is available rather than a bare SQLITE_CONSTRAINT.
// TestCreateDuplicateISBN pins this mapping.
func isUniqueViolation(err error) bool {
	var serr *sqlite.Error
	if !errors.As(err, &serr) {
		return false
	}
	return serr.Code() == sqlite3.SQLITE_CONSTRAINT_UNIQUE
}
