package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"testing"

	_ "modernc.org/sqlite"
)

func testServer(t *testing.T) http.Handler {
	t.Helper()
	db, err := sql.Open("sqlite", filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatal(err)
	}
	if err := initialize(db); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return newServer(db)
}

func request(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var data []byte
	if body != nil {
		var err error
		data, err = json.Marshal(body)
		if err != nil {
			t.Fatal(err)
		}
	}
	r := httptest.NewRequest(method, path, bytes.NewReader(data))
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func TestCreateAndGetBook(t *testing.T) {
	h := testServer(t)
	created := request(t, h, http.MethodPost, "/books", Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"})
	if created.Code != http.StatusCreated {
		t.Fatalf("POST status = %d, body %s", created.Code, created.Body)
	}
	var b Book
	if err := json.Unmarshal(created.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	if b.ID == 0 || b.Title != "Dune" {
		t.Fatalf("unexpected created book: %+v", b)
	}
	got := request(t, h, http.MethodGet, "/books/"+strconv.FormatInt(b.ID, 10), nil)
	if got.Code != http.StatusOK {
		t.Fatalf("GET status = %d, body %s", got.Code, got.Body)
	}
}

func TestFilterUpdateAndDeleteBooks(t *testing.T) {
	h := testServer(t)
	created := request(t, h, http.MethodPost, "/books", Book{Title: "Dune", Author: "Frank Herbert"})
	var b Book
	if err := json.Unmarshal(created.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	path := "/books/" + strconv.FormatInt(b.ID, 10)
	filtered := request(t, h, http.MethodGet, "/books?author=Frank%20Herbert", nil)
	var list []Book
	if filtered.Code != http.StatusOK || json.Unmarshal(filtered.Body.Bytes(), &list) != nil || len(list) != 1 {
		t.Fatalf("author filter failed: status %d, body %s", filtered.Code, filtered.Body)
	}
	updated := request(t, h, http.MethodPut, path, Book{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969})
	if updated.Code != http.StatusOK {
		t.Fatalf("PUT status = %d, body %s", updated.Code, updated.Body)
	}
	deleted := request(t, h, http.MethodDelete, path, nil)
	if deleted.Code != http.StatusNoContent {
		t.Fatalf("DELETE status = %d", deleted.Code)
	}
	missing := request(t, h, http.MethodGet, path, nil)
	if missing.Code != http.StatusNotFound {
		t.Fatalf("deleted book GET status = %d", missing.Code)
	}
}

func TestValidationAndHealth(t *testing.T) {
	h := testServer(t)
	invalid := request(t, h, http.MethodPost, "/books", Book{Title: "No author"})
	if invalid.Code != http.StatusBadRequest {
		t.Fatalf("invalid POST status = %d", invalid.Code)
	}
	if got := request(t, h, http.MethodGet, "/health", nil).Code; got != http.StatusOK {
		t.Fatalf("health status = %d", got)
	}
}
