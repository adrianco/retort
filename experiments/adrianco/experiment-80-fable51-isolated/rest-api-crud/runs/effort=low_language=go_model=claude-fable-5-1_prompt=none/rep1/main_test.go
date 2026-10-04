package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newTestHandler(t *testing.T) http.Handler {
	t.Helper()
	db, err := OpenDB(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return NewServer(db).Handler()
}

func do(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(method, path, strings.NewReader(body)))
	return rec
}

func TestHealth(t *testing.T) {
	rec := do(newTestHandler(t), "GET", "/health", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"ok"`) {
		t.Fatalf("got %d %s", rec.Code, rec.Body)
	}
}

func TestCRUD(t *testing.T) {
	h := newTestHandler(t)

	rec := do(h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: got %d %s", rec.Code, rec.Body)
	}
	var b Book
	if err := json.Unmarshal(rec.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	if b.ID == 0 || b.Title != "Dune" || b.Year != 1965 {
		t.Fatalf("unexpected book: %+v", b)
	}

	rec = do(h, "GET", "/books/1", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "Dune") {
		t.Fatalf("get: got %d %s", rec.Code, rec.Body)
	}

	rec = do(h, "PUT", "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("update: got %d %s", rec.Code, rec.Body)
	}
	rec = do(h, "GET", "/books/1", "")
	if !strings.Contains(rec.Body.String(), "Dune Messiah") {
		t.Fatalf("update not persisted: %s", rec.Body)
	}

	if rec = do(h, "DELETE", "/books/1", ""); rec.Code != http.StatusNoContent {
		t.Fatalf("delete: got %d", rec.Code)
	}
	if rec = do(h, "GET", "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete: got %d", rec.Code)
	}
}

func TestValidation(t *testing.T) {
	h := newTestHandler(t)
	for _, body := range []string{`{"author":"A"}`, `{"title":"T"}`, `{"title":"  ","author":"A"}`, `not json`} {
		if rec := do(h, "POST", "/books", body); rec.Code != http.StatusBadRequest {
			t.Errorf("body %q: got %d, want 400", body, rec.Code)
		}
	}
	do(h, "POST", "/books", `{"title":"T","author":"A"}`)
	if rec := do(h, "PUT", "/books/1", `{"title":"","author":"A"}`); rec.Code != http.StatusBadRequest {
		t.Errorf("invalid update: got %d, want 400", rec.Code)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	h := newTestHandler(t)

	rec := do(h, "GET", "/books", "")
	if rec.Code != http.StatusOK || strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Fatalf("empty list: got %d %s", rec.Code, rec.Body)
	}

	do(h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert"}`)
	do(h, "POST", "/books", `{"title":"Emma","author":"Jane Austen"}`)
	do(h, "POST", "/books", `{"title":"Persuasion","author":"Jane Austen"}`)

	var books []Book
	json.Unmarshal(do(h, "GET", "/books", "").Body.Bytes(), &books)
	if len(books) != 3 {
		t.Fatalf("list: got %d books, want 3", len(books))
	}
	json.Unmarshal(do(h, "GET", "/books?author=Jane+Austen", "").Body.Bytes(), &books)
	if len(books) != 2 {
		t.Fatalf("filter: got %d books, want 2", len(books))
	}
}

func TestNotFoundAndBadID(t *testing.T) {
	h := newTestHandler(t)
	if rec := do(h, "GET", "/books/99", ""); rec.Code != http.StatusNotFound {
		t.Errorf("get: got %d", rec.Code)
	}
	if rec := do(h, "PUT", "/books/99", `{"title":"T","author":"A"}`); rec.Code != http.StatusNotFound {
		t.Errorf("put: got %d", rec.Code)
	}
	if rec := do(h, "DELETE", "/books/99", ""); rec.Code != http.StatusNotFound {
		t.Errorf("delete: got %d", rec.Code)
	}
	if rec := do(h, "GET", "/books/abc", ""); rec.Code != http.StatusBadRequest {
		t.Errorf("bad id: got %d", rec.Code)
	}
}
