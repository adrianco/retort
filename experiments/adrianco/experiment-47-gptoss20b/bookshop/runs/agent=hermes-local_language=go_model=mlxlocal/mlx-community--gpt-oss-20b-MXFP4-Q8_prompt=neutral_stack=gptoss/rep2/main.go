package main

import (
    "database/sql"
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "strconv"

    "github.com/gorilla/mux"
    _ "github.com/mattn/go-sqlite3"
)

// Book represents a book resource.
type Book struct {
    ID     int    `json:"id"`
    Title  string `json:"title"`
    Author string `json:"author"`
    Year   int    `json:"year,omitempty"`
    ISBN   string `json:"isbn,omitempty"`
}

// App holds application state.
type App struct {
    DB *sql.DB
}

func main() {
    db, err := sql.Open("sqlite3", "books.db")
    if err != nil {
        log.Fatalf("failed to open db: %v", err)
    }
    defer db.Close()

    app := &App{DB: db}
    if err := app.initDB(); err != nil {
        log.Fatalf("failed to init db: %v", err)
    }

    r := mux.NewRouter()
    r.HandleFunc("/books", app.handleCreate).Methods("POST")
    r.HandleFunc("/books", app.handleList).Methods("GET")
    r.HandleFunc("/books/{id:[0-9]+}", app.handleGet).Methods("GET")
    r.HandleFunc("/books/{id:[0-9]+}", app.handleUpdate).Methods("PUT")
    r.HandleFunc("/books/{id:[0-9]+}", app.handleDelete).Methods("DELETE")
    r.HandleFunc("/health", app.handleHealth).Methods("GET")

    fmt.Println("Starting server on :8080")
    if err := http.ListenAndServe(":8080", r); err != nil {
        log.Fatalf("server failed: %v", err)
    }
}

func (a *App) initDB() error {
    query := `
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        );
    `
    _, err := a.DB.Exec(query)
    return err
}

// handleCreate creates a new book.
func (a *App) handleCreate(w http.ResponseWriter, r *http.Request) {
    var b Book
    if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
        http.Error(w, "invalid JSON", http.StatusBadRequest)
        return
    }
    if b.Title == "" || b.Author == "" {
        http.Error(w, "title and author are required", http.StatusBadRequest)
        return
    }
    res, err := a.DB.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", b.Title, b.Author, b.Year, b.ISBN)
    if err != nil {
        http.Error(w, "db insert error", http.StatusInternalServerError)
        return
    }
    id, _ := res.LastInsertId()
    b.ID = int(id)
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(b)
}

// handleList returns all books, optionally filtered by author.
func (a *App) handleList(w http.ResponseWriter, r *http.Request) {
    author := r.URL.Query().Get("author")
    var rows *sql.Rows
    var err error
    if author != "" {
        rows, err = a.DB.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", author)
    } else {
        rows, err = a.DB.Query("SELECT id, title, author, year, isbn FROM books")
    }
    if err != nil {
        http.Error(w, "db query error", http.StatusInternalServerError)
        return
    }
    defer rows.Close()
    books := []Book{}
    for rows.Next() {
        var b Book
        if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
            http.Error(w, "row scan error", http.StatusInternalServerError)
            return
        }
        books = append(books, b)
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(books)
}

// handleGet returns a single book by ID.
func (a *App) handleGet(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    id, _ := strconv.Atoi(vars["id"])
    row := a.DB.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id)
    var b Book
    if err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
        if err == sql.ErrNoRows {
            http.Error(w, "not found", http.StatusNotFound)
        } else {
            http.Error(w, "db query error", http.StatusInternalServerError)
        }
        return
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(b)
}

// handleUpdate updates a book.
func (a *App) handleUpdate(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    id, _ := strconv.Atoi(vars["id"])
    var b Book
    if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
        http.Error(w, "invalid JSON", http.StatusBadRequest)
        return
    }
    if b.Title == "" || b.Author == "" {
        http.Error(w, "title and author are required", http.StatusBadRequest)
        return
    }
    res, err := a.DB.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", b.Title, b.Author, b.Year, b.ISBN, id)
    if err != nil {
        http.Error(w, "db update error", http.StatusInternalServerError)
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

// handleDelete removes a book.
func (a *App) handleDelete(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    id, _ := strconv.Atoi(vars["id"])
    res, err := a.DB.Exec("DELETE FROM books WHERE id = ?", id)
    if err != nil {
        http.Error(w, "db delete error", http.StatusInternalServerError)
        return
    }
    rowsAffected, _ := res.RowsAffected()
    if rowsAffected == 0 {
        http.Error(w, "not found", http.StatusNotFound)
        return
    }
    w.WriteHeader(http.StatusNoContent)
}

// handleHealth returns a simple health status.
func (a *App) handleHealth(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}
