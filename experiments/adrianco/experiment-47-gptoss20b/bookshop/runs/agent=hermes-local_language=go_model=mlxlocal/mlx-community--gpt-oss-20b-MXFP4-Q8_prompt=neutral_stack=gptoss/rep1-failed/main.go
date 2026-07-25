package main

import (
    "database/sql"
    "encoding/json"
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
    Year   int    `json:"year"`
    ISBN   string `json:"isbn"`
}

var db *sql.DB

// setTestDB allows tests to inject a database connection.
func setTestDB(d *sql.DB) { db = d }


func main() {
    var err error
    db, err = sql.Open("sqlite3", "file:books.db?cache=shared&mode=rwc")
    if err != nil {
        log.Fatalf("failed to open db: %v", err)
    }
    defer db.Close()

    if err = initDB(); err != nil {
        log.Fatalf("failed to init db: %v", err)
    }

    r := mux.NewRouter()
    r.HandleFunc("/health", healthHandler).Methods("GET")

    r.HandleFunc("/books", createBookHandler).Methods("POST")
    r.HandleFunc("/books", listBooksHandler).Methods("GET")
    r.HandleFunc("/books/{id:[0-9]+}", getBookHandler).Methods("GET")
    r.HandleFunc("/books/{id:[0-9]+}", updateBookHandler).Methods("PUT")
    r.HandleFunc("/books/{id:[0-9]+}", deleteBookHandler).Methods("DELETE")

    log.Println("server listening on :8080")
    if err = http.ListenAndServe(":8080", r); err != nil {
        log.Fatalf("listen: %v", err)
    }
}

func initDB() error {
    schema := `
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
);
`
    _, err := db.Exec(schema)
    return err
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func createBookHandler(w http.ResponseWriter, r *http.Request) {
    var b Book
    if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
        http.Error(w, "invalid JSON", http.StatusBadRequest)
        return
    }
    if b.Title == "" || b.Author == "" {
        http.Error(w, "title and author required", http.StatusBadRequest)
        return
    }
    res, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?,?,?,?)", b.Title, b.Author, b.Year, b.ISBN)
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

func listBooksHandler(w http.ResponseWriter, r *http.Request) {
    author := r.URL.Query().Get("author")
    var rows *sql.Rows
    var err error
    if author != "" {
        rows, err = db.Query("SELECT id,title,author,year,isbn FROM books WHERE author=?", author)
    } else {
        rows, err = db.Query("SELECT id,title,author,year,isbn FROM books")
    }
    if err != nil {
        http.Error(w, "db error", http.StatusInternalServerError)
        return
    }
    defer rows.Close()
    books := []Book{}
    for rows.Next() {
        var b Book
        if err = rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
            http.Error(w, "db error", http.StatusInternalServerError)
            return
        }
        books = append(books, b)
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(books)
}

func getBookHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    id, _ := strconv.Atoi(vars["id"])
    row := db.QueryRow("SELECT id,title,author,year,isbn FROM books WHERE id=?", id)
    var b Book
    if err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
        if err == sql.ErrNoRows {
            http.Error(w, "not found", http.StatusNotFound)
        } else {
            http.Error(w, "db error", http.StatusInternalServerError)
        }
        return
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(b)
}

func updateBookHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    id, _ := strconv.Atoi(vars["id"])
    var b Book
    if err := json.NewDecoder(r.Body).Decode(&b); err != nil {
        http.Error(w, "invalid JSON", http.StatusBadRequest)
        return
    }
    if b.Title == "" || b.Author == "" {
        http.Error(w, "title and author required", http.StatusBadRequest)
        return
    }
    res, err := db.Exec("UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?", b.Title, b.Author, b.Year, b.ISBN, id)
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

func deleteBookHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    id, _ := strconv.Atoi(vars["id"])
    res, err := db.Exec("DELETE FROM books WHERE id=?", id)
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
