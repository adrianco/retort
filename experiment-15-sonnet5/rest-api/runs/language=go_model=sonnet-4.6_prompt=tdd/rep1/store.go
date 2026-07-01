package main

import (
	"database/sql"
	"errors"
	"fmt"

	_ "modernc.org/sqlite"
)

var errNotFound = errors.New("not found")

type store interface {
	create(b Book) (Book, error)
	list(author string) ([]Book, error)
	get(id int64) (Book, error)
	update(id int64, b Book) (Book, error)
	delete(id int64) error
	close() error
}

type sqliteStore struct {
	db *sql.DB
}

func newSQLiteStore(dsn string) (*sqliteStore, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	if _, err := db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id     INTEGER PRIMARY KEY AUTOINCREMENT,
		title  TEXT NOT NULL,
		author TEXT NOT NULL,
		year   INTEGER,
		isbn   TEXT
	)`); err != nil {
		db.Close()
		return nil, fmt.Errorf("create table: %w", err)
	}
	return &sqliteStore{db: db}, nil
}

func (s *sqliteStore) create(b Book) (Book, error) {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN,
	)
	if err != nil {
		return Book{}, err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Book{}, err
	}
	b.ID = id
	return b, nil
}

func (s *sqliteStore) list(author string) ([]Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if author != "" {
		rows, err = s.db.Query(
			`SELECT id, title, author, year, isbn FROM books WHERE author = ?`, author)
	} else {
		rows, err = s.db.Query(`SELECT id, title, author, year, isbn FROM books`)
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	if books == nil {
		books = []Book{}
	}
	return books, rows.Err()
}

func (s *sqliteStore) get(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, errNotFound
	}
	return b, err
}

func (s *sqliteStore) update(id int64, b Book) (Book, error) {
	res, err := s.db.Exec(
		`UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?`,
		b.Title, b.Author, b.Year, b.ISBN, id,
	)
	if err != nil {
		return Book{}, err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return Book{}, err
	}
	if n == 0 {
		return Book{}, errNotFound
	}
	b.ID = id
	return b, nil
}

func (s *sqliteStore) delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return errNotFound
	}
	return nil
}

func (s *sqliteStore) close() error {
	return s.db.Close()
}
