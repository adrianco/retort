package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func setup(t *testing.T) (http.Handler, string) {
	t.Helper()
	path := filepath.Join(t.TempDir(), "books.db")
	db, err := openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return (&server{db}).routes(), path
}
func request(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}
func createBook(t *testing.T, h http.Handler, body string) book {
	t.Helper()
	w := request(h, "POST", "/books", body)
	if w.Code != 201 {
		t.Fatalf("create: %d %s", w.Code, w.Body)
	}
	var b book
	if err := json.Unmarshal(w.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	return b
}
func TestCRUDAndPersistence(t *testing.T) {
	h, path := setup(t)
	b := createBook(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}`)
	url := fmt.Sprintf("/books/%d", b.ID)
	w := request(h, "GET", url, "")
	if w.Code != 200 || !strings.Contains(w.Body.String(), `"title":"Dune"`) {
		t.Fatalf("get: %d %s", w.Code, w.Body)
	}
	w = request(h, "PUT", url, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"456"}`)
	if w.Code != 200 {
		t.Fatalf("update: %d %s", w.Code, w.Body)
	}
	db, err := openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	w = request((&server{db}).routes(), "GET", url, "")
	if w.Code != 200 || !strings.Contains(w.Body.String(), "Dune Messiah") {
		t.Fatalf("persisted get: %d %s", w.Code, w.Body)
	}
	w = request(h, "DELETE", url, "")
	if w.Code != 204 {
		t.Fatalf("delete: %d", w.Code)
	}
	if w = request(h, "GET", url, ""); w.Code != 404 {
		t.Fatalf("deleted get: %d", w.Code)
	}
	if w = request(h, "DELETE", url, ""); w.Code != 404 {
		t.Fatalf("repeated delete: %d", w.Code)
	}
}
func TestListAndFilter(t *testing.T) {
	h, _ := setup(t)
	if w := request(h, "GET", "/books", ""); w.Code != 200 || strings.TrimSpace(w.Body.String()) != "[]" {
		t.Fatalf("empty list: %d %s", w.Code, w.Body)
	}
	createBook(t, h, `{"title":"One","author":"Alice"}`)
	createBook(t, h, `{"title":"Two","author":"Bob"}`)
	w := request(h, "GET", "/books?author=Alice", "")
	var books []book
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil || len(books) != 1 || books[0].Title != "One" {
		t.Fatalf("filter: %d %s", w.Code, w.Body)
	}
}
func TestValidationAndHealth(t *testing.T) {
	h, _ := setup(t)
	for _, body := range []string{`{}`, `{"title":" ","author":"A"}`, `{"title":"T"}`, `{`, `{"title":"T","author":"A"} {}`} {
		if w := request(h, "POST", "/books", body); w.Code != 400 {
			t.Errorf("body %q: %d", body, w.Code)
		}
	}
	if w := request(h, "GET", "/books/nope", ""); w.Code != 400 {
		t.Errorf("invalid id: %d", w.Code)
	}
	if w := request(h, "PUT", "/books/999", `{"title":"T","author":"A"}`); w.Code != 404 {
		t.Errorf("missing update: %d", w.Code)
	}
	if w := request(h, "GET", "/health", ""); w.Code != 200 || !strings.Contains(w.Body.String(), `"ok"`) {
		t.Errorf("health: %d %s", w.Code, w.Body)
	}
}
