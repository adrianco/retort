package main

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func testAPI(t *testing.T) http.Handler {
	t.Helper()
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	t.Cleanup(func() { db.Close() })
	api, err := NewAPI(db)
	if err != nil {
		t.Fatal(err)
	}
	return api.Routes()
}
func request(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func TestCreateAndGetBook(t *testing.T) {
	h := testAPI(t)
	created := request(h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}`)
	if created.Code != http.StatusCreated {
		t.Fatalf("create status = %d, body %s", created.Code, created.Body)
	}
	var b Book
	if err := json.Unmarshal(created.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	if b.ID == 0 || b.Title != "Dune" {
		t.Fatalf("unexpected book: %+v", b)
	}
	got := request(h, "GET", "/books/1", "")
	if got.Code != http.StatusOK {
		t.Fatalf("get status = %d", got.Code)
	}
}
func TestListFiltersByAuthor(t *testing.T) {
	h := testAPI(t)
	for _, body := range []string{`{"title":"Dune","author":"Frank Herbert"}`, `{"title":"Foundation","author":"Isaac Asimov"}`} {
		if w := request(h, "POST", "/books", body); w.Code != http.StatusCreated {
			t.Fatal(w.Body)
		}
	}
	w := request(h, "GET", "/books?author=Frank%20Herbert", "")
	var books []Book
	if w.Code != http.StatusOK {
		t.Fatalf("status %d", w.Code)
	}
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
		t.Fatal(err)
	}
	if len(books) != 1 || books[0].Author != "Frank Herbert" {
		t.Fatalf("unexpected results: %+v", books)
	}
}
func TestValidationAndUpdateDelete(t *testing.T) {
	h := testAPI(t)
	bad := request(h, "POST", "/books", `{"title":"No author"}`)
	if bad.Code != http.StatusBadRequest {
		t.Fatalf("validation status = %d", bad.Code)
	}
	created := request(h, "POST", "/books", `{"title":"Old","author":"Writer"}`)
	if created.Code != http.StatusCreated {
		t.Fatal(created.Body)
	}
	updated := request(h, "PUT", "/books/1", `{"title":"New","author":"Writer","year":2000}`)
	if updated.Code != http.StatusOK {
		t.Fatalf("update status = %d: %s", updated.Code, updated.Body)
	}
	deleted := request(h, "DELETE", "/books/1", "")
	if deleted.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d", deleted.Code)
	}
	missing := request(h, "GET", "/books/1", "")
	if missing.Code != http.StatusNotFound {
		t.Fatalf("missing status = %d", missing.Code)
	}
}
func TestHealth(t *testing.T) {
	if w := request(testAPI(t), "GET", "/health", ""); w.Code != http.StatusOK {
		t.Fatalf("health status = %d", w.Code)
	}
}
