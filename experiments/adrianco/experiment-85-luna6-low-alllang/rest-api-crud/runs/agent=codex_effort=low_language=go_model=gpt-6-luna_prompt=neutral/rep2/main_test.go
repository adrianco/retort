package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func newTestAPI(t *testing.T) *API {
	t.Helper()
	db, err := openDB(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return &API{db: db}
}

func request(api *API, method, path string, body any) *httptest.ResponseRecorder {
	var data []byte
	if body != nil {
		data, _ = json.Marshal(body)
	}
	r := httptest.NewRequest(method, path, bytes.NewReader(data))
	w := httptest.NewRecorder()
	api.ServeHTTP(w, r)
	return w
}

func TestCreateAndGetBook(t *testing.T) {
	api := newTestAPI(t)
	created := request(api, http.MethodPost, "/books", Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"})
	if created.Code != http.StatusCreated {
		t.Fatalf("create status = %d, body %s", created.Code, created.Body)
	}
	var b Book
	if err := json.Unmarshal(created.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	if b.ID == 0 || b.Title != "Dune" {
		t.Fatalf("unexpected created book: %+v", b)
	}
	got := request(api, http.MethodGet, "/books/1", nil)
	if got.Code != http.StatusOK {
		t.Fatalf("get status = %d, body %s", got.Code, got.Body)
	}
}

func TestListAuthorFilterAndValidation(t *testing.T) {
	api := newTestAPI(t)
	for _, b := range []Book{{Title: "Dune", Author: "Frank Herbert"}, {Title: "Foundation", Author: "Isaac Asimov"}} {
		w := request(api, http.MethodPost, "/books", b)
		if w.Code != http.StatusCreated {
			t.Fatalf("create status = %d", w.Code)
		}
	}
	filtered := request(api, http.MethodGet, "/books?author=Frank%20Herbert", nil)
	var books []Book
	if err := json.Unmarshal(filtered.Body.Bytes(), &books); err != nil {
		t.Fatal(err)
	}
	if filtered.Code != http.StatusOK || len(books) != 1 || books[0].Author != "Frank Herbert" {
		t.Fatalf("unexpected filtered list: %d %+v", filtered.Code, books)
	}
	invalid := request(api, http.MethodPost, "/books", Book{Author: "Unknown"})
	if invalid.Code != http.StatusBadRequest {
		t.Fatalf("missing title status = %d", invalid.Code)
	}
}

func TestUpdateDeleteAndHealth(t *testing.T) {
	api := newTestAPI(t)
	created := request(api, http.MethodPost, "/books", Book{Title: "Old", Author: "Writer"})
	if created.Code != http.StatusCreated {
		t.Fatal(created.Code)
	}
	updated := request(api, http.MethodPut, "/books/1", Book{Title: "New", Author: "Writer", Year: 2024})
	if updated.Code != http.StatusOK {
		t.Fatalf("update status = %d", updated.Code)
	}
	deleted := request(api, http.MethodDelete, "/books/1", nil)
	if deleted.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d", deleted.Code)
	}
	missing := request(api, http.MethodGet, "/books/1", nil)
	if missing.Code != http.StatusNotFound {
		t.Fatalf("missing status = %d", missing.Code)
	}
	health := request(api, http.MethodGet, "/health", nil)
	if health.Code != http.StatusOK {
		t.Fatalf("health status = %d", health.Code)
	}
}
