package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"

	_ "modernc.org/sqlite" // pure-Go SQLite driver (no cgo required)
)

// ErrNotFound is returned when a book with the requested ID does not exist.
var ErrNotFound = errors.New("book not found")

// Book is the persisted representation of a book.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year"`
	ISBN   string `json:"isbn"`
}

// Store is the persistence interface used by the HTTP handlers.
type Store interface {
	Create(ctx context.Context, b Book) (Book, error)
	List(ctx context.Context, author string) ([]Book, error)
	Get(ctx context.Context, id int64) (Book, error)
	Update(ctx context.Context, b Book) (Book, error)
	Delete(ctx context.Context, id int64) error
	Ping(ctx context.Context) error
	Close() error
}

// SQLiteStore implements Store on top of an SQLite database.
type SQLiteStore struct {
	db *sql.DB
}

const schema = `
CREATE TABLE IF NOT EXISTS books (
	id     INTEGER PRIMARY KEY AUTOINCREMENT,
	title  TEXT    NOT NULL,
	author TEXT    NOT NULL,
	year   INTEGER,
	isbn   TEXT    NOT NULL DEFAULT ''
);
`

// OpenSQLiteStore opens (creating if necessary) the SQLite database at path
// and ensures the schema exists.
func OpenSQLiteStore(path string) (*SQLiteStore, error) {
	dsn := fmt.Sprintf("file:%s?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)&_pragma=foreign_keys(1)", path)
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	// SQLite permits a single writer; serialising through one connection
	// avoids SQLITE_BUSY errors under concurrent requests.
	db.SetMaxOpenConns(1)

	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema: %w", err)
	}
	return &SQLiteStore{db: db}, nil
}

func (s *SQLiteStore) Create(ctx context.Context, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, nullableInt(b.Year), b.ISBN)
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, fmt.Errorf("insert book: %w", err)
	}
	b.ID = id
	return b, nil
}

// List returns all books ordered by ID. If author is non-empty, only books
// whose author contains it (case-insensitive) are returned.
func (s *SQLiteStore) List(ctx context.Context, author string) ([]Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author != "" {
		query += ` WHERE author LIKE ? ESCAPE '\'`
		args = append(args, "%"+escapeLike(author)+"%")
	}
	query += ` ORDER BY id`

	rows, err := s.db.QueryContext(ctx, query, args...)
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

func (s *SQLiteStore) Get(ctx context.Context, id int64) (Book, error) {
	row := s.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id)
	b, err := scanBook(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	if err != nil {
		return Book{}, fmt.Errorf("get book: %w", err)
	}
	return b, nil
}

func (s *SQLiteStore) Update(ctx context.Context, b Book) (Book, error) {
	res, err := s.db.ExecContext(ctx,
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, nullableInt(b.Year), b.ISBN, b.ID)
	if err != nil {
		return Book{}, fmt.Errorf("update book: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, fmt.Errorf("update book: %w", err)
	}
	if n == 0 {
		return Book{}, ErrNotFound
	}
	return b, nil
}

func (s *SQLiteStore) Delete(ctx context.Context, id int64) error {
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

func (s *SQLiteStore) Ping(ctx context.Context) error { return s.db.PingContext(ctx) }

func (s *SQLiteStore) Close() error { return s.db.Close() }

type scanner interface {
	Scan(dest ...any) error
}

func scanBook(sc scanner) (Book, error) {
	var b Book
	var year sql.NullInt64
	if err := sc.Scan(&b.ID, &b.Title, &b.Author, &year, &b.ISBN); err != nil {
		return Book{}, err
	}
	if year.Valid {
		y := int(year.Int64)
		b.Year = &y
	}
	return b, nil
}

func nullableInt(p *int) any {
	if p == nil {
		return nil
	}
	return *p
}

// escapeLike escapes LIKE wildcards so user input is matched literally.
func escapeLike(s string) string {
	r := strings.NewReplacer(`\`, `\\`, `%`, `\%`, `_`, `\_`)
	return r.Replace(s)
}
