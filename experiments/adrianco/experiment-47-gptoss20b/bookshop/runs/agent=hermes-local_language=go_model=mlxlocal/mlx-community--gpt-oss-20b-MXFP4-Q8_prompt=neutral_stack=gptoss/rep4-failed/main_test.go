package main

import (
    "bytes"
    "database/sql"
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "strconv"
    "testing"

    "github.com/gorilla/mux"
    _ "github.com/mattn/go-sqlite3"
)

func setupTestDB(t *testing.T) {
    var err error
    db, err = sql.Open("sqlite3", ":memory:")
    if err != nil {
        t.Fatalf("failed to open memory db: %v", err)
    }
    if err := initDB(); err != nil {
        t.Fatalf("failed to init db: %v", err)
    }
}

func newTestRouter() *mux.Router {
    r := mux.NewRouter()
    r.HandleFunc("/health", healthHandler).Methods("GET")
    api := r.PathPrefix("/books").Subrouter()
    api.HandleFunc("", listBooksHandler).Methods("GET")
    api.HandleFunc("", createBookHandler).Methods("POST")
    api.HandleFunc("/{id}", getBookHandler).Methods("GET")
    api.HandleFunc("/{id}", updateBookHandler).Methods("PUT")
    api.HandleFunc("/{id}", deleteBookHandler).Methods("DELETE")
    return r
}

func TestHealth(t *testing.T) {
    setupTestDB(t)
    r := newTestRouter()
    req := httptest.NewRequest("GET", "/health", nil)
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)
    if w.Code != http.StatusOK {
        t.Fatalf("expected 200 got %d", w.Code)
    }
}

func TestCreateAndGetBook(t *testing.T) {
    setupTestDB(t)
    r := newTestRouter()

    // Create
    book := Book{Title: "Go in Action", Author: "William Kennedy", Year: 2015, ISBN: "12345"}
    body, _ := json.Marshal(book)
    req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)
    if w.Code != http.StatusCreated {
        t.Fatalf("expected 201 got %d", w.Code)
    }
    var created Book
    if err := json.NewDecoder(w.Body).Decode(&created); err != nil {
        t.Fatalf("decode error: %v", err)
    }
    if created.ID == 0 || created.Title != book.Title {
        t.Fatalf("unexpected created book: %+v", created)
    }

    // Get
    getReq := httptest.NewRequest("GET", "/books/"+strconv.Itoa(created.ID), nil)
    w = httptest.NewRecorder()
    r.ServeHTTP(w, getReq)
    if w.Code != http.StatusOK {
        t.Fatalf("expected 200 got %d", w.Code)
    }
    var fetched Book
    if err := json.NewDecoder(w.Body).Decode(&fetched); err != nil {
        t.Fatalf("decode error: %v", err)
    }
    if fetched.ID != created.ID || fetched.Title != created.Title {
        t.Fatalf("fetched mismatch: %+v", fetched)
    }
}

func TestListBooksWithFilter(t *testing.T) {
    setupTestDB(t)
    r := newTestRouter()
    // Add two books
    books := []Book{{Title: "A", Author: "X", Year: 2000}, {Title: "B", Author: "Y", Year: 2001}}
    for _, b := range books {
        body, _ := json.Marshal(b)
        req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
        w := httptest.NewRecorder()
        r.ServeHTTP(w, req)
        if w.Code != http.StatusCreated {
            t.Fatalf("create failed with %d", w.Code)
        }
    }
    // List all
    req := httptest.NewRequest("GET", "/books", nil)
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)
    var list []Book
    json.NewDecoder(w.Body).Decode(&list)
    if len(list) != 2 {
        t.Fatalf("expected 2 books got %d", len(list))
    }
    // Filter by author X
    req = httptest.NewRequest("GET", "/books?author=X", nil)
    w = httptest.NewRecorder()
    r.ServeHTTP(w, req)
    json.NewDecoder(w.Body).Decode(&list)
    if len(list) != 1 || list[0].Author != "X" {
        t.Fatalf("filter failed: %+v", list)
    }
}

func TestUpdateAndDelete(t *testing.T) {
    setupTestDB(t)
    r := newTestRouter()
    // Create
    b := Book{Title: "Old", Author: "A"}
    body, _ := json.Marshal(b)
    req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)
    var created Book
    json.NewDecoder(w.Body).Decode(&created)
    // Update
    updated := Book{Title: "New", Author: "A", Year: 2020}
    body, _ = json.Marshal(updated)
    updReq := httptest.NewRequest("PUT", "/books/"+strconv.Itoa(created.ID), bytes.NewReader(body))
    w = httptest.NewRecorder()
    r.ServeHTTP(w, updReq)
    if w.Code != http.StatusOK {
        t.Fatalf("update failed %d", w.Code)
    }
    var updResp Book
    json.NewDecoder(w.Body).Decode(&updResp)
    if updResp.Title != "New" || updResp.Year != 2020 {
        t.Fatalf("update response wrong: %+v", updResp)
    }
    // Delete
    delReq := httptest.NewRequest("DELETE", "/books/"+strconv.Itoa(created.ID), nil)
    w = httptest.NewRecorder()
    r.ServeHTTP(w, delReq)
    if w.Code != http.StatusNoContent {
        t.Fatalf("delete failed %d", w.Code)
    }
    // Verify deleted
    getReq := httptest.NewRequest("GET", "/books/"+strconv.Itoa(created.ID), nil)
    w = httptest.NewRecorder()
    r.ServeHTTP(w, getReq)
    if w.Code != http.StatusNotFound {
        t.Fatalf("expected 404 after delete got %d", w.Code)
    }
}

func TestValidation(t *testing.T) {
    setupTestDB(t)
    r := newTestRouter()
    // Missing title
    b := Book{Author: "A"}
    body, _ := json.Marshal(b)
    req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)
    if w.Code != http.StatusBadRequest {
        t.Fatalf("expected 400 for missing title got %d", w.Code)
    }
}
