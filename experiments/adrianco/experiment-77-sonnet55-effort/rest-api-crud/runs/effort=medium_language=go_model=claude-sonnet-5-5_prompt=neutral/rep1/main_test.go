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
	return NewHandler(s)
}

func do(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	if rec := do(setup(t), "GET", "/health", ""); rec.Code != 200 {
		t.Fatalf("got %d", rec.Code)
	}
}

func TestCRUD(t *testing.T) {
	h := setup(t)
	rec := do(h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}`)
	if rec.Code != 201 {
		t.Fatalf("create: %d %s", rec.Code, rec.Body)
	}
	var b Book
	json.Unmarshal(rec.Body.Bytes(), &b)
	if b.ID != 1 || b.Title != "Dune" {
		t.Fatalf("bad book %+v", b)
	}

	rec = do(h, "GET", "/books/1", "")
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), "Frank Herbert") {
		t.Fatalf("get: %d %s", rec.Code, rec.Body)
	}

	rec = do(h, "PUT", "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"456"}`)
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), "Dune Messiah") {
		t.Fatalf("update: %d %s", rec.Code, rec.Body)
	}
	if rec = do(h, "GET", "/books/1", ""); !strings.Contains(rec.Body.String(), "1969") {
		t.Fatalf("update not persisted: %s", rec.Body)
	}

	if rec = do(h, "DELETE", "/books/1", ""); rec.Code != 204 {
		t.Fatalf("delete: %d", rec.Code)
	}
	if rec = do(h, "GET", "/books/1", ""); rec.Code != 404 {
		t.Fatalf("after delete: %d", rec.Code)
	}
	if rec = do(h, "DELETE", "/books/1", ""); rec.Code != 404 {
		t.Fatalf("delete missing: %d", rec.Code)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	h := setup(t)
	if rec := do(h, "GET", "/books", ""); strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Fatalf("empty list should be []: %s", rec.Body)
	}
	do(h, "POST", "/books", `{"title":"A","author":"X"}`)
	do(h, "POST", "/books", `{"title":"B","author":"Y"}`)
	do(h, "POST", "/books", `{"title":"C","author":"X"}`)

	var all, xs []Book
	json.Unmarshal(do(h, "GET", "/books", "").Body.Bytes(), &all)
	json.Unmarshal(do(h, "GET", "/books?author=X", "").Body.Bytes(), &xs)
	if len(all) != 3 || len(xs) != 2 {
		t.Fatalf("all=%d xs=%d", len(all), len(xs))
	}
}

func TestValidation(t *testing.T) {
	h := setup(t)
	cases := []struct {
		method, path, body string
		want               int
	}{
		{"POST", "/books", `{"author":"X"}`, 400},
		{"POST", "/books", `{"title":"T","author":"  "}`, 400},
		{"POST", "/books", `not json`, 400},
		{"POST", "/books", `{"title":"T","author":"A","year":-1}`, 400},
		{"PUT", "/books/1", `{"title":"T"}`, 400},
		{"PUT", "/books/99", `{"title":"T","author":"A"}`, 404},
		{"GET", "/books/abc", "", 400},
		{"GET", "/books/42", "", 404},
	}
	for _, c := range cases {
		if rec := do(h, c.method, c.path, c.body); rec.Code != c.want {
			t.Errorf("%s %s %q: got %d want %d", c.method, c.path, c.body, rec.Code, c.want)
		}
	}
}
