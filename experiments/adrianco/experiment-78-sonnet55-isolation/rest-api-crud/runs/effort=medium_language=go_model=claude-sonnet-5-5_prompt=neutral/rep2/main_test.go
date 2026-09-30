package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	s, err := NewServer(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { s.Close() })
	return s.Handler()
}

func do(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	rec := do(newTestServer(t), "GET", "/health", "")
	if rec.Code != 200 {
		t.Fatalf("got %d", rec.Code)
	}
}

func TestCRUD(t *testing.T) {
	h := newTestServer(t)
	rec := do(h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}`)
	if rec.Code != 201 {
		t.Fatalf("create: %d %s", rec.Code, rec.Body)
	}
	var b Book
	json.Unmarshal(rec.Body.Bytes(), &b)
	if b.ID == 0 || b.Title != "Dune" {
		t.Fatalf("bad book %+v", b)
	}

	if rec = do(h, "GET", "/books/1", ""); rec.Code != 200 || !strings.Contains(rec.Body.String(), "Dune") {
		t.Fatalf("get: %d %s", rec.Code, rec.Body)
	}
	if rec = do(h, "PUT", "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`); rec.Code != 200 {
		t.Fatalf("put: %d", rec.Code)
	}
	if rec = do(h, "GET", "/books/1", ""); !strings.Contains(rec.Body.String(), "Dune Messiah") {
		t.Fatalf("update not persisted: %s", rec.Body)
	}
	if rec = do(h, "DELETE", "/books/1", ""); rec.Code != 204 {
		t.Fatalf("delete: %d", rec.Code)
	}
	if rec = do(h, "GET", "/books/1", ""); rec.Code != 404 {
		t.Fatalf("after delete: %d", rec.Code)
	}
	if rec = do(h, "PUT", "/books/1", `{"title":"a","author":"b"}`); rec.Code != 404 {
		t.Fatalf("put missing: %d", rec.Code)
	}
	if rec = do(h, "DELETE", "/books/1", ""); rec.Code != 404 {
		t.Fatalf("delete missing: %d", rec.Code)
	}
}

func TestValidation(t *testing.T) {
	h := newTestServer(t)
	for _, body := range []string{`{"author":"a"}`, `{"title":"t"}`, `{"title":"  ","author":"a"}`, `not json`, `{"title":"t","author":"a","year":-1}`} {
		if rec := do(h, "POST", "/books", body); rec.Code != 400 {
			t.Errorf("%q: got %d", body, rec.Code)
		}
	}
	if rec := do(h, "GET", "/books/abc", ""); rec.Code != 400 {
		t.Errorf("bad id: got %d", rec.Code)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	h := newTestServer(t)
	if rec := do(h, "GET", "/books", ""); strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Fatalf("empty list should be []: %s", rec.Body)
	}
	do(h, "POST", "/books", `{"title":"A","author":"X"}`)
	do(h, "POST", "/books", `{"title":"B","author":"Y"}`)
	do(h, "POST", "/books", `{"title":"C","author":"X"}`)

	var all, filtered []Book
	json.Unmarshal(do(h, "GET", "/books", "").Body.Bytes(), &all)
	json.Unmarshal(do(h, "GET", "/books?author=x", "").Body.Bytes(), &filtered)
	if len(all) != 3 || len(filtered) != 2 {
		t.Fatalf("all=%d filtered=%d", len(all), len(filtered))
	}
}
