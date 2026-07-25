package main

import (
    "bytes"
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "testing"
    "github.com/gorilla/mux"
    "database/sql"
    _ "github.com/mattn/go-sqlite3"
    "strconv"
)

func setupTestApp(t *testing.T) *App {
    db, err := sql.Open("sqlite3", ":memory:")
    if err != nil {
        t.Fatalf("failed to open db: %v", err)
    }
    app := &App{DB: db}
    if err := app.initDB(); err != nil {
        t.Fatalf("failed to init db: %v", err)
    }
    return app
}

func TestCreateAndGetBook(t *testing.T) {
    app := setupTestApp(t)
    router := mux.NewRouter()
    router.HandleFunc("/books", app.handleCreate).Methods("POST")
    router.HandleFunc("/books/{id:[0-9]+}", app.handleGet).Methods("GET")

    b := Book{Title: "Go in Action", Author: "William Kennedy", Year: 2015, ISBN: "9781617291784"}
    payload, _ := json.Marshal(b)
    req := httptest.NewRequest("POST", "/books", bytes.NewReader(payload))
    w := httptest.NewRecorder()
    router.ServeHTTP(w, req)
    if w.Code != http.StatusCreated {
        t.Fatalf("expected status %d got %d", http.StatusCreated, w.Code)
    }
    var created Book
    if err := json.NewDecoder(w.Body).Decode(&created); err != nil {
        t.Fatalf("decode error: %v", err)
    }
    if created.ID == 0 || created.Title != b.Title {
        t.Fatalf("created book mismatch: %+v", created)
    }

    // Get
    getReq := httptest.NewRequest("GET", "/books/"+strconv.Itoa(created.ID), nil)
    getW := httptest.NewRecorder()
    router.ServeHTTP(getW, getReq)
    if getW.Code != http.StatusOK {
        t.Fatalf("expected status %d got %d", http.StatusOK, getW.Code)
    }
    var fetched Book
    if err := json.NewDecoder(getW.Body).Decode(&fetched); err != nil {
        t.Fatalf("decode error: %v", err)
    }
    if fetched.ID != created.ID || fetched.Title != created.Title {
        t.Fatalf("fetched book mismatch: %+v", fetched)
    }
}

func TestListFilter(t *testing.T) {
    app := setupTestApp(t)
    router := mux.NewRouter()
    router.HandleFunc("/books", app.handleCreate).Methods("POST")
    router.HandleFunc("/books", app.handleList).Methods("GET")

    books := []Book{{Title: "A", Author: "X", Year: 2000}, {Title: "B", Author: "Y", Year: 2001}, {Title: "C", Author: "X", Year: 2002}}
    for _, b := range books {
        payload, _ := json.Marshal(b)
        req := httptest.NewRequest("POST", "/books", bytes.NewReader(payload))
        w := httptest.NewRecorder()
        router.ServeHTTP(w, req)
        if w.Code != http.StatusCreated {
            t.Fatalf("create failed status %d", w.Code)
        }
    }
    // List all
    listReq := httptest.NewRequest("GET", "/books", nil)
    listW := httptest.NewRecorder()
    router.ServeHTTP(listW, listReq)
    if listW.Code != http.StatusOK {
        t.Fatalf("list status %d", listW.Code)
    }
    var all []Book
    if err := json.NewDecoder(listW.Body).Decode(&all); err != nil {
        t.Fatalf("decode all: %v", err)
    }
    if len(all) != 3 {
        t.Fatalf("expected 3 books got %d", len(all))
    }
    // Filter by author X
    filterReq := httptest.NewRequest("GET", "/books?author=X", nil)
    filterW := httptest.NewRecorder()
    router.ServeHTTP(filterW, filterReq)
    if filterW.Code != http.StatusOK {
        t.Fatalf("filter status %d", filterW.Code)
    }
    var filtered []Book
    if err := json.NewDecoder(filterW.Body).Decode(&filtered); err != nil {
        t.Fatalf("decode filtered: %v", err)
    }
    if len(filtered) != 2 {
        t.Fatalf("expected 2 books got %d", len(filtered))
    }
}

func TestUpdateAndDelete(t *testing.T) {
    app := setupTestApp(t)
    router := mux.NewRouter()
    router.HandleFunc("/books", app.handleCreate).Methods("POST")
    router.HandleFunc("/books/{id:[0-9]+}", app.handleUpdate).Methods("PUT")
    router.HandleFunc("/books/{id:[0-9]+}", app.handleDelete).Methods("DELETE")
    router.HandleFunc("/books/{id:[0-9]+}", app.handleGet).Methods("GET")

    // Create
    b := Book{Title: "Old", Author: "Auth"}
    payload, _ := json.Marshal(b)
    req := httptest.NewRequest("POST", "/books", bytes.NewReader(payload))
    w := httptest.NewRecorder()
    router.ServeHTTP(w, req)
    if w.Code != http.StatusCreated {
        t.Fatalf("create status %d", w.Code)
    }
    var created Book
    json.NewDecoder(w.Body).Decode(&created)

    // Update
    updated := Book{Title: "New", Author: "Auth", Year: 2021}
    updPayload, _ := json.Marshal(updated)
    updReq := httptest.NewRequest("PUT", "/books/"+strconv.Itoa(created.ID), bytes.NewReader(updPayload))
    updW := httptest.NewRecorder()
    router.ServeHTTP(updW, updReq)
    if updW.Code != http.StatusOK {
        t.Fatalf("update status %d", updW.Code)
    }
    var updResp Book
    json.NewDecoder(updW.Body).Decode(&updResp)
    if updResp.Title != "New" || updResp.Year != 2021 {
        t.Fatalf("update mismatch: %+v", updResp)
    }

    // Delete
    delReq := httptest.NewRequest("DELETE", "/books/"+strconv.Itoa(created.ID), nil)
    delW := httptest.NewRecorder()
    router.ServeHTTP(delW, delReq)
    if delW.Code != http.StatusNoContent {
        t.Fatalf("delete status %d", delW.Code)
    }

    // Get should 404
    getReq := httptest.NewRequest("GET", "/books/"+strconv.Itoa(created.ID), nil)
    getW := httptest.NewRecorder()
    router.ServeHTTP(getW, getReq)
    if getW.Code != http.StatusNotFound {
        t.Fatalf("expected 404 got %d", getW.Code)
    }
}

func TestHealth(t *testing.T) {
    app := setupTestApp(t)
    router := mux.NewRouter()
    router.HandleFunc("/health", app.handleHealth).Methods("GET")
    req := httptest.NewRequest("GET", "/health", nil)
    w := httptest.NewRecorder()
    router.ServeHTTP(w, req)
    if w.Code != http.StatusOK {
        t.Fatalf("health status %d", w.Code)
    }
    var resp map[string]string
    if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
        t.Fatalf("decode health: %v", err)
    }
    if resp["status"] != "ok" {
        t.Fatalf("health status not ok: %v", resp)
    }
}
