package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"

	_ "modernc.org/sqlite"
)

type book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type server struct{ db *sql.DB }

func openDB(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	// A single connection also makes in-memory databases consistent across requests.
	db.SetMaxOpenConns(1)
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER NOT NULL, isbn TEXT NOT NULL)`)
	if err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

func (s *server) routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		if err := s.db.PingContext(r.Context()); err != nil {
			writeError(w, http.StatusServiceUnavailable, "database unavailable")
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /books", s.create)
	mux.HandleFunc("GET /books", s.list)
	mux.HandleFunc("GET /books/{id}", s.get)
	mux.HandleFunc("PUT /books/{id}", s.update)
	mux.HandleFunc("DELETE /books/{id}", s.delete)
	// Return JSON for unmatched routes and methods as well.
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, pattern := mux.Handler(r)
		if pattern == "" {
			writeError(w, http.StatusNotFound, "not found")
			return
		}
		mux.ServeHTTP(w, r)
	})
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}
func decodeBook(w http.ResponseWriter, r *http.Request) (book, bool) {
	var b book
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&b); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return b, false
	}
	var extra any
	if err := dec.Decode(&extra); err != io.EOF {
		writeError(w, http.StatusBadRequest, "invalid JSON body")
		return b, false
	}
	b.Title = strings.TrimSpace(b.Title)
	b.Author = strings.TrimSpace(b.Author)
	if b.Title == "" || b.Author == "" {
		writeError(w, http.StatusBadRequest, "title and author are required")
		return b, false
	}
	return b, true
}
func idFromRequest(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "invalid book id")
		return 0, false
	}
	return id, true
}
func (s *server) create(w http.ResponseWriter, r *http.Request) {
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	result, err := s.db.ExecContext(r.Context(), `INSERT INTO books(title, author, year, isbn) VALUES(?,?,?,?)`, b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		writeError(w, 500, "database error")
		return
	}
	b.ID, err = result.LastInsertId()
	if err != nil {
		writeError(w, 500, "database error")
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", b.ID))
	writeJSON(w, 201, b)
}
func (s *server) list(w http.ResponseWriter, r *http.Request) {
	query := `SELECT id,title,author,year,isbn FROM books`
	var args []any
	if author := r.URL.Query().Get("author"); author != "" {
		query += ` WHERE author = ?`
		args = append(args, author)
	}
	query += ` ORDER BY id`
	rows, err := s.db.QueryContext(r.Context(), query, args...)
	if err != nil {
		writeError(w, 500, "database error")
		return
	}
	defer rows.Close()
	books := make([]book, 0)
	for rows.Next() {
		var b book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			writeError(w, 500, "database error")
			return
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		writeError(w, 500, "database error")
		return
	}
	writeJSON(w, 200, books)
}
func (s *server) get(w http.ResponseWriter, r *http.Request) {
	id, ok := idFromRequest(w, r)
	if !ok {
		return
	}
	var b book
	err := s.db.QueryRowContext(r.Context(), `SELECT id,title,author,year,isbn FROM books WHERE id = ?`, id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		writeError(w, 404, "book not found")
		return
	}
	if err != nil {
		writeError(w, 500, "database error")
		return
	}
	writeJSON(w, 200, b)
}
func (s *server) update(w http.ResponseWriter, r *http.Request) {
	id, ok := idFromRequest(w, r)
	if !ok {
		return
	}
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	result, err := s.db.ExecContext(r.Context(), `UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?`, b.Title, b.Author, b.Year, b.ISBN, id)
	if err != nil {
		writeError(w, 500, "database error")
		return
	}
	n, err := result.RowsAffected()
	if err != nil {
		writeError(w, 500, "database error")
		return
	}
	if n == 0 {
		writeError(w, 404, "book not found")
		return
	}
	b.ID = id
	writeJSON(w, 200, b)
}
func (s *server) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := idFromRequest(w, r)
	if !ok {
		return
	}
	result, err := s.db.ExecContext(r.Context(), `DELETE FROM books WHERE id=?`, id)
	if err != nil {
		writeError(w, 500, "database error")
		return
	}
	n, err := result.RowsAffected()
	if err != nil {
		writeError(w, 500, "database error")
		return
	}
	if n == 0 {
		writeError(w, 404, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
func main() {
	path := os.Getenv("DB_PATH")
	if path == "" {
		path = "books.db"
	}
	db, err := openDB(path)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}
	log.Printf("listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, (&server{db}).routes()))
}
