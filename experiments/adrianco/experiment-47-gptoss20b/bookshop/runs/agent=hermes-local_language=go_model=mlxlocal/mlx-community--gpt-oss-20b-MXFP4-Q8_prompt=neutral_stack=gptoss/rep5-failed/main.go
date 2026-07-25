package main

import (
    "database/sql"
    "encoding/json"
    "log"
    "net/http"
    "strconv"
    "strings"

    "github.com/gorilla/mux"
    _ "github.com/mattn/go-sqlite3"
)

// Book represents a book record
type Book struct {
    ID     int    `json:"id"`
    Title  string `json:"title"`
    Author string `json:"author"`
    Year   int    `json:"year,omitempty"`
    ISBN   string `json:"isbn,omitempty"`
}

// DB holds the SQLite connection
type DB struct {
    Conn *sql.DB
}

func main() {
    // Open or create database
    dbFile := "books.db"
    conn, err := sql.Open("sqlite3", dbFile)
    if err != nil {
        log.Fatalf("Failed to open database: %v", err)
    }
    defer conn.Close()

    // Ensure table exists
    if err := initDB(conn); err != nil {
        log.Fatalf("Failed to init db: %v", err)
    }

    db := &DB{Conn: conn}

    r := mux.NewRouter()
    r.HandleFunc("/health", healthHandler).Methods("GET")

    // Book routes
    r.HandleFunc("/books", db.createBookHandler).Methods("POST")
    r.HandleFunc("/books", db.listBooksHandler).Methods("GET")
    r.HandleFunc("/books/{id}", db.getBookHandler).Methods("GET")
    r.HandleFunc("/books/{id}", db.updateBookHandler).Methods("PUT")
    r.HandleFunc("/books/{id}", db.deleteBookHandler).Methods("DELETE")

    addr := ":8080"
    log.Printf("Server listening on %s", addr)
    if err := http.ListenAndServe(addr, r); err != nil {
        log.Fatalf("ListenAndServe: %v", err)
    }
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("OK"))
}

func initDB(conn *sql.DB) error {
    stmt := `CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
    );`
    _, err := conn.Exec(stmt)
    return err
}

// createBookHandler handles POST /books
func (db *DB) createBookHandler(w http.ResponseWriter, r *http.Request) {
    var b Book
    if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
        http.Error(w, "invalid JSON", http.StatusBadRequest)
        return
    }
    // Validation
    if strings.TrimSpace(b.Title) == "" || strings.TrimSpace(b.Author) == "" {
        http.Error(w, "title and author required", http.StatusBadRequest)
        return
    }
    res, err := db.Conn.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", b.Title, b.Author, b.Year, b.ISBN)
    if err != nil {
        http.Error(w, "db error", http.StatusInternalServerError)
        return
    }
    id, _ := res.LastInsertId()
    b.ID = int(id)
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(b)
}

// listBooksHandler handles GET /books?author=...
func (db *DB) listBooksHandler(w http.ResponseWriter, r *http.Request) {
    author := r.URL.Query().Get("author")
    var rows *sql.Rows
    var err error
    if author != "" {
        rows, err = db.Conn.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", author)
    } else {
        rows, err = db.Conn.Query("SELECT id, title, author, year, isbn FROM books")
    }
    if err != nil {
        http.Error(w, "db error", http.StatusInternalServerError)
        return
    }
    defer rows.Close()
    books := []Book{}
    for rows.Next() {
        var b Book
        rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
        books = append(books, b)
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(books)
}

// getBookHandler handles GET /books/{id}
func (db *DB) getBookHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    id, err := strconv.Atoi(vars["id"])
    if err != nil {
        http.Error(w, "invalid id", http.StatusBadRequest)
        return
    }
    var b Book
    err = db.Conn.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
    if err == sql.ErrNoRows {
        http.Error(w, "not found", http.StatusNotFound)
        return
    } else if err != nil {
        http.Error(w, "db error", http.StatusInternalServerError)
        return
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(b)
}

// updateBookHandler handles PUT /books/{id}
func (db *DB) updateBookHandler(w http.ResponseWriter, r *http.Request) {
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
    if strings.TrimSpace(b.Title) == "" || strings.TrimSpace(b.Author) == "" {
        http.Error(w, "title and author required", http.StatusBadRequest)
        return
    }
    res, err := db.Conn.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", b.Title, b.Author, b.Year, b.ISBN, id)
    if err != nil {
        http.Error(w, "db error", http.StatusInternalServerError)
        return
    }
    rows, _ := res.RowsAffected()
    if rows == 0 {
        http.Error(w, "not found", http.StatusNotFound)
        return
    }
    b.ID = id
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(b)
}

// deleteBookHandler handles DELETE /books/{id}
func (db *DB) deleteBookHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    id, err := strconv.Atoi(vars["id"])
    if err != nil {
        http.Error(w, "invalid id", http.StatusBadRequest)
        return
    }
    res, err := db.Conn.Exec("DELETE FROM books WHERE id = ?", id)
    if err != nil {
        http.Error(w, "db error", http.StatusInternalServerError)
        return
    }
    rows, _ := res.RowsAffected()
    if rows == 0 {
        http.Error(w, "not found", http.StatusNotFound)
        return
    }
    w.WriteHeader(http.StatusNoContent)
}
