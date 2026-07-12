package main

import (
	"database/sql"
	"errors"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

type Database struct {
	path string
	db   *sql.DB
}

func NewDatabase(path string) (*Database, error) {
	db, err := sql.Open("sqlite3", path)
	if err != nil {
		return nil, err
	}

	return &Database{path: path, db: db}, nil
}

func (d *Database) Close() error {
	return d.db.Close()
}

func (d *Database) Init() error {
	query := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT UNIQUE
	);`

	_, err := d.db.Exec(query)
	return err
}

type bookRow struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type sqliteBookRepository struct {
	db *Database
}

func NewBookRepository(db *Database) BookRepository {
	return &sqliteBookRepository{db: db}
}

func (r *sqliteBookRepository) Create(book *Book) error {
	query := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`
	result, err := r.db.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		return err
	}

	id, err := result.LastInsertId()
	if err != nil {
		return err
	}

	book.ID = int(id)
	return nil
}

func (r *sqliteBookRepository) GetByID(id int) (*Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books WHERE id = ?`
	var row bookRow
	err := r.db.db.QueryRow(query, id).Scan(&row.ID, &row.Title, &row.Author, &row.Year, &row.ISBN)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, errors.New("book not found")
		}
		return nil, err
	}

	return &Book{
		ID:     row.ID,
		Title:  row.Title,
		Author: row.Author,
		Year:   row.Year,
		ISBN:   row.ISBN,
	}, nil
}

func (r *sqliteBookRepository) List(filters map[string]string) ([]*Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	var conditions []string
	var args []interface{}

	if author, ok := filters["author"]; ok && author != "" {
		conditions = append(conditions, "author LIKE ?")
		args = append(args, "%"+author+"%")
	}

	if len(conditions) > 0 {
		query += " WHERE " + strings.Join(conditions, " AND ")
	}

	rows, err := r.db.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []*Book
	for rows.Next() {
		var row bookRow
		if err := rows.Scan(&row.ID, &row.Title, &row.Author, &row.Year, &row.ISBN); err != nil {
			return nil, err
		}
		books = append(books, &Book{
			ID:     row.ID,
			Title:  row.Title,
			Author: row.Author,
			Year:   row.Year,
			ISBN:   row.ISBN,
		})
	}

	if err := rows.Err(); err != nil {
		return nil, err
	}

	return books, nil
}

func (r *sqliteBookRepository) Update(book *Book) error {
	query := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`
	_, err := r.db.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN, book.ID)
	if err != nil {
		return err
	}
	return nil
}

func (r *sqliteBookRepository) Delete(id int) error {
	query := `DELETE FROM books WHERE id = ?`
	_, err := r.db.db.Exec(query, id)
	if err != nil {
		return err
	}
	return nil
}
