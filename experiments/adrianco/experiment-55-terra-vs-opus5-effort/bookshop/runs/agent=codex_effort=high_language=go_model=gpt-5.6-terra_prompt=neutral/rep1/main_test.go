package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func newTestHandler(t *testing.T) http.Handler {
	t.Helper()
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	_, err = db.Exec(`CREATE TABLE books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`)
	if err != nil {
		db.Close()
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return NewHandler(db)
}

func request(t *testing.T, h http.Handler, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, target, bytes.NewBufferString(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	response := httptest.NewRecorder()
	h.ServeHTTP(response, req)
	return response
}

func createBook(t *testing.T, h http.Handler, title, author string) Book {
	t.Helper()
	response := request(t, h, http.MethodPost, "/books", `{"title":"`+title+`","author":"`+author+`","year":2024,"isbn":"123"}`)
	if response.Code != http.StatusCreated {
		t.Fatalf("create status = %d, body = %s", response.Code, response.Body.String())
	}
	var book Book
	if err := json.NewDecoder(response.Body).Decode(&book); err != nil {
		t.Fatal(err)
	}
	return book
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestHandler(t)
	created := createBook(t, h, "Kindred", "Octavia E. Butler")
	if created.ID == 0 || created.Year != 2024 {
		t.Fatalf("unexpected created book: %#v", created)
	}

	response := request(t, h, http.MethodGet, "/books/1", "")
	if response.Code != http.StatusOK {
		t.Fatalf("get status = %d, body = %s", response.Code, response.Body.String())
	}
	var got Book
	if err := json.NewDecoder(response.Body).Decode(&got); err != nil {
		t.Fatal(err)
	}
	if got != created {
		t.Fatalf("got %#v, want %#v", got, created)
	}
}

func TestListBooksFiltersByAuthor(t *testing.T) {
	h := newTestHandler(t)
	createBook(t, h, "Parable of the Sower", "Octavia E. Butler")
	createBook(t, h, "The Dispossessed", "Ursula K. Le Guin")
	createBook(t, h, "Fledgling", "Octavia E. Butler")

	response := request(t, h, http.MethodGet, "/books?author=Octavia%20E.%20Butler", "")
	if response.Code != http.StatusOK {
		t.Fatalf("list status = %d, body = %s", response.Code, response.Body.String())
	}
	var books []Book
	if err := json.NewDecoder(response.Body).Decode(&books); err != nil {
		t.Fatal(err)
	}
	if len(books) != 2 || books[0].Title != "Parable of the Sower" || books[1].Title != "Fledgling" {
		t.Fatalf("unexpected filtered books: %#v", books)
	}
}

func TestUpdateDeleteAndValidation(t *testing.T) {
	h := newTestHandler(t)
	created := createBook(t, h, "Old Title", "Author")

	invalid := request(t, h, http.MethodPost, "/books", `{"title":"","author":"Author"}`)
	if invalid.Code != http.StatusBadRequest {
		t.Fatalf("invalid create status = %d", invalid.Code)
	}

	updated := request(t, h, http.MethodPut, "/books/1", `{"title":"New Title","author":"New Author","year":1999,"isbn":"updated"}`)
	if updated.Code != http.StatusOK {
		t.Fatalf("update status = %d, body = %s", updated.Code, updated.Body.String())
	}

	deleted := request(t, h, http.MethodDelete, "/books/"+jsonNumber(created.ID), "")
	if deleted.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, body = %s", deleted.Code, deleted.Body.String())
	}
	notFound := request(t, h, http.MethodGet, "/books/1", "")
	if notFound.Code != http.StatusNotFound {
		t.Fatalf("get after delete status = %d", notFound.Code)
	}
}

func TestHealth(t *testing.T) {
	response := request(t, newTestHandler(t), http.MethodGet, "/health", "")
	if response.Code != http.StatusOK || response.Body.String() != "{\"status\":\"ok\"}\n" {
		t.Fatalf("health response = %d %q", response.Code, response.Body.String())
	}
}

func jsonNumber(id int64) string {
	return strconv.FormatInt(id, 10)
}
