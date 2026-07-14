package main

import (
	"database/sql"
	"errors"
	"fmt"

	_ "modernc.org/sqlite"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

var ErrNotFound = errors.New("book not found")

type Store struct {
	db *sql.DB
}

func OpenStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	s := &Store{db: db}
	if err := s.init(); err != nil {
		_ = db.Close()
		return nil, err
	}
	return s, nil
}

func (s *Store) Close() error {
	return s.db.Close()
}

func (s *Store) init() error {
	_, err := s.db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id     INTEGER PRIMARY KEY AUTOINCREMENT,
			title  TEXT NOT NULL,
			author TEXT NOT NULL,
			year   INTEGER NOT NULL DEFAULT 0,
			isbn   TEXT NOT NULL DEFAULT ''
		)
	`)
	return err
}

func (s *Store) Create(b *Book) error {
	res, err := s.db.Exec(
		`INSERT INTO books(title, author, year, isbn) VALUES(?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN,
	)
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

func (s *Store) Get(id int64) (*Book, error) {
	row := s.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id)
	var b Book
	if err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, ErrNotFound
		}
		return nil, err
	}
	return &b, nil
}

func (s *Store) List(authorFilter string) ([]Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if authorFilter != "" {
		rows, err = s.db.Query(
			`SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id`,
			authorFilter,
		)
	} else {
		rows, err = s.db.Query(`SELECT id, title, author, year, isbn FROM books ORDER BY id`)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	books := make([]Book, 0)
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

func (s *Store) Update(b *Book) error {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, b.ID,
	)
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
