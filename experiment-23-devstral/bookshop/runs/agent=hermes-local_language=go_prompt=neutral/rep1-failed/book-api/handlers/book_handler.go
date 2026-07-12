package handlers

import (
    "database/sql"
    "encoding/json"
    "net/http"
    "strconv"
    
    "github.com/gorilla/mux"
)

var DB *sql.DB

// Book represents a book model
type Book struct {
    ID     int    `json:"id"`
    Title  string `json:"title"`
    Author string `json:"author"`
    Year   int    `json:"year"`
    ISBN   string `json:"isbn"`
}

func GetBooks(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    
    author := r.URL.Query().Get("author")
    var rows *sql.Rows
    var err error
    
    if author != "" {
        query := "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
        rows, err = DB.Query(query, author)
    } else {
        query := "SELECT id, title, author, year, isbn FROM books"
        rows, err = DB.Query(query)
    }
    
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    defer rows.Close()
    
    books := []Book{}
    for rows.Next() {
        var book Book
        if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
            http.Error(w, err.Error(), http.StatusInternalServerError)
            return
        }
        books = append(books, book)
    }
    
    json.NewEncoder(w).Encode(books)
}

func GetBook(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    
    params := mux.Vars(r)
    id, err := strconv.Atoi(params["id"])
    if err != nil {
        http.Error(w, "Invalid book ID", http.StatusBadRequest)
        return
    }
    
    var book Book
    query := "SELECT id, title, author, year, isbn FROM books WHERE id = ?"
    row := DB.QueryRow(query, id)
    
    err = row.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
    if err == sql.ErrNoRows {
        http.Error(w, "Book not found", http.StatusNotFound)
        return
    } else if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    json.NewEncoder(w).Encode(book)
}

func CreateBook(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    
    var book Book
    if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    
    if book.Title == "" || book.Author == "" {
        http.Error(w, "Title and author are required", http.StatusBadRequest)
        return
    }
    
    query := "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)"
    res, err := DB.Exec(query, book.Title, book.Author, book.Year, book.ISBN)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    id, err := res.LastInsertId()
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    book.ID = int(id)
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(book)
}

func UpdateBook(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    
    params := mux.Vars(r)
    id, err := strconv.Atoi(params["id"])
    if err != nil {
        http.Error(w, "Invalid book ID", http.StatusBadRequest)
        return
    }
    
    var book Book
    if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    
    if book.Title == "" || book.Author == "" {
        http.Error(w, "Title and author are required", http.StatusBadRequest)
        return
    }
    
    query := "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?"
    _, err = DB.Exec(query, book.Title, book.Author, book.Year, book.ISBN, id)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    book.ID = id
    json.NewEncoder(w).Encode(book)
}

func DeleteBook(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    
    params := mux.Vars(r)
    id, err := strconv.Atoi(params["id"])
    if err != nil {
        http.Error(w, "Invalid book ID", http.StatusBadRequest)
        return
    }
    
    query := "DELETE FROM books WHERE id = ?"
    _, err = DB.Exec(query, id)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    w.WriteHeader(http.StatusNoContent)
}

func HealthCheck(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("OK"))
}
