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

func testHandler(t *testing.T) http.Handler {
	t.Helper()
	db, err := sql.Open("sqlite", "file:"+t.Name()+"?mode=memory&cache=shared")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	a, err := newAPI(db)
	if err != nil {
		t.Fatal(err)
	}
	return a.routes()
}

func request(t *testing.T, handler http.Handler, method, path, body string) *http.Response {
	t.Helper()
	r, err := http.NewRequest(method, path, bytes.NewBufferString(body))
	if err != nil {
		t.Fatal(err)
	}
	r.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, r)
	return w.Result()
}

func TestCreateAndGetBook(t *testing.T) {
	h := testHandler(t)
	resp := request(t, h, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("POST status = %d", resp.StatusCode)
	}
	var created Book
	json.NewDecoder(resp.Body).Decode(&created)
	if created.ID == 0 || created.Title != "Dune" {
		t.Fatalf("created = %#v", created)
	}
	get := request(t, h, http.MethodGet, "/books/1", "")
	defer get.Body.Close()
	if get.StatusCode != http.StatusOK {
		t.Fatalf("GET status = %d", get.StatusCode)
	}
}

func TestAuthorFilterAndUpdate(t *testing.T) {
	h := testHandler(t)
	for _, payload := range []string{`{"title":"A","author":"Octavia Butler"}`, `{"title":"B","author":"Other"}`} {
		resp := request(t, h, http.MethodPost, "/books", payload)
		resp.Body.Close()
	}
	filtered := request(t, h, http.MethodGet, "/books?author=Octavia%20Butler", "")
	defer filtered.Body.Close()
	var books []Book
	json.NewDecoder(filtered.Body).Decode(&books)
	if filtered.StatusCode != http.StatusOK || len(books) != 1 || books[0].Title != "A" {
		t.Fatalf("filter result = %#v, status = %d", books, filtered.StatusCode)
	}
	updated := request(t, h, http.MethodPut, "/books/1", `{"title":"Kindred","author":"Octavia Butler","year":1979}`)
	defer updated.Body.Close()
	if updated.StatusCode != http.StatusOK {
		t.Fatalf("PUT status = %d", updated.StatusCode)
	}
}

func TestValidationDeleteAndHealth(t *testing.T) {
	h := testHandler(t)
	invalid := request(t, h, http.MethodPost, "/books", `{"title":"Only a title"}`)
	invalid.Body.Close()
	if invalid.StatusCode != http.StatusBadRequest {
		t.Fatalf("validation status = %d", invalid.StatusCode)
	}
	created := request(t, h, http.MethodPost, "/books", `{"title":"A","author":"B"}`)
	created.Body.Close()
	deleted := request(t, h, http.MethodDelete, "/books/1", "")
	deleted.Body.Close()
	if deleted.StatusCode != http.StatusNoContent {
		t.Fatalf("DELETE status = %d", deleted.StatusCode)
	}
	health := request(t, h, http.MethodGet, "/health", "")
	defer health.Body.Close()
	if health.StatusCode != http.StatusOK {
		t.Fatalf("health status = %d", health.StatusCode)
	}
}
