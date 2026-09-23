package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"

	_ "modernc.org/sqlite"
)

type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

type Server struct{ db *sql.DB }

func OpenDB(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL, author TEXT NOT NULL,
		year INTEGER, isbn TEXT)`)
	return db, err
}

func NewServer(db *sql.DB) http.Handler {
	s := &Server{db: db}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		if err := s.db.Ping(); err != nil {
			writeJSON(w, 503, map[string]string{"status": "unhealthy"})
			return
		}
		writeJSON(w, 200, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /books", s.create)
	mux.HandleFunc("GET /books", s.list)
	mux.HandleFunc("GET /books/{id}", s.get)
	mux.HandleFunc("PUT /books/{id}", s.update)
	mux.HandleFunc("DELETE /books/{id}", s.delete)
	return mux
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}

func decodeBook(w http.ResponseWriter, r *http.Request) (*Book, bool) {
	var b Book
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20))
	if err := dec.Decode(&b); err != nil {
		writeErr(w, 400, "invalid JSON body")
		return nil, false
	}
	b.Title, b.Author, b.ISBN = strings.TrimSpace(b.Title), strings.TrimSpace(b.Author), strings.TrimSpace(b.ISBN)
	var errs []string
	if b.Title == "" {
		errs = append(errs, "title is required")
	}
	if b.Author == "" {
		errs = append(errs, "author is required")
	}
	if b.Year < 0 || b.Year > 9999 {
		errs = append(errs, "year must be between 0 and 9999")
	}
	if len(errs) > 0 {
		writeJSON(w, 400, map[string]any{"error": "validation failed", "details": errs})
		return nil, false
	}
	return &b, true
}

func pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeErr(w, 400, "invalid id")
		return 0, false
	}
	return id, true
}

func (s *Server) create(w http.ResponseWriter, r *http.Request) {
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	res, err := s.db.Exec(`INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)`, b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		writeErr(w, 500, "database error")
		return
	}
	b.ID, _ = res.LastInsertId()
	writeJSON(w, 201, b)
}

func (s *Server) list(w http.ResponseWriter, r *http.Request) {
	q := `SELECT id,title,author,COALESCE(year,0),COALESCE(isbn,'') FROM books`
	var args []any
	if a := r.URL.Query().Get("author"); a != "" {
		q += ` WHERE author = ? COLLATE NOCASE`
		args = append(args, a)
	}
	rows, err := s.db.Query(q+` ORDER BY id`, args...)
	if err != nil {
		writeErr(w, 500, "database error")
		return
	}
	defer rows.Close()
	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			writeErr(w, 500, "database error")
			return
		}
		books = append(books, b)
	}
	writeJSON(w, 200, books)
}

func (s *Server) get(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	var b Book
	err := s.db.QueryRow(`SELECT id,title,author,COALESCE(year,0),COALESCE(isbn,'') FROM books WHERE id=?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		writeErr(w, 404, "book not found")
		return
	} else if err != nil {
		writeErr(w, 500, "database error")
		return
	}
	writeJSON(w, 200, b)
}

func (s *Server) update(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	b, ok := decodeBook(w, r)
	if !ok {
		return
	}
	res, err := s.db.Exec(`UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?`, b.Title, b.Author, b.Year, b.ISBN, id)
	if err != nil {
		writeErr(w, 500, "database error")
		return
	}
	if n, _ := res.RowsAffected(); n == 0 {
		writeErr(w, 404, "book not found")
		return
	}
	b.ID = id
	writeJSON(w, 200, b)
}

func (s *Server) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := pathID(w, r)
	if !ok {
		return
	}
	res, err := s.db.Exec(`DELETE FROM books WHERE id=?`, id)
	if err != nil {
		writeErr(w, 500, "database error")
		return
	}
	if n, _ := res.RowsAffected(); n == 0 {
		writeErr(w, 404, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func main() {
	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "books.db"
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	db, err := OpenDB(dbPath)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	log.Printf("listening on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, NewServer(db)))
}
