package main

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"

	_ "github.com/mattn/go-sqlite3"
)

func testServer(t *testing.T) http.Handler {
	t.Helper()
	db, err := sql.Open("sqlite3", "file:"+t.Name()+"?mode=memory&cache=shared")
	if err != nil {
		t.Fatal(err)
	}
	if err := initialize(db); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return newAPI(db)
}

func request(t *testing.T, handler http.Handler, method, url, body string) *httptest.ResponseRecorder {
	t.Helper()
	res := httptest.NewRecorder()
	handler.ServeHTTP(res, mustRequest(t, method, url, body))
	return res
}

func mustRequest(t *testing.T, method, url, body string) *http.Request {
	t.Helper()
	r, err := http.NewRequest(method, url, strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	if body != "" {
		r.Header.Set("Content-Type", "application/json")
	}
	return r
}

func TestCreateAndFilterBooks(t *testing.T) {
	s := testServer(t)
	res := request(t, s, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if res.Code != http.StatusCreated {
		t.Fatalf("create status = %d", res.Code)
	}
	var created Book
	if err := json.NewDecoder(res.Body).Decode(&created); err != nil {
		t.Fatal(err)
	}
	if created.ID == 0 || created.Title != "Dune" {
		t.Fatalf("unexpected book: %+v", created)
	}
	res = request(t, s, http.MethodGet, "/books?author=Frank%20Herbert", "")
	var books []Book
	if err := json.NewDecoder(res.Body).Decode(&books); err != nil {
		t.Fatal(err)
	}
	if res.Code != http.StatusOK || len(books) != 1 || books[0].ID != created.ID {
		t.Fatalf("unexpected filter result: status %d, books %+v", res.Code, books)
	}
}

func TestRequiredFieldsAreValidated(t *testing.T) {
	s := testServer(t)
	for _, body := range []string{`{"title":"Only title"}`, `{"author":"Only author"}`, `not-json`} {
		res := request(t, s, http.MethodPost, "/books", body)
		if res.Code != http.StatusBadRequest {
			t.Errorf("body %q: status = %d, want 400", body, res.Code)
		}
	}
}

func TestBookLifecycleAndNotFound(t *testing.T) {
	s := testServer(t)
	res := request(t, s, http.MethodPost, "/books", `{"title":"Old","author":"A","year":2000}`)
	var b Book
	if err := json.NewDecoder(res.Body).Decode(&b); err != nil {
		t.Fatal(err)
	}
	id := strconv.FormatInt(b.ID, 10)
	res = request(t, s, http.MethodGet, "/books/"+id, "")
	if res.Code != http.StatusOK {
		t.Fatalf("get status = %d", res.Code)
	}
	res = request(t, s, http.MethodPut, "/books/"+id, `{"title":"New","author":"B","year":2024,"isbn":"X"}`)
	if res.Code != http.StatusOK {
		t.Fatalf("update status = %d", res.Code)
	}
	var updated Book
	if err := json.NewDecoder(res.Body).Decode(&updated); err != nil {
		t.Fatal(err)
	}
	if updated.Title != "New" || updated.Author != "B" {
		t.Fatalf("unexpected updated book: %+v", updated)
	}
	res = request(t, s, http.MethodDelete, "/books/"+id, "")
	if res.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d", res.Code)
	}
	res = request(t, s, http.MethodGet, "/books/"+id, "")
	if res.Code != http.StatusNotFound {
		t.Fatalf("missing book status = %d", res.Code)
	}
}
