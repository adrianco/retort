package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"strings"

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
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id     INTEGER PRIMARY KEY AUTOINCREMENT,
		title  TEXT NOT NULL,
		author TEXT NOT NULL,
		year   INTEGER,
		isbn   TEXT
	)`)
	if err != nil {
		return nil, err
	}
	return &App{db: db}, nil
}

func (a *App) Routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", a.handleHealth)
	mux.HandleFunc("POST /books", a.handleCreateBook)
	mux.HandleFunc("GET /books", a.handleListBooks)
	mux.HandleFunc("GET /books/{id}", a.handleGetBook)
	mux.HandleFunc("PUT /books/{id}", a.handleUpdateBook)
	mux.HandleFunc("DELETE /books/{id}", a.handleDeleteBook)
	return mux
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func (a *App) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *App) handleCreateBook(w http.ResponseWriter, r *http.Request) {
	var b Book
	if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	if b.Title == "" || b.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return
	}
	res, err := a.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, nullableInt(b.Year), nullableStr(b.ISBN),
	)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	id, _ := res.LastInsertId()
	b.ID = int(id)
	writeJSON(w, http.StatusCreated, b)
}

func (a *App) handleListBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	var (
		rows *sql.Rows
		err  error
	)
	if author != "" {
		rows, err = a.db.Query(
			`SELECT id, title, author, COALESCE(year,0), COALESCE(isbn,'') FROM books WHERE author = ?`,
			author,
		)
	} else {
		rows, err = a.db.Query(
			`SELECT id, title, author, COALESCE(year,0), COALESCE(isbn,'') FROM books`,
		)
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			writeError(w, http.StatusInternalServerError, "scan error")
			return
		}
		books = append(books, b)
	}
	writeJSON(w, http.StatusOK, books)
}

func (a *App) handleGetBook(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.Atoi(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid id")
		return
	}
	var b Book
	err = a.db.QueryRow(
		`SELECT id, title, author, COALESCE(year,0), COALESCE(isbn,'') FROM books WHERE id = ?`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	writeJSON(w, http.StatusOK, b)
}

func (a *App) handleUpdateBook(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.Atoi(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid id")
		return
	}
	var b Book
	if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	if b.Title == "" || b.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return
	}
	res, err := a.db.Exec(
		`UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?`,
		b.Title, b.Author, nullableInt(b.Year), nullableStr(b.ISBN), id,
	)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	b.ID = id
	writeJSON(w, http.StatusOK, b)
}

func (a *App) handleDeleteBook(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.Atoi(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid id")
		return
	}
	res, err := a.db.Exec(`DELETE FROM books WHERE id=?`, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "database error")
		return
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func nullableInt(v int) any {
	if v == 0 {
		return nil
	}
	return v
}

func nullableStr(v string) any {
	if v == "" {
		return nil
	}
	return v
}

func main() {
	app, err := NewApp("./books.db")
	if err != nil {
		log.Fatal(err)
	}
	log.Println("Listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", app.Routes()))
}
