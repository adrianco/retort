package main

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	_ "modernc.org/sqlite"
)

func testServer(t *testing.T) *Server {
	t.Helper()
	db, err := sql.Open("sqlite", "file:"+t.Name()+"?mode=memory&cache=shared")
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	t.Cleanup(func() { db.Close() })
	s, err := NewServer(db)
	if err != nil {
		t.Fatal(err)
	}
	return s
}

func request(s *Server, method, path, body string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	return w
}

func TestCreateAndGetBook(t *testing.T) {
	s := testServer(t)
	w := request(s, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	if w.Code != http.StatusCreated {
		t.Fatalf("POST status = %d: %s", w.Code, w.Body.String())
	}
	var created Book
	if err := json.NewDecoder(w.Body).Decode(&created); err != nil {
		t.Fatal(err)
	}
	if created.ID == 0 || created.Title != "Dune" {
		t.Fatalf("unexpected book: %#v", created)
	}
	w = request(s, http.MethodGet, "/books/1", "")
	if w.Code != http.StatusOK {
		t.Fatalf("GET status = %d", w.Code)
	}
	var got Book
	_ = json.NewDecoder(w.Body).Decode(&got)
	if got != created {
		t.Fatalf("GET = %#v, want %#v", got, created)
	}
}

func TestAuthorFilterAndUpdate(t *testing.T) {
	s := testServer(t)
	request(s, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert"}`)
	request(s, http.MethodPost, "/books", `{"title":"Foundation","author":"Isaac Asimov"}`)
	w := request(s, http.MethodGet, "/books?author=Frank+Herbert", "")
	if w.Code != http.StatusOK || !strings.Contains(w.Body.String(), "Dune") || strings.Contains(w.Body.String(), "Foundation") {
		t.Fatalf("unexpected filter response: %d %s", w.Code, w.Body.String())
	}
	w = request(s, http.MethodPut, "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	if w.Code != http.StatusOK || !strings.Contains(w.Body.String(), "Dune Messiah") {
		t.Fatalf("unexpected update response: %d %s", w.Code, w.Body.String())
	}
}

func TestValidationDeleteAndHealth(t *testing.T) {
	s := testServer(t)
	if w := request(s, http.MethodPost, "/books", `{"title":"Only title"}`); w.Code != http.StatusBadRequest {
		t.Fatalf("validation status = %d", w.Code)
	}
	request(s, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert"}`)
	if w := request(s, http.MethodDelete, "/books/1", ""); w.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d", w.Code)
	}
	if w := request(s, http.MethodGet, "/books/1", ""); w.Code != http.StatusNotFound {
		t.Fatalf("get deleted status = %d", w.Code)
	}
	if w := request(s, http.MethodGet, "/health", ""); w.Code != http.StatusOK || !strings.Contains(w.Body.String(), `"status":"ok"`) {
		t.Fatalf("health response: %d %s", w.Code, w.Body.String())
	}
}
