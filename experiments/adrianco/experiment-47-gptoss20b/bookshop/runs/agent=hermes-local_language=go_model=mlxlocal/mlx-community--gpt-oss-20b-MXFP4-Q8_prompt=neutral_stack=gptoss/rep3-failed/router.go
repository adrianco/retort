package main

import (
    "database/sql"
    "encoding/json"
    "net/http"
    "strconv"
    "strings"

    "github.com/go-chi/chi/v5"
)

// Book represents a book record.
type Book struct {
    ID     int64  `json:"id"`
    Title  string `json:"title"`
    Author string `json:"author"`
    Year   int    `json:"year,omitempty"`
    ISBN   string `json:"isbn,omitempty"`
}

func NewRouter() http.Handler {
    r := chi.NewRouter()

    r.Get("/health", healthHandler)

    r.Route("/books", func(r chi.Router) {
        r.Get("/", listBooksHandler)
        r.Post("/", createBookHandler)
        r.Get("/{id}", getBookHandler)
        r.Put("/{id}", updateBookHandler)
        r.Delete("/{id}", deleteBookHandler)
    })
    return r
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func createBookHandler(w http.ResponseWriter, r *http.Request) {
    var b Book
    if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
        http.Error(w, "invalid json", http.StatusBadRequest)
        return
    }
    if strings.TrimSpace(b.Title) == "" || strings.TrimSpace(b.Author) == "" {
        http.Error(w, "title and author required", http.StatusBadRequest)
        return
    }
    db := getDB()
    res, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", b.Title, b.Author, b.Year, b.ISBN)
    if err != nil {
        http.Error(w, "db error", http.StatusInternalServerError)
        return
    }
    id, _ := res.LastInsertId()
    b.ID = id
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(b)
}

func listBooksHandler(w http.ResponseWriter, r *http.Request) {
    author := r.URL.Query().Get("author")
    db := getDB()
    var rows *sql.Rows
    var err error
    if author != "" {
        rows, err = db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", author)
    } else {
        rows, err = db.Query("SELECT id, title, author, year, isbn FROM books")
    }
    if err != nil {
        http.Error(w, "db error", http.StatusInternalServerError)
        return
    }
    defer rows.Close()
    books := []Book{}
    for rows.Next() {
        var b Book
        if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
            continue
        }
        books = append(books, b)
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(books)
}

func getBookHandler(w http.ResponseWriter, r *http.Request) {
    idStr := chi.URLParam(r, "id")
    id, err := strconv.ParseInt(idStr, 10, 64)
    if err != nil {
        http.Error(w, "invalid id", http.StatusBadRequest)
        return
    }
    db := getDB()
    row := db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id)
    var b Book
    if err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
        http.Error(w, "not found", http.StatusNotFound)
        return
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(b)
}

func updateBookHandler(w http.ResponseWriter, r *http.Request) {
    idStr := chi.URLParam(r, "id")
    id, err := strconv.ParseInt(idStr, 10, 64)
    if err != nil {
        http.Error(w, "invalid id", http.StatusBadRequest)
        return
    }
    var b Book
    if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
        http.Error(w, "invalid json", http.StatusBadRequest)
        return
    }
    if strings.TrimSpace(b.Title) == "" || strings.TrimSpace(b.Author) == "" {
        http.Error(w, "title and author required", http.StatusBadRequest)
        return
    }
    db := getDB()
    res, err := db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", b.Title, b.Author, b.Year, b.ISBN, id)
    if err != nil {
        http.Error(w, "db error", http.StatusInternalServerError)
        return
    }
    if rows, _ := res.RowsAffected(); rows == 0 {
        http.Error(w, "not found", http.StatusNotFound)
        return
    }
    b.ID = id
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(b)
}

func deleteBookHandler(w http.ResponseWriter, r *http.Request) {
    idStr := chi.URLParam(r, "id")
    id, err := strconv.ParseInt(idStr, 10, 64)
    if err != nil {
        http.Error(w, "invalid id", http.StatusBadRequest)
        return
    }
    db := getDB()
    res, err := db.Exec("DELETE FROM books WHERE id = ?", id)
    if err != nil {
        http.Error(w, "db error", http.StatusInternalServerError)
        return
    }
    if rows, _ := res.RowsAffected(); rows == 0 {
        http.Error(w, "not found", http.StatusNotFound)
        return
    }
    w.WriteHeader(http.StatusNoContent)
}

