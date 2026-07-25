package main

import (
    "database/sql"
    "encoding/json"
    "log"
    "net/http"
    "strconv"

    "github.com/gorilla/mux"
    _ "github.com/mattn/go-sqlite3"
)

var db *sql.DB

// Book represents a book record.
type Book struct {
    ID     int    `json:"id"`
    Title  string `json:"title"`
    Author string `json:"author"`
    Year   int    `json:"year,omitempty"`
    ISBN   string `json:"isbn,omitempty"`
}

func main() {
    var err error
    db, err = sql.Open("sqlite3", "file:books.db?cache=shared&mode=rwc")
    if err != nil {
        log.Fatalf("failed to open database: %v", err)
    }
    defer db.Close()

    if err := initDB(); err != nil {
        log.Fatalf("failed to init database: %v", err)
    }

    r := mux.NewRouter()
    r.HandleFunc("/health", healthHandler).Methods("GET")

    api := r.PathPrefix("/books").Subrouter()
    api.HandleFunc("", listBooksHandler).Methods("GET")
    api.HandleFunc("", createBookHandler).Methods("POST")
    api.HandleFunc("/{id}", getBookHandler).Methods("GET")
    api.HandleFunc("/{id}", updateBookHandler).Methods("PUT")
    api.HandleFunc("/{id}", deleteBookHandler).Methods("DELETE")

    log.Println("Starting server on :8080")
    if err := http.ListenAndServe(":8080", r); err != nil {
        log.Fatalf("server error: %v", err)
    }
}

func initDB() error {
    stmt := `
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
    );`
    _, err := db.Exec(stmt)
    return err
}

// Health check endpoint
func healthHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("OK"))
}

// Create a new book
func createBookHandler(w http.ResponseWriter, r *http.Request) {
    var b Book
    if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
        http.Error(w, "invalid JSON", http.StatusBadRequest)
        return
    }
    if b.Title == "" || b.Author == "" {
        http.Error(w, "title and author are required", http.StatusBadRequest)
        return
    }
    res, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", b.Title, b.Author, b.Year, b.ISBN)
    if err != nil {
        http.Error(w, "database error", http.StatusInternalServerError)
        return
    }
    id, _ := res.LastInsertId()
    b.ID = int(id)
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(b)
}

// List books, optional author filter
func listBooksHandler(w http.ResponseWriter, r *http.Request) {
    author := r.URL.Query().Get("author")
    var rows *sql.Rows
    var err error
    if author != "" {
        rows, err = db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", author)
    } else {
        rows, err = db.Query("SELECT id, title, author, year, isbn FROM books")
    }
    if err != nil {
        http.Error(w, "database error", http.StatusInternalServerError)
        return
    }
    defer rows.Close()
    books := []Book{}
    for rows.Next() {
        var b Book
        if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
            http.Error(w, "database error", http.StatusInternalServerError)
            return
        }
        books = append(books, b)
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(books)
}

// Get single book
func getBookHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    id, err := strconv.Atoi(vars["id"])
    if err != nil {
        http.Error(w, "invalid id", http.StatusBadRequest)
        return
    }
    var b Book
    err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
    if err == sql.ErrNoRows {
        http.Error(w, "not found", http.StatusNotFound)
        return
    } else if err != nil {
        http.Error(w, "database error", http.StatusInternalServerError)
        return
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(b)
}

// Update book
func updateBookHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    id, err := strconv.Atoi(vars["id"])
    if err != nil {
        http.Error(w, "invalid id", http.StatusBadRequest)
        return
    }
    var b Book
    if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
        http.Error(w, "invalid JSON", http.StatusBadRequest)
        return
    }
    if b.Title == "" || b.Author == "" {
        http.Error(w, "title and author are required", http.StatusBadRequest)
        return
    }
    res, err := db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", b.Title, b.Author, b.Year, b.ISBN, id)
    if err != nil {
        http.Error(w, "database error", http.StatusInternalServerError)
        return
    }
    rowsAffected, _ := res.RowsAffected()
    if rowsAffected == 0 {
        http.Error(w, "not found", http.StatusNotFound)
        return
    }
    b.ID = id
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(b)
}

// Delete book
func deleteBookHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    id, err := strconv.Atoi(vars["id"])
    if err != nil {
        http.Error(w, "invalid id", http.StatusBadRequest)
        return
    }
    res, err := db.Exec("DELETE FROM books WHERE id = ?", id)
    if err != nil {
        http.Error(w, "database error", http.StatusInternalServerError)
        return
    }
    rowsAffected, _ := res.RowsAffected()
    if rowsAffected == 0 {
        http.Error(w, "not found", http.StatusNotFound)
        return
    }
    w.WriteHeader(http.StatusNoContent)
}
