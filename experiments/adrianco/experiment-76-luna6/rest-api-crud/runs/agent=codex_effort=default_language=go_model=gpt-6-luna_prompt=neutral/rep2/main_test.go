package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	_ "github.com/mattn/go-sqlite3"
)

func newTestAPI(t *testing.T) *API {
	t.Helper()
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	api, err := NewAPI(db)
	if err != nil {
		db.Close()
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return api
}
func request(api http.Handler, method, path, body string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, bytes.NewBufferString(body))
	w := httptest.NewRecorder()
	api.ServeHTTP(w, r)
	return w
}

func TestCreateListAndFilterBooks(t *testing.T) {
	api := newTestAPI(t)
	w := request(api, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	if w.Code != http.StatusCreated {
		t.Fatalf("create status=%d body=%s", w.Code, w.Body)
	}
	var created Book
	if err := json.Unmarshal(w.Body.Bytes(), &created); err != nil {
		t.Fatal(err)
	}
	if created.ID == 0 || created.Title != "Dune" {
		t.Fatalf("unexpected book: %+v", created)
	}
	request(api, http.MethodPost, "/books", `{"title":"Foundation","author":"Isaac Asimov"}`)
	w = request(api, http.MethodGet, "/books?author=Frank%20Herbert", "")
	if w.Code != http.StatusOK {
		t.Fatalf("list status=%d", w.Code)
	}
	var books []Book
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
		t.Fatal(err)
	}
	if len(books) != 1 || books[0].Title != "Dune" {
		t.Fatalf("unexpected filtered books: %+v", books)
	}
}

func TestValidationAndNotFound(t *testing.T) {
	api := newTestAPI(t)
	w := request(api, http.MethodPost, "/books", `{"title":" ","author":"Author"}`)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
	w = request(api, http.MethodGet, "/books/99", "")
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", w.Code)
	}
}

func TestUpdateAndDeleteBook(t *testing.T) {
	api := newTestAPI(t)
	w := request(api, http.MethodPost, "/books", `{"title":"Old","author":"Writer"}`)
	var b Book
	if err := json.Unmarshal(w.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	w = request(api, http.MethodPut, "/books/"+stringID(b.ID), `{"title":"New","author":"Writer","year":2024}`)
	if w.Code != http.StatusOK {
		t.Fatalf("update status=%d body=%s", w.Code, w.Body)
	}
	w = request(api, http.MethodDelete, "/books/"+stringID(b.ID), "")
	if w.Code != http.StatusNoContent {
		t.Fatalf("delete status=%d", w.Code)
	}
	w = request(api, http.MethodGet, "/books/"+stringID(b.ID), "")
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected deleted record 404, got %d", w.Code)
	}
}

func TestHealthCheck(t *testing.T) {
	api := newTestAPI(t)
	w := request(api, http.MethodGet, "/health", "")
	if w.Code != http.StatusOK {
		t.Fatalf("health status=%d", w.Code)
	}
}

func stringID(id int64) string { return strconv.FormatInt(id, 10) }
