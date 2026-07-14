package handlers

import (
    "bytes"
    "database/sql"
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "testing"
    
    "github.com/gorilla/mux"
    _ "github.com/mattn/go-sqlite3"
)

var testDB *sql.DB

func setup() {
    var err error
    testDB, err = sql.Open("sqlite3", ":memory:")
    if err != nil {
        panic(err)
    }
    
    createTableQuery := `
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        year INTEGER,
        isbn TEXT
    );
    `
    testDB.Exec(createTableQuery)
    
    // Import test data
    _, err = testDB.Exec(
        "INSERT INTO books (title, author, year, isbn) VALUES" +
        " ('1984', 'George Orwell', 1949, '9780451524935')," +
        " ('To Kill a Mockingbird', 'Harper Lee', 1960, '9780060935467')," +
        " ('The Great Gatsby', 'F. Scott Fitzgerald', 1925, '9780743273565');",
    )
    if err != nil {
        panic(err)
    }
    
    // Set the global database reference to our test DB
    DB = testDB
}

func teardown() {
    testDB.Close()
}

func TestGetBooks(t *testing.T) {
    setup()
    defer teardown()
    
    req, err := http.NewRequest("GET", "/books", nil)
    if err != nil {
        t.Fatal(err)
    }
    
    rr := httptest.NewRecorder()
    r := mux.NewRouter()
    r.HandleFunc("/books", GetBooks).Methods("GET")
    
    r.ServeHTTP(rr, req)
    
    if status := rr.Code; status != http.StatusOK {
        t.Errorf("handler returned wrong status code: got %v want %v",
            status, http.StatusOK)
    }
    
    var books []Book
    if err := json.NewDecoder(rr.Body).Decode(&books); err != nil {
        t.Fatal(err)
    }
    
    if len(books) != 3 {
        t.Errorf("handler returned wrong number of books: got %v want %v",
            len(books), 3)
    }
}

func TestGetBook(t *testing.T) {
    setup()
    defer teardown()
    
    req, err := http.NewRequest("GET", "/books/1", nil)
    if err != nil {
        t.Fatal(err)
    }
    
    rr := httptest.NewRecorder()
    r := mux.NewRouter()
    r.HandleFunc("/books/{id}", GetBook).Methods("GET")
    
    r.ServeHTTP(rr, req)
    
    if status := rr.Code; status != http.StatusOK {
        t.Errorf("handler returned wrong status code: got %v want %v",
            status, http.StatusOK)
    }
    
    var book Book
    if err := json.NewDecoder(rr.Body).Decode(&book); err != nil {
        t.Fatal(err)
    }
    
    if book.ID != 1 || book.Title != "1984" {
        t.Errorf("handler returned unexpected book: %v", book)
    }
}

func TestCreateBook(t *testing.T) {
    setup()
    defer teardown()
    
    book := Book{
        Title:  "Brave New World",
        Author: "Aldous Huxley",
        Year:   1932,
        ISBN:   "9780060935467",
    }
    
    body, err := json.Marshal(book)
    if err != nil {
        t.Fatal(err)
    }
    
    req, err := http.NewRequest("POST", "/books", bytes.NewBuffer(body))
    if err != nil {
        t.Fatal(err)
    }
    
    rr := httptest.NewRecorder()
    r := mux.NewRouter()
    r.HandleFunc("/books", CreateBook).Methods("POST")
    
    r.ServeHTTP(rr, req)
    
    if status := rr.Code; status != http.StatusCreated {
        t.Errorf("handler returned wrong status code: got %v want %v",
            status, http.StatusCreated)
    }
    
    var createdBook Book
    if err := json.NewDecoder(rr.Body).Decode(&createdBook); err != nil {
        t.Fatal(err)
    }
    
    if createdBook.Title != book.Title || createdBook.Author != book.Author {
        t.Errorf("handler returned unexpected book: %v", createdBook)
    }
}
