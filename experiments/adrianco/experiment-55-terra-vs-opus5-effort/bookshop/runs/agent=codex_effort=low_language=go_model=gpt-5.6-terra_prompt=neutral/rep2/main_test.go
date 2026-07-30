package main

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	_ "github.com/mattn/go-sqlite3"
)

func testAPI(t *testing.T) *API {
	t.Helper()
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	api, err := NewAPI(db)
	if err != nil {
		t.Fatal(err)
	}
	return api
}
func request(api *API, method, path, body string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	w := httptest.NewRecorder()
	api.ServeHTTP(w, r)
	return w
}

func TestBookCRUD(t *testing.T) {
	api := testAPI(t)
	w := request(api, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	if w.Code != http.StatusCreated {
		t.Fatalf("create: got %d: %s", w.Code, w.Body.String())
	}
	var created Book
	json.NewDecoder(w.Body).Decode(&created)
	if created.ID == 0 || created.Title != "Dune" {
		t.Fatalf("unexpected created book: %#v", created)
	}
	w = request(api, http.MethodPut, "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"x"}`)
	if w.Code != http.StatusOK {
		t.Fatalf("update: got %d: %s", w.Code, w.Body.String())
	}
	w = request(api, http.MethodGet, "/books/1", "")
	if w.Code != http.StatusOK || !strings.Contains(w.Body.String(), "Dune Messiah") {
		t.Fatalf("get: got %d: %s", w.Code, w.Body.String())
	}
	w = request(api, http.MethodDelete, "/books/1", "")
	if w.Code != http.StatusNoContent {
		t.Fatalf("delete: got %d", w.Code)
	}
}

func TestListFiltersByAuthor(t *testing.T) {
	api := testAPI(t)
	request(api, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert"}`)
	request(api, http.MethodPost, "/books", `{"title":"Foundation","author":"Isaac Asimov"}`)
	w := request(api, http.MethodGet, "/books?author=Frank%20Herbert", "")
	if w.Code != http.StatusOK || !strings.Contains(w.Body.String(), "Dune") || strings.Contains(w.Body.String(), "Foundation") {
		t.Fatalf("filter: got %d: %s", w.Code, w.Body.String())
	}
}

func TestValidationAndHealth(t *testing.T) {
	api := testAPI(t)
	w := request(api, http.MethodPost, "/books", `{"title":""}`)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("validation: got %d", w.Code)
	}
	w = request(api, http.MethodGet, "/health", "")
	if w.Code != http.StatusOK || w.Body.String() != "{\"status\":\"ok\"}\n" {
		t.Fatalf("health: got %d: %s", w.Code, w.Body.String())
	}
}
