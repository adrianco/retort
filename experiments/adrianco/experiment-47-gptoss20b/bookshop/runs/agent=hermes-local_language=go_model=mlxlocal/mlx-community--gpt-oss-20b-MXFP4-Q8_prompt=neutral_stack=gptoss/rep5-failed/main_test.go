package main

import (
    "bytes"
    "database/sql"
    "encoding/json"
    "fmt"
    "net/http"
    "net/http/httptest"
    "testing"

    "github.com/gorilla/mux"
    _ "github.com/mattn/go-sqlite3"
)

func setupRouter() *mux.Router {
    dbFile := "/tmp/books_test.db"
    conn, err := sql.Open("sqlite3", dbFile)
    if err != nil {
        panic(err)
    }
    initDB(conn)
    db := &DB{Conn: conn}
    r := mux.NewRouter()
    r.HandleFunc("/books", db.createBookHandler).Methods("POST")
    r.HandleFunc("/books", db.listBooksHandler).Methods("GET")
    r.HandleFunc("/books/{id}", db.getBookHandler).Methods("GET")
    r.HandleFunc("/books/{id}", db.updateBookHandler).Methods("PUT")
    r.HandleFunc("/books/{id}", db.deleteBookHandler).Methods("DELETE")
    return r
}

func TestCreateAndGetBook(t *testing.T) {
    r := setupRouter()
    book := Book{Title: "Go in Action", Author: "William Kennedy", Year: 2015, ISBN: "123456"}
    body, _ := json.Marshal(book)
    req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)
    if w.Code != http.StatusCreated {
        t.Fatalf("expected 201 got %d", w.Code)
    }
    var resp Book
    json.NewDecoder(w.Body).Decode(&resp)
    if resp.ID == 0 {
        t.Fatalf("expected id set")
    }
    // Get
    getReq := httptest.NewRequest("GET", fmt.Sprintf("/books/%d", resp.ID), nil)
    getW := httptest.NewRecorder()
    r.ServeHTTP(getW, getReq)
    if getW.Code != http.StatusOK {
        t.Fatalf("expected 200 got %d", getW.Code)
    }
    var getResp Book
    json.NewDecoder(getW.Body).Decode(&getResp)
    if getResp.Title != book.Title || getResp.Author != book.Author {
        t.Fatalf("data mismatch")
    }
}

func TestListBooksFilter(t *testing.T) {
    r := setupRouter()
    // create two books
    books := []Book{{Title: "A", Author: "X"}, {Title: "B", Author: "Y"}}
    for _, b := range books {
        body, _ := json.Marshal(b)
        req := httptest.NewRequest("POST", "/books", bytes.NewReader(body))
        w := httptest.NewRecorder()
        r.ServeHTTP(w, req)
    }
    req := httptest.NewRequest("GET", "/books?author=X", nil)
    w := httptest.NewRecorder()
    r.ServeHTTP(w, req)
    if w.Code != http.StatusOK {
        t.Fatalf("expected 200 got %d", w.Code)
    }
    var list []Book
    json.NewDecoder(w.Body).Decode(&list)
    if len(list) != 1 || list[0].Author != "X" {
        t.Fatalf("filter failed, got %v", list)
    }
}
