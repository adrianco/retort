package main

import (
    "database/sql"
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "strconv"

    _ "github.com/mattn/go-sqlite3"
    "github.com/gorilla/mux"
)

// Book represents a book record
type Book struct {
    ID     int    `json:"id"`
    Title  string `json:"title"`
    Author string `json:"author"`
    Year   int    `json:"year,omitempty"`
    ISBN   string `json:"isbn,omitempty"`
}

// DB wraps a sql.DB connection
type DB struct {
    Conn *sql.DB
}

// initDB creates the books table if it does not exist
func initDB(db *sql.DB) error {
    schema := `
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
    );`
    _, err := db.Exec(schema)
    return err
}

// createBookHandler handles POST /books
func (d *DB) createBookHandler(w http.ResponseWriter, r *http.Request) {
    var b Book
    if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
        http.Error(w, "Invalid JSON", http.StatusBadRequest)
        return
    }
    if b.Title == "" || b.Author == "" {
        http.Error(w, "Title and Author are required", http.StatusBadRequest)
        return
    }
    res, err := d.Conn.Exec("INSERT INTO books (title,author,year,isbn) VALUES (?,?,?,?)", b.Title, b.Author, b.Year, b.ISBN)
    if err != nil {
        http.Error(w, fmt.Sprintf("DB error: %v", err), http.StatusInternalServerError)
        return
    }
    id, _ := res.LastInsertId()
    b.ID = int(id)
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(b)
}

// listBooksHandler handles GET /books
func (d *DB) listBooksHandler(w http.ResponseWriter, r *http.Request) {
    author := r.URL.Query().Get("author")
    var rows *sql.Rows
    var err error
    if author != "" {
        rows, err = d.Conn.Query("SELECT id,title,author,year,isbn FROM books WHERE author=?", author)
    } else {
        rows, err = d.Conn.Query("SELECT id,title,author,year,isbn FROM books")
    }
    if err != nil {
        http.Error(w, fmt.Sprintf("DB error: %v", err), http.StatusInternalServerError)
        return
    }
    defer rows.Close()
    books := []Book{}
    for rows.Next() {
        var b Book
        if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
            http.Error(w, fmt.Sprintf("DB scan error: %v", err), http.StatusInternalServerError)
            return
        }
        books = append(books, b)
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(books)
}

// getBookHandler handles GET /books/{id}
func (d *DB) getBookHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    idStr, ok := vars["id"]
    if !ok {
        http.Error(w, "Missing ID", http.StatusBadRequest)
        return
    }
    id, err := strconv.Atoi(idStr)
    if err != nil {
        http.Error(w, "Invalid ID", http.StatusBadRequest)
        return
    }
    var b Book
    err = d.Conn.QueryRow("SELECT id,title,author,year,isbn FROM books WHERE id=?", id).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
    if err == sql.ErrNoRows {
        http.Error(w, "Not Found", http.StatusNotFound)
        return
    }
    if err != nil {
        http.Error(w, fmt.Sprintf("DB error: %v", err), http.StatusInternalServerError)
        return
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(b)
}

// updateBookHandler handles PUT /books/{id}
func (d *DB) updateBookHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    idStr, ok := vars["id"]
    if !ok {
        http.Error(w, "Missing ID", http.StatusBadRequest)
        return
    }
    id, err := strconv.Atoi(idStr)
    if err != nil {
        http.Error(w, "Invalid ID", http.StatusBadRequest)
        return
    }
    var b Book
    if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
        http.Error(w, "Invalid JSON", http.StatusBadRequest)
        return
    }
    if b.Title == "" || b.Author == "" {
        http.Error(w, "Title and Author are required", http.StatusBadRequest)
        return
    }
    res, err := d.Conn.Exec("UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?", b.Title, b.Author, b.Year, b.ISBN, id)
    if err != nil {
        http.Error(w, fmt.Sprintf("DB error: %v", err), http.StatusInternalServerError)
        return
    }
    if n, _ := res.RowsAffected(); n == 0 {
        http.Error(w, "Not Found", http.StatusNotFound)
        return
    }
    b.ID = id
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(b)
}

// deleteBookHandler handles DELETE /books/{id}
func (d *DB) deleteBookHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    idStr, ok := vars["id"]
    if !ok {
        http.Error(w, "Missing ID", http.StatusBadRequest)
        return
    }
    id, err := strconv.Atoi(idStr)
    if err != nil {
        http.Error(w, "Invalid ID", http.StatusBadRequest)
        return
    }
    res, err := d.Conn.Exec("DELETE FROM books WHERE id=?", id)
    if err != nil {
        http.Error(w, fmt.Sprintf("DB error: %v", err), http.StatusInternalServerError)
        return
    }
    if n, _ := res.RowsAffected(); n == 0 {
        http.Error(w, "Not Found", http.StatusNotFound)
        return
    }
    w.WriteHeader(http.StatusNoContent)
}

// healthHandler is not required for tests but kept for completeness
func healthHandler(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet {
        http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
        return
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func main() {
    // Example main to start server, not used in tests
    db, err := sql.Open("sqlite3", "books.db")
    if err != nil {
        log.Fatalf("failed to open db: %v", err)
    }
    defer db.Close()
    if err := initDB(db); err != nil {
        log.Fatalf("failed to init db: %v", err)
    }
    d := &DB{Conn: db}
    r := mux.NewRouter()
    r.HandleFunc("/health", healthHandler).Methods("GET")
    r.HandleFunc("/books", d.createBookHandler).Methods("POST")
    r.HandleFunc("/books", d.listBooksHandler).Methods("GET")
    r.HandleFunc("/books/{id}", d.getBookHandler).Methods("GET")
    r.HandleFunc("/books/{id}", d.updateBookHandler).Methods("PUT")
    r.HandleFunc("/books/{id}", d.deleteBookHandler).Methods("DELETE")
    log.Println("Server listening on :8080")
    log.Fatal(http.ListenAndServe(":8080", r))
}
