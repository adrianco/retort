package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
)

// Book is the JSON representation of a book. Year and ISBN are optional.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year,omitempty"`
	ISBN   string `json:"isbn,omitempty"`
}

// bookInput is the request body for POST /books and PUT /books/{id}.
type bookInput struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   *int   `json:"year"`
	ISBN   string `json:"isbn"`
}

type errorResponse struct {
	Error string `json:"error"`
}

type handler struct {
	db *sql.DB
}

// NewHandler builds the HTTP handler with all routes wired up.
func NewHandler(db *sql.DB) http.Handler {
	h := &handler{db: db}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", h.health)
	mux.HandleFunc("GET /", h.root)
	mux.HandleFunc("POST /books", h.create)
	mux.HandleFunc("GET /books", h.list)
	mux.HandleFunc("GET /books/{id}", h.get)
	mux.HandleFunc("PUT /books/{id}", h.update)
	mux.HandleFunc("DELETE /books/{id}", h.delete)
	return mux
}

func (h *handler) health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *handler) root(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"service": "book-api",
		"endpoints": []string{
			"GET /health",
			"POST /books",
			"GET /books",
			"GET /books/{id}",
			"PUT /books/{id}",
			"DELETE /books/{id}",
		},
	})
}

func (h *handler) create(w http.ResponseWriter, r *http.Request) {
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}

	res, err := h.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		in.Title, in.Author, in.Year, in.ISBN,
	)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}
	id, err := res.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}

	book, err := getBook(h.db, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to read created book")
		return
	}
	w.Header().Set("Location", "/books/"+strconv.FormatInt(id, 10))
	writeJSON(w, http.StatusCreated, book)
}

func (h *handler) list(w http.ResponseWriter, r *http.Request) {
	query := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author := strings.TrimSpace(r.URL.Query().Get("author")); author != "" {
		query += ` WHERE lower(author) = lower(?)`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := h.db.Query(query, args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to list books")
		return
	}
	defer rows.Close()

	books := make([]Book, 0)
	for rows.Next() {
		b, err := scanBook(rows)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "failed to list books")
			return
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		writeError(w, http.StatusInternalServerError, "failed to list books")
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (h *handler) get(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	book, err := getBook(h.db, id)
	if errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to get book")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (h *handler) update(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := decodeBookInput(w, r)
	if !ok {
		return
	}

	res, err := h.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		in.Title, in.Author, in.Year, in.ISBN, id,
	)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}
	if n, _ := res.RowsAffected(); n == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	book, err := getBook(h.db, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (h *handler) delete(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	res, err := h.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to delete book")
		return
	}
	if n, _ := res.RowsAffected(); n == 0 {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// decodeBookInput reads and validates the JSON request body.
// It reports the error to the client and returns ok=false on failure.
func decodeBookInput(w http.ResponseWriter, r *http.Request) (bookInput, bool) {
	var in bookInput
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+err.Error())
		return in, false
	}
	if msg := validateBookInput(&in); msg != "" {
		writeError(w, http.StatusBadRequest, msg)
		return in, false
	}
	return in, true
}

// validateBookInput returns an error message, or "" if the input is valid.
func validateBookInput(in *bookInput) string {
	if strings.TrimSpace(in.Title) == "" {
		return "title is required"
	}
	if strings.TrimSpace(in.Author) == "" {
		return "author is required"
	}
	if in.Year != nil && (*in.Year < 1 || *in.Year > 9999) {
		return "year must be between 1 and 9999"
	}
	if len(strings.TrimSpace(in.ISBN)) > 32 {
		return "isbn must be at most 32 characters"
	}
	return ""
}

// parseID extracts and validates the {id} path parameter.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "id must be a positive integer")
		return 0, false
	}
	return id, true
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		// Response headers already sent; nothing more we can do.
		_ = err
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errorResponse{Error: msg})
}
