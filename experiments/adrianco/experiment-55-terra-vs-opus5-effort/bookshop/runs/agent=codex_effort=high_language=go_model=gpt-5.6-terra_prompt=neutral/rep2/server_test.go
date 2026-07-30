package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	_ "modernc.org/sqlite"
)

func newTestServer(t *testing.T) (http.Handler, *sql.DB) {
	t.Helper()
	db, err := OpenDatabase(":memory:")
	if err != nil {
		t.Fatalf("OpenDatabase: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	return NewServer(db), db
}

func performRequest(t *testing.T, handler http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, bytes.NewBufferString(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	res := httptest.NewRecorder()
	handler.ServeHTTP(res, req)
	return res
}

func decodeBook(t *testing.T, res *httptest.ResponseRecorder) Book {
	t.Helper()
	var book Book
	if err := json.NewDecoder(res.Body).Decode(&book); err != nil {
		t.Fatalf("decode book: %v; response=%q", err, res.Body.String())
	}
	return book
}

func TestBookCRUD(t *testing.T) {
	handler, _ := newTestServer(t)

	created := performRequest(t, handler, http.MethodPost, "/books", `{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}`)
	if created.Code != http.StatusCreated {
		t.Fatalf("POST status = %d, body = %s", created.Code, created.Body.String())
	}
	book := decodeBook(t, created)
	if book.ID == 0 || book.Title != "Kindred" {
		t.Fatalf("unexpected created book: %#v", book)
	}

	fetched := performRequest(t, handler, http.MethodGet, "/books/1", "")
	if fetched.Code != http.StatusOK {
		t.Fatalf("GET status = %d, body = %s", fetched.Code, fetched.Body.String())
	}
	if got := decodeBook(t, fetched); got != book {
		t.Fatalf("GET returned %#v, want %#v", got, book)
	}

	updated := performRequest(t, handler, http.MethodPut, "/books/1", `{"title":"Parable of the Sower","author":"Octavia E. Butler","year":1993,"isbn":"9780446675505"}`)
	if updated.Code != http.StatusOK {
		t.Fatalf("PUT status = %d, body = %s", updated.Code, updated.Body.String())
	}
	if got := decodeBook(t, updated); got.Title != "Parable of the Sower" || got.Year != 1993 {
		t.Fatalf("unexpected updated book: %#v", got)
	}

	deleted := performRequest(t, handler, http.MethodDelete, "/books/1", "")
	if deleted.Code != http.StatusNoContent {
		t.Fatalf("DELETE status = %d, body = %s", deleted.Code, deleted.Body.String())
	}
	missing := performRequest(t, handler, http.MethodGet, "/books/1", "")
	if missing.Code != http.StatusNotFound {
		t.Fatalf("GET deleted book status = %d", missing.Code)
	}
}

func TestListBooksCanFilterByAuthor(t *testing.T) {
	handler, _ := newTestServer(t)
	for _, body := range []string{
		`{"title":"Kindred","author":"Octavia E. Butler"}`,
		`{"title":"Dawn","author":"Octavia E. Butler"}`,
		`{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin"}`,
	} {
		if res := performRequest(t, handler, http.MethodPost, "/books", body); res.Code != http.StatusCreated {
			t.Fatalf("POST status = %d, body = %s", res.Code, res.Body.String())
		}
	}

	res := performRequest(t, handler, http.MethodGet, "/books?author=Octavia%20E.%20Butler", "")
	if res.Code != http.StatusOK {
		t.Fatalf("GET status = %d, body = %s", res.Code, res.Body.String())
	}
	var books []Book
	if err := json.NewDecoder(res.Body).Decode(&books); err != nil {
		t.Fatal(err)
	}
	if len(books) != 2 || books[0].Author != "Octavia E. Butler" || books[1].Author != "Octavia E. Butler" {
		t.Fatalf("filtered books = %#v", books)
	}
}

func TestValidationAndHealth(t *testing.T) {
	handler, _ := newTestServer(t)

	invalid := performRequest(t, handler, http.MethodPost, "/books", `{"title":"   ","author":""}`)
	if invalid.Code != http.StatusBadRequest {
		t.Fatalf("invalid POST status = %d, body = %s", invalid.Code, invalid.Body.String())
	}
	if got := invalid.Header().Get("Content-Type"); got != "application/json; charset=utf-8" {
		t.Fatalf("content type = %q", got)
	}

	health := performRequest(t, handler, http.MethodGet, "/health", "")
	if health.Code != http.StatusOK {
		t.Fatalf("health status = %d", health.Code)
	}
	var status map[string]string
	if err := json.NewDecoder(health.Body).Decode(&status); err != nil {
		t.Fatal(err)
	}
	if status["status"] != "ok" {
		t.Fatalf("health response = %#v", status)
	}
}
