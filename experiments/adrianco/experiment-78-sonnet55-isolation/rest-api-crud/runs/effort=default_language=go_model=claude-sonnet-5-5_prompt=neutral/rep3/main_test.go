package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	w := httptest.NewRecorder()
	h.ServeHTTP(w, req)
	return w
}

func newHandler(t *testing.T) http.Handler {
	s, err := NewServer(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	return s.Handler()
}

func TestHealth(t *testing.T) {
	if w := do(t, newHandler(t), "GET", "/health", ""); w.Code != 200 {
		t.Fatalf("got %d", w.Code)
	}
}

func TestCRUD(t *testing.T) {
	h := newHandler(t)
	w := do(t, h, "POST", "/books", `{"title":"Dune","author":"Herbert","year":1965,"isbn":"123"}`)
	if w.Code != 201 || !strings.Contains(w.Body.String(), `"id":1`) {
		t.Fatalf("create: %d %s", w.Code, w.Body)
	}
	if w = do(t, h, "GET", "/books/1", ""); w.Code != 200 || !strings.Contains(w.Body.String(), "Dune") {
		t.Fatalf("get: %d %s", w.Code, w.Body)
	}
	if w = do(t, h, "PUT", "/books/1", `{"title":"Dune II","author":"Herbert"}`); w.Code != 200 || !strings.Contains(w.Body.String(), "Dune II") {
		t.Fatalf("update: %d %s", w.Code, w.Body)
	}
	if w = do(t, h, "DELETE", "/books/1", ""); w.Code != 204 {
		t.Fatalf("delete: %d", w.Code)
	}
	if w = do(t, h, "GET", "/books/1", ""); w.Code != 404 {
		t.Fatalf("after delete: %d", w.Code)
	}
	if w = do(t, h, "PUT", "/books/1", `{"title":"a","author":"b"}`); w.Code != 404 {
		t.Fatalf("update missing: %d", w.Code)
	}
	if w = do(t, h, "DELETE", "/books/1", ""); w.Code != 404 {
		t.Fatalf("delete missing: %d", w.Code)
	}
}

func TestValidation(t *testing.T) {
	h := newHandler(t)
	for _, body := range []string{`{"author":"x"}`, `{"title":"x"}`, `{"title":" ","author":"x"}`, `not json`, `{"title":"x","author":"y","year":-1}`} {
		if w := do(t, h, "POST", "/books", body); w.Code != 400 {
			t.Errorf("%s: got %d", body, w.Code)
		}
	}
	if w := do(t, h, "GET", "/books/abc", ""); w.Code != 400 {
		t.Errorf("bad id: %d", w.Code)
	}
}

func TestListFilter(t *testing.T) {
	h := newHandler(t)
	if w := do(t, h, "GET", "/books", ""); strings.TrimSpace(w.Body.String()) != "[]" {
		t.Fatalf("empty list: %s", w.Body)
	}
	do(t, h, "POST", "/books", `{"title":"A","author":"X"}`)
	do(t, h, "POST", "/books", `{"title":"B","author":"Y"}`)
	do(t, h, "POST", "/books", `{"title":"C","author":"X"}`)
	w := do(t, h, "GET", "/books?author=X", "")
	if strings.Count(w.Body.String(), `"id"`) != 2 || strings.Contains(w.Body.String(), `"B"`) {
		t.Fatalf("filter: %s", w.Body)
	}
	if w = do(t, h, "GET", "/books", ""); strings.Count(w.Body.String(), `"id"`) != 3 {
		t.Fatalf("all: %s", w.Body)
	}
}
