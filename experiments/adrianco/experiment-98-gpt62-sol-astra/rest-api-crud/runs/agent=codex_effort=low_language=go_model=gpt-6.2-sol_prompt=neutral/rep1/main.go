package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type book struct {
	ID int64 `json:"id"`
	bookInput
}

type api struct {
	db *sql.DB
}

func openDB(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL
	)`)
	if err != nil {
		db.Close()
		return nil, err
	}
	return db, nil
}

func main() {
	path := os.Getenv("BOOKS_DB")
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
	server := &http.Server{
		Addr: addr, Handler: newHandler(db),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      15 * time.Second,
	}
	log.Printf("Listening on %s", addr)
	log.Print(server.ListenAndServe())
}

func newHandler(db *sql.DB) http.Handler {
	a := api{db: db}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", a.health)
	mux.HandleFunc("POST /books", a.create)
	mux.HandleFunc("GET /books", a.list)
	mux.HandleFunc("GET /books/{id}", a.get)
	mux.HandleFunc("PUT /books/{id}", a.update)
	mux.HandleFunc("DELETE /books/{id}", a.delete)
	mux.HandleFunc("/health", methodNotAllowed("GET, HEAD"))
	mux.HandleFunc("/books", methodNotAllowed("GET, HEAD, POST"))
	mux.HandleFunc("/books/{id}", methodNotAllowed("GET, HEAD, PUT, DELETE"))
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		writeError(w, http.StatusNotFound, "route not found")
	})
	return mux
}

func methodNotAllowed(allow string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{"error": message})
}

func databaseError(w http.ResponseWriter, err error) {
	log.Printf("database error: %v", err)
	writeError(w, http.StatusInternalServerError, "database operation failed")
}

func readBook(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var input bookInput
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	decoder := json.NewDecoder(r.Body)
	err := decoder.Decode(&input)
	if err == nil {
		var extra json.RawMessage
		err = decoder.Decode(&extra)
		if errors.Is(err, io.EOF) {
			if strings.TrimSpace(input.Title) == "" || strings.TrimSpace(input.Author) == "" {
				writeError(w, http.StatusBadRequest, "title and author are required")
				return bookInput{}, false
			}
			return input, true
		}
	}
	var tooLarge *http.MaxBytesError
	if errors.As(err, &tooLarge) {
		writeError(w, http.StatusRequestEntityTooLarge, "request body exceeds 1 MiB")
	} else {
		writeError(w, http.StatusBadRequest, "request body must contain one valid book object")
	}
	return bookInput{}, false
}

func readID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id <= 0 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

func (a api) health(w http.ResponseWriter, r *http.Request) {
	if err := a.db.PingContext(r.Context()); err != nil {
		writeError(w, http.StatusServiceUnavailable, "database unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a api) create(w http.ResponseWriter, r *http.Request) {
	input, ok := readBook(w, r)
	if !ok {
		return
	}
	var id int64
	err := a.db.QueryRowContext(r.Context(),
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?) RETURNING id",
		input.Title, input.Author, input.Year, input.ISBN).Scan(&id)
	if err != nil {
		databaseError(w, err)
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(id, 10))
	writeJSON(w, http.StatusCreated, book{ID: id, bookInput: input})
}

func (a api) list(w http.ResponseWriter, r *http.Request) {
	query := "SELECT id, title, author, year, isbn FROM books"
	var args []any
	if author := r.URL.Query().Get("author"); author != "" {
		query += " WHERE author = ?"
		args = append(args, author)
	}
	rows, err := a.db.QueryContext(r.Context(), query+" ORDER BY id", args...)
	if err != nil {
		databaseError(w, err)
		return
	}
	defer rows.Close()
	books := make([]book, 0)
	for rows.Next() {
		var b book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			databaseError(w, err)
			return
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		databaseError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (a api) get(w http.ResponseWriter, r *http.Request) {
	id, ok := readID(w, r)
	if !ok {
		return
	}
	b := book{ID: id}
	err := a.db.QueryRowContext(r.Context(),
		"SELECT title, author, year, isbn FROM books WHERE id = ?", id).
		Scan(&b.Title, &b.Author, &b.Year, &b.ISBN)
	if checkBookResult(w, err) {
		writeJSON(w, http.StatusOK, b)
	}
}

func (a api) update(w http.ResponseWriter, r *http.Request) {
	id, ok := readID(w, r)
	if !ok {
		return
	}
	input, ok := readBook(w, r)
	if !ok {
		return
	}
	err := a.db.QueryRowContext(r.Context(),
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ? RETURNING id",
		input.Title, input.Author, input.Year, input.ISBN, id).Scan(&id)
	if checkBookResult(w, err) {
		writeJSON(w, http.StatusOK, book{ID: id, bookInput: input})
	}
}

func (a api) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := readID(w, r)
	if !ok {
		return
	}
	err := a.db.QueryRowContext(r.Context(), "DELETE FROM books WHERE id = ? RETURNING id", id).Scan(&id)
	if checkBookResult(w, err) {
		w.WriteHeader(http.StatusNoContent)
	}
}

func checkBookResult(w http.ResponseWriter, err error) bool {
	if errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusNotFound, "book not found")
	} else if err != nil {
		databaseError(w, err)
	}
	return err == nil
}
