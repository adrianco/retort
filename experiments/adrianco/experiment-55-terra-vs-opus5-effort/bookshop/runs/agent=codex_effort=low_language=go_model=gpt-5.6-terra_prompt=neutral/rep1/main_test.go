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

func testHandler(t *testing.T) http.Handler {
	t.Helper()
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	a, err := newAPI(db)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return a.routes()
}

func request(t *testing.T, h http.Handler, method, path, body string) *http.Response {
	t.Helper()
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	r.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w.Result()
}

func TestCreateGetUpdateDeleteBook(t *testing.T) {
	h := testHandler(t)
	resp := request(t, h, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d", resp.StatusCode)
	}
	var created Book
	json.NewDecoder(resp.Body).Decode(&created)
	if created.ID == 0 {
		t.Fatal("missing id")
	}
	resp = request(t, h, http.MethodGet, "/books/1", "")
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("get status = %d", resp.StatusCode)
	}
	resp = request(t, h, http.MethodPut, "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"x"}`)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("update status = %d", resp.StatusCode)
	}
	resp = request(t, h, http.MethodDelete, "/books/1", "")
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete status = %d", resp.StatusCode)
	}
}

func TestListFiltersByAuthor(t *testing.T) {
	h := testHandler(t)
	request(t, h, http.MethodPost, "/books", `{"title":"A","author":"Ursula"}`).Body.Close()
	request(t, h, http.MethodPost, "/books", `{"title":"B","author":"Octavia"}`).Body.Close()
	resp := request(t, h, http.MethodGet, "/books?author=Ursula", "")
	defer resp.Body.Close()
	var books []Book
	json.NewDecoder(resp.Body).Decode(&books)
	if resp.StatusCode != http.StatusOK || len(books) != 1 || books[0].Title != "A" {
		t.Fatalf("unexpected filtered result: status %d, %#v", resp.StatusCode, books)
	}
}

func TestCreateRequiresTitleAndAuthor(t *testing.T) {
	h := testHandler(t)
	resp := request(t, h, http.MethodPost, "/books", `{"title":"Only title"}`)
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", resp.StatusCode)
	}
}

func TestHealth(t *testing.T) {
	h := testHandler(t)
	resp := request(t, h, http.MethodGet, "/health", "")
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d", resp.StatusCode)
	}
}
