package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func setup(t *testing.T) http.Handler {
	t.Helper()
	s, err := NewStore(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { s.Close() })
	return newHandler(s)
}

func do(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	w := httptest.NewRecorder()
	h.ServeHTTP(w, req)
	return w
}

func TestHealth(t *testing.T) {
	w := do(setup(t), "GET", "/health", "")
	if w.Code != 200 {
		t.Fatalf("got %d", w.Code)
	}
}

func TestCRUD(t *testing.T) {
	h := setup(t)
	w := do(h, "POST", "/books", `{"title":"Dune","author":"Herbert","year":1965,"isbn":"123"}`)
	if w.Code != 201 {
		t.Fatalf("create: %d %s", w.Code, w.Body)
	}
	var b Book
	json.Unmarshal(w.Body.Bytes(), &b)
	if b.ID == 0 || b.Title != "Dune" {
		t.Fatalf("bad book %+v", b)
	}
	if w = do(h, "GET", "/books/1", ""); w.Code != 200 {
		t.Fatalf("get: %d", w.Code)
	}
	w = do(h, "PUT", "/books/1", `{"title":"Dune II","author":"Herbert","year":1969,"isbn":"123"}`)
	if w.Code != 200 || !strings.Contains(w.Body.String(), "Dune II") {
		t.Fatalf("update: %d %s", w.Code, w.Body)
	}
	if w = do(h, "DELETE", "/books/1", ""); w.Code != 204 {
		t.Fatalf("delete: %d", w.Code)
	}
	if w = do(h, "GET", "/books/1", ""); w.Code != 404 {
		t.Fatalf("get after delete: %d", w.Code)
	}
	if w = do(h, "DELETE", "/books/1", ""); w.Code != 404 {
		t.Fatalf("second delete: %d", w.Code)
	}
}

func TestValidation(t *testing.T) {
	h := setup(t)
	for _, body := range []string{`{"author":"A"}`, `{"title":"T"}`, `{"title":"  ","author":"A"}`, `nope`} {
		if w := do(h, "POST", "/books", body); w.Code != 400 {
			t.Errorf("%s: got %d", body, w.Code)
		}
	}
	if w := do(h, "PUT", "/books/1", `{"title":"T"}`); w.Code != 400 {
		t.Errorf("put invalid: %d", w.Code)
	}
	if w := do(h, "PUT", "/books/9", `{"title":"T","author":"A"}`); w.Code != 404 {
		t.Errorf("put missing: %d", w.Code)
	}
	if w := do(h, "GET", "/books/abc", ""); w.Code != 400 {
		t.Errorf("bad id: %d", w.Code)
	}
}

func TestListFilter(t *testing.T) {
	h := setup(t)
	do(h, "POST", "/books", `{"title":"A","author":"X"}`)
	do(h, "POST", "/books", `{"title":"B","author":"Y"}`)
	var all, xs []Book
	json.Unmarshal(do(h, "GET", "/books", "").Body.Bytes(), &all)
	json.Unmarshal(do(h, "GET", "/books?author=X", "").Body.Bytes(), &xs)
	if len(all) != 2 || len(xs) != 1 || xs[0].Title != "A" {
		t.Fatalf("all=%v xs=%v", all, xs)
	}
	w := do(h, "GET", "/books?author=Nobody", "")
	if strings.TrimSpace(w.Body.String()) != "[]" {
		t.Fatalf("expected empty array, got %s", w.Body)
	}
}
