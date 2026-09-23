package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	s, err := NewStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { s.Close() })
	return NewServer(s)
}

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, "GET", "/health", "")
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), `"ok"`) {
		t.Fatalf("got %d %s", rec.Code, rec.Body)
	}
}

func TestCRUDLifecycle(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: %d %s", rec.Code, rec.Body)
	}
	var b Book
	json.Unmarshal(rec.Body.Bytes(), &b)
	if b.ID == 0 || b.Title != "Dune" || b.Year != 1965 {
		t.Fatalf("bad book %+v", b)
	}

	rec = do(t, h, "GET", "/books/1", "")
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), "Dune") {
		t.Fatalf("get: %d %s", rec.Code, rec.Body)
	}

	rec = do(t, h, "PUT", "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), "Messiah") {
		t.Fatalf("update: %d %s", rec.Code, rec.Body)
	}

	if rec = do(t, h, "DELETE", "/books/1", ""); rec.Code != http.StatusNoContent {
		t.Fatalf("delete: %d", rec.Code)
	}
	if rec = do(t, h, "GET", "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete: %d", rec.Code)
	}
	if rec = do(t, h, "DELETE", "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("second delete: %d", rec.Code)
	}
}

func TestValidation(t *testing.T) {
	h := newTestServer(t)
	cases := map[string]string{
		"missing title":  `{"author":"A"}`,
		"missing author": `{"title":"T"}`,
		"blank title":    `{"title":"  ","author":"A"}`,
		"bad json":       `{`,
		"unknown field":  `{"title":"T","author":"A","x":1}`,
	}
	for name, body := range cases {
		if rec := do(t, h, "POST", "/books", body); rec.Code != http.StatusBadRequest {
			t.Errorf("%s: got %d", name, rec.Code)
		}
	}
	do(t, h, "POST", "/books", `{"title":"T","author":"A"}`)
	if rec := do(t, h, "PUT", "/books/1", `{"title":""}`); rec.Code != http.StatusBadRequest {
		t.Errorf("put invalid: %d", rec.Code)
	}
	if rec := do(t, h, "PUT", "/books/99", `{"title":"T","author":"A"}`); rec.Code != http.StatusNotFound {
		t.Errorf("put missing: %d", rec.Code)
	}
	if rec := do(t, h, "GET", "/books/abc", ""); rec.Code != http.StatusBadRequest {
		t.Errorf("bad id: %d", rec.Code)
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, "GET", "/books", "")
	if rec.Code != 200 || strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Fatalf("empty list: %d %s", rec.Code, rec.Body)
	}
	do(t, h, "POST", "/books", `{"title":"Emma","author":"Jane Austen"}`)
	do(t, h, "POST", "/books", `{"title":"Persuasion","author":"Jane Austen"}`)
	do(t, h, "POST", "/books", `{"title":"Ulysses","author":"James Joyce"}`)

	var all, filtered []Book
	json.Unmarshal(do(t, h, "GET", "/books", "").Body.Bytes(), &all)
	json.Unmarshal(do(t, h, "GET", "/books?author=jane%20austen", "").Body.Bytes(), &filtered)
	if len(all) != 3 || len(filtered) != 2 {
		t.Fatalf("all=%d filtered=%d", len(all), len(filtered))
	}
}
