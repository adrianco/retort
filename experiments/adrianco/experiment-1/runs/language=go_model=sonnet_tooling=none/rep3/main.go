package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

type App struct {
	db *sql.DB
}

func NewApp(dsn string) (*App, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		return nil, err
	}
	app := &App{db: db}
	if err := app.initDB(); err != nil {
		return nil, err
	}
	return app, nil
}

func (a *App) initDB() error {
	_, err := a.db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id     INTEGER PRIMARY KEY AUTOINCREMENT,
		title  TEXT NOT NULL,
		author TEXT NOT NULL,
		year   INTEGER,
		isbn   TEXT
	)`)
	return err
}

func (a *App) Close() error {
	return a.db.Close()
}

// writeJSON writes a JSON response with the given status code.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

// ServeHTTP routes requests.
func (a *App) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path

	switch {
	case path == "/health":
		a.handleHealth(w, r)
	case path == "/books" || path == "/books/":
		switch r.Method {
		case http.MethodGet:
			a.listBooks(w, r)
		case http.MethodPost:
			a.createBook(w, r)
		default:
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		}
	case strings.HasPrefix(path, "/books/"):
		idStr := strings.TrimPrefix(path, "/books/")
		id, err := strconv.Atoi(idStr)
		if err != nil || id <= 0 {
			writeError(w, http.StatusBadRequest, "invalid book id")
			return
		}
		switch r.Method {
		case http.MethodGet:
			a.getBook(w, r, id)
		case http.MethodPut:
			a.updateBook(w, r, id)
		case http.MethodDelete:
			a.deleteBook(w, r, id)
		default:
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		}
	default:
		writeError(w, http.StatusNotFound, "not found")
	}
}

func (a *App) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *App) listBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")

	var (
		rows *sql.Rows
		err  error
	)
	if author != "" {
		rows, err = a.db.Query(`SELECT id, title, author, year, isbn FROM books WHERE author = ?`, author)
	} else {
		rows, err = a.db.Query(`SELECT id, title, author, year, isbn FROM books`)
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to query books")
		return
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			writeError(w, http.StatusInternalServerError, "failed to scan book")
			return
		}
		books = append(books, b)
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *App) createBook(w http.ResponseWriter, r *http.Request) {
	var b Book
	if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}
	if strings.TrimSpace(b.Title) == "" {
		writeError(w, http.StatusBadRequest, "title is required")
		return
	}
	if strings.TrimSpace(b.Author) == "" {
		writeError(w, http.StatusBadRequest, "author is required")
		return
	}

	res, err := a.db.Exec(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}
	id, _ := res.LastInsertId()
	b.ID = int(id)
	writeJSON(w, http.StatusCreated, b)
}

func (a *App) getBook(w http.ResponseWriter, r *http.Request, id int) {
	var b Book
	err := a.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err == sql.ErrNoRows {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to get book")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *App) updateBook(w http.ResponseWriter, r *http.Request, id int) {
	// Check existence first.
	var exists int
	err := a.db.QueryRow(`SELECT COUNT(*) FROM books WHERE id = ?`, id).Scan(&exists)
	if err != nil || exists == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	var b Book
	if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}
	if strings.TrimSpace(b.Title) == "" {
		writeError(w, http.StatusBadRequest, "title is required")
		return
	}
	if strings.TrimSpace(b.Author) == "" {
		writeError(w, http.StatusBadRequest, "author is required")
		return
	}

	_, err = a.db.Exec(`UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?`,
		b.Title, b.Author, b.Year, b.ISBN, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}
	b.ID = id
	writeJSON(w, http.StatusOK, b)
}

func (a *App) deleteBook(w http.ResponseWriter, r *http.Request, id int) {
	res, err := a.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to delete book")
		return
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func main() {
	app, err := NewApp("books.db")
	if err != nil {
		log.Fatalf("failed to initialize app: %v", err)
	}
	defer app.Close()

	srv := &http.Server{
		Addr:         ":8080",
		Handler:      app,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	fmt.Println("Listening on :8080")
	log.Fatal(srv.ListenAndServe())
}
