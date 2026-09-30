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

func setup(t *testing.T) http.Handler {
	s, err := NewServer(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	return s.Handler()
}

func TestHealth(t *testing.T) {
	if w := do(t, setup(t), "GET", "/health", ""); w.Code != 200 {
		t.Fatalf("got %d", w.Code)
	}
}

func TestCRUD(t *testing.T) {
	h := setup(t)
	w := do(t, h, "POST", "/books", `{"title":"Dune","author":"Herbert","year":1965,"isbn":"1"}`)
	if w.Code != 201 || !strings.Contains(w.Body.String(), `"id":1`) {
		t.Fatalf("create: %d %s", w.Code, w.Body)
	}
	if w = do(t, h, "GET", "/books/1", ""); w.Code != 200 || !strings.Contains(w.Body.String(), "Dune") {
		t.Fatalf("get: %d %s", w.Code, w.Body)
	}
	if w = do(t, h, "PUT", "/books/1", `{"title":"Dune II","author":"Herbert"}`); w.Code != 200 || !strings.Contains(w.Body.String(), "Dune II") {
		t.Fatalf("put: %d %s", w.Code, w.Body)
	}
	if w = do(t, h, "DELETE", "/books/1", ""); w.Code != 204 {
		t.Fatalf("delete: %d", w.Code)
	}
	if w = do(t, h, "GET", "/books/1", ""); w.Code != 404 {
		t.Fatalf("get after delete: %d", w.Code)
	}
	if w = do(t, h, "PUT", "/books/1", `{"title":"a","author":"b"}`); w.Code != 404 {
		t.Fatalf("put missing: %d", w.Code)
	}
}

func TestValidation(t *testing.T) {
	h := setup(t)
	for _, body := range []string{`{"author":"x"}`, `{"title":"x"}`, `{"title":" ","author":"x"}`, `nope`} {
		if w := do(t, h, "POST", "/books", body); w.Code != 400 {
			t.Errorf("%s: got %d", body, w.Code)
		}
	}
	if w := do(t, h, "GET", "/books/abc", ""); w.Code != 400 {
		t.Errorf("bad id: %d", w.Code)
	}
}

func TestListFilter(t *testing.T) {
	h := setup(t)
	do(t, h, "POST", "/books", `{"title":"A","author":"X"}`)
	do(t, h, "POST", "/books", `{"title":"B","author":"Y"}`)
	w := do(t, h, "GET", "/books?author=X", "")
	if w.Code != 200 || !strings.Contains(w.Body.String(), `"A"`) || strings.Contains(w.Body.String(), `"B"`) {
		t.Fatalf("filter: %s", w.Body)
	}
	if w = do(t, h, "GET", "/books", ""); strings.Count(w.Body.String(), `"id"`) != 2 {
		t.Fatalf("list: %s", w.Body)
	}
}
