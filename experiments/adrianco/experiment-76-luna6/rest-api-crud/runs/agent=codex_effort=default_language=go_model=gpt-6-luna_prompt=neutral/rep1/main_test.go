package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func testServer(t *testing.T) http.Handler {
	t.Helper()
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	if err := initDB(db); err != nil {
		db.Close()
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return newAPI(db)
}

func request(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var payload bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&payload).Encode(body); err != nil {
			t.Fatal(err)
		}
	}
	req := httptest.NewRequest(method, path, &payload)
	res := httptest.NewRecorder()
	h.ServeHTTP(res, req)
	return res
}

func TestCreateBookAndGetByID(t *testing.T) {
	h := testServer(t)
	created := request(t, h, http.MethodPost, "/books", map[string]any{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"})
	if created.Code != http.StatusCreated {
		t.Fatalf("POST /books status = %d, body %s", created.Code, created.Body)
	}
	var book Book
	if err := json.Unmarshal(created.Body.Bytes(), &book); err != nil {
		t.Fatal(err)
	}
	if book.ID == 0 || book.Title != "Dune" || book.Author != "Frank Herbert" {
		t.Fatalf("unexpected created book: %+v", book)
	}
	got := request(t, h, http.MethodGet, "/books/1", nil)
	if got.Code != http.StatusOK {
		t.Fatalf("GET /books/1 status = %d, body %s", got.Code, got.Body)
	}
}

func TestCreateRequiresTitleAndAuthor(t *testing.T) {
	h := testServer(t)
	for _, body := range []any{
		map[string]any{"title": "Only a title"},
		map[string]any{"author": "Only an author"},
		map[string]any{"title": "  ", "author": "Author"},
	} {
		res := request(t, h, http.MethodPost, "/books", body)
		if res.Code != http.StatusBadRequest {
			t.Errorf("POST invalid book status = %d, want %d", res.Code, http.StatusBadRequest)
		}
	}
}

func TestListBooksFiltersByAuthor(t *testing.T) {
	h := testServer(t)
	for _, b := range []map[string]any{
		{"title": "Dune", "author": "Frank Herbert"},
		{"title": "The Hobbit", "author": "J.R.R. Tolkien"},
		{"title": "Children of Dune", "author": "Frank Herbert"},
	} {
		if res := request(t, h, http.MethodPost, "/books", b); res.Code != http.StatusCreated {
			t.Fatalf("create failed: %d %s", res.Code, res.Body)
		}
	}
	res := request(t, h, http.MethodGet, "/books?author=Frank%20Herbert", nil)
	if res.Code != http.StatusOK {
		t.Fatalf("GET /books status = %d", res.Code)
	}
	var books []Book
	if err := json.Unmarshal(res.Body.Bytes(), &books); err != nil {
		t.Fatal(err)
	}
	if len(books) != 2 || books[0].Author != "Frank Herbert" || books[1].Author != "Frank Herbert" {
		t.Fatalf("unexpected filtered books: %+v", books)
	}
}

func TestUpdateDeleteAndNotFound(t *testing.T) {
	h := testServer(t)
	request(t, h, http.MethodPost, "/books", map[string]any{"title": "Old", "author": "Writer"})
	updated := request(t, h, http.MethodPut, "/books/1", map[string]any{"title": "New", "author": "Writer", "year": 2024})
	if updated.Code != http.StatusOK {
		t.Fatalf("PUT status = %d, body %s", updated.Code, updated.Body)
	}
	deleted := request(t, h, http.MethodDelete, "/books/1", nil)
	if deleted.Code != http.StatusNoContent {
		t.Fatalf("DELETE status = %d, want %d", deleted.Code, http.StatusNoContent)
	}
	missing := request(t, h, http.MethodGet, "/books/1", nil)
	if missing.Code != http.StatusNotFound {
		t.Fatalf("GET deleted book status = %d, want %d", missing.Code, http.StatusNotFound)
	}
}

func TestHealth(t *testing.T) {
	res := request(t, testServer(t), http.MethodGet, "/health", nil)
	if res.Code != http.StatusOK {
		t.Fatalf("GET /health status = %d, want %d", res.Code, http.StatusOK)
	}
}
