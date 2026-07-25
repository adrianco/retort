package main

import (
    "bytes"
    "database/sql"
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "net/url"
    "strconv"
    "testing"

    "github.com/gorilla/mux"
)

func setUpTestDB(t *testing.T) *sql.DB {
    d, err := sql.Open("sqlite3", "file::memory:?cache=shared")
    if err != nil {t.Fatalf("db open: %v", err)}
    setTestDB(d)
    if err = initDB(); err != nil {t.Fatalf("init db: %v", err)}
    return d
}

func TestCreateAndGetBook(t *testing.T) {
    d := setUpTestDB(t)
    defer d.Close()

    r := mux.NewRouter()
    r.HandleFunc("/books", createBookHandler).Methods("POST")
    r.HandleFunc("/books/{id:[0-9]+}", getBookHandler).Methods("GET")
    ts := httptest.NewServer(r)
    defer ts.Close()

    b := map[string]interface{}{ "title":"Go in Action", "author":"William Kennedy", "year":2019, "isbn":"123456"}
    body, _ := json.Marshal(b)
    resp, err := http.Post(ts.URL+"/books", "application/json", bytes.NewReader(body))
    if err != nil {t.Fatalf("post: %v", err)}
    if resp.StatusCode != http.StatusCreated {t.Fatalf("expected 201 got %d", resp.StatusCode)}
    var created Book
    if err := json.NewDecoder(resp.Body).Decode(&created); err != nil {t.Fatalf("decode: %v", err)}
    if created.ID == 0 {t.Fatalf("expected id set")}

    resp2, err := http.Get(ts.URL+"/books/"+strconv.Itoa(created.ID))
    if err != nil {t.Fatalf("get: %v", err)}
    if resp2.StatusCode != http.StatusOK {t.Fatalf("expected 200 got %d", resp2.StatusCode)}
    var got Book
    if err := json.NewDecoder(resp2.Body).Decode(&got); err != nil {t.Fatalf("decode get: %v", err)}
    if got.Title != b["title"] {t.Fatalf("title mismatch %s != %s", got.Title, b["title"]) }
}

func TestListBooksWithFilter(t *testing.T) {
    d := setUpTestDB(t)
    defer d.Close()

    r := mux.NewRouter()
    r.HandleFunc("/books", listBooksHandler).Methods("GET")
    // insert books
    d.Exec("INSERT INTO books (title,author,year,isbn) VALUES (?,?,?,?)", "Book A", "Author X", 2000, "0001")
    d.Exec("INSERT INTO books (title,author,year,isbn) VALUES (?,?,?,?)", "Book B", "Author Y", 2001, "0002")

    ts := httptest.NewServer(r)
    defer ts.Close()
    resp, err := http.Get(ts.URL + "/books?author=" + url.QueryEscape("Author X"))
    if err != nil {t.Fatalf("get: %v", err)}
    if resp.StatusCode != http.StatusOK {t.Fatalf("expected 200 got %d", resp.StatusCode)}
    var books []Book
    if err := json.NewDecoder(resp.Body).Decode(&books); err != nil {t.Fatalf("decode: %v", err)}
    if len(books) != 1 || books[0].Author != "Author X" {t.Fatalf("filter failed: %+v", books)}
}

func TestHealthEndpoint(t *testing.T) {
    r := mux.NewRouter()
    r.HandleFunc("/health", healthHandler).Methods("GET")
    ts := httptest.NewServer(r)
    defer ts.Close()
    resp, err := http.Get(ts.URL + "/health")
    if err != nil {t.Fatalf("get: %v", err)}
    if resp.StatusCode != http.StatusOK {t.Fatalf("expected 200 got %d", resp.StatusCode)}
    var out map[string]string
    if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {t.Fatalf("decode: %v", err)}
    if out["status"] != "ok" {t.Fatalf("unexpected health status: %v", out)}
}
