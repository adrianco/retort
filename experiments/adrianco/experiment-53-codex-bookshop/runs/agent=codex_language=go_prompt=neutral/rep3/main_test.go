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

func testServer(t *testing.T) *Server {
	t.Helper()
	db, err := sql.Open("sqlite", "file:test?mode=memory&cache=shared")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	server, err := NewServer(db)
	if err != nil {
		t.Fatal(err)
	}
	return server
}

func request(server *Server, method, path string, body []byte) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	result := httptest.NewRecorder()
	server.ServeHTTP(result, req)
	return result
}

func TestCreateGetAndFilterBooks(t *testing.T) {
	server := testServer(t)
	created := request(server, http.MethodPost, "/books", []byte(`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`))
	if created.Code != http.StatusCreated {
		t.Fatalf("create status = %d", created.Code)
	}
	var book Book
	if err := json.Unmarshal(created.Body.Bytes(), &book); err != nil {
		t.Fatal(err)
	}
	if book.ID == 0 || book.Title != "Dune" {
		t.Fatalf("unexpected book: %+v", book)
	}
	list := request(server, http.MethodGet, "/books?author=Frank%20Herbert", nil)
	if list.Code != http.StatusOK || !bytes.Contains(list.Body.Bytes(), []byte("Dune")) {
		t.Fatalf("unexpected filtered response: %d %s", list.Code, list.Body.String())
	}
}

func TestValidationAndNotFound(t *testing.T) {
	server := testServer(t)
	invalid := request(server, http.MethodPost, "/books", []byte(`{"title":"","author":"Someone"}`))
	if invalid.Code != http.StatusBadRequest {
		t.Fatalf("validation status = %d", invalid.Code)
	}
	missing := request(server, http.MethodGet, "/books/999", nil)
	if missing.Code != http.StatusNotFound {
		t.Fatalf("missing status = %d", missing.Code)
	}
}

func TestUpdateAndDeleteBook(t *testing.T) {
	server := testServer(t)
	created := request(server, http.MethodPost, "/books", []byte(`{"title":"Old","author":"A"}`))
	var book Book
	_ = json.Unmarshal(created.Body.Bytes(), &book)
	updated := request(server, http.MethodPut, "/books/1", []byte(`{"title":"New","author":"B","year":2024}`))
	if updated.Code != http.StatusOK || !bytes.Contains(updated.Body.Bytes(), []byte("New")) {
		t.Fatalf("update response: %d %s", updated.Code, updated.Body.String())
	}
	deleted := request(server, http.MethodDelete, "/books/1", nil)
	if deleted.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d", deleted.Code)
	}
	if got := request(server, http.MethodGet, "/books/1", nil).Code; got != http.StatusNotFound {
		t.Fatalf("post-delete status = %d", got)
	}
}

func TestHealth(t *testing.T) {
	server := testServer(t)
	response := request(server, http.MethodGet, "/health", nil)
	if response.Code != http.StatusOK || !bytes.Contains(response.Body.Bytes(), []byte(`"status":"ok"`)) {
		t.Fatalf("health response: %d %s", response.Code, response.Body.String())
	}
}
