package main

import (
	"database/sql"
	"errors"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned when a book does not exist.
var ErrNotFound = errors.New("book not found")

// Book is a record in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Store persists books in SQLite.
type Store struct {
	db *sql.DB
}

// OpenStore opens (and migrates) the database at dsn. Use ":memory:" for tests.
func OpenStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	// The in-memory database lives per-connection, so keep the pool at one.
	db.SetMaxOpenConns(1)
	const schema = `CREATE TABLE IF NOT EXISTS books (
		id     INTEGER PRIMARY KEY AUTOINCREMENT,
		title  TEXT NOT NULL,
		author TEXT NOT NULL,
		year   INTEGER NOT NULL DEFAULT 0,
		isbn   TEXT NOT NULL DEFAULT ''
	)`
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, err
	}
	return &Store{db: db}, nil
}

func (s *Store) Close() error { return s.db.Close() }

func (s *Store) Create(b *Book) error {
	res, err := s.db.Exec(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		return err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return err
	}
	b.ID = id
	return nil
}

// List returns all books, optionally filtered by exact author match.
func (s *Store) List(author string) ([]Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	args := []any{}
	if author != "" {
		query += ` WHERE author = ?`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

func (s *Store) Get(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	return b, err
}

func (s *Store) Update(id int64, b *Book) error {
	res, err := s.db.Exec(`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id)
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
	b.ID = id
	return nil
}

func (s *Store) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
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

// Ping verifies the database is reachable.
func (s *Store) Ping() error { return s.db.Ping() }
