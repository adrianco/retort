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

func newH(t *testing.T) http.Handler {
	s, err := NewServer(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	return s.Routes()
}

func TestHealth(t *testing.T) {
	if w := do(t, newH(t), "GET", "/health", ""); w.Code != 200 {
		t.Fatal(w.Code)
	}
}

func TestCRUD(t *testing.T) {
	h := newH(t)
	w := do(t, h, "POST", "/books", `{"title":"Dune","author":"Herbert","year":1965,"isbn":"1"}`)
	if w.Code != 201 || !strings.Contains(w.Body.String(), `"id":1`) {
		t.Fatal(w.Code, w.Body)
	}
	if w = do(t, h, "GET", "/books/1", ""); w.Code != 200 || !strings.Contains(w.Body.String(), "Dune") {
		t.Fatal(w.Code, w.Body)
	}
	if w = do(t, h, "PUT", "/books/1", `{"title":"Dune 2","author":"Herbert"}`); w.Code != 200 || !strings.Contains(w.Body.String(), "Dune 2") {
		t.Fatal(w.Code, w.Body)
	}
	if w = do(t, h, "DELETE", "/books/1", ""); w.Code != 204 {
		t.Fatal(w.Code)
	}
	if w = do(t, h, "GET", "/books/1", ""); w.Code != 404 {
		t.Fatal(w.Code)
	}
	if w = do(t, h, "DELETE", "/books/1", ""); w.Code != 404 {
		t.Fatal(w.Code)
	}
}

func TestValidation(t *testing.T) {
	h := newH(t)
	for _, body := range []string{`{"author":"a"}`, `{"title":"t"}`, `{"title":" ","author":"a"}`, `nope`} {
		if w := do(t, h, "POST", "/books", body); w.Code != 400 {
			t.Errorf("%s: got %d", body, w.Code)
		}
	}
	if w := do(t, h, "GET", "/books/abc", ""); w.Code != 400 {
		t.Error(w.Code)
	}
	if w := do(t, h, "PUT", "/books/9", `{"title":"t","author":"a"}`); w.Code != 404 {
		t.Error(w.Code)
	}
}

func TestListFilter(t *testing.T) {
	h := newH(t)
	do(t, h, "POST", "/books", `{"title":"A","author":"X"}`)
	do(t, h, "POST", "/books", `{"title":"B","author":"Y"}`)
	w := do(t, h, "GET", "/books?author=X", "")
	if w.Code != 200 || !strings.Contains(w.Body.String(), `"A"`) || strings.Contains(w.Body.String(), `"B"`) {
		t.Fatal(w.Body)
	}
	if w = do(t, h, "GET", "/books", ""); strings.Count(w.Body.String(), `"id"`) != 2 {
		t.Fatal(w.Body)
	}
}
