package main

import (
    "bytes"
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "os"
    "strconv"
    "testing"
)

func setupTestDB() {
    // use in-memory db for tests
    dbPath := "file::memory:?cache=shared"
    os.Setenv("BOOKAPI_DB", dbPath)
    initDB()
}

func TestHealth(t *testing.T) {
    setupTestDB()
    r := NewRouter()
    req := httptest.NewRequest("GET", "/health", nil)
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)
    if w.Code != http.StatusOK {
        t.Fatalf("expected 200 got %d", w.Code)
    }
    var resp map[string]string
    if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
        t.Fatalf("invalid json: %v", err)
    }
    if resp["status"] != "ok" {
        t.Fatalf("expected status ok got %v", resp["status"])
    }
}

func TestCRUD(t *testing.T) {
    setupTestDB()
    r := NewRouter()
    // create
    book := Book{Title: "Test", Author: "A", Year: 2020, ISBN: "123"}
    body, _ := json.Marshal(book)
    req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)
    if w.Code != http.StatusCreated {
        t.Fatalf("create status %d", w.Code)
    }
    var created Book
    json.NewDecoder(w.Body).Decode(&created)
    if created.ID == 0 { t.Fatalf("no id") }
    // get
    req = httptest.NewRequest("GET", "/books/"+strconv.FormatInt(created.ID,10), nil)
    w = httptest.NewRecorder()
    r.ServeHTTP(w, req)
    if w.Code != http.StatusOK { t.Fatalf("get status %d", w.Code)}
    var got Book
    json.NewDecoder(w.Body).Decode(&got)
    if got.Title != book.Title { t.Fatalf("mismatch title %s", got.Title)}
    // update
    book.ID = created.ID
    book.Title = "Updated"
    body, _ = json.Marshal(book)
    req = httptest.NewRequest("PUT", "/books/"+strconv.FormatInt(created.ID,10), bytes.NewReader(body))
    w = httptest.NewRecorder()
    r.ServeHTTP(w, req)
    if w.Code != http.StatusOK { t.Fatalf("update status %d", w.Code)}
    // list
    req = httptest.NewRequest("GET", "/books", nil)
    w = httptest.NewRecorder()
    r.ServeHTTP(w, req)
    if w.Code != http.StatusOK { t.Fatalf("list status %d", w.Code)}
    var list []Book
    json.NewDecoder(w.Body).Decode(&list)
    if len(list) != 1 { t.Fatalf("expected 1 book got %d", len(list))}
    // delete
    req = httptest.NewRequest("DELETE", "/books/"+strconv.FormatInt(created.ID,10), nil)
    w = httptest.NewRecorder()
    r.ServeHTTP(w, req)
    if w.Code != http.StatusNoContent { t.Fatalf("delete status %d", w.Code)}
}

// Test that listing with author filter works
func TestListByAuthor(t *testing.T) {
    setupTestDB()
    r := NewRouter()
    // create two books with same author
    b1 := Book{Title: "Book1", Author: "AuthorX", Year: 2001, ISBN: "111"}
    b2 := Book{Title: "Book2", Author: "AuthorX", Year: 2002, ISBN: "222"}
    for _, b := range []Book{b1, b2} {
        body, _ := json.Marshal(b)
        req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
        w := httptest.NewRecorder()
        r.ServeHTTP(w, req)
        if w.Code != http.StatusCreated { t.Fatalf("create status %d", w.Code) }
    }
    // list with filter
    req := httptest.NewRequest("GET", "/books?author=AuthorX", nil)
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)
    if w.Code != http.StatusOK { t.Fatalf("list status %d", w.Code) }
    var list []Book
    json.NewDecoder(w.Body).Decode(&list)
    if len(list) != 2 { t.Fatalf("expected 2 books got %d", len(list)) }
}

